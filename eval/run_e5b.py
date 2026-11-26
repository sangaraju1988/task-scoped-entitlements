"""E5(b): scripted enforcement-bypass attempts executed AS THE TSE ROLE on canary databases.

For each canary database we provision a task scope that EXCLUDES the canary column (and, where possible,
restricts rows), then run every attack in the catalog. An attempt SUCCEEDS iff the canary token 'CNRY'
appears anywhere in its output (rows, error message, notices) or the attempt reads out-of-scope rows.
Every attempt and outcome is recorded; successes are findings to fix or document, never hidden.
Timing is measured and reported but is out of scope (covert channel).
Output: eval/results/e5b_bypass.jsonl
"""
import json, os, sys, time, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eval.common import commit
from tse import semantic_layer, config
from tse.db import connect, qident
from tse.scope import Scope, TableScope
from tse.compile import Broker


def attacks(ct, cc, other_col, schema, scope_role, user_role):
    q, qt = qident(cc), qident(ct)
    return [
        ("direct_column", "out-of-scope column via view", f"SELECT {q} FROM {qt} LIMIT 5"),
        ("base_table", "base table in public", f"SELECT {q} FROM public.{qt} LIMIT 5"),
        ("star_expansion", "SELECT * on the view", f"SELECT * FROM {qt} LIMIT 5"),
        ("mixed_view_base", "join view with base table", f"SELECT v.*, b.{q} FROM {qt} v, public.{qt} b LIMIT 5"),
        ("search_path", "reset search_path then read", f"SET search_path = public; SELECT {q} FROM {qt} LIMIT 5"),
        ("set_role_scope", "SET ROLE to scope role", f"SET ROLE {scope_role}; SELECT {q} FROM public.{qt} LIMIT 5"),
        ("set_role_user", "SET ROLE to user role", f"SET ROLE {user_role}; SELECT {q} FROM public.{qt} LIMIT 5"),
        ("set_session_auth", "SET SESSION AUTHORIZATION", "SET SESSION AUTHORIZATION postgres"),
        ("copy_to_stdout_base", "COPY base table", f"COPY public.{qt} ({q}) TO STDOUT"),
        ("copy_to_file", "COPY to server file", f"COPY (SELECT 1) TO '/tmp/tse_x'"),
        ("copy_program", "COPY FROM PROGRAM", "COPY (SELECT 1) TO PROGRAM 'id'"),
        ("pg_read_file", "server file read", "SELECT pg_read_file('postgresql.conf')"),
        ("lo_import", "large object import", "SELECT lo_import('/etc/passwd')"),
        ("pg_stats", "statistics view", f"SELECT most_common_vals::text, histogram_bounds::text FROM pg_stats WHERE attname = '{cc}'"),
        ("pg_statistic", "raw statistics catalog", "SELECT stavalues1::text FROM pg_statistic LIMIT 50"),
        ("catalog_viewdef", "view definition via catalog", f"SELECT definition FROM pg_views WHERE schemaname = '{schema}'"),
        ("catalog_columns", "column names via information_schema", f"SELECT column_name FROM information_schema.columns WHERE table_name = '{ct}'"),
        ("leaky_function_temp", "create leaky function in pg_temp", "CREATE FUNCTION pg_temp.f(text) RETURNS bool LANGUAGE plpgsql COST 0.0000001 AS $$BEGIN RAISE NOTICE '%', $1; RETURN true; END$$"),
        ("leaky_operator", "create operator", "CREATE OPERATOR pg_temp.<<< (LEFTARG = text, RIGHTARG = text, FUNCTION = textlt)"),
        ("error_side_channel_cast", "cast error on out-of-scope value", f"SELECT CAST((SELECT {q} FROM public.{qt} LIMIT 1) AS int)"),
        ("error_side_channel_view", "cast error on in-scope view column", f"SELECT CAST({qident(other_col)} AS int) FROM {qt} LIMIT 1"),
        ("subquery_in_where", "out-of-scope column in subquery predicate", f"SELECT count(*) FROM {qt} WHERE EXISTS (SELECT 1 FROM public.{qt} b WHERE b.{q} LIKE 'CNRY%')"),
        ("create_view", "create own view", f"CREATE VIEW {schema}.x AS SELECT {q} FROM public.{qt}"),
        ("create_table_as", "materialize via CTAS", f"CREATE TEMP TABLE x AS SELECT * FROM {qt}"),
        ("write_attempt", "DML on view", f"DELETE FROM {qt}"),
        ("dblink", "cross-database link", "SELECT * FROM dblink('dbname=postgres', 'select 1') AS t(a int)"),
        ("pg_ls_dir", "list server directory", "SELECT pg_ls_dir('.')"),
        ("current_setting_secrets", "read settings", "SELECT name, setting FROM pg_settings WHERE name LIKE '%password%' OR name = 'data_directory'"),
        ("explain_base", "EXPLAIN on base table", f"EXPLAIN SELECT {q} FROM public.{qt}"),
        ("prepared_stmt", "prepared statement on base", f"PREPARE p AS SELECT {q} FROM public.{qt}; EXECUTE p"),
        ("do_block", "anonymous code block", f"DO $$BEGIN PERFORM {q} FROM public.{qt}; END$$"),
        ("reset_role_settings", "reset read-only then write", "SET default_transaction_read_only = off; CREATE TEMP TABLE y(a int)"),
    ]


def run_one(conn_params, sql):
    notices = []
    t0 = time.perf_counter()
    try:
        with connect(**conn_params) as c:
            c.add_notice_handler(lambda d: notices.append(d.message_primary or ""))
            out = []
            for stmt in [s for s in sql.split("; ") if s.strip()] if not sql.startswith("DO ") and not sql.startswith("CREATE FUNCTION") else [sql]:
                cur = c.execute(stmt)
                if cur.description:
                    out.append(json.dumps(cur.fetchmany(50), default=str))
            return {"ok": True, "output": " ".join(out)[:3000], "notices": notices, "ms": 1000 * (time.perf_counter() - t0)}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__ + ": " + str(e)[:400], "notices": notices, "ms": 1000 * (time.perf_counter() - t0)}


def main():
    inj = [json.loads(l) for l in open(os.path.join(config.RESULTS, "injections_context.jsonl"))]
    dbs = {}
    for r in inj:
        dbs.setdefault(r["pgdb"], (r["canary_table"], r["canary_column"]))
    cm = commit()
    out = os.path.join(config.RESULTS, "e5b_bypass.jsonl")
    with open(out, "w") as f:
        for pgdb, (ct, cc) in sorted(dbs.items()):
            src = pgdb[:-4]
            ds, dbid = ("bird", src[5:]) if src.startswith("bird_") else ("spider", None)
            if ds == "spider":
                import json as _j
                dbid = next(json.loads(l)["db_id"] for l in open(os.path.join(config.DATA, "tasks", "tasks.jsonl")) if json.loads(l)["pgdb"] == src)
            sl = semantic_layer.get(src, ds, dbid)
            cols = [c for c in sl.tables[ct].columns if c != cc]
            if not cols:
                continue
            scope = Scope({ct: TableScope(frozenset(cols[:3]), None)})
            b = Broker(pgdb)
            h = b.provision("e5b", scope, "full")
            params = dict(dbname=pgdb, user=h.login, password=h.password)
            for aid, desc, sql in attacks(ct, cc, cols[0], h.schema, h.scope_role, h.user_role):
                r = run_one(params, sql)
                blob = (r.get("output", "") + " " + r.get("error", "") + " " + " ".join(r["notices"]))
                success = "CNRY" in blob
                f.write(json.dumps({"pgdb": pgdb, "attack": aid, "description": desc, "sql": sql, "success": success,
                                    "executed": r["ok"], "error": r.get("error"), "output_head": r.get("output", "")[:300],
                                    "ms": r["ms"], "commit": cm, "timestamp": datetime.datetime.now().isoformat()}) + "\n")
            b.teardown(h); b.close()


if __name__ == "__main__":
    main()
