"""Automatically built semantic layer (no hand-authored per-database content).

Sources, all machine-read:
  * PostgreSQL catalog: tables, columns, types, row counts, declared PKs.
  * Dataset-provided column descriptions and FK declarations:
      - BIRD Mini-Dev: the official `baseline_inference/schemas/postgresql.json` DDL (comments carry the
        BIRD `database_description` text; FOREIGN KEY clauses carry the FK graph). Example values in those
        comments are DISCARDED, so no data values reach any prompt.
      - Spider: `tables.json` (natural-language column names, primary/foreign keys).
"""
from __future__ import annotations
import json, os, re, collections
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from .db import connect, qident
from . import config

RAW = os.path.join(config.DATA, "raw")


@dataclass
class Column:
    name: str
    type: str
    description: str = ""


@dataclass
class Table:
    name: str
    columns: Dict[str, Column]
    pk: List[str] = field(default_factory=list)
    rowcount: int = 0


@dataclass
class SemanticLayer:
    pgdb: str
    dataset: str
    db_id: str
    tables: Dict[str, Table]
    fks: List[Tuple[str, str, str, str]]  # (table, column, ref_table, ref_column)

    # ------------------------------------------------------------------
    def all_scope(self):
        from .scope import Scope, TableScope
        return Scope({t: TableScope(frozenset(tb.columns), None) for t, tb in self.tables.items()})

    def key_columns(self, table: str) -> set:
        ks = set(self.tables[table].pk)
        for t, c, rt, rc in self.fks:
            if t == table:
                ks.add(c)
            if rt == table:
                ks.add(rc)
        return ks

    def fk_adjacency(self):
        adj = collections.defaultdict(list)
        for t, c, rt, rc in self.fks:
            if t in self.tables and rt in self.tables:
                adj[t].append((rt, c, rc))
                adj[rt].append((t, rc, c))
        return adj

    def fk_path(self, src: str, dst: str):
        """Shortest FK path src->dst as list of (t1, c1, t2, c2) hops (BFS, deterministic order)."""
        if src == dst:
            return []
        adj = self.fk_adjacency()
        prev = {src: None}
        q = collections.deque([src])
        while q:
            u = q.popleft()
            for v, cu, cv in sorted(adj[u]):
                if v not in prev:
                    prev[v] = (u, cu, cv)
                    if v == dst:
                        q.clear(); break
                    q.append(v)
        if dst not in prev:
            return None
        path, v = [], dst
        while prev[v] is not None:
            u, cu, cv = prev[v]
            path.append((u, cu, v, cv))
            v = u
        return list(reversed(path))

    def render(self, scope=None, with_desc=True, with_keys=True) -> str:
        """Render the (scoped) schema as compact DDL-like text for prompts. Never includes data values."""
        out = []
        for tname in sorted(self.tables):
            if scope is not None and tname not in scope.tables:
                continue
            tb = self.tables[tname]
            cols = [c for c in tb.columns.values() if scope is None or c.name in scope.tables[tname].columns]
            lines = []
            for c in cols:
                d = f"  -- {c.description}" if with_desc and c.description and c.description.lower() != c.name.lower() else ""
                lines.append(f"  {qident(c.name)} {c.type}{d}")
            out.append(f"TABLE {qident(tname)} (\n" + ",\n".join(lines) + "\n)")
            if with_keys:
                fk = [f"{qident(c)} -> {qident(rt)}.{qident(rc)}" for t, c, rt, rc in self.fks
                      if t == tname and (scope is None or (c in scope.tables[tname].columns and rt in scope.tables
                                                           and rc in scope.tables[rt].columns))]
                pk = [p for p in tb.pk if scope is None or p in scope.tables[tname].columns]
                if scope is not None and scope.tables[tname].predicate:
                    # non-Truman transparency: the agent is told which rows its scope exposes
                    out[-1] += f"\n  ROW FILTER (only rows satisfying this are visible): {scope.tables[tname].predicate}"
                if pk:
                    out[-1] += f"\n  PRIMARY KEY: {', '.join(qident(p) for p in pk)}"
                if fk:
                    out[-1] += "\n  FOREIGN KEYS: " + "; ".join(fk)
        return "\n\n".join(out)


# ----------------------------------------------------------------------
_COMMENT = re.compile(r'^\s*"(?P<col>(?:[^"]|"")+)"\s+[^,]*?,?\s*--\s*(?P<c>.*)$')
_FK = re.compile(r'FOREIGN KEY \("(?P<c>[^"]+)"\) REFERENCES "(?P<rt>[^"]+)" \("(?P<rc>[^"]+)"\)')
_CREATE = re.compile(r'CREATE TABLE "(?P<t>[^"]+)"')


def _bird_metadata(db_id):
    ddl = json.load(open(os.path.join(RAW, "bird_minidev", "postgresql.json")))[db_id]
    desc, fks, cur = {}, [], None
    for line in ddl.splitlines():
        m = _CREATE.search(line)
        if m:
            cur = m.group("t"); continue
        m = _FK.search(line)
        if m and cur:
            fks.append((cur, m.group("c"), m.group("rt"), m.group("rc"))); continue
        m = _COMMENT.match(line)
        if m and cur:
            text = m.group("c")
            text = re.split(r";?\s*example:", text)[0].strip().rstrip(";").strip()  # drop example values
            desc[(cur, m.group("col").replace('""', '"'))] = text
    return desc, fks


def _spider_metadata(db_id):
    meta = {d["db_id"]: d for d in json.load(open(os.path.join(RAW, "spider", "spider_data", "tables.json")))}[db_id]
    tn = [t.lower() for t in meta["table_names_original"]]
    desc = {}
    for (ti, co), (_, cn) in zip(meta["column_names_original"], meta["column_names"]):
        if ti >= 0:
            desc[(tn[ti], co.lower())] = cn
    fks = []
    for a, b in meta["foreign_keys"]:
        ta, ca = meta["column_names_original"][a]
        tb, cb = meta["column_names_original"][b]
        fks.append((tn[ta], ca.lower(), tn[tb], cb.lower()))
    return desc, fks


def build(pgdb: str, dataset: str, db_id: str, use_descriptions: bool = True) -> SemanticLayer:
    with connect(pgdb) as c:
        cols = c.execute("""select table_name, column_name, data_type from information_schema.columns
                            where table_schema='public' order by table_name, ordinal_position""").fetchall()
        pks = c.execute("""select tc.table_name, kcu.column_name from information_schema.table_constraints tc
                           join information_schema.key_column_usage kcu on tc.constraint_name=kcu.constraint_name
                             and tc.table_schema=kcu.table_schema
                           where tc.constraint_type='PRIMARY KEY' and tc.table_schema='public'
                           order by kcu.ordinal_position""").fetchall()
        dbfks = c.execute("""select cl.relname, a.attname, rcl.relname, ra.attname
                             from pg_constraint co join pg_class cl on cl.oid=co.conrelid
                             join pg_class rcl on rcl.oid=co.confrelid
                             join pg_attribute a on a.attrelid=co.conrelid and a.attnum=co.conkey[1]
                             join pg_attribute ra on ra.attrelid=co.confrelid and ra.attnum=co.confkey[1]
                             where co.contype='f'""").fetchall()
        counts = {}
        for (t,) in c.execute("select table_name from information_schema.tables where table_schema='public' and table_type='BASE TABLE'").fetchall():
            counts[t] = c.execute(f"select count(*) from public.{qident(t)}").fetchone()[0]
    if dataset == "bird":
        desc, fks = _bird_metadata(db_id)
    else:
        desc, fks = _spider_metadata(db_id)
    tables = {}
    for t, cn, ty in cols:
        if t not in counts:
            continue
        tables.setdefault(t, Table(t, {}, [], counts[t]))
        tables[t].columns[cn] = Column(cn, ty, desc.get((t, cn), "") if use_descriptions else "")
    for t, cn in pks:
        if t in tables:
            tables[t].pk.append(cn)
    allfks = []
    for fk in list(fks) + [tuple(x) for x in dbfks]:
        t, c_, rt, rc = fk
        if t in tables and rt in tables and c_ in tables[t].columns and rc in tables[rt].columns and fk not in allfks:
            allfks.append(fk)
    return SemanticLayer(pgdb, dataset, db_id, tables, allfks)


_CACHE = {}
def get(pgdb, dataset, db_id, use_descriptions=True) -> SemanticLayer:
    k = (pgdb, use_descriptions)
    if k not in _CACHE:
        _CACHE[k] = build(pgdb, dataset, db_id, use_descriptions)
    return _CACHE[k]
