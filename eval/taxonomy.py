"""E3 under-scoping error taxonomy.

Sampling (preregistered procedure): all permitted tasks whose default TSE scope (k=1) is insufficient; simple
random sample of min(100, n) with numpy seed 0. Each case is classified by deterministic rules on (a) the
execution error of the gold query under the scope and (b) the difference between the scope and N(t); every
sampled case is then printed in full for manual verification (eval/results/taxonomy_cases.md), and manual
overrides, if any, are recorded in eval/taxonomy_overrides.json with a reason.

Categories:
  missing_table        a relation of N(t) is absent from S(t)
  missing_column       all relations present, >=1 needed column absent (subtypes: key / non-key)
  row_filter           columns cover N(t), result differs or is empty: a task row filter excluded needed rows
  view_semantics       columns cover N(t) but the query is rejected through views (e.g. GROUP BY on a PK
                       column whose functional dependency is not visible through a view)
  other
"""
import json, os, sys, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tse.scope import Scope
from tse import semantic_layer

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
TASKS = {json.loads(l)["task_id"]: json.loads(l) for l in open(os.path.join(os.path.dirname(RES), "..", "data", "tasks", "tasks.jsonl"))}
PREP = {json.loads(l)["task_id"]: json.loads(l) for l in open(os.path.join(RES, "prep.jsonl"))}


def classify(rec, t):
    s = rec["scopes"]["tse"]
    S = Scope.from_json(s["scope"]); N = Scope.from_json(PREP[rec["task_id"]]["gold_scope"])
    err = s.get("suff_err") or ""
    miss_t = sorted(set(N.tables) - set(S.tables))
    miss_c = sorted(f"{a}.{b}" for a, b in N.missing_columns(S) if a in S.tables)
    if miss_t:
        return "missing_table", {"missing_tables": miss_t, "missing_cols": miss_c}
    if miss_c:
        sl = semantic_layer.get(t["pgdb"], t["dataset"], t["db_id"])
        keys = [c for c in miss_c if c.split(".", 1)[1] in sl.key_columns(c.split(".", 1)[0])]
        return ("missing_column_key" if keys and len(keys) == len(miss_c) else "missing_column"), {"missing_cols": miss_c}
    if "GroupingError" in err or "must appear in the GROUP BY" in err:
        return "view_semantics", {"err": err}
    preds = {tb: ts.predicate for tb, ts in S.tables.items() if ts.predicate}
    if preds:
        return "row_filter", {"predicates": preds, "err": err}
    return "other", {"err": err}


def main():
    sc = [json.loads(l) for l in open(os.path.join(RES, "e1e3_scopes.jsonl"))]
    insuff = sorted([r for r in sc if "tse" in r["scopes"] and not r["scopes"]["tse"]["sufficient"]], key=lambda r: r["task_id"])
    rng = np.random.default_rng(0)
    idx = rng.choice(len(insuff), size=min(100, len(insuff)), replace=False)
    sample = [insuff[i] for i in sorted(idx)]
    ov = {}
    op = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taxonomy_overrides.json")
    if os.path.exists(op):
        ov = json.load(open(op))
    out, md = [], ["# Under-scoping sample (E3)\n", f"Population: {len(insuff)} insufficient TSE (k=1) scopes; sample: {len(sample)} (numpy seed 0).\n"]
    for r in sample:
        t = TASKS[r["task_id"]]
        cat, det = classify(r, t)
        if r["task_id"] in ov:
            cat = ov[r["task_id"]]["category"]; det["override_reason"] = ov[r["task_id"]]["reason"]
        out.append({"task_id": r["task_id"], "dataset": t["dataset"], "difficulty": t["difficulty"], "category": cat, **det})
        md.append(f"## {r['task_id']} ({t['dataset']}, {t['difficulty']}) -> **{cat}**\n- Q: {t['question']}\n- Evidence: {t.get('evidence','')}\n"
                  f"- Gold: `{t['gold_sql'][:400]}`\n- Detail: {json.dumps(det)[:500]}\n")
    with open(os.path.join(RES, "taxonomy_sample.jsonl"), "w") as f:
        for o in out:
            f.write(json.dumps(o) + "\n")
    open(os.path.join(RES, "taxonomy_cases.md"), "w").write("\n".join(md))
    c = collections.Counter(o["category"] for o in out)
    print(len(insuff), dict(c))


if __name__ == "__main__":
    main()
