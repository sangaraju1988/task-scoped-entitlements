"""Extract the 'needed data' scope N(t) from gold SQL.

Columns: every base-table column the query references (after star expansion and column qualification).
Rows: for each base table occurrence, the conjunction of WHERE / INNER-JOIN-ON conjuncts that reference only
that occurrence's columns and contain no subquery; occurrences of the same table are OR-ed (union of rows).
Conjuncts we cannot attribute to a single table are dropped, which can only *enlarge* N(t); this makes OER
for baselines conservative (smaller), never inflated.
"""
from __future__ import annotations
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import traverse_scope
from .scope import Scope, TableScope, _and, _or


def _schema_dict(sl):
    return {t: {c: "TEXT" for c in tb.columns} for t, tb in sl.tables.items()}


def _conjuncts(e):
    if e is None:
        return []
    if isinstance(e, exp.And):
        return _conjuncts(e.left) + _conjuncts(e.right)
    if isinstance(e, exp.Paren):
        return _conjuncts(e.this)
    return [e]


def parse_qualified(sql: str, sl):
    tree = sqlglot.parse_one(sql, read="postgres")
    tree = qualify(tree, schema=_schema_dict(sl), dialect="postgres", quote_identifiers=True,
                   validate_qualify_columns=False, identify=True)
    return tree


def extract(sql: str, sl) -> Scope:
    tree = parse_qualified(sql, sl)
    cols = {}
    preds = {}       # table -> OR over occurrences of AND of local conjuncts (None == all rows)
    seen_occ = set()
    for sc in traverse_scope(tree):
        alias_to_table = {}
        for alias, src in sc.sources.items():
            if isinstance(src, exp.Table) and src.name in sl.tables:
                alias_to_table[alias] = src.name
        for col in sc.columns:
            t = alias_to_table.get(col.table)
            if t and col.name in sl.tables[t].columns:
                cols.setdefault(t, set()).add(col.name)
        # local predicates per alias in this scope
        local = {a: None for a in alias_to_table}
        conj = _conjuncts(sc.expression.args.get("where").this) if sc.expression.args.get("where") else []
        for j in sc.expression.args.get("joins") or []:
            if not j.side and j.args.get("on") is not None and (j.kind or "").upper() in ("", "INNER"):
                conj += _conjuncts(j.args["on"])
        for c in conj:
            if c.find(exp.Subquery) or c.find(exp.Select):
                continue
            aliases = {x.table for x in c.find_all(exp.Column)}
            if len(aliases) != 1:
                continue
            a = aliases.pop()
            if a not in alias_to_table:
                continue
            cc = c.copy()
            for x in cc.find_all(exp.Column):
                x.set("table", None)
            local[a] = _and(local[a], cc.sql(dialect="postgres"))
        for a, t in alias_to_table.items():
            key = (id(sc), a)
            if key in seen_occ:
                continue
            seen_occ.add(key)
            if t not in preds:
                preds[t] = local[a]
            else:
                preds[t] = _or(preds[t], local[a])
            cols.setdefault(t, set())
    out = {}
    for t, cs in cols.items():
        if not cs:  # e.g. COUNT(*) FROM t: needs the table's rows but no specific column; use PK or first col
            pk = sl.tables[t].pk
            cs = {pk[0]} if pk else {next(iter(sl.tables[t].columns))}
        out[t] = TableScope(frozenset(cs), preds.get(t))
    return Scope(out)
