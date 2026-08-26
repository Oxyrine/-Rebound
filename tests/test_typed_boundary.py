import pytest
from pydantic import ValidationError

from src.typed_boundary import AgentOutput

VALID = dict(
    case_id="rcv_1042",
    customer_state="POSSIBLE_ALREADY_PAID_OR_DISPUTE",
    stop_signals=["PAYMENT_ALREADY_MADE_CLAIM"],
    confidence=0.91,
    evidence_refs=["customer_reply"],
    requires_human_review=True,
    suspected_injection=False,
)


def test_valid_output_constructs():
    out = AgentOutput(**VALID)
    assert out.case_id == "rcv_1042"


@pytest.mark.parametrize(
    "forbidden_field,value",
    [
        ("amount", 500),
        ("discount", 100),
        ("waiver", True),
        ("refund", 500),
        ("payment_link_url", "https://rzp.io/l/abc"),
        ("execution_action", "CREATE_PAYMENT_LINK"),
        ("retry_time", "2026-09-01T00:00:00"),
        ("message", "Please pay now"),
        ("policy_override", True),
        ("tool_name", "create_payment_link"),
    ],
)
def test_forbidden_fields_rejected(forbidden_field, value):
    with pytest.raises(ValidationError):
        AgentOutput(**VALID, **{forbidden_field: value})


def test_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        AgentOutput(**{**VALID, "confidence": 1.5})


def test_missing_required_field_rejected():
    incomplete = dict(VALID)
    del incomplete["case_id"]
    with pytest.raises(ValidationError):
        AgentOutput(**incomplete)
