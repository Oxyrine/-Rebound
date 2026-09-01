# 05: Red-team runner + report

**What to build:** A standalone runner that puts the adversarial cases through both interpreter arms and produces a report whose disclosure — author-written, single-pass, not an accuracy claim — is impossible to miss, and which states plainly which cases the system got wrong.

**Blocked by:** 03 (needs the authored cases for the real run). Code + tests are done (commit 47a78bc); only the probe run and committed report remain.

**Status:** resolved (open question flagged below)

## Progress

`scripts/run_redteam.py` + `tests/test_redteam.py` landed in 47a78bc — runner reuses `run_batch.run()` with `execute_links` hard-wired False, writes `evidence/redteam_results_{arm}.json` + `evidence/redteam_report.md` (disclosure first, per-case + by-mode tables, names divergences, raw counts only). 5 tests: no `PAYMENT_LINK_CREATED` even on a RECOVER stub, no link status, disclosure precedes every result, `execute_links` never a flag.

**Remaining once ticket 03 lands:** run `python -m scripts.run_redteam`, review the generated report, decide whether to un-gitignore `evidence/redteam_report.md` so a panel sees the findings without running it, wire the README section (via `final-evaluation/04-readme-update`).

- [x] A new standalone runner script loads the red-team fixture and runs both arms through the existing pipeline entry point
- [x] Link execution is hard-coded off and not exposed as a parameter; the runner is a separate script, never a new value on the batch runner's split argument, so it can never sit adjacent to live link execution
- [x] Ground truth for each case is its authored expected outcome
- [x] The runner writes per-arm result JSON and a markdown report
- [x] The report's disclosure block — author-written, single-pass, unblinded, establishes no accuracy claim, not part of the fixture, not held out — is the first content in the file, above any result
- [x] Raw counts only in the report; no percentages, no recall or precision language
- [x] The report names which cases each arm got wrong
- [x] An optional second table grouping outcomes by `failure_mode` is added only if the authoring time-box had slack
- [x] Test at the pipeline entry-point seam with a mock interpreter: a run over the adversarial cases produces no payment-link-created events in the audit log and sets no link status on any result, regardless of route. Prior art: the chaos-mock suite

## Answer

Resolved in commit 0f2b7cf. Probe run against the 6 authored cases; `evidence/redteam_report.md` committed (un-gitignored -- it is a deliverable). Disclosure block first, raw counts, no percentages. Zero `PAYMENT_LINK` events in either audit log (5 `test_redteam.py` tests already pinned this).

**Result:** rules arm diverged from the intended label on 5 of 6 cases; LLM arm on 0 of 6.

**Open question for the human:** 0/6 LLM divergence is honest but a weak probe outcome -- AI-drafted traps did not catch the AI interpreter, exactly the circularity risk flagged when ticket 03 was assigned. The rules-vs-LLM contrast (5/6 vs 0/6) is itself a strong result for the §23 AI-justification. Options: (a) ship as-is, leaning on the contrast; (b) hand-write 2-3 genuinely harder cases. Not blocking; recorded for the README-wiring step (final-evaluation/04-readme-update).

## Open question — resolved 2026-09-01

Ship the six as-is; do not add harder cases. Rationale (the human's call, recorded
verbatim in substance): adding cases after observing 0/6 LLM divergence would be
searching for a failing case having already seen the first six pass — informal
adversarial tuning that undercuts the epistemic discipline the amendment exists to
demonstrate. The 5/6-vs-0/6 contrast is itself the stronger result; a zero-failure
probe is legitimate provided the construction is disclosed, which it is.

README §5 updated to the precise framing: "In six author-written adversarial
probes... establish no accuracy claim," the two-evidence-streams separation
(59-case fixture = quantitative, red-team = qualitative characterization), the
literal-vs-contextual pattern in RT-001/002/005/006 as qualitative support for the
architectural thesis, and the 0/6 result left deliberately uncomfortable rather
than smoothed over. The six cases are frozen; ticket 05 is fully closed.
