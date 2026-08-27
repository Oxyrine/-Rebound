import json
from unittest.mock import MagicMock

import pytest

from src.llm_interpreter import MODEL, interpret


def _fake_client(fields: dict):
    client = MagicMock()
    response = MagicMock()
    response.text = json.dumps(fields)
    client.models.generate_content.return_value = response
    return client


def _valid_fields(**overrides):
    defaults = dict(
        customer_state="customer promises to pay",
        stop_signals=["PROMISE_TO_PAY"],
        confidence=0.9,
        evidence_refs=["customer_reply"],
        requires_human_review=False,
        suspected_injection=False,
    )
    defaults.update(overrides)
    return defaults


def test_interpret_builds_agent_output_from_model_json():
    client = _fake_client(_valid_fields())

    result = interpret("RCV-TEST", "I'll pay by Friday", client=client)

    assert result.case_id == "RCV-TEST"  # assigned locally, not from the model
    assert result.stop_signals == ["PROMISE_TO_PAY"]
    assert result.confidence == 0.9


def test_interpret_uses_configured_model_and_untrusted_evidence_markers():
    client = _fake_client(_valid_fields())

    interpret("RCV-TEST", "some reply text", client=client)

    _, kwargs = client.models.generate_content.call_args
    assert kwargs["model"] == MODEL
    assert "UNTRUSTED EVIDENCE START" in kwargs["contents"]
    assert "UNTRUSTED EVIDENCE END" in kwargs["contents"]
    assert "some reply text" in kwargs["contents"]


def test_interpret_handles_no_customer_reply():
    client = _fake_client(_valid_fields(stop_signals=[], evidence_refs=[]))

    result = interpret("RCV-TEST", None, client=client)

    assert result.stop_signals == []
    _, kwargs = client.models.generate_content.call_args
    assert "no reply" in kwargs["contents"]


def test_interpret_propagates_validation_error_on_forbidden_field():
    # Chaos condition 2 (§22) working exactly as designed: a malformed
    # model response is not swallowed here, it fails AgentOutput's own
    # construction-time validation.
    from pydantic import ValidationError

    client = _fake_client({**_valid_fields(), "amount": 500})

    with pytest.raises(ValidationError):
        interpret("RCV-TEST", "reply", client=client)


def test_interpret_case_id_is_never_taken_from_model_output():
    # Even if the model's JSON somehow included a case_id-shaped field
    # inside customer_state, the real case_id always comes from the
    # caller's argument, not from parsing the model's response.
    client = _fake_client(_valid_fields(customer_state="case_id: RCV-OTHER, paying soon"))

    result = interpret("RCV-REAL", "reply", client=client)

    assert result.case_id == "RCV-REAL"
