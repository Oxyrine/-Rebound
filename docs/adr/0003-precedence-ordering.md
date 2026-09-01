# ADR 0003: Deterministic precedence ordering, most-conservative-wins

Status: accepted · 2026-09-01 · relates to SPEC.md §15, §22

## Context

A real customer message carries several signals at once — a dispute and an opt-out, an
already-paid claim and a dispute, a promise-to-pay next to injection-like wording. The
system needs one routing decision, and which signal wins must be explicit and tested, not
emergent from evaluation order.

## Decision

`src/policy_engine.route()` applies a fixed **first-match precedence order**, and the most
conservative outcome always wins: malformed/duplicate → verified-paid → explicit opt-out →
dispute/refund → suspicious-instruction → low-confidence → ambiguous/conflicting →
promise-to-pay → recovery-eligible (with a quota guard below it). The function is pure —
no I/O, no state — and takes the confidence threshold as a parameter so re-sweeping it
never changes the signature.

## Implementation note

The specification (§15) defines **nine** precedence rungs. During the 2026-09-01 drift
reconciliation the code was found to implement **ten** first-match checks: an
`EVIDENCE_REFS_MISSING` rung (a stop_signal asserted with an empty `evidence_refs` list →
REVIEW) sits between rung 5 (suspicious-instruction) and rung 6 (low-confidence). It exists
for Chaos condition 3 (§22, "Missing / invalid evidence_refs → review") and is a
schema-consistency check on the interpreter's own output, not a signal to route on. The
other nine rungs map 1:1 to §15. This tenth rung is recorded here as reconciliation — it
was **not** part of the original nine-rung specification.

## Consequences

- Every multi-signal case in the fixture has a single defensible expected route.
- `tests/test_precedence.py` pins the multi-signal orderings; changing the table is a
  visible, tested diff.
- A conservative route can be "wrong" against ground truth (a false stop). That cost is
  accepted: §24 weights an unsafe miss at 5× a false stop.
