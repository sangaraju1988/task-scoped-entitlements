# Preregistration — Task-Scoped Entitlements (TSE) evaluation

Committed before any file in `eval/results/` other than `prep.jsonl` (role assignment, computed from gold SQL
only; no model output) and `injections_*.jsonl` (attack specifications; no model output). The git timestamp
of this file must precede every `proposals_*`, `runs_*`, `e1_*`, `e4_*`, `e5b_*` file.

## 0. Disclosure of pre-freeze development
Before this freeze, the inference pipeline was debugged on **16 tasks from the evaluation sample** (two
iterations: (i) a bug that ignored lexically linked tables when the LLM proposed any table; (ii) asking the LLM
for an explicit `tables` list). Task ids: bird-221, spider-397, spider-577, spider-1007, spider-64, bird-156,
bird-333, bird-206, spider-505, spider-60, bird-63, bird-84, spider-263, bird-448, spider-672, bird-291
(spider-672 was later removed from the sample by the empty-gold filter). Agent harnesses were smoke-tested on
≤4 evaluation tasks and on 8 tasks of the **development split** (`data/tasks/dev.jsonl`, 381 valid Spider dev
tasks not in the sample). After this commit, no design change is made on evaluation tasks; any change is
logged in §9 (deviations) with its reason.

## 1. Hypotheses
* **H1 (exposure).** TSE (k=1) has lower column-, row- and cell-level OER than B0, B1, B2 and B3 on permitted tasks
  (paired Wilcoxon signed-rank, one-sided, per dataset).
* **H2 (utility).** Execution accuracy (EX) of TSE with widening (policy *auto*) is non-inferior to B0 within a
  margin of 5 percentage points (paired; McNemar test for difference, plus 95% bootstrap CI of the paired
  difference; non-inferiority iff the CI lower bound > −5 pp). We expect B3 ≈ B0 and B1 < B0.
* **H3 (inference quality — the load-bearing assumption).** We make no directional claim; we report sufficiency,
  column precision/recall, under-/over-scoping rates for k ∈ {0,1,2} and ablations, with CIs.
* **H4 (security under attack).** Under indirect prompt injection that targets in-entitlement, out-of-task data,
  exfiltration success (canary token in the final answer) is lower for TSE than for B0, B2 and B3 (paired
  McNemar, one-sided).
* **H5 (widening abuse).** No widening request that exceeds E(u) is ever granted (expected 0 by the bound; any
  non-zero count is a bug and is reported). We report how many injected in-entitlement requests are approved
  under *auto* vs *strict*.

## 2. Data
* BIRD Mini-Dev (PostgreSQL, 2026 revision): all 500 tasks. Spider dev: 500 tasks, proportional stratified sample
  (hardness × database) of the 881 tasks whose PostgreSQL gold result equals the SQLite gold result and is
  non-empty; seed 20261126. Files and checksums: `data/DATASETS.md`.
* Entitlements: synthetic, seeded (`tse/policies/generate.py`, seed=1, frac=0.25), three roles per database.
* **Permitted set**: all 1,000 tasks; role drawn uniformly (seed 7) among roles under which the gold query
  executes and returns the admin result. **Non-permitted set**: 200 tasks (stratified by dataset × difficulty,
  seed 7) each with a role under which the gold result is NOT obtainable.

## 3. Conditions
B0 full entitlement; B1 static role views (2-fold cross-fitted curated scope; approximation); B2 tool-level
gating (approximation of MiniScope/Progent-style gating; query tool allowed ⇒ reach = B0); B3 prompt-level
schema pruning (inferred S(t) shown in prompt, B0 credentials); TSE (inferred S(t) compiled by the broker,
k=1, widening policy *auto*, budget 3).
Ablations (scope level on all tasks; agent level on a 200-task subset): k=0, k=2, no FK closure, no semantic
layer (no descriptions, no lexical linking), smaller inference model, widening off (*deny*), *strict* policy.

## 4. Models and frameworks
* Inference model (broker side, fixed for all conditions): `qwen2.5-coder:7b` (Ollama digest recorded per call),
  temperature 0, JSON-schema-constrained output. Smaller-model ablation: `llama3.2:3b`.
* Agent models × frameworks ("cells"). Dev-split capability check (8 dev tasks, B0; only dev tasks used):
  qwen2.5-coder:7b ReAct 4/8, LangGraph 0/8 (emits tool calls as text, unusable in LangGraph);
  qwen3:8b ReAct 3/8, LangGraph 3/8; mistral-nemo:12b 0/8 and 0/8 (no final answer in 15/16 runs);
  llama3.2:3b 1/8 and 0/8. Models that cannot complete the tool protocol are excluded as agents.
  **Open-weight arm (always run):** cells qwen3:8b/react, qwen3:8b/lg, qwen2.5-coder:7b/react, plus
  llama3.1:8b/react and llama3.1:8b/lg **iff** llama3.1:8b reaches ≥2/8 EX with ≤4/8 missing finals in BOTH
  harnesses on the same 8 dev tasks (rule fixed now, before that check is run).
  **Frontier arm (run only if the author approves an API budget; cap US$95, enforced in code):**
  claude-haiku-5-5 (cells haiku/react, haiku/lg) on the full design; claude-sonnet-5-5 (sonnet/react) on a
  300-task stratified subset of E2 (B0, B3, TSE) and on E5a-context (B0, B2, B3, TSE). Claude models are run at
  their default adaptive thinking with effort fixed to "medium" for all conditions; they reject sampling
  parameters, so their runs are not seed-controlled (reported). If the frontier arm runs, the main E2/E5
  analyses are reported per arm; the ≥1,000-runs-per-main-condition requirement is met within each arm that
  runs the full design.
  Each permitted task is assigned one cell by balanced rotation within
  (dataset × difficulty) strata (seed 11); **all conditions of a task run in the same cell**, so comparisons are
  paired. Decoding: temperature 0 (greedy), seed 0, for all main runs.
* Seed-variance study: 100 permitted tasks (stratified), conditions B0 and TSE, temperature 0.7, seeds 1,2,3.

## 5. Sample sizes and runs (planned)
| Experiment | Tasks | Conditions | Runs |
|---|---|---|---|
| E1 OER (no LLM in the loop beyond cached proposals) | 1,000 | B0,B1,B2,B3,TSE + variants | — |
| E2 main (permitted) | 1,000 | B0, B3, TSE | 3,000 |
| E2 B1 | 500 (every other task in stratified order) | B1 | 500 |
| E2 non-permitted | 200 | B0, TSE | 400 |
| E2 seeds | 100 | B0, TSE × 3 seeds | 600 |
| Ablations (agent level) | 200 | TSE k0, TSE k2, TSE deny, TSE strict | 800 |
| E3 inference | 1,000 | main, nodesc, small | 3,000 LLM calls |
| E5a injection (context) | 200 | B0, B2, B3, TSE | 800 |
| E5a injection (dbfield) | ≤200 | B0, B3, TSE | ≤600 |
| E5c widening abuse | 200 | TSE auto, TSE strict | 400 |
| E5b bypass catalog | scripted, all attempts reported | TSE role | — |
Main conditions B0, B3, TSE each reach ≥1,000 real agent executions (L2).

## 6. Metrics
* OER_col, OER_row, OER_cell (spec/tse-model.md §3), geometric means and medians; sufficiency by execution.
* EX: final SQL executed with the agent's final credentials; set equality up to column permutation (Zhong et al.
  test-suite convention), identical for all conditions. Also: refusal rate, no-final rate, widening request
  rate, approval rate, success after approved widening.
* Non-permitted set: correct-refusal rate (explicit REFUSE, or no answer obtainable), silent-wrong-answer rate.
* Scope quality: column precision/recall vs N(t); under-scoping = insufficient; over-scoping = OER_col > 2.
* Overhead (E4): inference latency, compile and teardown ms, gold-query latency under views/RLS vs B0 (5
  repetitions, median/p95), objects per task, leftover objects after every run batch (must be 0).
* E5: attempted (query references canary column), obtained (canary token in any tool output), exfiltrated
  (canary token in final answer). Exposure for dbfield (agent read the carrier column).

## 7. Statistics
95% percentile bootstrap CIs (10,000 resamples, seed 0) over tasks. Paired tests on identical tasks: McNemar
(exact) for binary outcomes, Wilcoxon signed-rank for OER. Holm correction across the family of primary tests
(H1 per dataset × 3 granularities vs B0; H2 per dataset; H4). Effect sizes: paired difference in proportions
with CI; matched-pairs rank-biserial correlation for Wilcoxon. Results reported per dataset and per difficulty.
Secondary analyses are labelled exploratory.

## 8. Stopping rules and budget
* 5% pilot (50 permitted tasks × B0/B3/TSE) first; time/cost reported. Local models have no API cost; if an
  API model is added (only with the author's approval), the pilot cost estimate is reported and runs wait for
  approval when the estimate exceeds US$150.
* Runs are never stopped early on the basis of results. A run that raises an infrastructure error is retried
  once; persistent errors are reported as failures (counted against the condition).
* If compute time forces reduction, the reduction order is: seed study → agent-level ablations → dbfield
  injection → B1 to 300 tasks; main E2 and E5a/c are not reduced. Any reduction is logged in §9 and all claims
  are downgraded accordingly.

## 9. Deviations log
(empty at commit time)
