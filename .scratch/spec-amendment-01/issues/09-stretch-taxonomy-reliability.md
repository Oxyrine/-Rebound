# 09: Stretch — divergence taxonomy + confidence reliability check

**What to build:** Two depth-adds that sharpen already-honest analysis: a mechanism label on each divergence, and a dev-set check of whether reported confidence tracks correctness.

**Blocked by:** 02 — the taxonomy is a column on the divergence table.

**Status:** ready-for-agent

- [ ] A `divergence_type` field on each divergence row: lexical-gap, semantic-composition, ambiguity-resolution
- [ ] A dev-set check comparing reported confidence buckets with observed correctness, presented as a plain text table or a single matplotlib PNG, with no new charting dependency
- [ ] The confidence check is named as not a formal calibration assessment, in both the code and the report
- [ ] This ticket is cut-first under time pressure and is never a dependency of ticket 02; if it is not done, its items move to NICE_TO_HAVE.md
