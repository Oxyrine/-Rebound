# ADR 0001: Payment Links are the only intervention surface

Status: accepted · 2026-09-01 · relates to SPEC.md §3, §10, §14

## Context

Track 03's brief names several recovery interventions — reminders, checkout-abandonment
recovery, overdue receivables, alternate payment methods, subscription retry. A submission
could try to touch all of them.

## Decision

REBOUND executes recovery through **one rail: a Razorpay Test Mode Payment Link**, and
nothing else. Subscriptions and mandates are detected and refused (`DETECTED_SCOPE_OUT`),
not partially implemented.

## Rationale

1. Most of the named interventions are not independent — reminder, checkout recovery, and
   B2B receivables all terminate in the same artifact, a Payment Link. Alternate-payment-method
   is the same link with different copy. Six labels, largely one rail.
2. The two genuinely distinct rails — subscription retry orchestration and mandate renewal —
   are separate state machines and unbuildable faithfully in the submission window on
   documented Test Mode constraints (3-day token expiry; halted-period invoices are a
   Dashboard-only manual action). Detecting and refusing them is the honest move.
3. The track rewards decision quality over breadth: "why, when, and whether you touch
   [an endpoint] at all," not how many.

## Consequences

- The recovery funnel is narrow but every stage is real and demoable.
- "Why only Payment Links?" is a rehearsed 30-second answer, not a gap to hide.
- Adding a second rail later is additive: the interpreter → typed boundary → policy engine
  path does not change, only the execution leaf.
