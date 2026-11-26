"""Enforcement tests executed AS THE AGENT'S EPHEMERAL ROLE (C3). Requires the experiment cluster."""
import psycopg, pytest
from tse import semantic_layer
from tse.compile import Broker, compile_ddl
from tse.db import connect
from tse.scope import Scope, TableScope

DB, DS, DBID = "spider_concert_singer", "spider", "concert_singer"


@pytest.fixture(scope="module")
def sl():
    return semantic_layer.get(DB, DS, DBID)


@pytest.fixture()
def handle(sl):
    b = Broker(DB)
    scope = Scope({"singer": TableScope(frozenset({"singer_id", "name", "country"}), "lower(\"country\"::text) = lower('France')")})
    h = b.provision("test", scope, "full")
    yield h
    b.teardown(h)
    b.close()


def agent(h):
    return connect(DB, user=h.login, password=h.password)


def test_in_scope_query_works(handle):
    with agent(handle) as c:
        rows = c.execute('select name from singer').fetchall()
    with connect(DB) as a:
        ref = a.execute("select name from public.singer where lower(country)='france'").fetchall()
    assert sorted(rows) == sorted(ref) and len(rows) > 0


def test_out_of_scope_column_fails(handle):
    with agent(handle) as c, pytest.raises(psycopg.errors.UndefinedColumn):
        c.execute('select age from singer').fetchall()


def test_out_of_scope_rows_invisible(handle):
    with agent(handle) as c:
        assert c.execute("select count(*) from singer where country <> 'France'").fetchone()[0] == 0


def test_base_table_denied(handle):
    with agent(handle) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
        c.execute('select * from public.singer').fetchall()


def test_out_of_scope_table_denied(handle):
    with agent(handle) as c, pytest.raises((psycopg.errors.UndefinedTable, psycopg.errors.InsufficientPrivilege)):
        c.execute('select * from concert').fetchall()


def test_set_role_fails(handle):
    with agent(handle) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
        c.execute(f"set role {handle.scope_role}")


def test_set_role_to_user_role_fails(handle):
    with agent(handle) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
        c.execute(f"set role {handle.user_role}")


def test_set_session_authorization_fails(handle):
    with agent(handle) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
        c.execute("set session authorization postgres")


def test_copy_to_file_fails(handle):
    with agent(handle) as c, pytest.raises((psycopg.errors.InsufficientPrivilege, psycopg.errors.ReadOnlySqlTransaction)):
        c.execute("copy (select name from singer) to '/tmp/x.csv'")


def test_copy_from_program_fails(handle):
    with agent(handle) as c, pytest.raises((psycopg.errors.InsufficientPrivilege, psycopg.errors.ReadOnlySqlTransaction)):
        c.execute("copy singer from program 'id'")


def test_pg_read_file_fails(handle):
    with agent(handle) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
        c.execute("select pg_read_file('/etc/passwd')")


def test_pg_stats_reveals_no_out_of_scope_values(handle):
    with agent(handle) as c:
        rows = c.execute("select tablename, attname, most_common_vals::text from pg_stats where schemaname='public'").fetchall()
    assert rows == []  # pg_stats filters by column privilege; the agent role has none on base tables


def test_pg_statistic_denied(handle):
    with agent(handle) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
        c.execute("select * from pg_statistic").fetchall()


def test_cannot_create_objects(handle):
    with agent(handle) as c:
        for stmt in ["create table x(a int)", f"create view {handle.schema}.v as select 1",
                     "create function pg_temp.f() returns int language sql as 'select 1'"]:
            with pytest.raises((psycopg.errors.InsufficientPrivilege, psycopg.errors.ReadOnlySqlTransaction)):
                c.execute(stmt)


def test_cannot_write(handle):
    with agent(handle) as c, pytest.raises((psycopg.errors.ReadOnlySqlTransaction, psycopg.errors.InsufficientPrivilege)):
        c.execute("delete from singer")


def test_search_path_change_does_not_help(handle):
    with agent(handle) as c:
        c.execute("set search_path = public")
        with pytest.raises((psycopg.errors.InsufficientPrivilege, psycopg.errors.UndefinedTable)):
            c.execute("select age from singer").fetchall()


def test_mixing_view_and_base_table_fails(handle):
    with agent(handle) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
        c.execute(f"select v.name, b.age from {handle.schema}.singer v join public.singer b on b.singer_id=v.singer_id").fetchall()


def test_security_barrier_blocks_leaky_function(sl):
    """A leaky function (NOTICE with its argument, tiny cost) must not see rows the view predicate filters out.
    TEMP is granted only for this test (the hardened configuration revokes it); security_barrier must still hold."""
    b = Broker(DB)
    scope = Scope({"singer": TableScope(frozenset({"singer_id", "name", "country"}), "lower(\"country\"::text) = lower('France')")})
    h = b.provision("leaky", scope, "full")
    try:
        with connect(DB) as a:
            a.execute(f'GRANT TEMPORARY ON DATABASE "{DB}" TO {h.scope_role}')
        seen = []
        with connect(DB, user=h.login, password=h.password) as c:
            c.add_notice_handler(lambda d: seen.append(d.message_primary))
            c.execute("set default_transaction_read_only = off")
            c.execute("""create function pg_temp.leak(text) returns boolean language plpgsql cost 0.0000001 as
                         $$ begin raise notice 'LEAK %', $1; return true; end $$""")
            c.execute("select name from singer where pg_temp.leak(country)").fetchall()
        with connect(DB) as a:
            others = {r[0] for r in a.execute("select country from public.singer where lower(country) <> 'france'").fetchall()}
        leaked = {m.replace("LEAK ", "") for m in seen} & others
        assert seen, "leaky function did not run (test is vacuous)"
        assert not leaked, f"security_barrier failed, leaked {leaked}"
    finally:
        with connect(DB) as a:
            a.execute(f'REVOKE TEMPORARY ON DATABASE "{DB}" FROM {h.scope_role}')
        b.teardown(h); b.close()


def test_error_messages_do_not_echo_out_of_scope_values(handle):
    msg = ""
    with agent(handle) as c:
        try:
            c.execute("select cast(name as int) from singer").fetchall()
        except psycopg.Error as e:
            msg = str(e)
    with connect(DB) as a:
        hidden = {r[0] for r in a.execute("select name from public.singer where lower(country) <> 'france'").fetchall()}
    assert not any(x in msg for x in hidden)


def test_view_owned_by_user_role_caps_at_entitlement():
    """Even if the broker wrongly puts a non-entitled column in S(t), the view runs with U's privileges."""
    db, ds, dbid = "spider_dog_kennels", "spider", "dog_kennels"
    sl2 = semantic_layer.get(db, ds, dbid)
    from tse.policies.generate import generate
    E = generate(sl2)["restricted"]
    t = next(t for t in sorted(sl2.tables) if t in E.tables and set(sl2.tables[t].columns) - set(E.tables[t].columns))
    hidden = sorted(set(sl2.tables[t].columns) - set(E.tables[t].columns))[0]
    b = Broker(db)
    h = b.provision("cap", Scope({t: TableScope(frozenset([hidden]), None)}), "restricted")
    try:
        with connect(db, user=h.login, password=h.password) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute(f'select "{hidden}" from "{t}"').fetchall()
    finally:
        b.teardown(h); b.close()


def test_ddl_listing_has_no_superuser_ops():
    from tse.compile import Handle
    h = Handle(DB, "x", "tse_x", "tse_r_x", "tse_l_x", "pw", "u_s_concert_singer_full",
               Scope({"singer": TableScope(frozenset({"name"}), None)}))
    ddl = " ".join(compile_ddl(h)).upper()
    assert "SUPERUSER" not in ddl and "BYPASSRLS" not in ddl and "SECURITY_INVOKER" not in ddl
    assert "SECURITY_BARRIER = TRUE" in ddl and "SET FALSE" in ddl
