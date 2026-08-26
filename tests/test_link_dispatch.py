from unittest.mock import MagicMock

from src.audit_log import AuditLog, verify_chain
from src.link_dispatch import LINK_QUOTA_CAP, dispatch_link, reconcile_created_links


def _fake_client(link_id="plink_1", short_url="https://rzp.io/i/x", status="paid"):
    client = MagicMock()
    client.create_payment_link.return_value = {"id": link_id, "short_url": short_url}
    client.fetch_payment_link.return_value = {"id": link_id, "status": status}
    return client


def test_dispatch_creates_link_first_time(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    client = _fake_client()

    result = dispatch_link(
        log, client, case_id="RCV-001", amount_paise=500, reference_id="REBOUND-RCV-001", description="d"
    )

    assert result.status == "CREATED"
    assert result.payment_link_id == "plink_1"
    client.create_payment_link.assert_called_once()


def test_dispatch_is_idempotent_for_same_case(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    client = _fake_client()
    dispatch_link(log, client, case_id="RCV-001", amount_paise=500, reference_id="REBOUND-RCV-001", description="d")

    result = dispatch_link(
        log, client, case_id="RCV-001", amount_paise=500, reference_id="REBOUND-RCV-001", description="d"
    )

    assert result.status == "ALREADY_EXISTS"
    assert result.payment_link_id == "plink_1"
    client.create_payment_link.assert_called_once()


def test_dispatch_blocks_and_logs_when_quota_exhausted(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    client = _fake_client()
    for i in range(LINK_QUOTA_CAP):
        dispatch_link(
            log, client, case_id=f"RCV-{i:03d}", amount_paise=100, reference_id=f"REBOUND-RCV-{i:03d}", description="d"
        )

    result = dispatch_link(
        log, client, case_id="RCV-OVER", amount_paise=100, reference_id="REBOUND-RCV-OVER", description="d"
    )

    assert result.status == "QUOTA_EXCEEDED"
    assert client.create_payment_link.call_count == LINK_QUOTA_CAP
    blocked = [r for r in log.records() if r["event_type"] == "LINK_QUOTA_GUARD_BLOCKED"]
    assert len(blocked) == 1
    assert blocked[0]["case_id"] == "RCV-OVER"


def test_reconcile_created_links_fetches_current_status(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    client = _fake_client(status="paid")
    dispatch_link(log, client, case_id="RCV-001", amount_paise=500, reference_id="REBOUND-RCV-001", description="d")

    results = reconcile_created_links(log, client)

    assert results == [{"case_id": "RCV-001", "payment_link_id": "plink_1", "status": "paid"}]
    reconciled = [r for r in log.records() if r["event_type"] == "PAYMENT_LINK_RECONCILED"]
    assert len(reconciled) == 1
    assert reconciled[0]["payload"]["status"] == "paid"


def test_audit_chain_stays_valid_after_dispatch_and_reconcile(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    client = _fake_client()
    dispatch_link(log, client, case_id="RCV-001", amount_paise=500, reference_id="REBOUND-RCV-001", description="d")
    reconcile_created_links(log, client)

    ok, problems = verify_chain(path)

    assert ok is True
    assert problems == []
