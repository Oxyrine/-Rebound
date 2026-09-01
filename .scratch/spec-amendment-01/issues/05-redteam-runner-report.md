# 05: Red-team runner + report

**What to build:** A standalone runner that puts the adversarial cases through both interpreter arms and produces a report whose disclosure — author-written, single-pass, not an accuracy claim — is impossible to miss, and which states plainly which cases the system got wrong.

**Blocked by:** 03 (needs the authored cases to run). 04 recommended first — it validates the file the runner consumes.

**Status:** ready-for-agent

- [ ] A new standalone runner script loads the red-team fixture and runs both arms through the existing pipeline entry point
- [ ] Link execution is hard-coded off and not exposed as a parameter; the runner is a separate script, never a new value on the batch runner's split argument, so it can never sit adjacent to live link execution
- [ ] Ground truth for each case is its authored expected outcome
- [ ] The runner writes per-arm result JSON and a markdown report
- [ ] The report's disclosure block — author-written, single-pass, unblinded, establishes no accuracy claim, not part of the fixture, not held out — is the first content in the file, above any result
- [ ] Raw counts only in the report; no percentages, no recall or precision language
- [ ] The report names which cases each arm got wrong
- [ ] An optional second table grouping outcomes by `failure_mode` is added only if the authoring time-box had slack
- [ ] Test at the pipeline entry-point seam with a mock interpreter: a run over the adversarial cases produces no payment-link-created events in the audit log and sets no link status on any result, regardless of route. Prior art: the chaos-mock suite
