# Red-team adversarial probe

> **Disclosure — read before any result below.**
> These cases are adversarial probes authored by the system's own author,
> single-pass labelled with no blind protocol. They are **not** part of the
> 59-case evaluation fixture, **not** held out, and establish **no accuracy
> claim**. They exist to characterise known semantic failure modes of the
> interpreter; failures are reported as found and are not fixed in response
> (ADR 0005). Raw counts only — no percentages, no recall/precision.


6 cases. Link execution: disabled (this runner cannot create a link).

## Per case

| case | failure mode | intended | rules → | rules | llm → | llm |
|---|---|---|---|---|---|---|
| RCV-RT-001 | indirect_opt_out | HARD_STOP | RECOVERY_ELIGIBLE | **diverges** | HARD_STOP | matches |
| RCV-RT-002 | buried_dispute | HARD_STOP | RECOVERY_ELIGIBLE | **diverges** | HARD_STOP | matches |
| RCV-RT-003 | negated_payment_claim | RECOVERY_ELIGIBLE | HUMAN_REVIEW | **diverges** | RECOVERY_ELIGIBLE | matches |
| RCV-RT-004 | hedged_promise_no_date | RECOVERY_ELIGIBLE | RECOVERY_ELIGIBLE | matches | RECOVERY_ELIGIBLE | matches |
| RCV-RT-005 | multi_signal_hardstop_last | HARD_STOP | RECOVERY_ELIGIBLE | **diverges** | HARD_STOP | matches |
| RCV-RT-006 | sarcastic_false_agreement | HUMAN_REVIEW | RECOVERY_ELIGIBLE | **diverges** | HUMAN_REVIEW | matches |

## Where each arm diverged from the intended label

**rules** — 5 of 6 diverged:
- RCV-RT-001 (indirect_opt_out): intended HARD_STOP, got RECOVERY_ELIGIBLE
- RCV-RT-002 (buried_dispute): intended HARD_STOP, got RECOVERY_ELIGIBLE
- RCV-RT-003 (negated_payment_claim): intended RECOVERY_ELIGIBLE, got HUMAN_REVIEW
- RCV-RT-005 (multi_signal_hardstop_last): intended HARD_STOP, got RECOVERY_ELIGIBLE
- RCV-RT-006 (sarcastic_false_agreement): intended HUMAN_REVIEW, got RECOVERY_ELIGIBLE

**llm** — 0 of 6 diverged.

## By failure mode

| failure mode | rules diverged | llm diverged |
|---|---|---|
| indirect_opt_out | 1/1 | 0/1 |
| buried_dispute | 1/1 | 0/1 |
| negated_payment_claim | 1/1 | 0/1 |
| hedged_promise_no_date | 0/1 | 0/1 |
| multi_signal_hardstop_last | 1/1 | 0/1 |
| sarcastic_false_agreement | 1/1 | 0/1 |
