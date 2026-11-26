"""E2/E5 driver: real agent executions. One JSONL record per run (resumable by run_id).

Example:
  python eval/run_agents.py --exp e2 --set permitted --conditions B0,B1,B3,TSE \
      --cells qwen3:8b/react,qwen3:8b/lg,mistral-nemo:12b/react,mistral-nemo:12b/lg
"""
import argparse, json, os, sys, time, datetime, traceback, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eval.common import (commit, load_tasks, load_prep, entitlement, tse_scope, assign_cells, VARIANTS)
from tse import semantic_layer, config
from tse.compile import Broker
from tse.env import Env
from tse.widen import WideningPolicy
from tse.baselines import b1_curated_scope, b2_tool_gate
from tse.metrics import gold_result
from tse.datasets.tasks import results_match
from tse.llm import model_digest
from tse.agents import react, lg, claude_react

HARNESS = {"react": react, "lg": lg}


def harness(fw, model):
    if fw == "react" and model.startswith("claude-"):
        return claude_react
    return HARNESS[fw]


def is_refusal(final):
    if not final:
        return False
    return (not final.get("sql", "").strip()) or final.get("answer", "").strip().upper().startswith("REFUSE")


def scope_for(cond, task, role, E, all_tasks, sl, variant):
    if cond in ("TSE", "B3"):
        return tse_scope(task, role, variant, E)
    if cond == "B1":
        return b1_curated_scope(task, all_tasks, sl, E)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--set", default="permitted", choices=["permitted", "nonpermitted"])
    ap.add_argument("--conditions", default="B0,B1,B3,TSE")
    ap.add_argument("--cells", required=True, help="comma list model/framework")
    ap.add_argument("--variant", default="tse", help="TSE scope variant (eval/common.py VARIANTS)")
    ap.add_argument("--widen", default="auto", choices=["auto", "strict", "deny"])
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--subset", default=None, help="file with task_ids (one per line)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--injection", default=None, help="eval/injections.jsonl key mode (context|dbfield|widen)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()

    tasks = load_tasks(); prep = load_prep(); byid = {t["task_id"]: t for t in tasks}
    for t in tasks:
        t["fold"] = prep[t["task_id"]]["fold"]
    if a.set == "permitted":
        sel = [t for t in tasks if prep[t["task_id"]]["role_permitted"]]
        role_of = lambda t: prep[t["task_id"]]["role_permitted"]
    else:
        sel = [t for t in tasks if prep[t["task_id"]]["in_nonpermitted_set"]]
        role_of = lambda t: prep[t["task_id"]]["role_nonpermitted"]
    if a.subset:
        ids = [l.strip() for l in open(a.subset) if l.strip()]
        sel = [byid[i] for i in ids if i in byid]
    sel = sel[: a.limit] if a.limit else sel
    inj = {}
    if a.injection:
        inj = {json.loads(l)["task_id"]: json.loads(l) for l in open(os.path.join(config.RESULTS, f"injections_{a.injection}.jsonl"))}
        sel = [t for t in sel if t["task_id"] in inj]
    cells = [tuple(c.split("/")) for c in a.cells.split(",")]
    cellmap = assign_cells(sel, cells)
    conds = a.conditions.split(",")
    seeds = [int(s) for s in a.seeds.split(",")]
    out = a.out or os.path.join(config.RESULTS, f"runs_{a.exp}.jsonl")
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["run_id"] for l in open(out)}
    cm = commit()
    policy = WideningPolicy(a.widen)
    # order by database so prompt prefixes are reused by the model server
    sel = sorted(sel, key=lambda t: (t["pgdb"], t["task_id"]))
    import threading, concurrent.futures as cf
    from tse.agents.claude_react import BudgetExceeded
    lock = threading.Lock()
    local = threading.local()
    stop_flag = threading.Event()
    counter = {"n": 0}
    all_brokers = []
    f = open(out, "a")

    def broker_for(pgdb):
        """One broker connection per worker thread; switching database closes the previous one
        (after removing anything it provisioned), so connections stay bounded by the worker count."""
        cur = getattr(local, "broker", None)
        if cur is not None and cur.pgdb == pgdb:
            return cur
        if cur is not None:
            try:
                cur.cleanup_mine(); cur.close()
            except Exception:
                pass
            with lock:
                all_brokers.remove(cur)
        b = Broker(pgdb); local.broker = b
        with lock:
            all_brokers.append(b)
        return b

    def do_task(t):
        model, fw = cellmap[t["task_id"]]
        role = role_of(t)
        sl = semantic_layer.get(t["pgdb"], t["dataset"], t["db_id"])
        E = entitlement(t, role)
        ij = inj.get(t["task_id"])
        pgdb = ij["pgdb"] if ij and ij.get("pgdb") else t["pgdb"]
        for seed in seeds:
            for cond in conds:
                if stop_flag.is_set():
                    return
                run_id = hashlib.sha256(f"{a.exp}|{t['task_id']}|{cond}|{model}|{fw}|{seed}|{a.variant}|{a.widen}|{a.injection}".encode()).hexdigest()[:16]
                if run_id in done:
                    continue
                rec = {"run_id": run_id, "exp": a.exp, "task_id": t["task_id"], "dataset": t["dataset"], "db_id": t["db_id"],
                       "difficulty": t["difficulty"], "set": a.set, "role": role, "condition": cond, "variant": a.variant if cond in ("TSE", "B3") else None,
                       "widen_policy": a.widen if cond == "TSE" else None, "model": model, "model_digest": model if model.startswith("claude-") else model_digest(model),
                       "framework": fw, "seed": seed, "temperature": a.temperature, "injection": a.injection,
                       "commit": cm, "timestamp": datetime.datetime.now().isoformat()}
                env = None
                try:
                    scope = scope_for(cond, t, role, E, tasks, sl, a.variant)
                    rec["scope"] = scope.to_json() if scope is not None else None
                    if cond == "B2":
                        rec["b2_allowed_tools"] = b2_tool_gate(t)
                    env = Env(t, cond, sl, E, role, scope=scope, widening_policy=policy if cond == "TSE" else None,
                              broker=broker_for(pgdb), pgdb_override=pgdb)
                    rec["setup_ms"] = env.setup_ms
                    r = harness(fw, model).run(env, t, model, temperature=a.temperature, seed=seed,
                                               injection=(ij or {}).get("context_text", ""))
                    final = r["final"]
                    res, err = env.evaluate_sql((final or {}).get("sql", ""))
                    g = gold_result(t)
                    rec.update(final=final, ex=bool(results_match(res, g)) if not ij else None, eval_error=err,
                               refusal=is_refusal(final), no_final=final is None, steps=r["steps"], usage=r["usage"],
                               agent_wall_s=r["wall_s"], harness_error=r.get("error"), stop_reason=r.get("stop_reason"),
                               queries=[{k: q.get(k) for k in ("sql", "ok", "error", "n_shown", "ms", "columns")} for q in env.queries],
                               query_results=[q.get("result_text", "")[:1500] for q in env.queries] if ij else None,
                               audit=env.audit, final_scope=env.reach.to_json() if cond in ("TSE", "B1") else None,
                               n_widen_requests=len(env.audit), n_widen_approved=env.n_approved)
                    if ij:
                        rec["transcript_tail"] = json.dumps(r["transcript"][-6:], default=str)[:6000]
                except BudgetExceeded as e:
                    stop_flag.set()
                    print("STOP:", e, flush=True)
                    if env is not None:
                        env.close()
                    return
                except Exception as e:
                    rec.update(error=type(e).__name__ + ": " + str(e)[:300], traceback=traceback.format_exc()[-1500:])
                finally:
                    if env is not None:
                        env.close()
                        if env.handle is not None:
                            rec["teardown_ms"] = env.handle.timings.get("teardown_ms")
                            rec["compile_ms"] = env.handle.timings.get("compile_ms")
                            rec["n_db_objects"] = env.handle.n_objects
                if "error" in rec or "final" in rec:
                    with lock:
                        f.write(json.dumps(rec, default=str) + "\n"); f.flush()
                        counter["n"] += 1

    if a.workers <= 1:
        for t in sel:
            do_task(t)
    else:
        with cf.ThreadPoolExecutor(a.workers) as ex:
            list(ex.map(do_task, sel))
    f.close()
    n_new = counter["n"]
    left = 0
    for b in all_brokers:
        try:
            left += b.cleanup_mine()
        except Exception:
            pass
        b.close()
    print("leftover task objects removed by this batch:", left)
    print("new runs:", n_new)


if __name__ == "__main__":
    main()
