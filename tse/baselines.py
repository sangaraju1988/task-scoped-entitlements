"""Baselines B1 (static role views) and B2 (tool-level task scoping). Both are *approximations* of the
mechanisms described in vendor guidance / MiniScope / Progent, re-implemented here; not the original systems."""
from __future__ import annotations
import hashlib
from . import gold_scope
from .scope import Scope, TableScope


def fold_of(task_id: str) -> int:
    return int(hashlib.sha256(task_id.encode()).hexdigest(), 16) % 2


_GOLD = {}
def _gold(t, sl):
    if t["task_id"] not in _GOLD:
        _GOLD[t["task_id"]] = gold_scope.extract(t["gold_sql"], sl)
    return _GOLD[t["task_id"]]


def b1_curated_scope(task, all_tasks, sl, E: Scope) -> Scope:
    """Static, role-level curated view: union of the needed columns of the *other fold's* tasks on the same
    database (2-fold cross-fitting, so a task never contributes to its own view), plus key columns of every
    included table, intersected with E(u). Rows: E(u) only (no task predicates). This approximates an
    expertly curated reporting schema built from historical workload, and is optimistic for B1."""
    f = task.get("fold", fold_of(task["task_id"]))
    s = Scope()
    for t in all_tasks:
        if t["pgdb"] != task["pgdb"] or t["task_id"] == task["task_id"] or t.get("fold", fold_of(t["task_id"])) == f:
            continue
        for tb, ts in _gold(t, sl).tables.items():
            s.add_columns(tb, ts.columns)
    for tb in list(s.tables):
        s.add_columns(tb, sl.key_columns(tb) & set(sl.tables[tb].columns))
    out = {}
    for tb, ts in s.tables.items():
        if tb in E.tables and ts.columns & E.tables[tb].columns:
            out[tb] = TableScope(ts.columns & E.tables[tb].columns, None)
    return Scope(out)


def b2_tool_gate(task) -> list:
    """Per-task tool allow-list in the style of task-scoped tool authorization. The task is a data question,
    so the query tool must be allowed; the gate can only remove unrelated tools (none exist here). Data reach
    therefore equals B0 (= E(u)); this is the point the baseline demonstrates."""
    allowed = ["run_query", "submit_answer"]
    return allowed
