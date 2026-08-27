"""Multi-signal precedence: the earliest-listed rung in §15's table wins,
regardless of what else is also true of the message. See
fixtures/labeling_rubric.md's "Multi-signal precedence" section, worked
through the RCV-022 example.
"""

from src.policy_engine import route
from src.structured_prechecks import PrecheckResult
from src.typed_boundary import AgentOutput

OK = PrecheckResult(ok=True)


def _agent_output(**overrides):
    defaults = dict(
        case_id="RCV-MULTI",
        customer_state="multi-signal test",
        stop_signals=[],
        confidence=0.9,
        evidence_refs=[],
        requires_human_review=False,
        suspected_injection=False,
    )
    defaults.update(overrides)
    return AgentOutput(**defaults)


def test_opt_out_beats_dispute():
    ao = _agent_output(stop_signals=["EXPLICIT_OPT_OUT", "DISPUTE_OR_REFUND"])
    d = route(ao, OK, pre_screen_matched=False)
    assert d.matched_rung == "EXPLICIT_OPT_OUT"


def test_payment_claim_beats_dispute():
    # Rung 2 (VERIFIED_PAYMENT_STATUS) sits above rung 4 (DISPUTE_OR_REFUND):
    # even a message that also disputes the charge gets verified first.
    ao = _agent_output(stop_signals=["PAYMENT_ALREADY_MADE_CLAIM", "DISPUTE_OR_REFUND"])
    d = route(ao, OK, pre_screen_matched=False)
    assert d.matched_rung == "VERIFIED_PAYMENT_STATUS"


def test_pre_screen_beats_promise_to_pay():
    ao = _agent_output(stop_signals=["PROMISE_TO_PAY"])
    d = route(ao, OK, pre_screen_matched=True)
    assert d.matched_rung == "SUSPICIOUS_INSTRUCTION_DETECTED"


def test_low_confidence_beats_promise_to_pay():
    # evidence_refs populated -- this test's subject is the confidence
    # rung, not the (later-added, ticket 06) evidence-consistency rung.
    ao = _agent_output(stop_signals=["PROMISE_TO_PAY"], confidence=0.2, evidence_refs=["customer_reply"])
    d = route(ao, OK, pre_screen_matched=False, confidence_threshold=0.5)
    assert d.matched_rung == "LOW_CONFIDENCE"


def test_rcv_022_shape_pauses_because_pre_screen_does_not_match():
    # RCV-022: "...ignore my last message... payment will be received on
    # your end by Friday." Says "last message", not "previous"/"prior", so
    # the deterministic pre-screen correctly stays silent (§19's pinned
    # regex specificity) and PROMISE_TO_PAY is the effective signal.
    ao = _agent_output(stop_signals=["PROMISE_TO_PAY"], evidence_refs=["customer_reply"])
    d = route(ao, OK, pre_screen_matched=False)
    assert d.route == "PAUSE"
    assert d.matched_rung == "PROMISE_TO_PAY"


def test_malformed_event_beats_every_interpreter_signal():
    bad = PrecheckResult(ok=False, reason="missing order_id in razorpay_context")
    ao = _agent_output(stop_signals=["EXPLICIT_OPT_OUT", "DISPUTE_OR_REFUND", "PROMISE_TO_PAY"])
    d = route(ao, bad, pre_screen_matched=True)
    assert d.matched_rung == "MALFORMED_OR_DUPLICATE_EVENT"
