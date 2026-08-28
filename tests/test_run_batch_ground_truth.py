"""Regression tests for the gt_hard_stop type bug caught during Day-1 review
of tickets 02-05: gt_map holds frozen-label STRINGS (RECOVERY_ELIGIBLE,
HARD_STOP, ...), never booleans. `gt_map.get(case_id, <bool default>)`
silently returned the raw string when a case_id was present -- every
non-empty string is truthy in Python, so every held-out case with a frozen
label would register as gt_hard_stop=True regardless of what the label
actually said. This corrupted src/metrics.py's hard_stop_matrix() silently,
and nothing in the existing test_run_batch.py suite exercised run()'s
actual dict construction (every test there mocks run() or _load_cases()
out).
"""

from unittest.mock import MagicMock

from src.audit_log import AuditLog
from src.typed_boundary import AgentOutput
from scripts.run_batch import run


def _case(case_id, expected_outcome, bucket="BENIGN"):
    return {
        "case_id": case_id,
        "bucket": bucket,
        "expected_outcome": expected_outcome,
        "razorpay_context": {"order_id": "order_x", "payment_id": None},
        "merchant_reference_id": f"REBOUND-{case_id}",
        "customer_reply": "hello",
    }


def _interpret(case_id, customer_reply):
    return AgentOutput(
        case_id=case_id, customer_state="benign", stop_signals=[], confidence=1.0,
        evidence_refs=[], requires_human_review=False, suspected_injection=False,
    )


def test_gt_hard_stop_is_a_real_bool_when_frozen_label_says_not_a_hard_stop(tmp_path):
    # Frozen ground truth says RECOVERY_ELIGIBLE -- a truthy STRING under the
    # old `gt_map.get(case_id, default)` bug, which would have reported this
    # case as gt_hard_stop=True purely because the string is non-empty.
    gt_map = {"RCV-X": "RECOVERY_ELIGIBLE"}
    case = _case("RCV-X", expected_outcome="HARD_STOP")  # Day-1 fixture disagreed -- irrelevant here
    log = AuditLog(tmp_path / "audit.jsonl")

    results = run([case], _interpret, log, MagicMock(), gt_map, execute_links=False, is_llm=False)

    assert results[0]["gt_hard_stop"] is False
    assert results[0]["has_frozen_ground_truth"] is True


def test_gt_hard_stop_is_true_only_for_the_hard_stop_label(tmp_path):
    gt_map = {"RCV-Y": "HARD_STOP"}
    case = _case("RCV-Y", expected_outcome="HARD_STOP")
    log = AuditLog(tmp_path / "audit.jsonl")

    results = run([case], _interpret, log, MagicMock(), gt_map, execute_links=False, is_llm=False)

    assert results[0]["gt_hard_stop"] is True
    assert results[0]["has_frozen_ground_truth"] is True


def test_gt_hard_stop_falls_back_to_fixture_label_when_not_frozen(tmp_path):
    # Dev cases (or held-out cases not yet frozen) have no entry in gt_map.
    case = _case("RCV-Z", expected_outcome="HARD_STOP")
    log = AuditLog(tmp_path / "audit.jsonl")

    results = run([case], _interpret, log, MagicMock(), {}, execute_links=False, is_llm=False)

    assert results[0]["gt_hard_stop"] is True
    assert results[0]["has_frozen_ground_truth"] is False
