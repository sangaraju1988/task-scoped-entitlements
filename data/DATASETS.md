# Datasets (verified 2026-11-26)

| Dataset | Version / source | License | Checksum (sha256) | Use |
|---|---|---|---|---|
| BIRD-SQL Mini-Dev | HF `birdsql/bird_mini_dev`, release "Mini-Dev 1024", revision `colleague_review_fixes_20261025`; `data/mini_dev_postgresql.jsonl` (500 questions, native PostgreSQL gold SQL) | CC BY-SA 4.0 (dataset card) | ff8b561724d8e643bc906434e9e612cc43a782a385764f1c288ffe82c73cbc2c (matches official manifest) | 500 tasks (all) |
| BIRD Mini-Dev PostgreSQL databases | Docker Hub `3036197201/bird-mini-dev-postgresql:20261009` (linked from the official dataset card), image `sha256:df7eca15…`; 11 `pg_restore` dumps extracted from `/opt/bird/dumps` and restored into PostgreSQL 16.16 | CC BY-SA 4.0 | image id above | databases |
| BIRD column descriptions + FKs | HF `birdsql/bird_mini_dev` `baseline_inference/schemas/postgresql.json` (example values stripped by our parser) | CC BY-SA 4.0 | — | semantic layer |
| Spider 1.0 | `spider_data.zip` (Google Drive id 1403EGqzIDoHMdQF4c9Bkyl7dZLZ5Wt6J, the official Spider download), dev set: 1,034 questions, 20 databases | CC BY-SA 4.0 (dataset card `xlangai/spider`) | 00636695dabed6b5f4b8328a16b13e069a2f16591d5efcce57660669c85b121b | 500 tasks (stratified sample) |
| Spider official evaluation script | `taoyds/spider` `evaluation.py` (hardness function only) | Apache-2.0 (repo) | c61f18f40bec5af1984af0e8731e678f6cee7976611d910e6e5c144d757fd827 | difficulty labels |
| RBAC benchmark (Fei et al., PACMMOD 2026) | **No public data release found** (web search 2026-11-26) | — | — | not used; synthetic seeded policies instead (`tse/policies/generate.py`) |

## Processing
* **Spider → PostgreSQL** (`tse/datasets/spider_load.py`): identifiers lower-cased; column types inferred from stored values (integer-like strings without leading zeros → bigint); primary keys from `tables.json` declared where data permits; FKs are *not* declared in Postgres (orphans exist) and are read from `tables.json` for the semantic layer.
* **Spider gold SQL** (`tse/datasets/tasks.py`): transpiled SQLite→PostgreSQL with sqlglot 25.34.1; SQLite's rule that a double-quoted token naming no column is a string literal is reproduced. A task is kept only if the PostgreSQL gold result set equals the SQLite gold result set and is non-empty.
  * Spider dev outcome: 881 valid; excluded 66 (PostgreSQL error, e.g. non-standard GROUP BY), 44 (result mismatch SQLite vs PG), 43 (empty gold result: degenerate for execution accuracy).
  * Sample: 500 of 881 by proportional stratified sampling over (hardness × database), seed 20261126.
  * **Development split** (for any tuning after design freeze): the 381 valid Spider dev tasks not in the sample.
* **BIRD**: all 500 Mini-Dev questions; all gold queries execute and are non-empty on our restore (500/500). Difficulty mix of this 2026 revision: 460 challenging, 32 moderate, 8 simple.

## Files
* `data/tasks/tasks_all.jsonl` (sha256 prefix ebd05f78661136c8): every candidate with validation status and reason.
* `data/tasks/tasks.jsonl` (sha256 prefix 729ce62b2ff7e56c): the 1,000 evaluation tasks.
* `data/policies/`: generated entitlements (seed, frac recorded in file name).
