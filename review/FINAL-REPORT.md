# Final report: TSE paper build (IEEE Access)

Date: 2026-11-27. Working repository: `~/Downloads/tse-agents-work` (local git, not pushed). PDF: `paper/main.pdf`
(16 pages). Supplement: `supplement/supplement.pdf`.

## 1. Files created

- **Paper:**
  - `paper/main.tex` and `paper/sections/*.tex` (11 sections)
  - `paper/refs.bib` (76 entries)
  - `paper/numbers.tex` (381 generated macros)
  - `paper/tables/` (14 generated tables and text fragments)
  - `paper/figs/architecture.pdf` and `paper/figs/fig_e1.pdf`
  - `paper/cover-letter.md`
- **Supplement:** `supplement/supplement.tex`
- **Model:** `spec/tse-model.md`
- **Code:**
  - `tse/`: scope, semantic layer, inference, compile/broker, widening, environment, agents (ReAct / LangGraph / Claude), metrics, policies
  - `tests/`: 50 tests
- **Evaluation:**
  - `eval/PREREGISTRATION.md`: committed before any model output; deviations D1-D9 and incidents I1-I2
  - Experiment drivers, `eval/aggregate.py`, `eval/NUMBERS.md`
  - `eval/results/`: raw logs for every run
- **Review:**
  - `review/lessons-audit.md`
  - `review/independent-review.md` and `review/independent-review-round2.md`
  - `review/rebuttal-notes.md`
  - `review/numbers-report.md`, `review/refs-report.md`, `review/overlap-report.md`
  - `review/desk-reject-checklist.md`
  - Check scripts
- **Grounding:** `novelty-check.md`, `references-verified.md`, `data/DATASETS.md`, `paper/IEEE-ACCESS-REQUIREMENTS.md`
- **Repository:** `README.md`, `requirements.txt` (pinned)

## 2. Novelty check

The gate passed: no prior work combines per-task automatic relational scope inference (C2) with database-enforced
ephemeral scopes (C3).

Closest prior work:
- **Agent tool-scoping:** IntentCap, MiniScope, Progent, AgentSentry, IGAC, SecureMCP.
- **Access-controlled text-to-SQL:** Fei et al. (PACMMOD 2026), Klisura et al. (EACL Findings 2026), PCC-SQL (AACL 2026).
- **Per-task policies and minimisation:** Conseca (HotOS'25), AirGapAgent (CCS'24).

The technical delta is stated in Related Work, "What is new …".

## 3. Tests

50 of 50 pass. They include:
- Enforcement as the ephemeral role.
- Two regression tests added this session: DDL injection through a grounded literal, and repeated widening.

## 4. Citations

- **Coverage:** 76 cited, 76 defined, 76 resolved (`review/bib-check-2.txt`: Crossref, arXiv, URL), with DOIs
  wherever one exists.
- **Flagged entries:** six remain flagged CHECK only because of Crossref metadata gaps (e.g., missing co-authors),
  each confirmed against the publisher or RFC text.
- **Additions:** six references added after the first review, each verified in this session.

## 5. Datasets, models, cost

**Datasets**
- BIRD Mini-Dev 2026 PostgreSQL release: 500 tasks.
- Spider dev: 500 sampled from the 881 that validate on PostgreSQL.
- Both CC BY-SA 4.0; checksums are in `data/DATASETS.md`.

**Models**
- Claude Haiku 5.5 and Sonnet 5.5 (Anthropic API, effort "medium").
- qwen3:8b and qwen2.5-coder:7b as agents.
- qwen2.5-coder:7b as the inference model; llama3.2:3b for the ablation (Ollama 0.35.0).

**Software:** PostgreSQL 16.16, LangGraph 1.2.24.

**API spend:** US$60.55 (cap US$95).

## 6. Results summary

All values are in `paper/numbers.tex`, with sources in `eval/NUMBERS.md`.

**Exposure** (`eval/results/e1e3_scopes.jsonl`, `eval/results/e1_postwiden.jsonl`)
- TSE vs full entitlement: 5.0× fewer reachable columns, 24× fewer cells.
- 11.9× fewer cells on tasks whose scope was sufficient.
- About 13–14× fewer cells counting approved widening (exploratory).

**Scope inference**
- Sufficient on 63.9% of tasks.
- k=2: 91.3%. Haiku as inference model: 78.2%.
- Without BIRD hints: 34.0% vs 47.5% on the same hinted tasks (exploratory; `eval/results/e3_nohint.jsonl`).

**Utility** (`eval/results/runs_e2_haiku.jsonl`, `eval/results/runs_e2_sonnet_r.jsonl`)

| Model | Full access | TSE | Change (95% CI) |
|---|---|---|---|
| Haiku 5.5 | 65.8% | 59.3% | −6.5 pp [−9.6, −3.5] |
| Sonnet 5.5 | 83.5% | 72.2% | −11.3 pp [−13.9, −8.7] |

- H2 (non-inferiority within 5 pp) is **not** supported.
- Static role views cost −18.8 pp.
- Against prompt-only scoping with the same widening tool, TSE scored higher: +8.5 pp (Haiku) and +7.0 pp (Sonnet), exploratory.

**Injection** (`eval/results/runs_e5ctx_*.jsonl`, `eval/results/runs_e5wid_*.jsonl`)
- Column-naming injection: exfiltration fell from 91.0% to 27.6% (Sonnet) and from 89.0% to 25.0% (Haiku); Holm-adjusted p < 1e-6.
- Widening-targeted injection under auto-approval: 60.1% (Sonnet) and 71.7% (Haiku).
- With widening denied: 2.6% (exploratory).

**Bypass:** 0 of 928 scripted attempts (32 types × 29 databases).

**Overhead:** median compile 8.4 ms, teardown 4.3 ms.

## 6b. Additions after external review (exploratory; deviations D10-D12)
- Task-grounded approval judge (broker-side, sees only the original task):
  - Replay over logged grants: approved 92.0% of needed columns and 0.6% of canary columns.
  - Live widening attack, exfiltration: 0.0% (Sonnet) and 1.5% (Haiku), against 60.1% and 71.7% under auto approval.
  - Accuracy cost vs auto: -1.0 and -2.0 pp, with CIs including 0.
  - Lexical grounding fails: it approves only 5.7% of needed columns.
- Haiku 5.5 as broker inference model, accuracy vs B0: -3.3 pp [-6.1, -0.5] (Haiku agent, 1,000 tasks) and -7.6 pp
  [-10.8, -4.4] (Sonnet agent, 500 tasks).
- SQL-parsing gate (B4): 0 leaks on the original catalog, but 58/87 leaks via query_to_xml and table_to_xml.
  TSE: 0/87.
- References: OpenFGA task-based authorization and Auth0 blog added (verified); MiniScope pinned to arXiv v2; Sophos
  not cited (unverifiable).
- API spend after additions: see `paper/numbers.tex` (apiSpend).

## 7. Lessons audit

L1-L12 all addressed; 0 blockers (`review/lessons-audit.md`, generated by `review/lessons_audit.py`).

## 8. Independent review

- **Round 1:** major revision, six concerns. All were addressed with new analyses and rewrites (D6, D7, B3W,
  post-widening and per-role exposure, H2 outcome, references, figures).
- **Round 2:** minor revision. Every item was addressed, including the no-hint experiment (D9) and the
  read-only/GUC wording.
- Details: `review/rebuttal-notes.md`.

## 9. Open TODOs (author)

1. **AI-use disclosure.** Review and edit it in the Acknowledgment (placeholder note).
2. **Repository URL.** Push the repository and fill `[REPOSITORY URL TO BE ADDED]`. Choose a code license (README
   placeholder). Git history was rewritten (2026-11-27) so that no commit, message or stored object contains the employer's
   name; old objects were purged.
3. **Biography and photo.** The photo is needed at the final stage.
4. **Suggested reviewers.** Add 3–5 to `paper/cover-letter.md`.
5. **Contact e-mail.** Confirm the address in the author block.
6. **Overlap check.** Done against the local PDFs of prior papers: no shared prose. Paper 06 (aggregation-inference
   authorization) is adjacent but has no overlap.
7. **APC.** About US$2,160 on acceptance.
8. **API key.** Rotate the Anthropic key that was shared in the session.
9. **Co-author decision.** Single-author unless you decide otherwise.
