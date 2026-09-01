# Final Evaluation Phase

This tracks the non-code, operational phase of the Buildathon project submission: the rigorous manual labeling, ground truth freezing, and final official evidence runs. (Note: Demo script, HTML tables, and video production will be handled in a separate tracking space to keep this focused purely on evaluation).

## Status
Active

## Decisions so far
- **§25 Scope:** §25 is swept on the dev set only and frozen before held-out is touched. It is already generated in `scripts/threshold_sweep_report.md` and does not block or wait on the final evidence run.
- **Rules Arm Requirement:** The final evidence run must run BOTH the LLM arm (`--execute-links`) and the rules arm (dry) to ensure `generate_metrics.py` can produce the §23 two-arm table.
- **Dry Rehearsal:** A dry rehearsal of the Razorpay execute/checkout/reconcile flow must be done prior to the one-shot run to de-risk the integration.

- **Pass 1:** Completed successfully today at 08:22 AM. The 48-hour clock has started.

## 2026-09-01 status

- **Pass 1**: done 2026-08-26 12:26 IST (22/22 labelled). 48h cool-down long cleared.
- **spec-amendment-01**: complete and merged — divergence analysis, red-team probe (6 cases; LLM 0/6, rules 5/6), manifest guard, replay test, 5 ADRs, NICE_TO_HAVE. 145 tests.
- **Ticket 04 (README)**: drafted with `[from run]` placeholders (445e0d4).
- **Rules-arm dev pipeline**: validated free — 3/9 hard stops, 0 false stops, 6 fall-through. Metrics path (incl. divergence + reliability) works end to end.
- **Blocked on the human**: pass 2 labelling (02), the Razorpay browser checkouts (00 and 03), and the go/no-go on the one-shot `--execute-links` run (03). The 30-link Test Mode cap is the one irreversible resource.

## 2026-09-01: rubric gap found in pass-2 review — RCV-015 unanchored

labeling_rubric.md's Payment-claim section says text cannot verify payment
status and compensates with named worked anchors (RCV-014 true, RCV-018
false). RCV-015 (held-out, ALREADY_PAID_TRUE) has no anchor, and its only
textual cue reads as the *false*-claim tell by the rubric's own pattern
while its authored outcome is true. Confirmed by grepping the rubric for
every RCV-\d+ mention -- RCV-015 is genuinely absent.

Decision: do not amend the rubric or leak expected_outcome into pass 2.
Label RCV-015 as best judgment same as any case; reconcile_labeling.py now
flags it automatically post-hoc (unanchored_payment_claim_cases(), derived
generically from the rubric text + heldout bucket, not hardcoded) and
records the caveat in heldout_ground_truth_frozen.json rather than letting
a pass1==pass2 agreement on it silently count as verified judgment. README
§21 discloses this. 5 new tests (tests/test_reconcile_labeling.py), 150 pass.
