"""Scope-level metrics: sufficiency (executed), column precision/recall, OER (column/row/cell)."""
from __future__ import annotations
from .db import connect, qident
from .datasets.tasks import result_set
from .compile import Broker
from .scope import Scope

_GOLD = {}
def gold_result(task):
    if task["task_id"] not in _GOLD:
        with connect(task["pgdb"]) as c:
            c.execute("SET statement_timeout = 120000")
            _GOLD[task["task_id"]] = result_set(c.execute(task["gold_sql"]).fetchall())
    return _GOLD[task["task_id"]]

def run_as(h, sql, limit=None, timeout_ms=60000):
    with connect(h.pgdb, user=h.login, password=h.password) as c:
        c.execute(f"SET statement_timeout = {timeout_ms}")
        cur = c.execute(sql)
        return cur.fetchall() if cur.description else []

def sufficiency(task, scope: Scope, role: str, broker: Broker):
    """Sufficient iff the gold query executes under the compiled scope and returns the gold result."""
    h = broker.provision(task["task_id"], scope, role)
    try:
        try:
            got = result_set(run_as(h, task["gold_sql"]))
            return got == gold_result(task), None
        except Exception as e:
            return False, type(e).__name__ + ": " + str(e).splitlines()[0][:160]
    finally:
        broker.teardown(h)

def col_pr(inferred: Scope, needed: Scope):
    I, N = inferred.column_pairs(), needed.column_pairs()
    tp = len(I & N)
    return (tp / len(I) if I else 0.0), (tp / len(N) if N else 1.0)

_ROWS = {}
def count_rows(pgdb, table, pred, role_login=None):
    key = (pgdb, table, pred)
    if key not in _ROWS:
        with connect(pgdb) as c:
            c.execute("SET statement_timeout = 120000")
            q = f"SELECT count(*) FROM public.{qident(table)}" + (f" WHERE {pred}" if pred else "")
            _ROWS[key] = c.execute(q).fetchone()[0]
    return _ROWS[key]

def reach(scope: Scope, E: Scope, pgdb):
    """Effective reach of a scope under entitlement E: columns S∩E, rows satisfying pred_S AND pred_E."""
    from .scope import _and
    out = {}
    for t, ts in scope.tables.items():
        if t not in E.tables:
            continue
        cols = ts.columns & E.tables[t].columns
        if not cols:
            continue
        out[t] = (len(cols), count_rows(pgdb, t, _and(ts.predicate, E.tables[t].predicate)))
    return out

def oer(reach_scope: Scope, needed: Scope, E: Scope, pgdb):
    """Over-exposure ratios. Needed rows are counted under E as well (needed ⊆ E for permitted tasks)."""
    R, N = reach(reach_scope, E, pgdb), reach(needed, E, pgdb)
    ncols = sum(v[0] for v in N.values()); rcols = sum(v[0] for v in R.values())
    nrows = sum(max(1, N[t][1]) for t in N); rrows = sum(R[t][1] if t in R else 0 for t in N)
    ncell = sum(v[0] * max(1, v[1]) for v in N.values()); rcell = sum(v[0] * v[1] for v in R.values())
    return {"oer_col": rcols / max(1, ncols), "oer_row": rrows / max(1, nrows), "oer_cell": rcell / max(1, ncell),
            "reach_cols": rcols, "need_cols": ncols, "reach_rows_needed_tables": rrows, "need_rows": nrows,
            "reach_cells": rcell, "need_cells": ncell}
