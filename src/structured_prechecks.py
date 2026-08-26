"""Deterministic checks that run before any interpreter call (§11: "Structured
pre-checks -- no LLM"). Malformed or duplicate events are rejected here,
never spent on an interpretation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PrecheckResult:
    ok: bool
    reason: str = ""


def check(event: dict, seen_case_ids: set[str]) -> PrecheckResult:
    case_id = event.get("case_id")
    if not case_id:
        return PrecheckResult(ok=False, reason="missing case_id")

    # order_id is the one mandatory identity-chain field (§12): payment_id
    # can legitimately be null on a failed/pending payment (see RCV-019).
    if not event.get("razorpay_context", {}).get("order_id"):
        return PrecheckResult(ok=False, reason="missing order_id in razorpay_context")

    if case_id in seen_case_ids:
        return PrecheckResult(ok=False, reason="duplicate case_id")

    return PrecheckResult(ok=True)
