import json

from src.audit_log import AuditLog, verify_chain
from src.policy_engine import route
from src.structured_prechecks import PrecheckResult, check
from src.typed_boundary import AgentOutput

OK = PrecheckResult(ok=True)


def _agent_output(**overrides):
    defaults = dict(
        case_id="RCV-TEST",
        customer_state="RECOVERY_ELIGIBLE",
        stop_signals=[],
        confidence=0.9,
        evidence_refs=["customer_reply"],
        requires_human_review=False,
        suspected_injection=False,
    )
    defaults.update(overrides)
    return AgentOutput(**defaults)


def test_malformed_event_stops():
    bad = PrecheckResult(ok=False, reason="missing order_id in razorpay_context")
    d = route(_agent_output(), bad, pre_screen_matched=False)
    assert d.route == "STOP"
    assert d.matched_rung == "MALFORMED_OR_DUPLICATE_EVENT"


def test_payment_claim_routes_to_verify():
    ao = _agent_output(stop_signals=["PAYMENT_ALREADY_MADE_CLAIM"])
    d = route(ao, OK, pre_screen_matched=False)
    assert d.route == "VERIFY"
    assert d.matched_rung == "VERIFIED_PAYMENT_STATUS"


def test_opt_out_stops():
    ao = _agent_output(stop_signals=["EXPLICIT_OPT_OUT"])
    d = route(ao, OK, pre_screen_matched=False)
    assert d.route == "STOP"
    assert d.matched_rung == "EXPLICIT_OPT_OUT"


def test_dispute_stops():
    ao = _agent_output(stop_signals=["DISPUTE_OR_REFUND"])
    d = route(ao, OK, pre_screen_matched=False)
    assert d.route == "STOP"
    assert d.matched_rung == "DISPUTE_OR_REFUND"


def test_pre_screen_match_forces_review():
    d = route(_agent_output(), OK, pre_screen_matched=True)
    assert d.route == "REVIEW"
    assert d.matched_rung == "SUSPICIOUS_INSTRUCTION_DETECTED"


def test_suspected_injection_alone_does_not_force_review():
    # Layer 3 (the model's own label) is measured, not authoritative (§19)
    # -- it cannot override Layer 1. Only pre_screen_matched can.
    ao = _agent_output(suspected_injection=True, confidence=0.9)
    d = route(ao, OK, pre_screen_matched=False)
    assert d.route == "RECOVER"


def test_low_confidence_reviews():
    ao = _agent_output(confidence=0.3)
    d = route(ao, OK, pre_screen_matched=False, confidence_threshold=0.5)
    assert d.route == "REVIEW"
    assert d.matched_rung == "LOW_CONFIDENCE"


def test_ambiguous_reviews():
    ao = _agent_output(stop_signals=["AMBIGUOUS_OR_CONFLICTING"])
    d = route(ao, OK, pre_screen_matched=False)
    assert d.route == "REVIEW"
    assert d.matched_rung == "AMBIGUOUS_OR_CONFLICTING"


def test_promise_to_pay_pauses():
    ao = _agent_output(stop_signals=["PROMISE_TO_PAY"])
    d = route(ao, OK, pre_screen_matched=False)
    assert d.route == "PAUSE"
    assert d.matched_rung == "PROMISE_TO_PAY"


def test_recovery_eligible_with_quota_recovers():
    d = route(_agent_output(), OK, pre_screen_matched=False, quota_available=True)
    assert d.route == "RECOVER"
    assert d.matched_rung == "RECOVERY_ELIGIBLE"


def test_recovery_eligible_without_quota_guards():
    d = route(_agent_output(), OK, pre_screen_matched=False, quota_available=False)
    assert d.route == "LINK_QUOTA_GUARD"
    assert d.matched_rung == "RECOVERY_ELIGIBLE"


# --- Tracer bullet: real fixture cases through prechecks -> engine -> audit ---

CASES_DIR = "fixtures/development_cases.json"

# A mock interpreter's output for each case, hand-constructed the way a
# correct interpreter would read the customer_reply (§22: "mock the
# interpreter, build the engine against it, swap the real LLM in late").
# pre_screen_matched mirrors each case's own pre_screen_expected ground
# truth, standing in for ticket 03's not-yet-built detector.
MOCK_INTERPRETATIONS = {
    "RCV-004": dict(stop_signals=["DISPUTE_OR_REFUND"], pre_screen_matched=False, expected_route="STOP"),
    "RCV-011": dict(stop_signals=["EXPLICIT_OPT_OUT"], pre_screen_matched=False, expected_route="STOP"),
    "RCV-016": dict(stop_signals=["PAYMENT_ALREADY_MADE_CLAIM"], pre_screen_matched=False, expected_route="VERIFY"),
    "RCV-019": dict(stop_signals=["PAYMENT_ALREADY_MADE_CLAIM"], pre_screen_matched=False, expected_route="VERIFY"),
    # "...stop pestering me... don't call me... discuss later" -- opt-out
    # plus a vague, undated "later" that the specificity gate doesn't
    # count as PROMISE_TO_PAY, so opt-out is the only real signal.
    "RCV-023": dict(stop_signals=["EXPLICIT_OPT_OUT"], pre_screen_matched=False, expected_route="STOP"),
    "RCV-025": dict(stop_signals=[], pre_screen_matched=True, expected_route="REVIEW"),
    "RCV-034": dict(stop_signals=["AMBIGUOUS_OR_CONFLICTING"], pre_screen_matched=False, expected_route="REVIEW"),
    # Vague promise ("sure will pay soon") -- specificity gate says this
    # doesn't count, so the interpreter emits no PROMISE_TO_PAY signal.
    "RCV-045": dict(stop_signals=[], pre_screen_matched=False, expected_route="RECOVER"),
    "RCV-059": dict(stop_signals=["PROMISE_TO_PAY"], pre_screen_matched=False, expected_route="PAUSE"),
    # No customer_reply at all -- the ordinary, silent case (§20: "most
    # cases have no customer reply").
    "RCV-043": dict(stop_signals=[], pre_screen_matched=False, expected_route="RECOVER"),
}


def _load_case(case_id):
    with open(CASES_DIR, encoding="utf-8") as f:
        cases = json.load(f)
    return next(c for c in cases if c["case_id"] == case_id)


def test_tracer_bullet_matches_expected_route_for_each_case(tmp_path):
    audit_path = tmp_path / "tracer.jsonl"
    log = AuditLog(audit_path)
    seen_case_ids = set()

    for case_id, mock in MOCK_INTERPRETATIONS.items():
        case = _load_case(case_id)

        precheck = check(case, seen_case_ids)
        assert precheck.ok, f"{case_id}: unexpected precheck failure ({precheck.reason})"
        seen_case_ids.add(case_id)

        ao = AgentOutput(
            case_id=case_id,
            customer_state="from mock interpreter",
            stop_signals=mock["stop_signals"],
            confidence=0.9,
            evidence_refs=["customer_reply"] if case.get("customer_reply") else [],
            requires_human_review=False,
            suspected_injection=False,
        )
        decision = route(ao, precheck, pre_screen_matched=mock["pre_screen_matched"])

        assert decision.route == mock["expected_route"], (
            f"{case_id}: got {decision.route}, expected {mock['expected_route']}"
        )

        log.append(case_id, "POLICY_DECISION", {
            "route": decision.route,
            "matched_rung": decision.matched_rung,
            "reason": decision.reason,
        })

    ok, problems = verify_chain(audit_path)
    assert ok is True
    assert len(log.records()) == len(MOCK_INTERPRETATIONS)


def test_tracer_bullet_duplicate_event_is_precheck_stopped(tmp_path):
    case = _load_case("RCV-004")
    seen = {"RCV-004"}
    precheck = check(case, seen)
    assert precheck.ok is False
    assert "duplicate" in precheck.reason
