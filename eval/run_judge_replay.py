"""D10 (exploratory): offline evaluation of widening-approval policies on logged requests.

Items: (a) every column granted under 'auto' in E2 TSE runs (Haiku 5.5, Sonnet 5.5), labelled needed iff it is in
the gold scope N(t); (b) every canary column granted under 'auto'/'strict' in the widening-abuse runs (never needed).
Policies scored: lexical grounding (broker linker on the original task) and an LLM judge (tse/approval_judge.py).
Output: eval/results/judge_replay.jsonl (one record per unique (task, column)).
"""
import json, os, sys, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eval.common import load_tasks, load_prep
from tse import config, semantic_layer
from tse.scope import Scope
from tse.infer import link_columns, task_text
from tse.approval_judge import judge


def main():
    T = {t["task_id"]: t for t in load_tasks()}
    prep = load_prep()
    inj = {json.loads(l)["task_id"]: json.loads(l) for l in open(os.path.join(config.RESULTS, "injections_widen.jsonl"))}
    items = {}
    for f in ("runs_e2_haiku.jsonl", "runs_e2_sonnet_r.jsonl"):
        for l in open(os.path.join(config.RESULTS, f)):
            r = json.loads(l)
            if r["condition"] != "TSE":
                continue
            N = Scope.from_json(prep[r["task_id"]]["gold_scope"])
            for a in r.get("audit", []):
                for gc in a.get("granted_columns", []):
                    t, c = gc.split(".", 1)
                    items.setdefault((r["task_id"], gc), {"kind": "legit", "needed": t in N.tables and c in N.tables[t].columns})
    for f in ("runs_e5wid_haiku.jsonl", "runs_e5wid_sonnet.jsonl"):
        for l in open(os.path.join(config.RESULTS, f)):
            r = json.loads(l)
            cc = inj[r["task_id"]]["canary_table"] + "." + inj[r["task_id"]]["canary_column"]
            if any(cc in a.get("granted_columns", []) for a in r.get("audit", [])):
                items.setdefault((r["task_id"], cc), {"kind": "canary", "needed": False})
    out = os.path.join(config.RESULTS, "judge_replay.jsonl")
    done = {(x["task_id"], x["column"]) for x in map(json.loads, open(out))} if os.path.exists(out) else set()
    todo = [k for k in sorted(items) if k not in done]

    def one(k):
        tid, gc = k
        t = T[tid]; sl = semantic_layer.get(t["pgdb"], t["dataset"], t["db_id"])
        tb, c = gc.split(".", 1)
        lex = (tb, c) in link_columns(task_text(t), sl, {tb}, lenient=True)
        return dict(task_id=tid, column=gc, **items[k], lexical=lex, judge=judge(t, sl, tb, c))

    with open(out, "a") as f, cf.ThreadPoolExecutor(4) as ex:
        for rec in ex.map(one, todo):
            f.write(json.dumps(rec) + "\n"); f.flush()
    print("items", len(items), "new", len(todo))


if __name__ == "__main__":
    main()
