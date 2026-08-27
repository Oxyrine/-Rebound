import json

from src.rules_interpreter import interpret


def test_paid_flags_payment_claim():
    result = interpret("RCV-TEST", "I already paid this yesterday")
    assert result.stop_signals == ["PAYMENT_ALREADY_MADE_CLAIM"]
    assert result.confidence == 1.0


def test_payment_done_flags_payment_claim():
    result = interpret("RCV-TEST", "payment done on my end")
    assert result.stop_signals == ["PAYMENT_ALREADY_MADE_CLAIM"]


def test_stop_flags_opt_out():
    result = interpret("RCV-TEST", "please stop calling me")
    assert result.stop_signals == ["EXPLICIT_OPT_OUT"]


def test_dont_contact_flags_opt_out():
    result = interpret("RCV-TEST", "don't contact me again")
    assert result.stop_signals == ["EXPLICIT_OPT_OUT"]


def test_refund_flags_dispute():
    result = interpret("RCV-TEST", "I want a refund for this")
    assert result.stop_signals == ["DISPUTE_OR_REFUND"]


def test_wrong_item_flags_dispute():
    result = interpret("RCV-TEST", "this is the wrong item")
    assert result.stop_signals == ["DISPUTE_OR_REFUND"]


def test_dispute_word_flags_dispute():
    result = interpret("RCV-TEST", "I want to dispute this charge")
    assert result.stop_signals == ["DISPUTE_OR_REFUND"]


def test_no_keywords_no_signal():
    result = interpret("RCV-TEST", "will look into it")
    assert result.stop_signals == []
    assert result.confidence == 0.9
    assert result.evidence_refs == []


def test_none_reply_no_signal():
    result = interpret("RCV-TEST", None)
    assert result.stop_signals == []


def test_multiple_keyword_classes_all_returned():
    # Doesn't pre-apply precedence -- policy_engine.route() does that.
    result = interpret("RCV-TEST", "I already paid, now please stop contacting me")
    assert set(result.stop_signals) == {"PAYMENT_ALREADY_MADE_CLAIM", "EXPLICIT_OPT_OUT"}


def test_case_id_assigned_locally():
    result = interpret("RCV-REAL", "paid")
    assert result.case_id == "RCV-REAL"


def test_full_fixture_never_crashes():
    # Not an accuracy assertion -- a keyword baseline is expected to miss
    # most Tamil/Hinglish cases. This just guards construction (encoding,
    # AgentOutput validity) across every real case in the fixture.
    dev = json.load(open("fixtures/development_cases.json", encoding="utf-8"))
    held = json.load(open("fixtures/heldout_cases.json", encoding="utf-8"))
    for case in dev + held:
        result = interpret(case["case_id"], case.get("customer_reply"))
        assert result.case_id == case["case_id"]
