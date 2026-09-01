# 09: Stretch — divergence taxonomy + confidence reliability check

**What to build:** Two depth-adds that sharpen already-honest analysis: a mechanism label on each divergence, and a dev-set check of whether reported confidence tracks correctness.

**Blocked by:** 02 — the taxonomy is a column on the divergence table.

**Status:** resolved

- [x] A `divergence_type` field on each divergence row: lexical-gap, semantic-composition, ambiguity-resolution
- [x] A dev-set check comparing reported confidence buckets with observed correctness, presented as a plain text table or a single matplotlib PNG, with no new charting dependency
- [x] The confidence check is named as not a formal calibration assessment, in both the code and the report
- [x] This ticket is cut-first under time pressure and is never a dependency of ticket 02; if it is not done, its items move to NICE_TO_HAVE.md

## Answer

Done (not cut — there was slack). 

- **Taxonomy:** `divergence_analysis(arms, replies, types=None)` gains an optional `types` map (`case_id -> lexical_gap | semantic_composition | ambiguity_resolution`), an AUTHORED judgement, not computed — routes alone can't tell a paraphrase miss from cross-clause composition. `format_divergence` renders a `type` column (`—` when absent). `generate_metrics` loads an optional `fixtures/divergence_types.json`.
- **Reliability check:** `run()` now records `result["confidence"]` (None on malformed/rejected paths). `confidence_reliability(results)` buckets scored cases into 4 confidence bands and, per band, counts how many routed outcomes matched the case's intended outcome. `format_confidence_reliability` leads with "NOT a formal calibration assessment" and uses raw counts, no percentages. Emitted per arm after its full report.
- 5 new tests. 145 pass. Verified end to end: both render in `evidence/metrics_report.md`.
