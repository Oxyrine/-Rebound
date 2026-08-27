from src.metrics import (
    format_report,
    hard_stop_matrix,
    operational_reliability,
    recovery_funnel,
    safety_outcomes,
)


def _result(**overrides):
    defaults = dict(
        case_id="RCV-X", bucket="BENIGN", route="RECOVER", matched_rung="RECOVERY_ELIGIBLE",
        resolved_outcome=None, link_status=None, link_amount_paise=None, link_completed=False,
        gt_hard_stop=False, stop_signals=[],
    )
    defaults.update(overrides)
    return defaults


def test_recovery_funnel_counts_stages():
    results = [
        _result(route="RECOVER", link_status="CREATED", link_amount_paise=500, link_completed=True),
        _result(route="RECOVER", link_status="CREATED", link_amount_paise=300, link_completed=False),
        _result(route="LINK_QUOTA_GUARD"),
        _result(route="STOP"),
    ]
    funnel = recovery_funnel(results)
    assert funnel == {
        "evaluated": 4, "eligible": 3, "link_attempts": 2,
        "created": 2, "completed": 1, "completed_value_rupees": 5.0,
    }


def test_safety_outcomes_counts_each_route():
    results = [
        _result(route="STOP"),
        _result(route="PAUSE"),
        _result(route="REVIEW", resolved_outcome="HUMAN_REVIEW"),
        _result(route="VERIFY", resolved_outcome="HUMAN_REVIEW"),
        _result(route="VERIFY", resolved_outcome="ALREADY_PAID_CLOSED"),
        _result(route="RECOVER"),
    ]
    safety = safety_outcomes(results)
    assert safety == {"STOPPED": 1, "PAUSED": 1, "HUMAN_REVIEW": 2, "NO_ACTION": 2}


def test_hard_stop_matrix_only_counts_relevant_buckets():
    results = [
        _result(bucket="DISPUTE_REFUND", gt_hard_stop=True, route="STOP"),  # true stop
        _result(bucket="OPT_OUT", gt_hard_stop=True, route="RECOVER"),  # missed, unsafe
        _result(bucket="MULTI_SIGNAL", gt_hard_stop=False, route="STOP"),  # false stop
        _result(bucket="MULTI_SIGNAL", gt_hard_stop=False, route="RECOVER"),  # correct non-stop
        _result(bucket="ALREADY_PAID_TRUE", gt_hard_stop=False, route="RECOVER"),  # excluded bucket
    ]
    matrix = hard_stop_matrix(results)
    assert matrix == {
        "true_stop": 1, "false_stop": 1, "missed_stop": 1,
        "missed_stop_but_still_safe": 0, "missed_stop_unsafe": 1,
        "correct_non_stop": 1, "denominator": 4,
    }


def test_hard_stop_matrix_distinguishes_safe_from_unsafe_misses():
    # A dispute-bucket case that also carries a payment claim correctly
    # routes to VERIFY first (policy_engine's own frozen precedence) --
    # that's not the same danger as silently falling through to RECOVER.
    results = [
        _result(bucket="DISPUTE_REFUND", gt_hard_stop=True, route="VERIFY"),
        _result(bucket="DISPUTE_REFUND", gt_hard_stop=True, route="RECOVER"),
    ]
    matrix = hard_stop_matrix(results)
    assert matrix["missed_stop"] == 2
    assert matrix["missed_stop_but_still_safe"] == 1
    assert matrix["missed_stop_unsafe"] == 1


def test_operational_reliability_counts_audit_events():
    audit_records = [
        {"event_type": "POLICY_DECISION", "payload": {"matched_rung": "MALFORMED_OR_DUPLICATE_EVENT"}},
        {"event_type": "POLICY_DECISION", "payload": {"matched_rung": "RECOVERY_ELIGIBLE"}},
        {"event_type": "PAYMENT_LINK_RECONCILED", "payload": {}},
        {"event_type": "LINK_QUOTA_GUARD_BLOCKED", "payload": {}},
    ]
    results = [
        _result(route="VERIFY", stop_signals=["PAYMENT_ALREADY_MADE_CLAIM"]),
        _result(route="RECOVER", stop_signals=[]),
    ]
    reliability = operational_reliability(audit_records, results)
    assert reliability == {
        "duplicates_prevented": 1,
        "unknown_reconciled": 1,
        "quota_blocks": 1,
        "payment_claims_verified_engine": 1,
        "payment_claims_detected_interpreter": 1,
    }


def test_format_report_uses_held_out_framing_not_percentage_claims():
    funnel = recovery_funnel([_result()])
    safety = safety_outcomes([_result()])
    matrix = hard_stop_matrix([_result(bucket="DISPUTE_REFUND", gt_hard_stop=True, route="STOP")])
    reliability = operational_reliability([], [_result()])

    report = format_report(funnel, safety, matrix, reliability, split_label="held-out")

    assert "on this held-out fixture" in report.lower()
    assert "%" not in report  # raw counts, no percentages, per §24
