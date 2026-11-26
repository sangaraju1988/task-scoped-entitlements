"""Load Spider dev SQLite databases into PostgreSQL (one database per Spider db_id, prefixed 'spider_').

Identifiers are lower-cased (Spider is case-insensitive under SQLite). Column types are inferred from the
stored values (SQLite is dynamically typed): all-integer -> bigint, all-numeric -> double precision, else text.
PK/FK constraints are NOT created in Postgres (Spider data contains orphan keys); the FK graph used by the
semantic layer comes from the dataset's tables.json.
"""
import json, os, sqlite3, sys
from ..db import connect, qident
from .. import config

RAW = os.path.join(config.DATA, "raw", "spider", "spider_data")

import re
_INT = re.compile(r"^-?\d+$")
_NUM = re.compile(r"^-?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")

def _as_int(v):
    return isinstance(v, int) and not isinstance(v, bool) or (isinstance(v, str) and bool(_INT.match(v.strip())) and not (len(v.strip()) > 1 and v.strip().startswith("0")))

def _as_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) or (isinstance(v, str) and bool(_NUM.match(v.strip())))

def infer_type(values):
    """Integer-like strings (no leading zeros) count as integers: SQLite compares them by affinity."""
    vals = [v for v in values if v is not None and v != ""]
    if not vals:
        return "text"
    if all(_as_int(v) for v in vals):
        return "bigint"
    if all(_as_num(v) for v in vals):
        return "double precision"
    return "text"

def convert(v, typ):
    if v is None:
        return None
    if typ == "text":
        if isinstance(v, bytes):
            return v.decode("utf-8", "replace")
        return str(v)
    if isinstance(v, str):
        v = v.strip()
        if v == "":
            return None
        return int(v) if typ == "bigint" else float(v)
    return v

def add_primary_keys(c, db_id):
    """Declare PKs from tables.json where the data permits (lets Postgres accept GROUP BY <pk> with
    functionally dependent columns, as SQLite does). Failures (duplicates/NULLs) are skipped."""
    meta = {d["db_id"]: d for d in json.load(open(os.path.join(RAW, "tables.json")))}[db_id]
    for ci in meta["primary_keys"]:
        cis = ci if isinstance(ci, list) else [ci]
        tidx = meta["column_names_original"][cis[0]][0]
        t = meta["table_names_original"][tidx].lower()
        cols = ", ".join(qident(meta["column_names_original"][i][1].lower()) for i in cis)
        try:
            c.execute(f"ALTER TABLE {qident(t)} ADD PRIMARY KEY ({cols})"); c.commit()
        except Exception:
            c.rollback()

def load_db(db_id):
    path = os.path.join(RAW, "database", db_id, db_id + ".sqlite")
    src = sqlite3.connect(path)
    src.text_factory = lambda b: b.decode("utf-8", "replace")
    tables = [r[0] for r in src.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'")]
    pgdb = "spider_" + db_id.lower()
    with connect("postgres") as c:
        c.execute(f"DROP DATABASE IF EXISTS {qident(pgdb)}")
        c.execute(f"CREATE DATABASE {qident(pgdb)} ENCODING 'UTF8'")
    with connect(pgdb, autocommit=False) as c:
        for t in tables:
            cols = [r[1] for r in src.execute(f"PRAGMA table_info({qident(t)})")]
            rows = src.execute(f"SELECT * FROM {qident(t)}").fetchall()
            types = [infer_type([r[i] for r in rows]) for i in range(len(cols))]
            ddl = ", ".join(f"{qident(cn.lower())} {ty}" for cn, ty in zip(cols, types))
            c.execute(f"CREATE TABLE {qident(t.lower())} ({ddl})")
            if rows:
                with c.cursor().copy(f"COPY {qident(t.lower())} FROM STDIN") as cp:
                    for r in rows:
                        cp.write_row([convert(v, ty) for v, ty in zip(r, types)])
        c.commit()
        add_primary_keys(c, db_id)
    return pgdb, len(tables)

def main():
    dev = json.load(open(os.path.join(RAW, "dev.json")))
    dbs = sorted({x["db_id"] for x in dev})
    for d in dbs:
        print(d, load_db(d), flush=True)

if __name__ == "__main__":
    main()
