from unittest.mock import MagicMock

import pytest
import requests

from src.payment_verifier import verify_payment_claim


def _client(payment=None, http_error_status=None, error_body=None):
    client = MagicMock()
    if http_error_status is not None:
        resp = MagicMock()
        resp.status_code = http_error_status
        resp.json.return_value = error_body or {}
        client.fetch_payment.side_effect = requests.HTTPError(response=resp)
    else:
        client.fetch_payment.return_value = payment
    return client


def test_no_payment_id_reviews_without_calling_api():
    client = _client()

    result = verify_payment_claim(client, order_id="order_x", claimed_payment_id=None)

    assert result.outcome == "HUMAN_REVIEW"
    client.fetch_payment.assert_not_called()


def test_captured_payment_matching_order_closes():
    # RCV-016 shape: real payment_id, captured, matches this case's order.
    client = _client(payment={"status": "captured", "order_id": "order_puMTPyLvA9Q276"})

    result = verify_payment_claim(
        client, order_id="order_puMTPyLvA9Q276", claimed_payment_id="pay_1T0Ayx1ZzgwgFO"
    )

    assert result.outcome == "ALREADY_PAID_CLOSED"


def test_captured_payment_wrong_order_reviews():
    client = _client(payment={"status": "captured", "order_id": "order_OTHER"})

    result = verify_payment_claim(client, order_id="order_mine", claimed_payment_id="pay_x")

    assert result.outcome == "HUMAN_REVIEW"


def test_uncaptured_payment_reviews():
    client = _client(payment={"status": "authorized", "order_id": "order_mine"})

    result = verify_payment_claim(client, order_id="order_mine", claimed_payment_id="pay_x")

    assert result.outcome == "HUMAN_REVIEW"


def test_payment_not_found_reviews():
    # RCV-019 shape: no payment_id at all is tested separately; this covers
    # a payment_id that was given but doesn't exist (RCV-018 shape).
    # Body shape confirmed against the live API, not assumed: Razorpay
    # returns 400/BAD_REQUEST_ERROR for an unknown payment_id, not 404.
    client = _client(
        http_error_status=400,
        error_body={"error": {"code": "BAD_REQUEST_ERROR", "description": "The id provided does not exist"}},
    )

    result = verify_payment_claim(client, order_id="order_mine", claimed_payment_id="pay_ghost")

    assert result.outcome == "HUMAN_REVIEW"


def test_other_400_does_not_get_treated_as_not_found():
    # A 400 for some other reason (e.g. a malformed request of our own
    # making) must not be silently downgraded into a business decision.
    client = _client(http_error_status=400, error_body={"error": {"code": "SERVER_ERROR"}})

    with pytest.raises(requests.HTTPError):
        verify_payment_claim(client, order_id="order_mine", claimed_payment_id="pay_x")


def test_other_http_error_propagates():
    client = _client(http_error_status=500, error_body={"error": {"code": "SERVER_ERROR"}})

    with pytest.raises(requests.HTTPError):
        verify_payment_claim(client, order_id="order_mine", claimed_payment_id="pay_x")
