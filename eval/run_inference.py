"""E3 driver: run the LLM scope proposal once per (task, inference model, variant) and cache it.
Deterministic post-processing (k, FK closure, linking on/off) is applied later from the cached proposal.

Variants:  main   = schema with descriptions (semantic layer)  [model: --model]
           nodesc = schema without descriptions; linking disabled at assembly (ablation 'no semantic layer')
Output: eval/results/proposals_<model>_<variant>.jsonl  (resumable)
"""
import argparse, json, os, sys, time, subprocess, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tse import semantic_layer, infer, config
from tse.llm import LLM, model_digest


def commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=config.ROOT).decode().strip()
    except Exception:
        return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--variant", default="main", choices=["main", "nodesc", "nohint"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tasks", default=os.path.join(config.DATA, "tasks", "tasks.jsonl"))
    a = ap.parse_args()
    tasks = [json.loads(l) for l in open(a.tasks)][: a.limit]
    if a.variant == "nohint":
        tasks = [t for t in tasks if t.get("evidence")]   # only tasks that carry a benchmark hint
    out = os.path.join(config.RESULTS, f"proposals_{a.model.replace(':', '_').replace('/', '_')}_{a.variant}.jsonl")
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["task_id"] for l in open(out)}
    if a.model.startswith("claude-"):
        from tse.claude_llm import ClaudeLLM
        llm = ClaudeLLM(a.model)
    else:
        llm = LLM(a.model, temperature=0.0, seed=0)
    c = commit()
    with open(out, "a") as f:
        for t in tasks:
            if t["task_id"] in done:
                continue
            sl = semantic_layer.get(t["pgdb"], t["dataset"], t["db_id"], use_descriptions=(a.variant == "main"))
            t0 = time.perf_counter()
            n0 = len(llm.calls)
            tt = dict(t, evidence="") if a.variant == "nohint" else t   # D9: broker sees the question only
            prop = infer.llm_propose(tt, sl, llm)
            rec = {"task_id": t["task_id"], "model": a.model, "model_digest": a.model if a.model.startswith("claude-") else model_digest(a.model), "variant": a.variant,
                   "proposal": {"tables": prop["tables"], "columns": [list(x) for x in prop["columns"]], "filters": prop["filters"],
                                "parse_error": prop["parse_error"]},
                   "raw": prop["raw"][:4000], "latency_ms": 1000 * (time.perf_counter() - t0),
                   "usage": llm.calls[n0:], "commit": c, "timestamp": datetime.datetime.now().isoformat()}
            f.write(json.dumps(rec) + "\n"); f.flush()


if __name__ == "__main__":
    main()
