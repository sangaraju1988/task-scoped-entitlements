"""C4: controlled widening.

The agent emits a structured request: {"columns": ["table.column", ...], "drop_row_filter": ["table", ...],
"reason": "..."}. The broker-side policy check:
  1. BOUND: every requested item must lie in E(u) \\ S(t); items outside E(u) are rejected and logged as
     'exceeds_entitlement' (they can never be granted: the view owner U lacks the privilege anyway).
  2. APPROVAL (simulated user, documented policy):
       auto    approve every in-bound item, at most `budget` approved requests per task, reason non-empty.
       strict  as auto, but items on columns tagged sensitive (policies/generate.py) are denied
               (models a user who refuses to release sensitive fields to an agent).
       deny    never approve (ablation 'no widening').
  3. AUDIT: every request, decision and the resulting scope is appended to the task's audit log.
"""
from __future__ import annotations
import time
from .scope import Scope, TableScope
from .infer import parse_colref
from .policies.generate import is_sensitive


class WideningPolicy:
    def __init__(self, mode="auto", budget=3):
        assert mode in ("auto", "strict", "deny")
        self.mode, self.budget = mode, budget


def handle_request(req: dict, scope: Scope, E: Scope, sl, policy: WideningPolicy, audit: list, n_approved_so_far: int):
    """Return (new_scope, decision_dict). Never returns a scope outside E(u) (column-wise)."""
    rec = {"t": time.time(), "request": req, "granted_columns": [], "granted_row_drops": [],
           "exceeds_entitlement": [], "denied": [], "invalid": []}
    reason = str(req.get("reason", "")).strip()
    new = scope.copy()
    if policy.mode == "deny":
        rec["decision"] = "denied_policy"
        audit.append(rec)
        return scope, rec
    if n_approved_so_far >= policy.budget:
        rec["decision"] = "denied_budget"
        audit.append(rec)
        return scope, rec
    if not reason:
        rec["decision"] = "denied_no_reason"
        audit.append(rec)
        return scope, rec
    for ref in req.get("columns", []) or []:
        p = parse_colref(str(ref), sl)
        if p is None:
            rec["invalid"].append(ref); continue
        t, c = p
        if t not in E.tables or c not in E.tables[t].columns:
            rec["exceeds_entitlement"].append(f"{t}.{c}"); continue
        if t in new.tables and c in new.tables[t].columns:
            continue
        if policy.mode == "strict" and is_sensitive(c, sl.tables[t].columns[c].description):
            rec["denied"].append(f"{t}.{c}"); continue
        new.add_columns(t, [c])
        rec["granted_columns"].append(f"{t}.{c}")
    for t in req.get("drop_row_filter", []) or []:
        t = str(t).strip().strip('"')
        if t in new.tables and new.tables[t].predicate is not None:
            new.set_predicate(t, None)  # E(u)'s row predicate still applies via the view owner's RLS
            rec["granted_row_drops"].append(t)
    granted = bool(rec["granted_columns"] or rec["granted_row_drops"])
    rec["decision"] = "approved" if granted else ("rejected_exceeds" if rec["exceeds_entitlement"] else "nothing_granted")
    # invariant (checked, not assumed): result column set ⊆ E(u)
    assert all(t in E.tables and ts.columns <= E.tables[t].columns for t, ts in new.tables.items() if t not in scope.tables or ts.columns != scope.tables[t].columns)
    audit.append(rec)
    return new, rec
