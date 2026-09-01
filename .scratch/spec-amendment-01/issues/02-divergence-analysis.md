# 02: Divergence analysis end-to-end

**What to build:** Whenever the rules arm and the LLM arm route the same case differently, the evaluation records that case individually — the customer message, both routes, the frozen ground truth, and which arm was safer — so the "why an LLM" claim rests on visible per-case evidence rather than aggregate counts that might tie.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A pure function in the batch-metrics module takes both arms' result records (keyed by case) plus a case-to-message mapping and returns the list of cases where the two arms produced different routes, each annotated with case id, bucket, both routes, frozen ground truth, and a safety classification
- [ ] The safety classification reuses the module's existing still-safe-routes set and the hard-stop ground-truth flag already on each result record; classes are llm-safer, rules-safer, both-safe-via-different-rung, both-unsafe; no new notion of correctness is introduced
- [ ] A companion formatting function renders the divergence list as a markdown table with the customer message truncated; full text stays in the JSON artifact
- [ ] The customer message is joined from the fixture files at render time, not added to pipeline result records
- [ ] The metrics-generation script emits the divergence section inside the existing two-arm comparison block, before the per-arm full reports
- [ ] Fewer than two arm result files emits an explicit "not computed, N of 2 arms found" line, never an empty or placeholder table
- [ ] An aggregate tie still populates the per-case table; identical arms return an empty list with an "arms agreed on all cases" note, not an error
- [ ] Tests at the batch-metrics module seam: classification correctness, the tie case, the identical-arms case, the single-arm guard, formatter truncation. Prior art: the existing batch-metrics tests and their result-record factory, and the existing assertion that the report uses held-out framing rather than percentage claims
