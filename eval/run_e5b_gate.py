"""D12 (after review): enforcement-bypass catalog against a SQL-parsing gate (tse/sql_gate.py) vs database
enforcement (TSE). Same canary databases and scope as E5(b). The catalog is extended with three attacks that hide a
query inside a string argument of a built-in function (query_to_xml, table_to_xml, ts_stat); these new attacks are
also run as the TSE role. Output: eval/results/e5b_gate.jsonl.
"""
import json, os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eval.common import commit
from eval.run_e5b import attacks, run_one
from tse import semantic_layer, config
from tse.db import qident
from tse.scope import Scope, TableScope
from tse.compile import Broker
from tse.setup_db import get_secrets, login_role
from tse.sql_gate import gate


def string_attacks(ct, cc):
    q, qt = qident(cc), qident(ct)
    return [
        ("query_to_xml", "query hidden in a string argument", f"SELECT query_to_xml('SELECT {q} FROM public.{qt} LIMIT 5', true, false, '')"),
        ("table_to_xml", "table name as a string argument", f"SELECT table_to_xml('public.{qt}', true, false, '')"),
        ("ts_stat", "query string executed by ts_stat", f"SELECT word FROM ts_stat('SELECT to_tsvector(''simple'', {q}::text) FROM public.{qt}') LIMIT 20"),
    ]


def main():
    inj = [json.loads(l) for l in open(os.path.join(config.RESULTS, "injections_context.jsonl"))]
    dbs = {}
    for r in inj:
        dbs.setdefault(r["pgdb"], (r["canary_table"], r["canary_column"]))
    cm = commit(); sec = get_secrets()
    out = os.path.join(config.RESULTS, "e5b_gate.jsonl")
    with open(out, "w") as f:
        for pgdb, (ct, cc) in sorted(dbs.items()):
            src = pgdb[:-4]
            ds, dbid = ("bird", src[5:]) if src.startswith("bird_") else ("spider", None)
            if ds == "spider":
                dbid = next(json.loads(l)["db_id"] for l in open(os.path.join(config.DATA, "tasks", "tasks.jsonl")) if json.loads(l)["pgdb"] == src)
            sl = semantic_layer.get(src, ds, dbid)
            cols = [c for c in sl.tables[ct].columns if c != cc]
            if not cols:
                continue
            scope = Scope({ct: TableScope(frozenset(cols[:3]), None)})
            L = login_role(pgdb, "full")
            user = dict(dbname=pgdb, user=L, password=sec["logins"][L])
            b = Broker(pgdb); h = b.provision("e5b_gate", scope, "full")
            tse = dict(dbname=pgdb, user=h.login, password=h.password)
            cat = [(a, d, s, "original") for a, d, s in attacks(ct, cc, cols[0], h.schema, h.scope_role, h.user_role)] + \
                  [(a, d, s, "string") for a, d, s in string_attacks(ct, cc)]
            for aid, desc, sql, kind in cat:
                ok, why = gate(sql, sl, scope)
                rec = {"pgdb": pgdb, "attack": aid, "kind": kind, "sql": sql, "gate_allowed": ok, "gate_reason": why,
                       "commit": cm, "timestamp": datetime.datetime.now().isoformat()}
                if ok:
                    r = run_one(user, sql)
                    blob = r.get("output", "") + " " + (r.get("error") or "") + " " + " ".join(r["notices"])
                    rec.update(gate_executed=r["ok"], gate_success="CNRY" in blob, gate_error=r.get("error"))
                else:
                    rec.update(gate_executed=False, gate_success=False)
                if kind == "string":
                    r = run_one(tse, sql)
                    blob = r.get("output", "") + " " + (r.get("error") or "") + " " + " ".join(r["notices"])
                    rec.update(tse_executed=r["ok"], tse_success="CNRY" in blob, tse_error=r.get("error"))
                f.write(json.dumps(rec) + "\n")
            b.teardown(h); b.close()


if __name__ == "__main__":
    main()
