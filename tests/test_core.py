"""Unit tests: scope algebra, deterministic inference steps, widening bounds, cleanup, gold extraction,
policies and baselines."""
import pytest
from tse import semantic_layer, gold_scope, infer
from tse.compile import Broker
from tse.scope import Scope, TableScope
from tse.widen import WideningPolicy, handle_request
from tse.policies.generate import generate, is_sensitive
from tse.db import connect

DB, DS, DBID = "spider_concert_singer", "spider", "concert_singer"


@pytest.fixture(scope="module")
def sl():
    return semantic_layer.get(DB, DS, DBID)


# ---------------- scope algebra
def test_intersect_and_union():
    a = Scope({"t": TableScope(frozenset({"x", "y"}), "x > 1"), "u": TableScope(frozenset({"z"}))})
    b = Scope({"t": TableScope(frozenset({"y", "w"}), "y < 3")})
    i = a.intersect(b)
    assert set(i.tables) == {"t"} and i.tables["t"].columns == {"y"} and "x > 1" in i.tables["t"].predicate and "y < 3" in i.tables["t"].predicate
    u = a.union(b)
    assert u.tables["t"].columns == {"x", "y", "w"} and " OR " in u.tables["t"].predicate


def test_union_with_unrestricted_is_unrestricted():
    a = Scope({"t": TableScope(frozenset({"x"}), "x > 1")})
    b = Scope({"t": TableScope(frozenset({"x"}), None)})
    assert a.union(b).tables["t"].predicate is None


# ---------------- semantic layer is automatic
def test_semantic_layer_has_fks_and_no_values(sl):
    assert sl.fks, "FK graph should come from tables.json"
    text = sl.render()
    with connect(DB) as c:
        names = [r[0] for r in c.execute("select name from public.singer").fetchall()]
    assert not any(n in text for n in names if n and len(n) > 3)


def test_bird_descriptions_drop_examples():
    s = semantic_layer.get("bird_formula_1", "bird", "formula_1")
    assert all("example" not in c.description.lower() for t in s.tables.values() for c in t.columns.values())


# ---------------- deterministic inference parts
def test_tokens_and_linking(sl):
    assert infer.tokens("SingerName") == ["singer", "name"]
    assert "singer" in infer.link_tables("How many singers are from France?", sl)
    cols = infer.link_columns("What is the average age of singers?", sl, {"singer"}, lenient=False)
    assert ("singer", "age") in cols


def test_grounding():
    assert infer.grounded("France", "singers from france")
    assert not infer.grounded("Germany", "singers from france")
    assert infer.grounded(2014, "concerts in 2014 or 2015")
    assert not infer.grounded(201, "concerts in 2014")


def test_render_filter_types(sl):
    assert infer.render_filter({"table": "singer", "column": "country", "op": "=", "value": "France"}, sl) == \
        "lower(\"country\"::text) = lower('France')"
    assert infer.render_filter({"table": "singer", "column": "age", "op": ">", "value": "30"}, sl) == '"age" > 30'
    assert infer.render_filter({"table": "singer", "column": "nope", "op": "=", "value": 1}, sl) is None


def test_k_monotone(sl):
    task = {"question": "List names of singers from France older than 30", "evidence": ""}
    prop = {"tables": ["singer"], "columns": [("singer", "name")],
            "filters": [{"table": "singer", "column": "country", "op": "=", "value": "France"},
                        {"table": "singer", "column": "age", "op": ">", "value": 30}]}
    s0, s1, s2 = (infer.assemble(prop, task, sl, k) for k in (0, 1, 2))
    assert s0.column_pairs() <= s1.column_pairs() <= s2.column_pairs()
    assert "30" in s0.tables["singer"].predicate and "30" not in (s1.tables["singer"].predicate or "")
    assert s2.tables["singer"].predicate is None


def test_ungrounded_filter_dropped(sl):
    task = {"question": "List singer names", "evidence": ""}
    prop = {"tables": ["singer"], "columns": [("singer", "name")],
            "filters": [{"table": "singer", "column": "country", "op": "=", "value": "France"}]}
    assert infer.assemble(prop, task, sl, 0).tables["singer"].predicate is None


def test_fk_closure_adds_bridge(sl):
    s = Scope({"singer": TableScope(frozenset({"name"})), "concert": TableScope(frozenset({"concert_name"}))})
    c = infer.fk_closure(s, sl)
    assert "singer_in_concert" in c.tables
    assert {"singer_id"} <= c.tables["singer_in_concert"].columns


def test_restrict_to_entitlement_drops_foreign_predicate():
    s = Scope({"t": TableScope(frozenset({"a", "b"}), '"secret" = 1')})
    E = Scope({"t": TableScope(frozenset({"a"}), None)})
    r = infer.restrict_to_entitlement(s, E)
    assert r.tables["t"].columns == {"a"} and r.tables["t"].predicate is None


# ---------------- widening bounds
def test_widening_bounded_by_entitlement(sl):
    E = Scope({"singer": TableScope(frozenset({"singer_id", "name", "country"}))})
    S = Scope({"singer": TableScope(frozenset({"name"}))})
    audit = []
    new, rec = handle_request({"columns": ["singer.country", "singer.age", "concert.year"], "reason": "need it"},
                              S, E, sl, WideningPolicy("auto"), audit, 0)
    assert rec["granted_columns"] == ["singer.country"]
    assert set(rec["exceeds_entitlement"]) == {"singer.age", "concert.year"}
    assert new.column_pairs() <= E.column_pairs() and audit


def test_widening_requires_reason_and_budget(sl):
    E = sl.all_scope(); S = Scope({"singer": TableScope(frozenset({"name"}))})
    _, r1 = handle_request({"columns": ["singer.age"], "reason": ""}, S, E, sl, WideningPolicy("auto"), [], 0)
    _, r2 = handle_request({"columns": ["singer.age"], "reason": "x"}, S, E, sl, WideningPolicy("auto", budget=1), [], 1)
    _, r3 = handle_request({"columns": ["singer.age"], "reason": "x"}, S, E, sl, WideningPolicy("deny"), [], 0)
    assert r1["decision"] == "denied_no_reason" and r2["decision"] == "denied_budget" and r3["decision"] == "denied_policy"


def test_strict_policy_denies_sensitive():
    assert is_sensitive("email_address") and is_sensitive("dob") and not is_sensitive("concert_name")


def test_widening_applied_in_db(sl):
    b = Broker(DB)
    S = Scope({"singer": TableScope(frozenset({"name"}), None)})
    h = b.provision("w", S, "full")
    try:
        new = Scope({"singer": TableScope(frozenset({"name", "age"}), None)})
        b.widen(h, new)
        with connect(DB, user=h.login, password=h.password) as c:
            assert c.execute("select name, age from singer limit 1").fetchone() is not None
    finally:
        b.teardown(h); b.close()


# ---------------- cleanup
def test_teardown_and_idempotent_cleanup(sl):
    b = Broker(DB)
    hs = [b.provision(f"c{i}", Scope({"singer": TableScope(frozenset({"name"}))}), "full") for i in range(3)]
    b.teardown(hs[0])
    b.teardown(hs[0])  # idempotent
    assert b.cleanup_mine() == 2
    assert b.mine == {}
    for h in hs:  # every object this broker created is gone (other concurrent batches are untouched)
        assert b.conn.execute("select count(*) from pg_namespace where nspname=%s", (h.schema,)).fetchone()[0] == 0
        assert b.conn.execute("select count(*) from pg_roles where rolname in (%s,%s)", (h.login, h.scope_role)).fetchone()[0] == 0
    b.close()


# ---------------- gold extraction
def test_gold_scope_extraction(sl):
    g = gold_scope.extract('SELECT T2."name" FROM "singer_in_concert" AS T1 JOIN "singer" AS T2 ON T1."singer_id" = T2."singer_id" WHERE T2."age" > 30', sl)
    assert g.tables["singer"].columns == {"name", "singer_id", "age"}
    assert g.tables["singer"].predicate is not None and "30" in g.tables["singer"].predicate
    assert g.tables["singer_in_concert"].predicate is None


def test_gold_scope_count_star(sl):
    g = gold_scope.extract('SELECT count(*) FROM "singer"', sl)
    assert set(g.tables) == {"singer"} and len(g.tables["singer"].columns) == 1


# ---------------- policies / baselines
def test_policies_seeded_and_bounded(sl):
    p1, p2 = generate(sl, seed=1), generate(sl, seed=1)
    assert {r: s.to_json() for r, s in p1.items()} == {r: s.to_json() for r, s in p2.items()}
    full = p1["full"].column_pairs()
    assert p1["restricted"].column_pairs() <= full and p1["partition"].column_pairs() <= full


def test_b2_reach_equals_b0():
    from tse.baselines import b2_tool_gate
    tools = b2_tool_gate({"question": "How many singers?"})
    assert "run_query" in tools  # a data task always needs the query tool => reach(B2) = reach(B0) = E(u)


def test_b1_cross_fitting_excludes_own_task():
    from tse.baselines import b1_curated_scope
    sl2 = semantic_layer.get(DB, DS, DBID)
    E = sl2.all_scope()
    tasks = [{"task_id": "a", "pgdb": DB, "fold": 0, "gold_sql": 'SELECT "name" FROM "singer"'},
             {"task_id": "b", "pgdb": DB, "fold": 1, "gold_sql": 'SELECT "concert_name" FROM "concert"'}]
    s = b1_curated_scope(tasks[0], tasks, sl2, E)
    assert "concert" in s.tables and "singer" not in s.tables


def test_results_match_permutation():
    from tse.datasets.tasks import results_match
    assert results_match({(1, "a"), (2, "b")}, {("a", 1), ("b", 2)})
    assert not results_match({(1, "a")}, {("a", 2)})
    assert not results_match(None, {(1,)})
