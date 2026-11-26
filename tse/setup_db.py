"""One-time database hardening and entitlement provisioning (run as the setup superuser).

For every task database:
  * all base tables are owned by tse_owner (NOLOGIN); RLS is ENABLED on every table;
  * PUBLIC loses CONNECT/TEMPORARY on the database and all privileges on schema public;
  * each synthetic user role U = u_<db>_<role> (NOLOGIN) receives column-level SELECT grants and one
    permissive SELECT policy per table (USING entitlement predicate or TRUE) -> E(u) enforced by Postgres;
  * a login proxy l_<db>_<role> is a member of U WITH INHERIT TRUE, SET FALSE (cannot SET ROLE);
  * the broker tse_broker (LOGIN, CREATEROLE, not superuser) may SET ROLE U (INHERIT FALSE) so that the views
    it creates for a task are OWNED BY U and are therefore evaluated with U's grants and U's RLS policies.
"""
from __future__ import annotations
import json, os, secrets, sys
from .db import connect, qident, qlit
from . import config, semantic_layer
from .policies import generate as polgen

SECRETS = os.path.join(config.DATA, ".secrets.json")


def get_secrets():
    if os.path.exists(SECRETS):
        return json.load(open(SECRETS))
    s = {"broker": secrets.token_hex(16), "logins": {}}
    json.dump(s, open(SECRETS, "w"))
    os.chmod(SECRETS, 0o600)
    return s


def save_secrets(s):
    json.dump(s, open(SECRETS, "w"))
    os.chmod(SECRETS, 0o600)


def short(db):
    db = db[:-4] if db.endswith("_inj") else db  # canary clones share the source database's roles
    return db.lower().replace("bird_", "b_").replace("spider_", "s_")[:40]


def user_role(pgdb, role):
    return f"u_{short(pgdb)}_{role}"


def login_role(pgdb, role):
    return f"l_{short(pgdb)}_{role}"


def ensure_global_roles(c, sec):
    have = {r[0] for r in c.execute("select rolname from pg_roles").fetchall()}
    if config.OWNER_ROLE not in have:
        c.execute(f"CREATE ROLE {config.OWNER_ROLE} NOLOGIN")
    if config.BROKER_ROLE not in have:
        c.execute(f"CREATE ROLE {config.BROKER_ROLE} LOGIN CREATEROLE PASSWORD {qlit(sec['broker'])}")
    c.execute(f"GRANT pg_signal_backend TO {config.BROKER_ROLE}")  # broker terminates task sessions at teardown


def setup_database(pgdb, dataset, db_id, sec, seed=1, frac=0.25):
    sl = semantic_layer.build(pgdb, dataset, db_id)
    roles = polgen.generate(sl, seed=seed, frac=frac)
    with connect("postgres") as c:
        ensure_global_roles(c, sec)
    with connect(pgdb) as c:
        c.execute(f"REVOKE ALL ON DATABASE {qident(pgdb)} FROM PUBLIC")
        c.execute(f"GRANT CONNECT, CREATE ON DATABASE {qident(pgdb)} TO {config.BROKER_ROLE} WITH GRANT OPTION")
        c.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
        for t in sl.tables:
            c.execute(f"ALTER TABLE public.{qident(t)} OWNER TO {config.OWNER_ROLE}")
            c.execute(f"ALTER TABLE public.{qident(t)} ENABLE ROW LEVEL SECURITY")
            for (pol,) in c.execute("select policyname from pg_policies where schemaname='public' and tablename=%s", (t,)).fetchall():
                c.execute(f"DROP POLICY {qident(pol)} ON public.{qident(t)}")
        existing = {r[0] for r in c.execute("select rolname from pg_roles").fetchall()}
        for role, scope in roles.items():
            U, L = user_role(pgdb, role), login_role(pgdb, role)
            pw = sec["logins"].setdefault(L, secrets.token_hex(16))
            if U not in existing:
                c.execute(f"CREATE ROLE {U} NOLOGIN")
            if L not in existing:
                c.execute(f"CREATE ROLE {L} LOGIN PASSWORD {qlit(pw)}")
            c.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {U}")
            c.execute(f"GRANT CONNECT ON DATABASE {qident(pgdb)} TO {U}")
            c.execute(f"GRANT USAGE ON SCHEMA public TO {U}")
            for t, ts in scope.tables.items():
                cols = ", ".join(qident(x) for x in sorted(ts.columns))
                c.execute(f"GRANT SELECT ({cols}) ON public.{qident(t)} TO {U}")
                c.execute(f"CREATE POLICY {qident('e_' + role)} ON public.{qident(t)} FOR SELECT TO {U} "
                          f"USING ({ts.predicate or 'true'})")
            c.execute(f"GRANT {U} TO {L} WITH INHERIT TRUE, SET FALSE")
            c.execute(f"GRANT {U} TO {config.BROKER_ROLE} WITH INHERIT FALSE, SET TRUE")
            c.execute(f"ALTER ROLE {L} IN DATABASE {qident(pgdb)} SET default_transaction_read_only = on")
            c.execute(f"ALTER ROLE {L} IN DATABASE {qident(pgdb)} SET statement_timeout = '60s'")
    return roles


def main():
    sec = get_secrets()
    tasks = [json.loads(l) for l in open(os.path.join(config.DATA, "tasks", "tasks.jsonl"))]
    dbs = sorted({(t["pgdb"], t["dataset"], t["db_id"]) for t in tasks})
    allpol = {}
    for pgdb, ds, db_id in dbs:
        roles = setup_database(pgdb, ds, db_id, sec)
        allpol[pgdb] = polgen.policies_to_json(roles)
        print(pgdb, {r: (len(s.tables), len(s), any(ts.predicate for ts in s.tables.values())) for r, s in roles.items()}, flush=True)
    save_secrets(sec)
    os.makedirs(os.path.join(config.DATA, "policies"), exist_ok=True)
    json.dump(allpol, open(os.path.join(config.DATA, "policies", "policies_seed1_frac0.25.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
