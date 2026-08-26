"""Resolves the policy engine's VERIFY route (PAYMENT_ALREADY_MADE_CLAIM)
against real Razorpay payment status -- ticket 05.

Only produces a positive close when a specific payment_id both exists and
is captured against the case's own order. Every other outcome -- no
payment_id to check, the id doesn't exist, it exists but isn't captured, or
it belongs to a different order -- routes to human review rather than to
either side of an assumption. This matches the fixture's own ground truth:
every ALREADY_PAID_FALSE case (a claim that doesn't hold up) resolves to
HUMAN_REVIEW, never silently back into RECOVER -- re-dunning someone who
may have genuinely paid is exactly the failure mode REBOUND exists to
prevent.

Razorpay's Payments API returns 400 (not 404) for a payment_id that doesn't
exist, with body {"error": {"code": "BAD_REQUEST_ERROR", ...}} -- confirmed
empirically against the live Test Mode account, not assumed from REST
convention. Only that specific 400 downgrades to review; any other HTTP
error (auth failure, 5xx, a genuinely malformed request of our own making)
propagates instead of being swallowed into a business decision -- those are
ops failures, not evidence about the claim.
"""

from dataclasses import dataclass

import requests

from src.razorpay_client import RazorpayClient


@dataclass(frozen=True)
class VerificationResult:
    outcome: str  # ALREADY_PAID_CLOSED | HUMAN_REVIEW
    reason: str


def verify_payment_claim(
    client: RazorpayClient, *, order_id: str, claimed_payment_id: str | None
) -> VerificationResult:
    if not claimed_payment_id:
        return VerificationResult("HUMAN_REVIEW", "no payment_id to verify against")

    try:
        payment = client.fetch_payment(claimed_payment_id)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 400:
            body = exc.response.json()
            if body.get("error", {}).get("code") == "BAD_REQUEST_ERROR":
                return VerificationResult("HUMAN_REVIEW", f"payment_id {claimed_payment_id} not found")
        raise

    if payment.get("status") != "captured":
        return VerificationResult("HUMAN_REVIEW", f"payment status is '{payment.get('status')}', not captured")

    if payment.get("order_id") != order_id:
        return VerificationResult("HUMAN_REVIEW", "payment does not match this case's order_id")

    return VerificationResult("ALREADY_PAID_CLOSED", "payment captured and matches order")
