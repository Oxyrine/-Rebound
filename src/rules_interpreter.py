"""Rules-baseline interpreter -- ticket 08, §23. Deliberately simple
keyword matching, not a competing NLP system: the rules-vs-LLM comparison
asks "does semantic interpretation beat the simplest alternative," which
only holds if the baseline stays naive. Do not make this smarter.

Same call contract as llm_interpreter.interpret(): returns AgentOutput,
case_id assigned locally, never derived from matched text.

Only three of the five frozen stop_signals are attempted, per §23's own
keyword table -- PROMISE_TO_PAY (needs the specificity-gate judgment: is
this date specific enough?) and AMBIGUOUS_OR_CONFLICTING (definitionally
"can't tell from keywords") are exactly what keyword matching can't do.
That gap is part of what the comparison measures, not an oversight.

English keywords only -- a large share of the fixture is Tamil/Hinglish,
where this baseline will not fire at all. That's an honest, expected
result of comparing against a semantic interpreter, not a bug to patch.
"""

import re

from src.typed_boundary import AgentOutput

# Order matches §23's own table. All matching rules fire -- this doesn't
# pre-apply precedence between signals; that's policy_engine.route()'s job.
_KEYWORD_RULES = [
    (re.compile(r"\bpaid\b|\bpayment done\b", re.IGNORECASE), "PAYMENT_ALREADY_MADE_CLAIM"),
    (re.compile(r"\bstop\b|\bdon'?t contact\b", re.IGNORECASE), "EXPLICIT_OPT_OUT"),
    (re.compile(r"\brefund\b|\bwrong item\b|\bdispute\b", re.IGNORECASE), "DISPUTE_OR_REFUND"),
]


def interpret(case_id: str, customer_reply: str | None) -> AgentOutput:
    text = customer_reply or ""
    signals = [signal for pattern, signal in _KEYWORD_RULES if pattern.search(text)]

    return AgentOutput(
        case_id=case_id,
        customer_state=f"keyword match: {signals}" if signals else "no keyword match",
        stop_signals=signals,
        confidence=1.0 if signals else 0.9,
        evidence_refs=["customer_reply"] if signals else [],
        requires_human_review=False,
        suspected_injection=False,
    )
