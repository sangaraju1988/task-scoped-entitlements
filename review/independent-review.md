# Independent review (round 1)

Reviewer: a fresh subagent that had not seen the build, given only the compiled PDF (text + page images) and the
IEEE Access reviewer-form questions, instructed to act as a skeptical reviewer. Run on 2026-11-27 against the draft
compiled with the preliminary E1/E3 file. Recommendation: **major revision**. Responses: `review/rebuttal-notes.md`.

## Form answers (condensed)
1. Contribution: yes, but mainly systems integration plus the empirical trade-off; the value rests on the evaluation.
2. Technical soundness: enforcement sound; empirical side has issues (below).
3. Comprehensive: mostly; reproduction details missing or deferred to an artifact with a placeholder URL.
4. References: applicable but missing: per-task contextual policies (Conseca), contextual-integrity minimisation
   (AirGapAgent), prompt-injection defences (spotlighting, StruQ/SecAlign), permission-aware RAG, JIT access /
   OAuth token exchange (RFC 8693), warehouse masking/policy tags. Many 2025-26 preprints.
5. Inappropriate: ToolEmu cited as a permission mechanism; a dataset revision label that looks internal; vendor
   docs by access year.

## Top 6 concerns
1. Exposure headline inflated: includes insufficient scopes (sufficient-only cell reduction ~11.9x, not 24x);
   OER on initial scope ignores widening; 5.0x column headline outside the 3.4-4.5x sensitivity range (role mix).
2. Injection headline understates risk vs a widening-targeting attacker (64.1% under auto, 55.5% strict); deny arm
   is exploratory (D4) yet in the abstract; E5c lacks model/n/CI; single fixed template; unclear whether the broker
   sees the injected note.
3. Baselines: B3 lacks widening so B3 vs TSE does not isolate enforcement; B2 = B0 by construction ("four
   baselines" overstated); B1 not run for Sonnet; no prompt-injection-defence baseline.
4. Utility cost under-emphasised (BIRD sufficiency 48.2%; Sonnet loses more); run-to-run variance (-6 to 0 pp) not
   in CIs; k=2 result exploratory on 200 tasks; open-weight row pools two models incl. the inference model.
5. Inconsistencies: deviation count (D1-D3 vs D4, D5, "four"); leak attribution sums exceed totals; E4
   denominators; n=196 vs 200 in E5; row-OER n differences; "covers N" undefined; threat-matrix "out-of-E subset"
   not reported; non-permitted rates sum to 98%.
6. Reproducibility/prereg: hypotheses not stated; 16 pre-freeze tasks not excluded; placeholder artifact URL; 928
   bypass attempts = 32 templates x 29 DBs; broker literal quoting and broker-input injection untested.

## Minor
Placeholders and "VOLUME 11, 2023" footer; Fig. 1 illegible; Fig. 3 legend truncated and B0 off-axis; Delta
symbol broken in Tables 5/6 captions; "Listing 2" labelled "Figure 2"; Table 7 p95 increase not discussed; OER
summation domains inconsistent; error side channel "Mitigated (tested)" too strong; GROUP BY rejections are an
enforcement-induced utility loss.
