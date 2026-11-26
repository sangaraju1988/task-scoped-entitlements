"""C2: infer a task scope S(t) from the natural-language task.

    S_k(t) = Close_FK( Assemble_k( LLM-proposal ∪ SchemaLink_k ) )  ∩  E(u)

Conservativeness k (monotone: S_0 ⊆ S_1 ⊆ S_2 column-wise and row-wise):
  k=0  columns: LLM proposal ∪ strict lexical links;           rows: every grounded filter
  k=1  columns: + lenient lexical links + key columns of every included table;
       rows: only grounded equality / IN filters (range filters dropped)
  k=2  columns: every column of every included table;          rows: no task filters
A filter is *grounded* only if its literal value occurs verbatim (case-insensitive) in the task text, so an
LLM cannot invent row restrictions that are not stated in the task. Every deterministic step is unit-tested.
"""
from __future__ import annotations
import json, re, time
from typing import Optional
from .scope import Scope, TableScope, _and
from .db import qident, qlit

STOP = set("""a an the of in on at to for from by with and or not is are was were be been being what which who whom
whose how many much list give show find return all each every per than that this these those their its there
as into over under between among do does did have has had please any some most least more less top first last
number count total average avg sum max min value values""".split())
GENERIC = {"id", "code", "name", "num", "no", "type", "key", "date", "desc", "description", "value", "info", "text"}
NUMTYPES = ("integer", "bigint", "smallint", "real", "double precision", "numeric", "decimal")


def _stem(w: str) -> str:
    for suf in ("ies", "ing", "es", "ed", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def tokens(s: str):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s or "")
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", s.lower())]


def content_tokens(s: str):
    return [w for w in tokens(s) if w not in STOP]


# ---------------------------------------------------------------- schema linking (deterministic)
def link_tables(text: str, sl) -> set:
    tt = set(content_tokens(text))
    out = set()
    for t in sl.tables:
        nt = [w for w in content_tokens(t) if w not in GENERIC]
        if nt and all(w in tt for w in nt):
            out.add(t)
    return out


def link_columns(text: str, sl, tables: set, lenient: bool) -> set:
    tt = set(content_tokens(text))
    low = " " + " ".join(tokens(text)) + " "
    out = set()
    for t in tables:
        for c, col in sl.tables[t].columns.items():
            nt = [w for w in content_tokens(c) if w not in GENERIC]
            phrase = " " + " ".join(tokens(c)) + " "
            hit = False
            if nt and all(w in tt for w in nt):
                hit = True
            elif len(phrase.strip()) > 3 and phrase in low:
                hit = True
            elif lenient:
                if nt and sum(w in tt for w in nt) / len(nt) >= 0.5:
                    hit = True
                dt = [w for w in content_tokens(col.description) if w not in GENERIC]
                if len(dt) >= 2 and sum(w in tt for w in dt) / len(dt) >= 0.6:
                    hit = True
            if hit:
                out.add((t, c))
    return out


# ---------------------------------------------------------------- filters (grounding + rendering)
def grounded(value, text: str) -> bool:
    if value is None:
        return False
    v = str(value).strip().strip("%").strip()
    if not v:
        return False
    low = text.lower()
    if isinstance(value, (int, float)) or re.fullmatch(r"-?\d+(\.\d+)?", v):
        return re.search(r"(?<![0-9.])" + re.escape(v) + r"(?![0-9])", low) is not None
    return v.lower() in low


def render_filter(f: dict, sl) -> Optional[str]:
    t, c, op = f.get("table"), f.get("column"), str(f.get("op", "=")).upper().strip()
    if t not in sl.tables or c not in sl.tables[t].columns:
        return None
    ty = sl.tables[t].columns[c].type
    col = qident(c)
    vals = f.get("value")
    if op == "IN":
        vals = vals if isinstance(vals, list) else [vals]
        if not vals:
            return None
        if ty in NUMTYPES:
            try:
                return f"{col} IN ({', '.join(repr(float(v)) if '.' in str(v) else str(int(float(v))) for v in vals)})"
            except Exception:
                return None
        return f"lower({col}::text) IN ({', '.join('lower(' + qlit(str(v)) + ')' for v in vals)})"
    if isinstance(vals, list):
        return None
    if op in ("=", "==", "!=", "<>", "<", "<=", ">", ">="):
        op = {"==": "="}.get(op, op)
        if ty in NUMTYPES:
            try:
                num = float(vals)
                lit = str(int(num)) if num.is_integer() else repr(num)
            except Exception:
                return None
            return f"{col} {op} {lit}"
        if op in ("=", "!=", "<>"):
            return f"lower({col}::text) {op} lower({qlit(str(vals))})"
        return f"{col} {op} {qlit(str(vals))}"
    if op in ("LIKE", "ILIKE"):
        return f"{col}::text ILIKE {qlit(str(vals))}"
    return None


# ---------------------------------------------------------------- LLM proposal
SYSTEM = """You plan least-privilege data access for an analytics agent. Given a database schema and a task, list
ONLY the columns needed to answer the task (including columns needed for joins, filters, grouping and ordering),
and the row filters that the task states explicitly with a literal value. Use exact table and column names from
the schema. Output JSON only."""

FORMAT = {"type": "object", "properties": {
    "tables": {"type": "array", "items": {"type": "string"}},
    "columns": {"type": "array", "items": {"type": "string"}},
    "filters": {"type": "array", "items": {"type": "object", "properties": {
        "table": {"type": "string"}, "column": {"type": "string"}, "op": {"type": "string"},
        "value": {}}, "required": ["table", "column", "op", "value"]}}},
    "required": ["tables", "columns", "filters"]}


def task_text(task) -> str:
    return task["question"] + ((" Hint: " + task["evidence"]) if task.get("evidence") else "")


def parse_colref(s: str, sl):
    s = s.strip().strip('"')
    m = re.match(r'^"?([^".]+)"?\s*\.\s*"?(.+?)"?$', s)
    if not m:
        return None
    t, c = m.group(1).strip(), m.group(2).strip().strip('"')
    tl = {x.lower(): x for x in sl.tables}
    if t.lower() not in tl:
        return None
    t = tl[t.lower()]
    cl = {x.lower(): x for x in sl.tables[t].columns}
    if c.lower() not in cl:
        return None
    return (t, cl[c.lower()])


def llm_propose(task, sl, llm):
    prompt = (f"Schema:\n{sl.render()}\n\nTask: {task_text(task)}\n\nReturn JSON with keys 'tables' (every table the "
              f"query must read, including bridge tables needed to join), 'columns' (list of \"table.column\") and "
              f"'filters' (list of {{table, column, op, value}}).")
    msg = llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}], fmt=FORMAT, max_tokens=600)
    raw = msg.get("content", "")
    try:
        d = json.loads(raw)
    except Exception:
        return {"tables": [], "columns": [], "filters": [], "raw": raw, "parse_error": True}
    cols = [p for p in (parse_colref(x, sl) for x in d.get("columns", []) if isinstance(x, str)) if p]
    tl = {x.lower(): x for x in sl.tables}
    tabs = sorted({tl[x.strip().strip('"').lower()] for x in d.get("tables", []) or [] if isinstance(x, str) and x.strip().strip('"').lower() in tl})
    filters = []
    for f in d.get("filters", []) or []:
        if isinstance(f, dict):
            ref = parse_colref(f"{f.get('table', '')}.{f.get('column', '')}", sl)
            if ref:
                filters.append({**f, "table": ref[0], "column": ref[1]})
    return {"tables": tabs, "columns": cols, "filters": filters, "raw": raw, "parse_error": False}


# ---------------------------------------------------------------- assembly + closure
def fk_closure(scope: Scope, sl) -> Scope:
    """Connect all scope tables through shortest FK paths (greedy Steiner approximation); add every
    intermediate table and the join-key columns of each hop. Predicates are untouched."""
    out = scope.copy()
    tabs = sorted(out.tables, key=lambda t: (-len(out.tables[t].columns), t))
    if len(tabs) < 2:
        return out
    tree = {tabs[0]}
    for t in tabs[1:]:
        if t in tree:
            continue
        best = None
        for u in sorted(tree):
            p = sl.fk_path(u, t)
            if p is not None and (best is None or len(p) < len(best)):
                best = p
        if best is None:
            tree.add(t)
            continue
        for t1, c1, t2, c2 in best:
            out.add_columns(t1, [c1]); out.add_columns(t2, [c2])
            tree.update([t1, t2])
    return out


def assemble(proposal, task, sl, k: int, use_linking: bool = True) -> Scope:
    text = task_text(task)
    cols = set(proposal["columns"])
    tables = {t for t, _ in cols} | set(proposal.get("tables", []))
    if use_linking:
        tables |= link_tables(text, sl)
        cols |= link_columns(text, sl, tables, lenient=(k >= 1))
    if not cols and not tables:  # nothing usable: empty scope (agent must request widening)
        return Scope()
    s = Scope()
    for t, c in sorted(cols):
        s.add_columns(t, [c])
    for t in sorted(tables - set(s.tables)):  # table named but no column chosen: its key columns
        keys = sl.key_columns(t) & set(sl.tables[t].columns)
        s.add_columns(t, keys or set(list(sl.tables[t].columns)[:1]))
    if k >= 1:
        for t in list(s.tables):
            s.add_columns(t, sl.key_columns(t) & set(sl.tables[t].columns))
    if k >= 2:
        for t in list(s.tables):
            s.add_columns(t, sl.tables[t].columns.keys())
    if k <= 1:
        for f in proposal["filters"]:
            t = f["table"]
            if t not in s.tables:
                continue
            op = str(f.get("op", "=")).upper().strip()
            vals = f.get("value") if isinstance(f.get("value"), list) else [f.get("value")]
            if not all(grounded(v, text) for v in vals):
                continue
            s.add_columns(t, [f["column"]])  # the agent needs the column even if the row filter is dropped
            if k == 1 and op not in ("=", "==", "IN"):
                continue
            pred = render_filter(f, sl)
            if pred:
                s.add_columns(t, [f["column"]])
                s.set_predicate(t, _and(s.tables[t].predicate, pred))
    return s


def restrict_to_entitlement(s: Scope, E: Scope) -> Scope:
    """S ∩ E (columns). Task predicates that reference non-entitled columns are dropped (the row
    entitlement itself is enforced by the database through the view owner's RLS policy)."""
    out = {}
    for t, ts in s.tables.items():
        if t not in E.tables:
            continue
        cols = ts.columns & E.tables[t].columns
        if not cols:
            continue
        pred = ts.predicate
        if pred:
            refd = set(re.findall(r'"((?:[^"]|"")+)"', pred))
            if not refd <= set(E.tables[t].columns):
                pred = None
        out[t] = TableScope(cols, pred)
    return Scope(out)


def infer(task, sl, E: Scope, llm, k: int = 1, use_linking=True, use_closure=True, proposal=None):
    t0 = time.perf_counter()
    if proposal is None:
        proposal = llm_propose(task, sl, llm)
    t1 = time.perf_counter()
    s = assemble(proposal, task, sl, k, use_linking)
    if use_closure:
        s = fk_closure(s, sl)
    s = restrict_to_entitlement(s, E)
    return s, proposal, {"llm_ms": 1000 * (t1 - t0), "post_ms": 1000 * (time.perf_counter() - t1)}
