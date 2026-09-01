# 02: Divergence analysis end-to-end

**What to build:** Whenever the rules arm and the LLM arm route the same case differently, the evaluation records that case individually — the customer message, both routes, the frozen ground truth, and which arm was safer — so the "why an LLM" claim rests on visible per-case evidence rather than aggregate counts that might tie.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] A pure function in the batch-metrics module takes both arms' result records (keyed by case) plus a case-to-message mapping and returns the list of cases where the two arms produced different routes, each annotated with case id, bucket, both routes, frozen ground truth, and a safety classification
- [x] The safety classification reuses the module's existing still-safe-routes set and the hard-stop ground-truth flag already on each result record; classes are llm-safer, rules-safer, both-safe-via-different-rung, both-unsafe; no new notion of correctness is introduced
- [x] A companion formatting function renders the divergence list as a markdown table with the customer message truncated; full text stays in the JSON artifact
- [x] The customer message is joined from the fixture files at render time, not added to pipeline result records
- [x] The metrics-generation script emits the divergence section inside the existing two-arm comparison block, before the per-arm full reports
- [x] Fewer than two arm result files emits an explicit "not computed, N of 2 arms found" line, never an empty or placeholder table
- [x] An aggregate tie still populates the per-case table; identical arms return an empty list with an "arms agreed on all cases" note, not an error
- [x] Tests at the batch-metrics module seam: classification correctness, the tie case, the identical-arms case, the single-arm guard, formatter truncation. Prior art: the existing batch-metrics tests and their result-record factory, and the existing assertion that the report uses held-out framing rather than percentage claims

## Answer

Resolved in commit 64528e8.

- `divergence_analysis(arms, replies)` and `format_divergence(divergence, *, max_reply_chars=80)` added to `src/metrics.py`, both pure. Conservatism ordering `STOP(3) > VERIFY/PAUSE/REVIEW(2) > RECOVER/LINK_QUOTA_GUARD(1)` decides the safer arm; `gt_hard_stop` rides along in every row so the reader judges correctness. Classes: the arm label when one is strictly more conservative, else `both_safe_different_rung` / `both_unsafe` / `unclassified`.
- `scripts/generate_metrics.py`: new `_load_replies()` joins `customer_reply` from `development_cases.json` + `heldout_cases.json`; divergence section emitted right after the §23 aggregate table; `evidence/divergence.json` written with full untruncated text when there are divergences.
- Guard: exactly 2 arm files required; otherwise `_Not computed: N arm result file(s) found, exactly 2 required._`
- 10 new tests (`tests/test_metrics.py` unit, `tests/test_generate_metrics.py` integration). Full suite 127 pass.
- Verified end to end against a real `--interpreter=rules --split=dev` run with a second arm manufactured by flipping 4 routes: divergence table rendered, truncation and multi-byte Tamil text handled, `divergence.json` correct.
