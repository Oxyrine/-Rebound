from unittest.mock import MagicMock

import pytest

from src.razorpay_client import RazorpayClient, RazorpayConfigError


def _fake_session(json_body, status_ok=True):
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = json_body
    if not status_ok:
        resp.raise_for_status.side_effect = Exception("http error")
    session.post.return_value = resp
    session.get.return_value = resp
    return session


def test_create_payment_link_posts_expected_payload():
    session = _fake_session({"id": "plink_123", "short_url": "https://rzp.io/i/abc"})
    client = RazorpayClient(session=session)

    result = client.create_payment_link(amount_paise=100, reference_id="REBOUND-RCV-001", description="Test")

    assert result["id"] == "plink_123"
    _, kwargs = session.post.call_args
    assert kwargs["json"]["amount"] == 100
    assert kwargs["json"]["reference_id"] == "REBOUND-RCV-001"
    assert kwargs["json"]["currency"] == "INR"


def test_fetch_payment_link_gets_by_id():
    session = _fake_session({"id": "plink_123", "status": "paid"})
    client = RazorpayClient(session=session)

    result = client.fetch_payment_link("plink_123")

    assert result["status"] == "paid"
    session.get.assert_called_once_with("https://api.razorpay.com/v1/payment_links/plink_123")


def test_fetch_payment_gets_by_id():
    session = _fake_session({"id": "pay_123", "status": "captured"})
    client = RazorpayClient(session=session)

    result = client.fetch_payment("pay_123")

    assert result["status"] == "captured"


def test_http_error_propagates():
    session = _fake_session({}, status_ok=False)
    client = RazorpayClient(session=session)

    with pytest.raises(Exception):
        client.create_payment_link(amount_paise=100, reference_id="X", description="Y")


def test_missing_credentials_raises(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    with pytest.raises(RazorpayConfigError):
        RazorpayClient()


def test_placeholder_credentials_raise(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_xxxxxxxxxxxx")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "xxxxxxxxxxxxxxxxxxxx")

    with pytest.raises(RazorpayConfigError):
        RazorpayClient()
