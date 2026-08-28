# 03: Final Evidence Run & Metrics Generation

Type: task
Status: unstarted
Blocked by: 00, 02

**What to build:** 
The execution of the official evaluation runs to generate the final §23 and §24 metrics reports in `evidence/metrics_report.md`. This consists of running the LLM arm real (`--execute-links`) and the rules arm dry, to ensure the two-arm table generates successfully. (Note: §25 is dev-only and already complete).

**Blocked by:** 
00-dry-rehearsal.md
02-pass-2-reconciliation.md

- [ ] Run `run_batch.py` with `--execute-links` against all 59 cases for the LLM arm
- [ ] Run `run_batch.py` for the rules arm (dry run, same split)
- [ ] Manually checkout the live Razorpay test links in the browser
- [ ] Run `run_batch.py` with `--reconcile-only` to lock in the payment statuses
- [ ] Confirm `evidence/metrics_report.md` generated with both §23 and §24 sections intact
