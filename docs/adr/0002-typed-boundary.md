# ADR 0002: A typed boundary between interpreter and engine

Status: accepted · 2026-09-01 · relates to SPEC.md §11, §13, §8

## Context

The interpreter is a language model reading untrusted, adversarial-capable customer text.
Downstream of it sits money-moving execution (Payment Link creation). Something has to
stop a compromised or hallucinating interpreter from reaching that execution.

## Decision

A value crosses from the interpreter into the engine **exactly once, through a validated
schema** (`AgentOutput`). The schema has no field for an amount, a discount, a waiver, a
refund, a link URL, an execution action, a retry time, or any customer-facing text —
those are rejected at construction. After that point no language model touches the
arithmetic, the amount, or the action.

## Rationale

Structural containment beats a runtime check: the model cannot express a financial action
because there is no field to put one in. This is the §31 principle — a guarantee that
could regress under pressure is made structural, not a note to be careful.

## Consequences

- Prompt injection cannot cause an action. Even a fully successful injection emits only a
  classification.
- **Stated limit (this is load-bearing):** the typed boundary prevents *action* injection,
  not *classification error*. `{"customer_state": "RECOVERY_ELIGIBLE", "confidence": 0.94}`
  on a message that genuinely means "I dispute this charge" is a valid schema, passes the
  policy engine, isolates the amount correctly — and is still the wrong decision. See
  ADR 0005 and SPEC.md §8's semantic-safety class.
- Customer-facing copy comes from deterministic pre-approved templates; the model never
  authors outbound language.
