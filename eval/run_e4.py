"""E4 overhead (no LLM): per permitted task, compile + teardown latency of the gold scope and of the TSE
scope, and gold-query latency under (a) B0 credentials (grants + RLS on base tables) and (b) the compiled TSE
views, 5 repetitions each after one warm-up. Also checks leftover task objects (must be 0).
Output: eval/results/e4_overhead.jsonl
"""
import json, os, sys, time, statistics, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eval.common import load_tasks, load_prep, entitlement, tse_scope, commit
from tse import semantic_layer, config
from tse.db import connect
from tse.scope import Scope
from tse.compile import Broker
from tse.setup_db import get_secrets, login_role
from tse.metrics import gold_result
from tse.datasets.tasks import result_set

REPS = 5


def timed(conn, sql):
    conn.execute(sql).fetchall()  # warm-up
    ts = []
    for _ in range(REPS):
        t0 = time.perf_counter(); conn.execute(sql).fetchall(); ts.append(1000 * (time.perf_counter() - t0))
    return statistics.median(ts)


def main():
    tasks = load_tasks(); prep = load_prep(); sec = get_secrets()
    out = os.path.join(config.RESULTS, "e4_overhead.jsonl")
    cm = commit()
    brokers = {}
    with open(out, "w") as f:
        for t in sorted(tasks, key=lambda x: (x["pgdb"], x["task_id"])):
            role = prep[t["task_id"]]["role_permitted"]
            E = entitlement(t, role)
            N = Scope.from_json(prep[t["task_id"]]["gold_scope"])
            b = brokers.setdefault(t["pgdb"], Broker(t["pgdb"]))
            rec = {"task_id": t["task_id"], "dataset": t["dataset"], "role": role, "commit": cm,
                   "timestamp": datetime.datetime.now().isoformat()}
            L = login_role(t["pgdb"], role)
            try:
                with connect(t["pgdb"], user=L, password=sec["logins"][L]) as c:
                    c.execute("SET statement_timeout = 120000"); c.execute("SET search_path = public")
                    rec["b0_query_ms"] = timed(c, t["gold_sql"])
                h = b.provision(t["task_id"], N, role)
                rec["compile_ms"] = h.timings["compile_ms"]; rec["n_objects"] = h.n_objects
                with connect(t["pgdb"], user=h.login, password=h.password) as c:
                    c.execute("SET statement_timeout = 120000")
                    rec["tse_query_ms"] = timed(c, t["gold_sql"])
                    rec["tse_result_equal"] = result_set(c.execute(t["gold_sql"]).fetchall()) == gold_result(t)
                b.teardown(h)
                rec["teardown_ms"] = h.timings["teardown_ms"]
            except Exception as e:
                rec["error"] = type(e).__name__ + ": " + str(e)[:200]
                b.cleanup_all()
            f.write(json.dumps(rec) + "\n"); f.flush()
    left = {}
    for db, b in brokers.items():
        left[db] = b.count_task_objects(); b.close()
    with open(os.path.join(config.RESULTS, "e4_leftovers.json"), "w") as f:
        json.dump({"leftover_task_objects": left, "all_zero": all(v == (0, 0) for v in left.values())}, f)


if __name__ == "__main__":
    main()
