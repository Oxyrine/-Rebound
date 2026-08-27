"""Chaos Mock containment suite (§22) -- ticket 06.

All seven inputs here are hand-crafted, never derived from a fixture case's
expected_outcome: "a perfect mock never exercises the paths that matter"
(§22). Each test proves one containment claim from the spec's table.

The last test is not one of the seven -- it proves the spec's own stated
ceiling instead of just asserting it in prose: "The Chaos Mock proves
containment of malformed, inconsistent, low-confidence, and
deterministically contradicted outputs. It does not prove that the system
can detect every confident semantic misclassification in unstructured
text." A dispute that exists only in free text, missed by a confident
interpreter, is not caught by anything here -- and shouldn't appear to be.
"""

from unittest.mock import MagicMock

import pytest
import requests
from pydantic import ValidationError

from src.audit_log import AuditLog
from src.link_dispatch import dispatch_link, resolve_unknown_links
from src.policy_engine import route
from src.structured_prechecks import check, validate_output_case_id
from src.typed_boundary import AgentOutput


def _ao(**overrides):
    defaults = dict(
        case_id="CHAOS",
        customer_state="from mock interpreter",
        stop_signals=[],
        confidence=0.9,
        evidence_refs=[],
        requires_human_review=False,
        suspected_injection=False,
    )
    defaults.update(overrides)
    return AgentOutput(**defaults)


# 1. dispute_open structured flag, model says benign.
def test_dispute_open_flag_hard_stops_before_model_output_matters():
    event = {"case_id": "CHAOS-001", "dispute_open": True, "razorpay_context": {"order_id": "order_chaos"}}

    precheck = check(event, seen_case_ids=set())

    assert precheck.ok is False
    assert "dispute_open" in precheck.reason
    # A confident "benign" from the interpreter is never reached: route()
    # is never called for a failed precheck in the real pipeline.


# 2. Invalid schema or forbidden field.
def test_forbidden_field_rejected_by_typed_boundary():
    with pytest.raises(ValidationError):
        AgentOutput(
            case_id="CHAOS-002",
            customer_state="x",
            stop_signals=[],
            confidence=0.9,
            evidence_refs=[],
            requires_human_review=False,
            suspected_injection=False,
            amount=500,  # forbidden -- a "confident" model trying to emit money
        )


# 3. Missing / invalid evidence_refs.
def test_stop_signal_without_evidence_refs_reviews():
    # PROMISE_TO_PAY, not DISPUTE_OR_REFUND/EXPLICIT_OPT_OUT/
    # PAYMENT_ALREADY_MADE_CLAIM: those three are checked earlier in the
    # precedence chain and would short-circuit before this rung is ever
    # reached, so they wouldn't actually exercise this containment path.
    event = {"case_id": "CHAOS-003", "razorpay_context": {"order_id": "order_chaos"}}
    precheck = check(event, set())
    ao = _ao(case_id="CHAOS-003", stop_signals=["PROMISE_TO_PAY"], evidence_refs=[])

    decision = route(ao, precheck, pre_screen_matched=False)

    assert decision.route == "REVIEW"
    assert decision.matched_rung == "EVIDENCE_REFS_MISSING"


# 4. Confidence 0.4.
def test_low_confidence_reviews():
    event = {"case_id": "CHAOS-004", "razorpay_context": {"order_id": "order_chaos"}}
    precheck = check(event, set())
    ao = _ao(case_id="CHAOS-004", confidence=0.4)

    decision = route(ao, precheck, pre_screen_matched=False)

    assert decision.route == "REVIEW"
    assert decision.matched_rung == "LOW_CONFIDENCE"


# 5. Mismatched case ID.
def test_mismatched_case_id_rejected_before_routing():
    event = {"case_id": "CHAOS-005", "razorpay_context": {"order_id": "order_chaos"}}

    result = validate_output_case_id("CHAOS-999", event)

    assert result.ok is False
    assert "CHAOS-005" in result.reason
    assert "CHAOS-999" in result.reason
    # route() is never called on a rejected output in the real pipeline --
    # there's no routing decision to make about output we can't trust the
    # identity of.


# 6. Timeout after remote link creation.
def test_timeout_after_link_creation_goes_unknown_and_is_reconciled_without_retry(tmp_path):
    log = AuditLog(tmp_path / "chaos.jsonl")
    client = MagicMock()
    client.create_payment_link.side_effect = requests.Timeout("simulated network timeout")

    result = dispatch_link(
        log, client, case_id="CHAOS-006", amount_paise=100, reference_id="REBOUND-CHAOS-006", description="d"
    )
    assert result.status == "UNKNOWN"

    # A second dispatch for the same case must not call create_payment_link
    # again -- no blind retry.
    result2 = dispatch_link(
        log, client, case_id="CHAOS-006", amount_paise=100, reference_id="REBOUND-CHAOS-006", description="d"
    )
    assert result2.status == "UNKNOWN"
    assert client.create_payment_link.call_count == 1

    # Reconciliation resolves it by lookup, never by retrying creation.
    client.find_link_by_reference.return_value = {"id": "plink_found", "short_url": "https://rzp.io/i/x"}
    resolved = resolve_unknown_links(log, client)

    assert resolved == [{"case_id": "CHAOS-006", "status": "RESOLVED_CREATED", "payment_link_id": "plink_found"}]
    assert client.create_payment_link.call_count == 1
    client.find_link_by_reference.assert_called_once_with("REBOUND-CHAOS-006")


# 7. Duplicate event ID.
def test_duplicate_case_id_deduped_no_second_action():
    event = {"case_id": "CHAOS-007", "razorpay_context": {"order_id": "order_chaos"}}

    precheck = check(event, seen_case_ids={"CHAOS-007"})

    assert precheck.ok is False
    assert "duplicate" in precheck.reason


# The honest ceiling, proven rather than asserted.
def test_semantic_misclassification_is_not_structurally_caught():
    event = {"case_id": "CHAOS-LIMIT", "razorpay_context": {"order_id": "order_chaos"}}
    precheck = check(event, set())
    # A real dispute that exists only in free text -- nothing structured
    # for the pre-check to see -- confidently (and wrongly) read as benign.
    ao = _ao(case_id="CHAOS-LIMIT", customer_state="benign", confidence=0.94, evidence_refs=["customer_reply"])

    decision = route(ao, precheck, pre_screen_matched=False)

    # This is the honest failure: nothing structural can know "benign" is
    # semantically wrong when the dispute lived only in text the
    # interpreter itself misjudged. It proceeds to RECOVER.
    assert decision.route == "RECOVER"
