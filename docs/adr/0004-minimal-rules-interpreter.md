# ADR 0004: The rules interpreter stays deliberately naive

Status: accepted · 2026-09-01 · relates to SPEC.md §23

## Context

The AI justification for the project is a controlled experiment: hold the fixture, policy
engine, execution and safety controls constant, change only the evidence interpreter, and
ask whether semantic interpretation produces a better recovery/suppression operating point
than the simplest alternative. That question is only meaningful if the baseline is
genuinely the simplest alternative.

## Decision

`src/rules_interpreter.py` is **three case-insensitive keyword rules** — `paid` /
`payment done` → payment claim; `stop` / `don't contact` → opt-out; `refund` / `wrong item`
/ `dispute` → dispute. English only. It attempts three of the five frozen stop_signals;
`PROMISE_TO_PAY` (needs the specificity-gate judgment) and `AMBIGUOUS_OR_CONFLICTING`
(definitionally not a keyword) are left out on purpose. It will not fire at all on the
Tamil/Hinglish share of the fixture.

## Rationale

Making the baseline smarter — regexes, negation handling, a small classifier — would
confound the experiment: a close result would no longer tell us whether *semantic
interpretation* helped or whether *a better baseline* did. The gaps (no promise-gate, no
ambiguity, no code-mixed languages) are part of what the comparison measures.

## Consequences

- The rules arm's misses on negated claims, buried disputes, and code-mixed text are
  expected results to report, not bugs to patch. The red-team probe (spec-amendment-01)
  targets exactly those gaps.
- If the LLM arm does not clearly beat this baseline, that is a reportable finding and is
  stronger stated honestly than asserted away (§23, §32).
