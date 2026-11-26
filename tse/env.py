"""Per-(task, condition) agent environment: credentials, visible schema, and the three tools.

Conditions
  B0   full entitlement: agent connects as the user's login proxy (grants + RLS = E(u)); sees E(u) schema.
  B1   static role view (approximation of vendor scoped-view practice): a role-level curated scope built by
       2-fold cross-fitting from the gold columns of *other* tasks on the same database/role, compiled with
       the same broker; sees that schema.
  B2   tool-level task scoping (approximation of MiniScope/Progent-style gating): a per-task tool allow-list
       is computed; `run_query` is necessarily allowed for every data task, so data reach equals B0.
  B3   prompt-level schema pruning: B0 credentials, but the prompt shows only the inferred scope S(t).
  TSE  ours: broker-compiled S(t); the agent's only credential is the ephemeral login; may request widening.
"""
from __future__ import annotations
import json, time, re
from .db import connect
from .compile import Broker, Handle
from .scope import Scope
from .setup_db import get_secrets, login_role
from . import widen as widen_mod
from .datasets.tasks import result_set, norm_val

MAX_ROWS_SHOWN = 20


class Env:
    def __init__(self, task, condition, sl, E: Scope, role: str, scope: Scope = None, widening_policy=None,
                 broker: Broker = None, pgdb_override: str = None):
        self.task, self.condition, self.sl, self.E, self.role = task, condition, sl, E, role
        self.pgdb = pgdb_override or task["pgdb"]
        self.audit, self.queries, self.n_approved = [], [], 0
        self.widening_policy = widening_policy
        self.handle: Handle = None
        self.broker = broker
        self.t_setup = time.perf_counter()
        if condition in ("B0", "B2", "B3"):
            self.login, self.password = login_role(task["pgdb"], role), get_secrets()["logins"][login_role(task["pgdb"], role)]
            self.visible = scope if condition == "B3" else E
            self.reach = E
        elif condition in ("B1", "TSE"):
            assert scope is not None and broker is not None
            self.handle = broker.provision(task["task_id"], scope, role)
            self.login, self.password = self.handle.login, self.handle.password
            self.visible = scope
            self.reach = scope
        else:
            raise ValueError(condition)
        self.setup_ms = 1000 * (time.perf_counter() - self.t_setup)
        self._connect()

    def _connect(self):
        self.conn = connect(self.pgdb, user=self.login, password=self.password)
        self.conn.execute("SET statement_timeout = 30000")
        if self.condition in ("B0", "B2", "B3"):
            self.conn.execute("SET search_path = public")

    # ------------------------------------------------------------------ tools
    @property
    def can_widen(self):
        return self.condition == "TSE" and self.widening_policy is not None

    def schema_text(self):
        return self.sl.render(self.visible)

    def run_query(self, sql: str) -> str:
        t0 = time.perf_counter()
        rec = {"sql": sql}
        try:
            cur = self.conn.execute(sql)
            rows = cur.fetchmany(MAX_ROWS_SHOWN + 1) if cur.description else []
            cols = [d.name for d in cur.description] if cur.description else []
            rec.update(ok=True, n_shown=min(len(rows), MAX_ROWS_SHOWN), columns=cols)
            more = len(rows) > MAX_ROWS_SHOWN
            rows = rows[:MAX_ROWS_SHOWN]
            out = "columns: " + json.dumps(cols) + "\n" + "\n".join(json.dumps([norm_val(v) for v in r], default=str) for r in rows)
            if more:
                out += f"\n... (more rows; showing first {MAX_ROWS_SHOWN})"
            if not rows:
                out += "\n(0 rows)"
        except Exception as e:
            msg = str(e).splitlines()[0][:300]
            rec.update(ok=False, error=type(e).__name__ + ": " + msg)
            out = "ERROR: " + msg
            try:
                if self.conn.closed or self.conn.broken:
                    self._connect()
                elif self.conn.info.transaction_status != 0:
                    self.conn.rollback()
            except Exception:
                self._connect()
        rec["ms"] = 1000 * (time.perf_counter() - t0)
        rec["result_text"] = out[:4000]
        self.queries.append(rec)
        return out[:3000]

    def request_access(self, columns=None, drop_row_filter=None, reason="") -> str:
        if not self.can_widen:
            return "ERROR: access requests are not available."
        req = {"columns": columns or [], "drop_row_filter": drop_row_filter or [], "reason": reason}
        new, rec = widen_mod.handle_request(req, self.handle.scope, self.E, self.sl, self.widening_policy,
                                            self.audit, self.n_approved)
        if rec["decision"] == "approved":
            self.broker.widen(self.handle, new)
            self.n_approved += 1
            self.visible = new
            self.reach = new
            return ("APPROVED. Granted columns: " + json.dumps(rec["granted_columns"]) +
                    ("; row filters removed on: " + json.dumps(rec["granted_row_drops"]) if rec["granted_row_drops"] else "") +
                    "\nUpdated visible schema:\n" + self.schema_text())
        return (f"DENIED ({rec['decision']}). " + (f"Outside your entitlement: {rec['exceeds_entitlement']}. " if rec["exceeds_entitlement"] else "")
                + (f"Denied by policy: {rec['denied']}. " if rec["denied"] else "")
                + (f"Unknown: {rec['invalid']}." if rec["invalid"] else ""))

    # ------------------------------------------------------------------ evaluation
    def evaluate_sql(self, sql: str):
        """Execute the final SQL with the agent's final credentials; return (result_set or None, error)."""
        if not sql or not sql.strip():
            return None, "empty"
        try:
            with connect(self.pgdb, user=self.login, password=self.password) as c:
                c.execute("SET statement_timeout = 60000")
                if self.condition in ("B0", "B2", "B3"):
                    c.execute("SET search_path = public")
                cur = c.execute(sql)
                return result_set(cur.fetchall() if cur.description else []), None
        except Exception as e:
            return None, type(e).__name__ + ": " + str(e).splitlines()[0][:200]

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
        if self.handle is not None:
            try:
                self.broker.teardown(self.handle)
            except Exception as e:  # recorded; leftover objects are removed by Broker.cleanup_all at batch end
                self.handle.timings["teardown_error"] = type(e).__name__ + ": " + str(e)[:200]
                try:
                    self.broker.conn.rollback()
                except Exception:
                    pass
