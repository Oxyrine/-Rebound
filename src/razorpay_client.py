"""Thin HTTP wrapper over the Razorpay Payment Links API (Test Mode).

Pure I/O -- no idempotency, no quota logic, no audit logging. Those live in
link_dispatch.py (ticket 04) because they need the audit log's history, not
the API. fetch_payment lives here (unused by ticket 04) because
payment_verifier.py (ticket 05, resolving PAYMENT_ALREADY_MADE_CLAIM) needs
the same client rather than a second one.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.razorpay.com/v1"


class RazorpayConfigError(RuntimeError):
    """RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET missing or still placeholders."""


def _credentials() -> tuple[str, str]:
    key_id = os.environ.get("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
    if not key_id or not key_secret or "xxxx" in key_id:
        raise RazorpayConfigError("RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET not set -- fill in .env")
    return key_id, key_secret


class RazorpayClient:
    def __init__(self, session: requests.Session | None = None):
        key_id, key_secret = _credentials()
        self._session = session or requests.Session()
        self._session.auth = (key_id, key_secret)

    def create_payment_link(
        self, *, amount_paise: int, reference_id: str, description: str, currency: str = "INR"
    ) -> dict:
        resp = self._session.post(
            f"{BASE_URL}/payment_links",
            json={
                "amount": amount_paise,
                "currency": currency,
                "reference_id": reference_id,
                "description": description,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_payment_link(self, payment_link_id: str) -> dict:
        resp = self._session.get(f"{BASE_URL}/payment_links/{payment_link_id}")
        resp.raise_for_status()
        return resp.json()

    def fetch_payment(self, payment_id: str) -> dict:
        resp = self._session.get(f"{BASE_URL}/payments/{payment_id}")
        resp.raise_for_status()
        return resp.json()
