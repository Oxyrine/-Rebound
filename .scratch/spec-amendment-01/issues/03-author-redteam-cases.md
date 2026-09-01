# 03: Author red-team adversarial cases

**What to build:** A small set of hand-written customer messages that deliberately attack the interpreter's reading comprehension — traps that are semantic, not lexical — held entirely outside the evaluation fixture, so the project has an instrument pointed at its stated worst-case risk.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] `fixtures/redteam_cases.json` created, using the same case shape as the evaluation fixture including the full identity chain, so the pipeline runs unmodified
- [x] Each case adds four fields: a split marker of "redteam", an authoring-method marker, a labeling-method marker of "single_pass_unblinded" (not reused from the fixture's double-labeling marker), and non-empty `failure_mode` and `probe_rationale` strings
- [x] Case ids carry a distinct prefix so contamination is visible on sight
- [x] At least 6 cases, each clearing the three-part quality bar: a competent human labeller reaches the intended label from the text alone; the trap is semantic, not lexical; the probed failure mode is stateable in one sentence
- [x] Authoring is time-boxed to 90 minutes; cut to 6 rather than pad to 10
- [x] Failure modes drawn in priority order: indirect opt-out, dispute buried in polite text, negated payment claim, hedged promise on the specificity-gate boundary, multi-signal with the hard stop buried last, code-mixed sarcasm reading as agreement

## Answer

Resolved in commit 0f2b7cf. `fixtures/redteam_cases.json` -- 6 cases, one per priority failure mode. AI-drafted against the failure-mode spec, human-reviewed and re-labelled by the user (two substantive edits: RT-004 rewritten to remove any date token so the trap is purely hedging; RT-006 rationale sharpened to name sarcasm-vs-context, not code-mixing). `authoring_method: "ai_drafted_human_reviewed"`, `labeling_method: "single_pass_unblinded"`. Validated by `manifest.py` (redteam_cases: 6, total still 59).
