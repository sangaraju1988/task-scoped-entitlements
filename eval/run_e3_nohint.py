"""D9 (exploratory, after round-2 internal review): scope inference without the BIRD 'evidence' hint.

For every permitted task that carries a hint, compile the tse_nohint scope (proposal from the question only;
grounding also sees the question only) and measure sufficiency by execution, column precision/recall and OER,
exactly as eval/run_e1_e3.py does for the other variants. Output: eval/results/e3_nohint.jsonl.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eval.common import load_tasks, load_prep, entitlement, tse_scope
from tse import config, metrics
from tse.scope import Scope
from tse.compile import Broker


def main():
    sub = {l.strip() for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "subset_nohint_200.txt")) if l.strip()}
    tasks = [t for t in load_tasks() if t.get("evidence") and t["task_id"] in sub]   # fixed random 200 (seed 20261128)
    prep = load_prep()
    out = os.path.join(config.RESULTS, "e3_nohint.jsonl")
    done = {json.loads(l)["task_id"] for l in open(out)} if os.path.exists(out) else set()
    brokers = {}
    with open(out, "a") as f:
        for t in sorted(tasks, key=lambda x: (x["pgdb"], x["task_id"])):
            if t["task_id"] in done:
                continue
            role = prep[t["task_id"]]["role_permitted"]
            E = entitlement(t, role)
            N = Scope.from_json(prep[t["task_id"]]["gold_scope"])
            try:
                s = tse_scope(t, role, "tse_nohint", E)
            except KeyError:
                continue
            b = brokers.setdefault(t["pgdb"], Broker(t["pgdb"]))
            suf, err = metrics.sufficiency(t, s, role, b)
            p, rc = metrics.col_pr(s, N)
            r = {"task_id": t["task_id"], "dataset": t["dataset"], "sufficient": suf, "suff_err": err, "precision": p, "recall": rc}
            r.update(metrics.oer(s, N, E, t["pgdb"]))
            f.write(json.dumps(r) + "\n"); f.flush()
    for b in brokers.values():
        b.close()


if __name__ == "__main__":
    main()
