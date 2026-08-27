"""Deterministic checks that run before any interpreter call (§11: "Structured
pre-checks -- no LLM"). Malformed or duplicate events are rejected here,
never spent on an interpretation. Also (§22 Chaos Mock) the structured
dispute_open flag: a real dispute recorded on the event itself hard-stops
here regardless of what the interpreter would have said, so a model that
confidently (and wrongly) calls a disputed charge benign never gets the
chance to matter.
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

    if event.get("dispute_open") is True:
        return PrecheckResult(ok=False, reason="dispute_open flag set -- hard stop before interpretation")

    # order_id is the one mandatory identity-chain field (§12): payment_id
    # can legitimately be null on a failed/pending payment (see RCV-019).
    if not event.get("razorpay_context", {}).get("order_id"):
        return PrecheckResult(ok=False, reason="missing order_id in razorpay_context")

    if case_id in seen_case_ids:
        return PrecheckResult(ok=False, reason="duplicate case_id")

    return PrecheckResult(ok=True)


def validate_output_case_id(agent_output_case_id: str, event: dict) -> PrecheckResult:
    """Chaos condition 5 (§22): interpreter output claiming a different
    case_id than the event being processed. No routing decision is
    trustworthy if we can't confirm which case the output is even about --
    reject outright, before route() is ever called, rather than routing on
    unverified metadata.
    """
    event_case_id = event.get("case_id")
    if agent_output_case_id != event_case_id:
        return PrecheckResult(
            ok=False,
            reason=f"output case_id {agent_output_case_id!r} does not match event case_id {event_case_id!r}",
        )
    return PrecheckResult(ok=True)
