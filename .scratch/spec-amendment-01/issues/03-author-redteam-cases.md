# 03: Author red-team adversarial cases

**What to build:** A small set of hand-written customer messages that deliberately attack the interpreter's reading comprehension — traps that are semantic, not lexical — held entirely outside the evaluation fixture, so the project has an instrument pointed at its stated worst-case risk.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `fixtures/redteam_cases.json` created, using the same case shape as the evaluation fixture including the full identity chain, so the pipeline runs unmodified
- [ ] Each case adds four fields: a split marker of "redteam", an authoring-method marker, a labeling-method marker of "single_pass_unblinded" (not reused from the fixture's double-labeling marker), and non-empty `failure_mode` and `probe_rationale` strings
- [ ] Case ids carry a distinct prefix so contamination is visible on sight
- [ ] At least 6 cases, each clearing the three-part quality bar: a competent human labeller reaches the intended label from the text alone; the trap is semantic, not lexical; the probed failure mode is stateable in one sentence
- [ ] Authoring is time-boxed to 90 minutes; cut to 6 rather than pad to 10
- [ ] Failure modes drawn in priority order: indirect opt-out, dispute buried in polite text, negated payment claim, hedged promise on the specificity-gate boundary, multi-signal with the hard stop buried last, code-mixed sarcasm reading as agreement
