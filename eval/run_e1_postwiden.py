"""E1 supplement (added after internal review, deviation D7): exposure of the scope an agent actually ended with.

For every E2 TSE run (Haiku 5.5, Sonnet 5.5) compute OER_col/row/cell of the run's final reach S'(t) = initial
scope plus approved widenings (recorded as `final_scope` in the run). Runs without an approved widening have
S'(t) = S(t); their OER is computed the same way so the file is self-contained.
Output: eval/results/e1_postwiden.jsonl (one record per run).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eval.common import load_tasks, load_prep, entitlement
from tse import config, metrics
from tse.scope import Scope


def main():
    tasks = {t["task_id"]: t for t in load_tasks()}
    prep = load_prep()
    out = os.path.join(config.RESULTS, "e1_postwiden.jsonl")
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["run_id"] for l in open(out)}
    cache = {}
    with open(out, "a") as f:
        for name in ("runs_e2_haiku.jsonl", "runs_e2_sonnet_r.jsonl"):
            for l in open(os.path.join(config.RESULTS, name)):
                r = json.loads(l)
                if r["condition"] != "TSE" or r["run_id"] in done or not r.get("final_scope"):
                    continue
                t = tasks[r["task_id"]]
                key = (r["task_id"], json.dumps(r["final_scope"], sort_keys=True))
                if key not in cache:
                    E = entitlement(t, r["role"])
                    N = Scope.from_json(prep[r["task_id"]]["gold_scope"])
                    cache[key] = metrics.oer(Scope.from_json(r["final_scope"]), N, E, t["pgdb"])
                o = cache[key]
                f.write(json.dumps({"run_id": r["run_id"], "exp": r["exp"], "model": r["model"], "task_id": r["task_id"],
                                    "dataset": t["dataset"], "role": r["role"], "widened": r.get("n_widen_approved", 0) > 0,
                                    "oer_col": o["oer_col"], "oer_row": o["oer_row"], "oer_cell": o["oer_cell"]}) + "\n")
                f.flush()


if __name__ == "__main__":
    main()
