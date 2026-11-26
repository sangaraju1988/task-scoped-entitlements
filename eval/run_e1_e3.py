"""E1 (over-exposure) and E3 (scope-inference quality), scope level, all permitted tasks.

For each task (assigned permitted role) and each scope source, compute: sufficiency (by execution, for
broker-compiled scopes), column precision/recall vs N(t), and OER_col/row/cell of the *reach*.
Reach: B0 = B2 = B3 = E(u); B1 = curated ∩ E(u); TSE variants = S(t) ∩ E(u).
Also: sensitivity of OER to the policy generator (seeds 1-3 × frac 0.10/0.25/0.40) using the column-only
'restricted' role (no execution needed: permitted iff N(t) ⊆ E columns).
Output: eval/results/e1e3_scopes.jsonl, eval/results/e1_sensitivity.jsonl
"""
import json, os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eval.common import load_tasks, load_prep, entitlement, tse_scope, VARIANTS, commit
from tse import semantic_layer, config, metrics
from tse.scope import Scope
from tse.compile import Broker
from tse.baselines import b1_curated_scope
from tse.policies.generate import generate


def main():
    tasks = load_tasks(); prep = load_prep()
    for t in tasks:
        t["fold"] = prep[t["task_id"]]["fold"]
    out = os.path.join(config.RESULTS, "e1e3_scopes.jsonl")
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["task_id"] for l in open(out)}
    brokers = {}
    cm = commit()
    with open(out, "a") as f:
        for t in sorted(tasks, key=lambda x: (x["pgdb"], x["task_id"])):
            if t["task_id"] in done:
                continue
            role = prep[t["task_id"]]["role_permitted"]
            sl = semantic_layer.get(t["pgdb"], t["dataset"], t["db_id"])
            E = entitlement(t, role)
            N = Scope.from_json(prep[t["task_id"]]["gold_scope"])
            b = brokers.setdefault(t["pgdb"], Broker(t["pgdb"]))
            rec = {"task_id": t["task_id"], "dataset": t["dataset"], "difficulty": t["difficulty"], "role": role,
                   "commit": cm, "timestamp": datetime.datetime.now().isoformat(), "scopes": {}}
            gsuf, gerr = metrics.sufficiency(t, N, role, b)
            rec["gold_scope_sufficient"] = gsuf; rec["gold_scope_err"] = gerr
            sources = {"B0": E, "B1": b1_curated_scope(t, tasks, sl, E)}
            for v in VARIANTS:
                try:
                    sources[v] = tse_scope(t, role, v, E)
                except KeyError:
                    pass
            for name, s in sources.items():
                r = {"n_cols": len(s), "n_tables": len(s.tables)}
                r.update(metrics.oer(s, N, E, t["pgdb"]))
                p, rc = metrics.col_pr(s, N)
                r.update(precision=p, recall=rc)
                if name != "B0":
                    suf, err = metrics.sufficiency(t, s, role, b)
                    r.update(sufficient=suf, suff_err=err)
                else:
                    r.update(sufficient=True, suff_err=None)
                if name.startswith("tse"):
                    r["scope"] = s.to_json()
                rec["scopes"][name] = r
            f.write(json.dumps(rec) + "\n"); f.flush()
    for b in brokers.values():
        b.close()
    # ---------------- sensitivity analysis over policy generation (column-level, restricted role)
    sens_out = os.path.join(config.RESULTS, "e1_sensitivity.jsonl")
    with open(sens_out, "w") as f:
        for seed in (1, 2, 3):
            for frac in (0.10, 0.25, 0.40):
                for t in tasks:
                    sl = semantic_layer.get(t["pgdb"], t["dataset"], t["db_id"])
                    E = generate(sl, seed=seed, frac=frac)["restricted"]
                    N = Scope.from_json(prep[t["task_id"]]["gold_scope"])
                    if not N.columns_subset_of(E):
                        continue
                    try:
                        S = tse_scope(t, "restricted", "tse", E)
                    except KeyError:
                        continue
                    nc = max(1, len(N))
                    f.write(json.dumps({"seed": seed, "frac": frac, "task_id": t["task_id"], "dataset": t["dataset"],
                                        "difficulty": t["difficulty"], "oer_col_B0": len(E) / nc,
                                        "oer_col_TSE": len(S) / nc,
                                        "covers_needed_cols": N.columns_subset_of(S)}) + "\n")


if __name__ == "__main__":
    main()
