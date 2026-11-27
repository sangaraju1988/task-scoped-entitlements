# Rebuttal notes: response to the independent review (round 1)

Each concern from `review/independent-review.md`, what was done, and where. Numbers are macros in
`paper/numbers.tex` (source map in `eval/NUMBERS.md`). New analyses added in response are logged as deviations D6-D8
in `eval/PREREGISTRATION.md` and labelled exploratory in the paper.

## 1. Exposure headline inflated (insufficient scopes; widening ignored; role mix)
**Fixed.**
- The abstract headline is now the exposure of each run's **final reach, including approved widening** (D7:
  `eval/run_e1_postwiden.py`): Sonnet 5.5 \oerColRedPostSonnet-fold columns, \oerCellRedPostSonnet-fold cells.
- Results E1 reports the all-task factors and states that they include insufficient scopes. It adds the
  sufficient-only reduction (\oerColReductionSuff / \oerCellReductionSuff) and the post-widening reduction for both
  models.
- **Per-role reductions** are added. The text explains that the sensitivity analysis covers only the *restricted*
  role, which is consistent with its \oerColRedRestricted-fold reduction. The all-task factor is higher because most
  tasks were assigned the *full* role.

## 2. Injection headline understates residual risk under widening-targeted attack
**Fixed.**
- The abstract and introduction now state the widening-attack success under *auto* (\widExfilAutoSonnet% Sonnet,
  \widExfilAutoHaiku% Haiku) and call widening approval the main residual channel.
- The denied-widening arm (D4) was removed from the abstract. It appears only in Results/Discussion, labelled
  exploratory.
- E5c is reported per model, with n and CIs.
- Setup and E5a state that the broker infers scopes from the clean task and never sees the injected note. The
  initial-scope leaks are therefore over-scoping, not injection-driven scope inflation.
- The *strict* policy's weakness is explained with data: only \widCanaryTagged% of canary columns were tagged.
- **Rebuttal on adaptive attacks and non-lexical approval:** these are out of scope for this paper. They are
  acknowledged in Limitations ("Attacks are fixed, not adaptive") and in the mitigations, and planned as follow-up
  work.

## 3. Baselines (B3 lacks widening; B2 = B0; B1 not for Sonnet; no injection-defence baseline)
**Mostly fixed.**
- **B3W** added (D6b): B3 plus the same request tool and policy, where approval only enlarges the shown schema.
  TSE minus B3W is +\dTseBthreewHaiku pp (Haiku) and +\dTseBthreewSonnet pp (Sonnet), both CIs above zero. So
  enforcement does not cost accuracy relative to prompt-only scoping with widening.
- The incorrect sentence "B3 and TSE ... isolates enforcement" was removed.
- **B2** is now described as a control that shows what tool-level scoping changes, not as an independent baseline.
- **B1 for Sonnet:** not run (D3, budget). Stated in Setup.
- **Injection-defence baselines:** discussed as complementary in Related Work (spotlighting, StruQ, SecAlign). Not
  compared; listed in Limitations.

## 4. Utility cost under-emphasised; run-to-run variance; k=2 exploratory; pooled open-weight row
**Fixed.**
- **H2 (non-inferiority within 5 pp) is explicitly reported as not supported.**
- The per-benchmark cost is now in the text: it is concentrated on BIRD.
- The Sonnet-vs-Haiku difference is discussed, labelled as an untested explanation.
- The size of the run-to-run variation is stated next to the CIs, with a caveat.
- Ablation contrasts now use same-harness references on the ablation subset (D6a; this also fixes a pairing flaw
  found while responding).
- Open-weight results are given per model; the text notes that qwen2.5-coder is also the inference model.

## 5. Inconsistencies and accounting
**Fixed.**
- Deviation count unified: eight deviations, listed in Setup.
- Leak attribution: the text now states that the categories overlap.
- E4 denominators: GroupingError rejections and timeouts are named and counted as an enforcement-induced utility
  loss; the p95 tail increase is discussed.
- E5 n=196: pairs exclude runs that ended with an infrastructure or broker error (stated).
- The out-of-E canary subset is reported (\nCanaryOutE tasks, 0 leaks under any condition) and correctly attributed
  to the user's grants.
- Non-permitted remainder: attributed to errors. The text adds that TSE does not improve refusal behaviour.
- **Pending (minor):** captions for Table 3 (Wilcoxon n excludes tied pairs) and Table 4 ("covers N").
- **Found while responding:** two broker defects (widening view-order bug; concurrent catalog updates). Fixed in
  code with regression tests; affected runs count as failures (D8); counts reported in Results.

## 6. Reproducibility / prereg / bypass depth / broker input
**Fixed, except for the repository URL.**
- Hypotheses H1-H5 are stated in Setup, with their outcomes in Results (H1, H4, H5 supported; H2 not; H3 descriptive).
- Pre-freeze tasks: a sensitivity check excluding the 16 tasks is reported (sufficiency \suffTseNoPre%; Sonnet
  difference \dExSonnetTseNoPre pp).
- The bypass catalog is described as 32 distinct scripted types run on 29 databases, explicitly not adaptive.
- **Broker literal quoting:** literals and identifiers are quoted. A new unit test,
  `test_malicious_filter_literal_cannot_inject_ddl`, covers a DDL-injection attempt through a grounded literal.
- Threat-matrix row 9 was downgraded to "partially mitigated (scripted tests only)". Row 1 now notes widening.
- **Repository URL:** remains an author TODO (the repository is prepared locally).

## References
Added and verified:
- Conseca (HotOS'25)
- AirGapAgent (CCS'24)
- SecAlign (CCS'25)
- StruQ (USENIX Sec'25)
- Spotlighting (arXiv)
- RFC 8693

Other changes:
- ToolEmu moved out of the tool-gating list.
- The dataset citation no longer shows the internal-looking revision label.

## Minor
- Fig. 1 redrawn at two-column width with larger fonts.
- Fig. 3 rebuilt at two-column width: readable labels, no truncation, B0 inside the axis range.
- The Δ glyph in table captions is replaced with text.
- Remaining items to close in the final pass: the "Listing 2" vs "Figure 2" label, the OER summation domains, and
  the template footer ("VOLUME 11, 2023").
