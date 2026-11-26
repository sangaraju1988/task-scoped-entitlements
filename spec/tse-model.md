# Task-Scoped Entitlements: formal model (C1)

## 1. Objects
* A database instance D over schema 𝓡 = {R₁,…,R_m}; each relation R has attribute set attr(R) and tuple set D(R).
* A **scope** is a map σ: R ↦ (C_R, φ_R) with C_R ⊆ attr(R) and φ_R a predicate over attr(R) (⊤ if absent).
  Its **reach** on D is reach_D(σ) = { (R, π_{C_R}(σ_{φ_R} D(R))) : R ∈ dom σ } — the cells an actor holding
  exactly σ can read. We write cols(σ) = {(R,c): c ∈ C_R} and rows_D(σ,R) = |σ_{φ_R} D(R)|.
* **Entitlement** E(u): the scope the database grants user u (column grants + row-level-security predicate).
* **Task** t: natural-language request with gold query q_t (from the benchmark).
* **Task scope** S(t): the scope provisioned for the agent acting for u on t. Requirement: S(t) ⊑ E(u), where
  σ ⊑ τ iff dom σ ⊆ dom τ and ∀R: C^σ_R ⊆ C^τ_R and φ^σ_R ⇒ φ^τ_R. Intersection σ ⊓ τ = (C^σ ∩ C^τ, φ^σ ∧ φ^τ).

## 2. Sufficiency, needed data, minimality
* **Executability.** q is executable under σ if every attribute q references is in cols(σ) (so q type-checks
  against the views V_σ(R) = π_{C_R} σ_{φ_R} R).
* **Sufficiency.** σ is sufficient for t on D iff q_t is executable under σ and q_t(V_σ(D)) = q_t(D) (result
  sets equal, the benchmark's execution-accuracy criterion). We test sufficiency *by execution*.
* **Needed data** N(t) (gold scope): C_R = attributes of R referenced by q_t (after star expansion);
  φ_R = OR over occurrences of R in q_t of the AND of that occurrence's single-relation, subquery-free
  WHERE / inner-join conjuncts. Unattributable conjuncts are dropped, so N(t) over-approximates what q_t touches;
  this makes OER for baselines *smaller*, never inflated.
* **Minimality.** A sufficient σ is minimal if no σ' ⊏ σ is sufficient (column-wise and row-wise).
  N(t) is sufficient by construction on every task we keep (verified by execution, Section E3) but need not be
  minimal (e.g., a join-key column may be replaceable).

## 3. Over-exposure ratio
For a reach scope ρ (B0: ρ = E(u); TSE: ρ = S(t) ⊓ E(u)) and permitted task t (N(t) ⊑ E(u)):
* OER_col(ρ,t) = |cols(ρ)| / |cols(N(t))|
* OER_row(ρ,t) = Σ_{R∈dom N} rows_D(ρ,R) / Σ_{R∈dom N} max(1, rows_D(N,R))  (row predicates via selectivity)
* OER_cell(ρ,t) = Σ_{R∈dom ρ} |C^ρ_R|·rows_D(ρ,R) / Σ_{R∈dom N} |C^N_R|·max(1, rows_D(N,R))
OER ≥ 1 for sufficient scopes covering N; OER = 1 is ideal. For insufficient scopes OER can be < 1 and is
reported only together with the sufficiency rate.

## 4. Widening
A widening request w = (C_w, Δφ_w, reason) asks for extra columns and/or removal of task row predicates.
The **bound** is W ⊆ E(u) \ S(t): the broker grants only the in-entitlement part w ⊓ E(u); items outside E(u)
are rejected and logged. An approval policy (auto / strict / deny; documented in tse/widen.py) decides the
in-bound part. After approval S'(t) = S(t) ⊔ (w ⊓ E(u)) and still S'(t) ⊑ E(u).

## 5. Trust assumptions
* **A1 (DB correctness).** PostgreSQL correctly enforces column privileges, RLS policies, view ownership
  semantics (a view is evaluated with its owner's privileges) and `security_barrier` predicate ordering.
* **A2 (single credential).** The agent's only database credential is the ephemeral login tse_l_t; the agent
  cannot obtain other credentials or network paths to the database (no superuser, owner, broker or user role).
* **A3 (trusted broker).** The broker process and its credential are not controlled by the adversary; it
  executes the compiler faithfully. The inference LLM may be wrong (and is evaluated), but does not need to be
  trusted for A-guarantee below, because enforcement is bounded by E(u) through view ownership.
* **A4 (no bypass privileges).** Neither the agent role nor the user role U has SUPERUSER, BYPASSRLS,
  table ownership, CREATEROLE, or membership with SET in any other role; PUBLIC has no privilege on base tables.

## 6. Remark (design guarantee — holds by construction under A1–A4; not an empirical result)
*Under A1–A4, every relation the agent can read through any query on its connection is a function of
V_{S'(t)}(D) and of catalog metadata, where S'(t) = S(t) ⊔ approved widenings; in particular the agent reads no
cell outside reach_D(S'(t) ⊓ E(u)).*

Proof sketch. The login tse_l_t holds privileges only through membership (INHERIT, no SET) in tse_r_t, which
holds USAGE on schema tse_t and SELECT on the views V_σ(R) (A2, A4: no other grants; PUBLIC stripped). Base
tables in schema public are not readable (no USAGE/SELECT). Each view is owned by U and, by A1, evaluated with
U's column grants and U's RLS policy, so its output is π_{C_R∩C^E_R} σ_{φ_R ∧ φ^E_R} D(R). security_barrier
ensures user-supplied predicates are evaluated after φ_R (A1), so no function observes filtered tuples. Writes
and object creation are impossible (read-only, no CREATE/TEMP). Widening changes only the views, through the
bound check, so S'(t) ⊑ E(u). ∎

What this does *not* say: it says nothing about (i) whether S(t) is sufficient (empirical; E2/E3), (ii) what can
be inferred from in-scope data (aggregation/inference attacks), (iii) catalog metadata (table/column names in
pg_catalog are readable by every role in PostgreSQL), (iv) timing or other covert channels, (v) what the agent
does with in-scope data (exfiltration of in-scope data), (vi) a malicious user u or a compromised broker.
Empirical attempts to break the Remark are reported in E5(b).

## 7. Complexity note (carefully stated)
Deciding whether a candidate column scope is sufficient for an *arbitrary* SQL query on *all* instances requires
deciding query equivalence/containment under views, which is undecidable for full relational algebra/SQL and
NP-complete already for conjunctive queries (Chandra & Merlin 1977) and for rewriting conjunctive queries using
views (Levy, Mendelzon, Sagiv 1995). Moreover q_t is unknown at inference time (only the NL task is), so S(t)
is a *prediction*. We therefore (a) never claim minimality of inferred scopes, (b) define sufficiency per
instance and test it by execution, and (c) bound the cost of mistakes with widening. Per-instance minimal
column scope for a known q_t is trivial (the referenced attributes); the minimal *row* scope for a known q_t
is the provenance (lineage) of its answer, which we do not compute.

## 8. Failure modes
| Mode | Cause | Effect | Mitigation |
|---|---|---|---|
| Under-scoping | inference misses a column/table/row | query error or wrong answer | widening (bounded, audited); k; better inference model |
| Over-scoping | inference adds unneeded columns/rows (k large, FK closure) | less reduction in OER | lower k; precision-oriented prompts |
| Widening abuse | injected text makes agent request in-entitlement data | data within E(u) released | bound W ⊆ E(u); strict/human approval; budget; audit |
| Broker compromise | attacker controls broker credential | can grant anything U can read | out of scope (A3); broker not superuser, so still ≤ union of user roles it can SET to |
| Misconfigured RLS/grants | E(u) itself wrong | TSE inherits the error (≤ E(u)) | outside TSE; tests in tests/test_enforcement.py |
