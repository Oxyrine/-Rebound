# ADR 0006: Completing the rate-limited evidence run operationally, not by changing frozen code

Status: accepted · 2026-09-01 · relates to SPEC.md §17, §18, §26, §31; final-evaluation

## Context

The Day-9 live evidence run (`run_batch --interpreter=llm --split=all
--execute-links`) creates a Razorpay Test Mode Payment Link for every
RECOVERY_ELIGIBLE case. Razorpay Test Mode rate-limited link creation at roughly
five per short rolling window — 3-second inter-request pacing did not help. The
run hit HTTP 429 after 5 links, then again after 5 more on resume, then again
during the reconciliation status-fetch (`GET /payment_links/{id}`). The frozen
Razorpay client (`src/razorpay_client.py`) has no retry/backoff and catches only
`requests.Timeout`, so each 429 propagated and stopped the run.

25 of 59 cases were interpreted in session 1 before the first failure. The LLM
interpreter is non-deterministic (no temperature or seed set) — one case already
routed differently between the dry run and session 1.

## Decision

Complete the run **operationally**, changing no evaluated component.

- No retry/backoff added to `razorpay_client.py`. No change to `link_dispatch.py`,
  the prompt, the policy engine, the rules interpreter, the fixture, the
  confidence threshold, or the metrics code. Audit history: append only.
- A recovery wrapper (`scripts/resume_evidence_run.py`) — a new operational file,
  not part of REBOUND — imports and calls the frozen functions unchanged
  (`_get_interpreter`, `check`, `route`, `is_suspicious`, `verify_payment_claim`,
  `verify_chain`, `AuditLog`) and mirrors `run()`'s per-case body.
- It **does not re-interpret** the 25 cases session 1 established. Re-interpreting
  would make the final dataset "25 cases at T1 + 34 at T2" rather than "59 cases,
  one interpretation each."
- **Path B:** it stops creating links. It finishes the remaining interpretations,
  calls no `dispatch_link`, and marks the remaining RECOVER cases
  `NOT_ATTEMPTED_RATE_LIMITED`. The 10 links already created are checked out and
  reconciled.
- Pre-flight and post-flight assertions fail loudly rather than attempting further
  recovery: 59 unique cases, 59 policy decisions, no duplicate decision, ≤ 28
  links, no duplicate link per case, valid chain.

## Rationale

Adding retry/backoff during the evaluation phase — even as objectively good
engineering — creates an avoidable methodological question: was the final run
performed with the frozen implementation? The freeze matters more than a fuller
operational number here. The central Track 03 result (LLM 0 unsafe misses vs rules
9) comes from the routing evaluation, which does not depend on link creation. Ten
completed Test Mode links already demonstrate the full chain — case → LLM
interpretation → policy decision → RECOVERY_ELIGIBLE → Payment Link → Test Mode
checkout → reconciliation → audit trail — end to end. Twenty-two repetitions of
that chain would not make it more established.

## Consequences

- The results artifact tags each case `interpretation_session` 1 or 2. Session-1
  cases carry `reconstructed_from_audit: true` — their per-case `stop_signals` and
  `confidence` were never persisted (only route + matched_rung), so `stop_signals`
  is reconstructed from the rung where it uniquely implies a signal and
  `confidence` is null for those 25. Headline metrics (funnel, safety outcomes,
  hard-stop matrix, divergence) are route-based and unaffected; the §25 confidence
  reliability check covers the 34 session-2 cases only.
- The README presents routing (59/59) and execution (10 links) as **two separate
  claims**, never as one clean funnel.
- The rate-limit incident is disclosed in the README process note, not hidden.
