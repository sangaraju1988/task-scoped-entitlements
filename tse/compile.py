"""C3: compile a task scope S(t) into ephemeral, database-enforced objects.

The trusted broker (tse_broker: LOGIN CREATEROLE, *not* superuser, no BYPASSRLS) creates, per task:
  schema  tse_<id>                         owned by the broker
  views   tse_<id>.<table>                 WITH (security_barrier), SELECT <scoped cols> FROM public.<table>
                                           WHERE <task predicate>; OWNED BY the user role U, hence evaluated
                                           with U's column grants and U's RLS policies (=> result ⊆ E(u)
                                           even if the broker computed S(t) incorrectly)
  role    tse_r_<id>  NOLOGIN              USAGE on the schema, SELECT on the views, CONNECT on the database
  role    tse_l_<id>  LOGIN (proxy)        member of tse_r_<id> WITH INHERIT TRUE, SET FALSE; search_path and
                                           read-only/timeout settings pinned; password random; VALID UNTIL
The agent's ONLY credential is tse_l_<id>. Teardown terminates its sessions and drops everything (idempotent).
"""
from __future__ import annotations
import hashlib, secrets, time, re
from dataclasses import dataclass, field
from typing import Optional
from .db import connect, qident, qlit
from .scope import Scope, TableScope
from . import config
from .setup_db import get_secrets, user_role

ID_RE = re.compile(r"^[a-z0-9_]+$")


@dataclass
class Handle:
    pgdb: str
    tid: str
    schema: str
    scope_role: str
    login: str
    password: str
    user_role: str
    scope: Scope
    n_objects: int = 0
    timings: dict = field(default_factory=dict)


def view_ddl(schema, table, ts: TableScope):
    cols = ", ".join(qident(c) for c in sorted(ts.columns))
    where = f" WHERE {ts.predicate}" if ts.predicate else ""
    return (f"CREATE OR REPLACE VIEW {qident(schema)}.{qident(table)} WITH (security_barrier = true) AS "
            f"SELECT {cols} FROM public.{qident(table)}{where}")


def compile_ddl(h: Handle):
    """Return the ordered DDL list (for inspection/paper listing; executed by Broker.provision)."""
    s, R, L, U = h.schema, h.scope_role, h.login, h.user_role
    ddl = [f"CREATE SCHEMA {qident(s)}",
           f"GRANT USAGE, CREATE ON SCHEMA {qident(s)} TO {U}",
           f"SET ROLE {U}"]
    ddl += [view_ddl(s, t, ts) for t, ts in sorted(h.scope.tables.items())]
    ddl += ["RESET ROLE",
            f"REVOKE CREATE ON SCHEMA {qident(s)} FROM {U}",
            f"CREATE ROLE {R} NOLOGIN",
            f"GRANT USAGE ON SCHEMA {qident(s)} TO {R}",
            f"SET ROLE {U}",
            f"GRANT SELECT ON ALL TABLES IN SCHEMA {qident(s)} TO {R}",
            "RESET ROLE",
            f"GRANT CONNECT ON DATABASE {qident(h.pgdb)} TO {R}",
            f"CREATE ROLE {L} LOGIN PASSWORD {qlit(h.password)} CONNECTION LIMIT 4 VALID UNTIL 'infinity'",
            f"GRANT {R} TO {L} WITH INHERIT TRUE, SET FALSE",
            f"ALTER ROLE {L} IN DATABASE {qident(h.pgdb)} SET search_path = {qident(s)}",
            f"ALTER ROLE {L} IN DATABASE {qident(h.pgdb)} SET default_transaction_read_only = on",
            f"ALTER ROLE {L} IN DATABASE {qident(h.pgdb)} SET statement_timeout = '60s'"]
    return ddl


class Broker:
    def __init__(self, pgdb: str):
        self.pgdb = pgdb
        self.sec = get_secrets()
        self.conn = connect(pgdb, user=config.BROKER_ROLE, password=self.sec["broker"])
        self.mine = {}  # schema -> (scope_role, login) provisioned by THIS broker and not yet torn down

    def close(self):
        self.conn.close()

    def _ids(self, task_key: str):
        tid = hashlib.sha256(f"{task_key}|{time.time_ns()}|{secrets.token_hex(4)}".encode()).hexdigest()[:12]
        return tid, f"tse_{tid}", f"tse_r_{tid}", f"tse_l_{tid}"

    def provision(self, task_key: str, scope: Scope, role: str) -> Handle:
        t0 = time.perf_counter()
        tid, s, R, L = self._ids(task_key)
        h = Handle(self.pgdb, tid, s, R, L, secrets.token_hex(16), user_role(self.pgdb, role), scope)
        with self.conn.transaction():
            for stmt in compile_ddl(h):
                self.conn.execute(stmt)
        h.n_objects = 1 + len(scope.tables) + 2  # schema + views + 2 roles
        self.mine[s] = (R, L)
        h.timings["compile_ms"] = 1000 * (time.perf_counter() - t0)
        return h

    def widen(self, h: Handle, new_scope: Scope):
        """Replace views so the scope becomes new_scope (columns may only be added; predicates relaxed)."""
        t0 = time.perf_counter()
        with self.conn.transaction():
            self.conn.execute(f"GRANT USAGE, CREATE ON SCHEMA {qident(h.schema)} TO {h.user_role}")
            self.conn.execute(f"SET ROLE {h.user_role}")
            for t, ts in sorted(new_scope.tables.items()):
                old = h.scope.tables.get(t)
                if old is not None and not (old.columns <= ts.columns):
                    raise ValueError("widening may not remove columns")
                if old is not None:
                    # CREATE OR REPLACE VIEW requires existing columns first, in the same order
                    cols = sorted(old.columns) + sorted(ts.columns - old.columns)
                    where = f" WHERE {ts.predicate}" if ts.predicate else ""
                    self.conn.execute(f"CREATE OR REPLACE VIEW {qident(h.schema)}.{qident(t)} WITH (security_barrier = true) AS "
                                      f"SELECT {', '.join(qident(c) for c in cols)} FROM public.{qident(t)}{where}")
                else:
                    self.conn.execute(view_ddl(h.schema, t, ts))
                    self.conn.execute(f"GRANT SELECT ON {qident(h.schema)}.{qident(t)} TO {h.scope_role}")
            self.conn.execute("RESET ROLE")
            self.conn.execute(f"REVOKE CREATE ON SCHEMA {qident(h.schema)} FROM {h.user_role}")
        h.scope = new_scope
        h.n_objects = 1 + len(new_scope.tables) + 2
        h.timings.setdefault("widen_ms", []).append(1000 * (time.perf_counter() - t0))

    def teardown(self, h: Handle):
        t0 = time.perf_counter()
        self._drop(h.schema, h.scope_role, h.login)
        self.mine.pop(h.schema, None)
        h.timings["teardown_ms"] = 1000 * (time.perf_counter() - t0)

    def _drop(self, schema, R, L):
        c = self.conn
        try:
            c.execute("select pg_terminate_backend(pid) from pg_stat_activity where usename = %s", (L,))
        except Exception:
            pass
        c.execute(f"DROP SCHEMA IF EXISTS {qident(schema)} CASCADE")
        for role in (L, R):
            if c.execute("select 1 from pg_roles where rolname=%s", (role,)).fetchone():
                if role == R:
                    c.execute(f"REVOKE CONNECT ON DATABASE {qident(self.pgdb)} FROM {role}")
                c.execute(f"DROP ROLE {role}")

    def cleanup_mine(self):
        """Drop only the objects this broker created and did not tear down (safe with concurrent batches)."""
        n = 0
        for schema, (R, L) in list(self.mine.items()):
            try:
                self._drop(schema, R, L); n += 1
            except Exception:
                self.conn.rollback() if self.conn.info.transaction_status else None
            self.mine.pop(schema, None)
        return n

    def cleanup_all(self):
        """Idempotent removal of any leftover task objects in this database (and their roles)."""
        c = self.conn
        n = 0
        for (s,) in c.execute("select nspname from pg_namespace where nspname ~ '^tse_[0-9a-f]{12}$'").fetchall():
            tid = s[4:]
            self._drop(s, f"tse_r_{tid}", f"tse_l_{tid}"); n += 1
        return n

    def count_task_objects(self):
        c = self.conn
        ns = c.execute("select count(*) from pg_namespace where nspname ~ '^tse_[0-9a-f]{12}$'").fetchone()[0]
        roles = c.execute("select count(*) from pg_roles where rolname ~ '^tse_[rl]_[0-9a-f]{12}$'").fetchone()[0]
        return ns, roles


def cleanup_orphan_roles():
    """Drop task roles whose schema no longer exists in any database (global, run as setup superuser)."""
    with connect("postgres") as c:
        roles = [r[0] for r in c.execute("select rolname from pg_roles where rolname ~ '^tse_[rl]_[0-9a-f]{12}$'").fetchall()]
        dbs = [r[0] for r in c.execute("select datname from pg_database where not datistemplate").fetchall()]
        for r in sorted(roles, key=lambda x: x[4] != "l"):  # logins first
            for d in dbs:
                try:
                    c.execute(f"REVOKE ALL ON DATABASE {qident(d)} FROM {r}")
                except Exception:
                    pass
            c.execute("select pg_terminate_backend(pid) from pg_stat_activity where usename=%s", (r,))
            c.execute(f"DROP ROLE IF EXISTS {r}")
        return len(roles)
