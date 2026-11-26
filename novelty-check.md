# Novelty check (stop gate) — 2026-11-26

**Question.** Does any prior work automatically derive a *per-task* row/column (relational) data scope for an LLM agent from the natural-language task (C2) **and** enforce it in the database, independently of the model (C3)?

**Result: gate PASSED.** No work found that does C2+C3 together. Raw search output: `novelty-raw-arxiv.txt`.

## Sources and queries
| Source | Queries (abbreviated) | Notes |
|---|---|---|
| arXiv API | "least privilege" + "text-to-SQL"; "task-scoped" + agent + database; "data minimization" + LLM + agent; "purpose-based access control" + LLM; "row-level security" + LLM; "least privilege" + database + agent; "fine-grained access control" + "text-to-SQL"; "access control" + "LLM agent" + SQL; "dynamic views" + LLM; abs: text-to-SQL + access control; text-to-SQL + privacy + agent; agent + least privilege + data; SQL agent + security; database + prompt injection + SQL; scoped + text-to-SQL; permission + text-to-SQL; data agent + access control | 18 queries |
| OpenAlex (indexes ACM DL, IEEE Xplore, Springer, ACL Anthology, NeurIPS) | least privilege text-to-SQL; access control text-to-SQL LLM; task-scoped permissions LLM agent; data minimization LLM agent database; row-level security LLM; purpose-based access control LLM; least privilege LLM agent database | used in place of dblp |
| Web search (Google-class index; vendor docs and blogs) | LLM agent task-scoped database access least privilege RLS views per task; text-to-SQL least privilege automatically derived views per query | |
| dblp | — | **Not usable**: dblp served a bot-check page to the scripted client. Replaced by OpenAlex. Google Scholar has no API and was not scraped. |

## Closest prior work and why it does not do C2+C3
| Work | What it does | Gap relative to this paper |
|---|---|---|
| IntentCap, arXiv 2609.14631 | LLM-generated, short-lived, task-scoped capability *leases*, narrowed from the user's authority, checked by a deterministic checker, enforced by tool- and OS-level information-flow policies | Closest in spirit (task-scoped narrowing of user authority). Scopes **tools/OS actions**, not relational rows/columns; no DB compilation |
| MiniScope 2512.11147; Progent 2504.11703; AgentSentry 2510.26212; IGAC 2606.22916; AC4A 2603.20933 | Task-centric permissions over **tools/APIs** (hierarchical roles, policy DSLs, intent certificates) | Once `run_query` is allowed, data reach is unchanged |
| SkillScope 2605.05868; AIRGuard 2605.28914; "When Lower Privileges Suffice" (EMNLP Findings 2026) | Least privilege for agent skills/actions/tool selection | Not data-level |
| Fei et al., RBAC text-to-SQL benchmark (PACMMOD 4(4), 2026, DOI 10.1145/3837098; arXiv 2607.22115) | Augments Spider/BIRD with synthesized roles; measures RBAC violations/compliance | Enforces/evaluates the **user's** policy, not a task-minimal subset; no per-task scope inference |
| Klisura et al., Role-Conditioned Refusals (EACL Findings 2026) | LLM refusal behaviour under table/column RBAC on Spider/BIRD | User-policy compliance by the model; no DB-enforced task scope |
| PCC-SQL (IJCNLP-AACL 2026; arXiv 2607.12341) | Constrained decoding that deterministically enforces a **role's** column-use policy | Role policy, not per-task; enforcement in decoder, not DB |
| SecureMCP (Applied Sciences 16(16), 2026; arXiv 2605.05260) | Static RBAC + SQL interceptors in an MCP server for LLM SQL | Static role policy; application-layer checks; no per-task inference |
| MaskSQL 2509.23459 | Abstraction/masking of schema/values sent to a remote LLM | Privacy of prompts to the model, not data reach of the agent |
| GapLeak 2611.22223 | Shows minimization/least privilege for web agents can be bypassed via information gaps | Attack paper; motivates bounded widening (C4) |
| Plan-then-Execute guide 2509.08646 | RBAC upper bound + task-scoped tool assignment | Tool assignment, not relational scope |
| Vendor/practitioner guidance (SurrealDB, Arcade, CockroachLabs, Dremio blogs) | Recommend dedicated low-privilege DB roles per agent, RLS, curated views | Static, hand-written, per role/agent; no automatic per-task derivation or evaluation |
| Classic DB FGAC (Stonebraker 1975; Rizvi et al. 2004; Oracle VPD; Hippocratic DBs; Byun & Li 2008) | Query modification, Truman/non-Truman models, purpose-based access | Machinery we reuse; scopes come from administrators/purposes, not inferred per task from NL |

## Wording consequence
Novelty claims in the paper use "to our knowledge" and are limited to: automatic per-task inference of a relational scope from NL + its compilation to ephemeral DB objects + bounded widening + the measured security/utility tradeoff. Views, RLS, and query modification are **not** claimed as new.
