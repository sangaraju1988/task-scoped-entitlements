"""Relational scope model (C1).

A scope maps each table to (columns, row predicate). The predicate is a SQL boolean expression over the
table's own (unqualified, quoted) columns, or None meaning "all rows". Entitlements E(u) and task scopes
S(t) share this representation.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional, Iterable, Tuple


def _and(a: Optional[str], b: Optional[str]) -> Optional[str]:
    if a is None:
        return b
    if b is None:
        return a
    if a == b:
        return a
    return f"({a}) AND ({b})"


def _or(a: Optional[str], b: Optional[str]) -> Optional[str]:
    if a is None or b is None:
        return None
    if a == b:
        return a
    return f"({a}) OR ({b})"


@dataclass(frozen=True)
class TableScope:
    columns: FrozenSet[str]
    predicate: Optional[str] = None  # None == TRUE (all rows)

    def to_json(self):
        return {"columns": sorted(self.columns), "predicate": self.predicate}


@dataclass
class Scope:
    tables: Dict[str, TableScope] = field(default_factory=dict)

    # ---- construction -------------------------------------------------
    @staticmethod
    def from_json(d) -> "Scope":
        if isinstance(d, str):
            d = json.loads(d)
        return Scope({t: TableScope(frozenset(v["columns"]), v.get("predicate")) for t, v in d.items()})

    def to_json(self):
        return {t: ts.to_json() for t, ts in sorted(self.tables.items())}

    def copy(self) -> "Scope":
        return Scope(dict(self.tables))

    def add_columns(self, table: str, cols: Iterable[str]):
        cols = frozenset(cols)
        if table in self.tables:
            ts = self.tables[table]
            self.tables[table] = TableScope(ts.columns | cols, ts.predicate)
        else:
            self.tables[table] = TableScope(cols, None)

    def set_predicate(self, table: str, pred: Optional[str]):
        ts = self.tables[table]
        self.tables[table] = TableScope(ts.columns, pred)

    # ---- algebra ------------------------------------------------------
    def column_pairs(self) -> FrozenSet[Tuple[str, str]]:
        return frozenset((t, c) for t, ts in self.tables.items() for c in ts.columns)

    def intersect(self, other: "Scope") -> "Scope":
        """S ∩ E: columns intersected per table; predicates conjoined. Tables absent in either are dropped."""
        out = {}
        for t, ts in self.tables.items():
            if t not in other.tables:
                continue
            o = other.tables[t]
            cols = ts.columns & o.columns
            if cols:
                out[t] = TableScope(cols, _and(ts.predicate, o.predicate))
        return Scope(out)

    def union(self, other: "Scope") -> "Scope":
        out = dict(self.tables)
        for t, o in other.tables.items():
            if t in out:
                out[t] = TableScope(out[t].columns | o.columns, _or(out[t].predicate, o.predicate))
            else:
                out[t] = o
        return Scope(out)

    def columns_subset_of(self, other: "Scope") -> bool:
        return self.column_pairs() <= other.column_pairs()

    def missing_columns(self, other: "Scope") -> FrozenSet[Tuple[str, str]]:
        """Column pairs of self not present in other."""
        return self.column_pairs() - other.column_pairs()

    def __len__(self):
        return len(self.column_pairs())
