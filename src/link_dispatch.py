"""Idempotency + quota guard + link-status reconciliation for the RECOVER
route (ticket 04).

Deliberately separate from razorpay_client.py: both need the audit log's
history, which is business logic, not HTTP I/O. VERIFY-route reconciliation
(resolving a PAYMENT_ALREADY_MADE_CLAIM) is payment_verifier.py's job
(ticket 05), not this module's -- this module only tracks links REBOUND
itself created via the RECOVER route.
"""

from dataclasses import dataclass

import requests

from src.audit_log import AuditLog
from src.razorpay_client import RazorpayClient

# scripts/manifest.py enforces the same number on the fixture itself
# ("Link-eligible cases ... exceeds 28-link cap") -- this is that cap
# enforced at run time, over the whole batch. Not a daily reset: REBOUND's
# evidence run is a single Day-9 batch, not a long-running service.
LINK_QUOTA_CAP = 28


@dataclass(frozen=True)
class DispatchResult:
    status: str  # CREATED | ALREADY_EXISTS | QUOTA_EXCEEDED | UNKNOWN
    payment_link_id: str | None
    short_url: str | None = None


def _created_links(log: AuditLog) -> list[dict]:
    return [r for r in log.records() if r["event_type"] == "PAYMENT_LINK_CREATED"]


def _unresolved_unknown_case_ids(log: AuditLog) -> set[str]:
    unknown = {r["case_id"] for r in log.records() if r["event_type"] == "PAYMENT_LINK_CREATE_UNKNOWN"}
    resolved = {r["case_id"] for r in _created_links(log)}
    return unknown - resolved


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

    # Chaos condition 6 (§22): a prior call for this case timed out and we
    # never learned whether Razorpay created the link before the response
    # was lost. Never call create_payment_link again for it -- that could
    # produce a real second link if the first request did succeed
    # server-side. Only resolve_unknown_links() (a lookup, not a retry) may
    # move this forward.
    if case_id in _unresolved_unknown_case_ids(log):
        return DispatchResult("UNKNOWN", None)

    if not quota_available(log):
        log.append(case_id, "LINK_QUOTA_GUARD_BLOCKED", {"quota_cap": LINK_QUOTA_CAP})
        return DispatchResult("QUOTA_EXCEEDED", None)

    try:
        link = client.create_payment_link(
            amount_paise=amount_paise, reference_id=reference_id, description=description
        )
    except requests.Timeout:
        log.append(case_id, "PAYMENT_LINK_CREATE_UNKNOWN", {"reference_id": reference_id})
        return DispatchResult("UNKNOWN", None)

    log.append(
        case_id,
        "PAYMENT_LINK_CREATED",
        {"payment_link_id": link["id"], "short_url": link["short_url"], "reference_id": reference_id},
    )
    return DispatchResult("CREATED", link["id"], link["short_url"])


def resolve_unknown_links(log: AuditLog, client: RazorpayClient) -> list[dict]:
    """Chaos condition 6 (§22): resolve every unresolved UNKNOWN case by
    looking its reference_id up on Razorpay -- never by retrying creation.
    Returns [{case_id, status: RESOLVED_CREATED|STILL_UNKNOWN, ...}, ...]."""
    results = []
    for record in log.records():
        if record["event_type"] != "PAYMENT_LINK_CREATE_UNKNOWN":
            continue
        if record["case_id"] not in _unresolved_unknown_case_ids(log):
            continue  # already resolved by an earlier record in this same pass

        reference_id = record["payload"]["reference_id"]
        found = client.find_link_by_reference(reference_id)
        if found is not None:
            log.append(
                record["case_id"],
                "PAYMENT_LINK_CREATED",
                {"payment_link_id": found["id"], "short_url": found["short_url"], "reference_id": reference_id},
            )
            results.append(
                {"case_id": record["case_id"], "status": "RESOLVED_CREATED", "payment_link_id": found["id"]}
            )
        else:
            results.append({"case_id": record["case_id"], "status": "STILL_UNKNOWN"})
    return results


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
