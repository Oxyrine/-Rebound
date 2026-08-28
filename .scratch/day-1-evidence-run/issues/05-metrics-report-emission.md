# 05: Metrics Report Emission

**What to build:** Updates `generate_metrics.py` to consume the unified JSON dictionary, compute the separated fixture-vs-frozen metrics, and emit the final combined report to `evidence/metrics_report.md`.

**Blocked by:** 04: Offline Reconciliation Phase

**Status:** ready-for-agent

- [ ] Modify `generate_metrics.py` to read the unified `evidence/run_all_results.json` dictionary.
- [ ] Compute metrics diffing `gt_hard_stop` (frozen truth) against `fixture_expected_outcome` (day-1 label) directly from the dictionary entries.
- [ ] Generate the §23 two-arm table and the §24 full report based on the reconciled `link_completed` fields.
- [ ] Write the final combined output to a markdown file at `evidence/metrics_report.md`.
