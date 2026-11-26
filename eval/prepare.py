"""Prepare the evaluation: gold scopes, per-role permission (by execution), task-role assignments, folds.

permitted(t, r) := cols(N(t)) ⊆ cols(E_r) AND gold result executed as r's login == gold result as admin.
Assignments (seed 7):
  permitted set     : every task with >=1 permitted role; role drawn uniformly among its permitted roles.
  non-permitted set : tasks with >=1 non-permitted role; one drawn uniformly; stratified sample of 200.
Output: eval/results/prep.jsonl
"""
import json, os, random, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tse import semantic_layer, gold_scope, config
from tse.db import connect
from tse.setup_db import get_secrets, login_role
from tse.datasets.tasks import result_set, stratified_sample
from tse.policies.generate import generate
from tse.baselines import fold_of
from tse.metrics import gold_result

ROLES = ["full", "restricted", "partition"]


def main():
    sec = get_secrets()
    tasks = [json.loads(l) for l in open(os.path.join(config.DATA, "tasks", "tasks.jsonl"))]
    pol = {}
    out = []
    for t in tasks:
        sl = semantic_layer.get(t["pgdb"], t["dataset"], t["db_id"])
        if t["pgdb"] not in pol:
            pol[t["pgdb"]] = generate(sl)
        N = gold_scope.extract(t["gold_sql"], sl)
        g = gold_result(t)
        perm = {}
        for r in ROLES:
            E = pol[t["pgdb"]][r]
            if not N.columns_subset_of(E):
                perm[r] = False; continue
            L = login_role(t["pgdb"], r)
            try:
                with connect(t["pgdb"], user=L, password=sec["logins"][L]) as c:
                    c.execute("SET statement_timeout = 120000")
                    perm[r] = result_set(c.execute(t["gold_sql"]).fetchall()) == g
            except Exception:
                perm[r] = False
        out.append({"task_id": t["task_id"], "gold_scope": N.to_json(), "permitted": perm, "fold": fold_of(t["task_id"])})
    rng = random.Random(7)
    for o in out:
        p = [r for r in ROLES if o["permitted"][r]]
        n = [r for r in ROLES if not o["permitted"][r]]
        o["role_permitted"] = rng.choice(p) if p else None
        o["role_nonpermitted"] = rng.choice(n) if n else None
    byid = {t["task_id"]: t for t in tasks}
    cand = [dict(byid[o["task_id"]], **o) for o in out if o["role_nonpermitted"]]
    np_sample = {t["task_id"] for t in stratified_sample(cand, min(200, len(cand)), seed=7, keys=("dataset", "difficulty"))}
    for o in out:
        o["in_nonpermitted_set"] = o["task_id"] in np_sample
    os.makedirs(config.RESULTS, exist_ok=True)
    with open(os.path.join(config.RESULTS, "prep.jsonl"), "w") as f:
        for o in out:
            f.write(json.dumps(o) + "\n")
    c = collections.Counter(o["role_permitted"] for o in out)
    print("permitted-role distribution:", c)
    print("tasks with no permitted role:", sum(1 for o in out if not o["role_permitted"]))
    print("per-role permitted rate:", {r: sum(o["permitted"][r] for o in out) / len(out) for r in ROLES})
    print("non-permitted set:", len(np_sample))


if __name__ == "__main__":
    main()
