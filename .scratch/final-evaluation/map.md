# Final Evaluation Phase

This tracks the non-code, operational phase of the Buildathon project submission: the rigorous manual labeling, ground truth freezing, and final official evidence runs. (Note: Demo script, HTML tables, and video production will be handled in a separate tracking space to keep this focused purely on evaluation).

## Status
Active

## Decisions so far
- **§25 Scope:** §25 is swept on the dev set only and frozen before held-out is touched. It is already generated in `scripts/threshold_sweep_report.md` and does not block or wait on the final evidence run.
- **Rules Arm Requirement:** The final evidence run must run BOTH the LLM arm (`--execute-links`) and the rules arm (dry) to ensure `generate_metrics.py` can produce the §23 two-arm table.
- **Dry Rehearsal:** A dry rehearsal of the Razorpay execute/checkout/reconcile flow must be done prior to the one-shot run to de-risk the integration.
