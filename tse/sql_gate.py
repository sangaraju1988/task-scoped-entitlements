"""Baseline B4 (added after review, deviation D12): the same task scope enforced by a SQL-parsing gate in front of
the user's own credentials, in the style of query-checking agent gateways (e.g. SecureMCP). The gate allows a
statement iff it parses as exactly one SELECT/set query, every table it reads (after qualification against the
full schema, which also expands '*') is a scope table in schema public, and every column it reads is a scope
column. Allowed statements run with the user's credentials (reach E(u)).
"""
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import traverse_scope


def gate(sql: str, sl, scope):
    try:
        stmts = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except Exception:
        return False, "parse_error"
    if len(stmts) != 1:
        return False, "multi_statement"
    tree = stmts[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Except, exp.Intersect)):
        return False, "not_select"
    schema = {t: {c: "TEXT" for c in tb.columns} for t, tb in sl.tables.items()}
    try:
        tree = qualify(tree, schema=schema, dialect="postgres", quote_identifiers=True, validate_qualify_columns=True, identify=True)
    except Exception as e:
        return False, "unresolved:" + type(e).__name__
    for sc in traverse_scope(tree):
        a2t = {}
        for alias, src in sc.sources.items():
            if isinstance(src, exp.Table):
                if src.name not in scope.tables or (src.db or "public") != "public":
                    return False, f"table:{src.db}.{src.name}"
                a2t[alias] = src.name
        for col in sc.columns:
            t = a2t.get(col.table)
            if t is not None and col.name not in scope.tables[t].columns:
                return False, f"column:{t}.{col.name}"
    return True, "allowed"
