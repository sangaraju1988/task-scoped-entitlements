# Desk-reject checklist (IEEE Access)

Checked 2026-11-27 against `paper/main.pdf` (16 pages) and `paper/IEEE-ACCESS-REQUIREMENTS.md`.

| Item | Status | Evidence |
|---|---|---|
| Within IEEE Access scope | ✅ | Security of computing systems / databases / AI; multidisciplinary, applied, with evaluation |
| Template followed | ✅ | Official `ieeeaccess.cls` (unmodified); review version: volume/year footer, DOI and history lines suppressed in `main.tex`, to be restored by the editorial office on acceptance |
| Abstract within limit | ✅ | Single paragraph, about 242 words in the rendered PDF (limit 150-250); no citations or abbreviations left undefined |
| Keywords present | ✅ | 8 index terms (limit 3-10) |
| Figures legible | ✅ | Fig. 1 and Fig. 3 redrawn at two-column width with fonts of at least 7 pt; grayscale-safe; round-2 review checks layout |
| References formatted with DOIs | ✅ | 76 entries, IEEEtran style; every entry resolved (`review/bib-check-2.txt`); DOIs wherever one exists; preprints carry arXiv IDs |
| Limitations present | ✅ | Section "Limitations" (benchmarks, synthetic policies, approximated baselines, PostgreSQL only, single-query tasks, fixed attacks, implementation defects, run variance, deviations) |
| Ethics / AI disclosure present | ⚠️ author | The Acknowledgment contains the AI-use disclosure; **the author must review and edit it** (placeholder note) |
| Data and code statement present | ⚠️ author | The statement is present; **the repository URL placeholder must be filled** |
| No identifying overlap with prior publications | ✅ | `review/overlap-report.md`: no shared prose with the author's prior papers (only a LaTeX table column spec matches); the lineage paper is cited once as complementary |
| English proofread | ✅ (model) / ⚠️ author | Two independent review passes read the full text (round 2: minor revision); a final human read is recommended |
| Author biography and photo | ⚠️ author | Biography placeholder; photo omitted (required at the final stage) |
| Number consistency | ✅ | `review/check_numbers.py`: 0 unmapped numbers; clean clone regenerates all 381 macros and all tables identically |
| Preregistration and deviations disclosed | ✅ | Setup section, with D1-D9 listed in `eval/PREREGISTRATION.md` |
| No employer data, metrics or mentions | ✅ | Repository-wide search for the employer's name: no hits |
| Commit hygiene | ✅ | No Co-Authored-By trailers or generator lines in `git log` |

**Blockers before submission (author):** AI-disclosure review, repository URL, biography (+ photo at the final
stage), suggested reviewers in the cover letter, and confirmation of the contact e-mail.
