"""Idempotency + quota guard + link-status reconciliation for the RECOVER
route (ticket 04).

Deliberately separate from razorpay_client.py: both need the audit log's
history, which is business logic, not HTTP I/O. VERIFY-route reconciliation
(resolving a PAYMENT_ALREADY_MADE_CLAIM) is payment_verifier.py's job
(ticket 05), not this module's -- this module only tracks links REBOUND
itself created via the RECOVER route.
"""

from dataclasses import dataclass

from src.audit_log import AuditLog
from src.razorpay_client import RazorpayClient

# scripts/manifest.py enforces the same number on the fixture itself
# ("Link-eligible cases ... exceeds 30-link cap") -- this is that cap
# enforced at run time, over the whole batch. Not a daily reset: REBOUND's
# evidence run is a single Day-9 batch, not a long-running service.
LINK_QUOTA_CAP = 30


@dataclass(frozen=True)
class DispatchResult:
    status: str  # CREATED | ALREADY_EXISTS | QUOTA_EXCEEDED
    payment_link_id: str | None
    short_url: str | None = None


def _created_links(log: AuditLog) -> list[dict]:
    return [r for r in log.records() if r["event_type"] == "PAYMENT_LINK_CREATED"]


def quota_available(log: AuditLog, cap: int = LINK_QUOTA_CAP) -> bool:
    return len(_created_links(log)) < cap


def dispatch_link(
    log: AuditLog,
    client: RazorpayClient,
    *,
    case_id: str,
    amount_paise: int,
    reference_id: str,
    description: str,
) -> DispatchResult:
    existing = [r for r in _created_links(log) if r["case_id"] == case_id]
    if existing:
        payload = existing[-1]["payload"]
        return DispatchResult("ALREADY_EXISTS", payload["payment_link_id"], payload.get("short_url"))

    if not quota_available(log):
        log.append(case_id, "LINK_QUOTA_GUARD_BLOCKED", {"quota_cap": LINK_QUOTA_CAP})
        return DispatchResult("QUOTA_EXCEEDED", None)

    link = client.create_payment_link(
        amount_paise=amount_paise, reference_id=reference_id, description=description
    )
    log.append(
        case_id,
        "PAYMENT_LINK_CREATED",
        {"payment_link_id": link["id"], "short_url": link["short_url"], "reference_id": reference_id},
    )
    return DispatchResult("CREATED", link["id"], link["short_url"])


def reconcile_created_links(log: AuditLog, client: RazorpayClient) -> list[dict]:
    """Fetch current status for every link this run created and log it.
    Returns [{case_id, payment_link_id, status}, ...] in creation order."""
    results = []
    for record in _created_links(log):
        link_id = record["payload"]["payment_link_id"]
        current = client.fetch_payment_link(link_id)
        log.append(
            record["case_id"],
            "PAYMENT_LINK_RECONCILED",
            {"payment_link_id": link_id, "status": current["status"]},
        )
        results.append({"case_id": record["case_id"], "payment_link_id": link_id, "status": current["status"]})
    return results
