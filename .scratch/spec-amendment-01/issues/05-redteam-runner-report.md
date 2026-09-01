# 05: Red-team runner + report

**What to build:** A standalone runner that puts the adversarial cases through both interpreter arms and produces a report whose disclosure — author-written, single-pass, not an accuracy claim — is impossible to miss, and which states plainly which cases the system got wrong.

**Blocked by:** 03 (needs the authored cases for the real run). Code + tests are done (commit 47a78bc); only the probe run and committed report remain.

**Status:** ready-for-agent (code complete, run pending 03)

## Progress

`scripts/run_redteam.py` + `tests/test_redteam.py` landed in 47a78bc — runner reuses `run_batch.run()` with `execute_links` hard-wired False, writes `evidence/redteam_results_{arm}.json` + `evidence/redteam_report.md` (disclosure first, per-case + by-mode tables, names divergences, raw counts only). 5 tests: no `PAYMENT_LINK_CREATED` even on a RECOVER stub, no link status, disclosure precedes every result, `execute_links` never a flag.

**Remaining once ticket 03 lands:** run `python -m scripts.run_redteam`, review the generated report, decide whether to un-gitignore `evidence/redteam_report.md` so a panel sees the findings without running it, wire the README section (via `final-evaluation/04-readme-update`).

- [ ] A new standalone runner script loads the red-team fixture and runs both arms through the existing pipeline entry point
- [ ] Link execution is hard-coded off and not exposed as a parameter; the runner is a separate script, never a new value on the batch runner's split argument, so it can never sit adjacent to live link execution
- [ ] Ground truth for each case is its authored expected outcome
- [ ] The runner writes per-arm result JSON and a markdown report
- [ ] The report's disclosure block — author-written, single-pass, unblinded, establishes no accuracy claim, not part of the fixture, not held out — is the first content in the file, above any result
- [ ] Raw counts only in the report; no percentages, no recall or precision language
- [ ] The report names which cases each arm got wrong
- [ ] An optional second table grouping outcomes by `failure_mode` is added only if the authoring time-box had slack
- [ ] Test at the pipeline entry-point seam with a mock interpreter: a run over the adversarial cases produces no payment-link-created events in the audit log and sets no link status on any result, regardless of route. Prior art: the chaos-mock suite
