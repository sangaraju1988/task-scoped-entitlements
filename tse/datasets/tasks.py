"""Build the task set (BIRD Mini-Dev PG + Spider dev) with validated PostgreSQL gold SQL.

Outputs data/tasks/tasks_all.jsonl (every candidate with validation status) and data/tasks/tasks.jsonl (the
evaluation sample). Gold SQL defines the 'needed data' (see tse/gold_scope.py).
"""
import json, os, random, sqlite3, sys, time, decimal, datetime, collections
import sqlglot
from sqlglot import exp
from ..db import connect
from .. import config

RAW = os.path.join(config.DATA, "raw")
OUT = os.path.join(config.DATA, "tasks")
sys.path.insert(0, os.path.join(RAW, "spider_eval"))

def norm_val(v):
    if isinstance(v, decimal.Decimal):
        v = float(v)
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, (datetime.date, datetime.datetime, datetime.time)):
        return str(v)
    if isinstance(v, memoryview):
        return bytes(v)
    return v

def result_set(rows):
    return set(tuple(norm_val(v) for v in r) for r in rows)

def run_pg(dbname, sql, timeout_ms=60000, user=None, password=None):
    with connect(dbname, user=user, password=password) as c:
        c.execute(f"SET statement_timeout = {timeout_ms}")
        cur = c.execute(sql)
        return cur.fetchall() if cur.description else []

def lower_identifiers(tree):
    for node in tree.find_all(exp.Identifier):
        node.set("this", node.this.lower())
        node.set("quoted", True)
    return tree

_COLS = {}
def db_columns(pgdb):
    if pgdb not in _COLS:
        rows = run_pg(pgdb, "select lower(column_name) from information_schema.columns where table_schema='public'")
        _COLS[pgdb] = {r[0] for r in rows}
    return _COLS[pgdb]

def spider_to_pg(sql, pgdb):
    """Transpile SQLite gold to PostgreSQL. SQLite treats a double-quoted token that names no column as a
    string literal; we reproduce that rule, then lower-case identifiers."""
    tree = sqlglot.parse_one(sql, read="sqlite")
    cols = db_columns(pgdb)
    for col in list(tree.find_all(exp.Column)):
        ident = col.this
        if isinstance(ident, exp.Identifier) and ident.quoted and not col.table and ident.this.lower() not in cols:
            col.replace(exp.Literal.string(ident.this))
    tree = lower_identifiers(tree)
    return tree.sql(dialect="postgres")

def build_bird():
    out = []
    for line in open(os.path.join(RAW, "bird_minidev", "mini_dev_postgresql.jsonl")):
        x = json.loads(line)
        t = dict(task_id=f"bird-{x['question_id']}", dataset="bird", db_id=x["db_id"], pgdb="bird_" + x["db_id"],
                 question=x["question"], evidence=x.get("evidence", ""), gold_sql=x["SQL"], difficulty=x["difficulty"])
        try:
            t0 = time.time(); rows = run_pg(t["pgdb"], t["gold_sql"]); t["gold_ms"] = round(1000 * (time.time() - t0), 1)
            t["gold_rows"] = len(rows); t["valid"] = True
        except Exception as e:
            t["valid"] = False; t["invalid_reason"] = f"pg_error: {str(e)[:200]}"
        out.append(t)
    return out

def build_spider():
    import evaluation  # official Spider evaluation.py (for eval_hardness)
    ev = evaluation.Evaluator()
    dev = json.load(open(os.path.join(RAW, "spider", "spider_data", "dev.json")))
    out = []
    for i, x in enumerate(dev):
        t = dict(task_id=f"spider-{i}", dataset="spider", db_id=x["db_id"], pgdb="spider_" + x["db_id"].lower(),
                 question=x["question"], evidence="", gold_sql_sqlite=x["query"], difficulty=ev.eval_hardness(x["sql"]))
        try:
            t["gold_sql"] = spider_to_pg(x["query"], t["pgdb"])
        except Exception as e:
            t["valid"] = False; t["invalid_reason"] = f"transpile_error: {str(e)[:200]}"; out.append(t); continue
        try:
            s = sqlite3.connect(os.path.join(RAW, "spider", "spider_data", "database", x["db_id"], x["db_id"] + ".sqlite"))
            s.text_factory = lambda b: b.decode("utf-8", "replace")
            ref = result_set(s.execute(x["query"]).fetchall())
            t0 = time.time(); rows = run_pg(t["pgdb"], t["gold_sql"]); t["gold_ms"] = round(1000 * (time.time() - t0), 1)
            got = result_set(rows)
            t["gold_rows"] = len(rows)
            if got == ref and len(rows) == 0:
                t["valid"] = False; t["invalid_reason"] = "empty_gold_result"  # degenerate for execution accuracy
            elif got == ref:
                t["valid"] = True
            else:
                t["valid"] = False; t["invalid_reason"] = "result_mismatch_sqlite_vs_pg"
        except Exception as e:
            t["valid"] = False; t["invalid_reason"] = f"pg_error: {str(e)[:200]}"
        out.append(t)
    return out

def stratified_sample(tasks, n, seed, keys=("difficulty", "db_id")):
    """Proportional allocation over strata (largest-remainder), then seeded random sampling within strata."""
    rng = random.Random(seed)
    strata = collections.defaultdict(list)
    for t in tasks:
        strata[tuple(t[k] for k in keys)].append(t)
    N = len(tasks)
    quotas = {k: n * len(v) / N for k, v in strata.items()}
    alloc = {k: int(q) for k, q in quotas.items()}
    rem = n - sum(alloc.values())
    for k in sorted(quotas, key=lambda k: (-(quotas[k] - alloc[k]), str(k)))[:rem]:
        alloc[k] += 1
    sample = []
    for k in sorted(strata, key=str):
        v = sorted(strata[k], key=lambda t: t["task_id"])
        sample += rng.sample(v, alloc[k])
    return sorted(sample, key=lambda t: (t["dataset"], t["db_id"], t["task_id"]))

def main(seed=20261126, n_spider=500):
    os.makedirs(OUT, exist_ok=True)
    allt = build_bird() + build_spider()
    with open(os.path.join(OUT, "tasks_all.jsonl"), "w") as f:
        for t in allt:
            f.write(json.dumps(t) + "\n")
    bird = [t for t in allt if t["dataset"] == "bird" and t["valid"]]
    spider = [t for t in allt if t["dataset"] == "spider" and t["valid"]]
    sample = sorted(bird, key=lambda t: t["task_id"]) + stratified_sample(spider, n_spider, seed)
    with open(os.path.join(OUT, "tasks.jsonl"), "w") as f:
        for t in sample:
            f.write(json.dumps(t) + "\n")
    c = collections.Counter((t["dataset"], t["valid"], t.get("invalid_reason", "").split(":")[0]) for t in allt)
    print(json.dumps({str(k): v for k, v in c.items()}, indent=1))
    print("sample:", collections.Counter((t["dataset"], t["difficulty"]) for t in sample))

if __name__ == "__main__":
    main()


def results_match(got: set, gold: set) -> bool:
    """Execution match as sets of tuples, allowing a permutation of columns (as in the Spider test-suite
    evaluation of Zhong et al., 2020). Applied identically to every condition."""
    if got is None:
        return False
    if got == gold:
        return True
    if not got or not gold:
        return False
    a, b = next(iter(got)), next(iter(gold))
    if len(a) != len(b) or len(a) > 6 or len(got) != len(gold):
        return False
    import itertools
    n = len(a)
    for perm in itertools.permutations(range(n)):
        if {tuple(r[i] for i in perm) for r in got} == gold:
            return True
    return False
