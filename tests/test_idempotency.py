"""spec-amendment-01 ticket 06: the replay / idempotency invariant.

    For a fixed case_id and a fixed pinned audit path, running the pipeline
    twice must not produce more than one PAYMENT_LINK_CREATED event.

This is a deterministic regression test, not property-based. It closes the
chain: §17's at-most-one guarantee -> dispatch_link()'s audit-log-based
idempotency check -> the real incident at scripts/run_batch.py (a removed
"--split=scratch" fell through to the full fixture and, with --execute-links,
created 5 real Payment Links for real DISPUTE_REFUND / OPT_OUT cases) -> an
automated guard against a re-run doing it again.

Exercised at the batch-runner CLI seam (main(argv=...)), the same seam
test_run_batch.py's test_cli_seam_accepts_argv established. The Razorpay
client is faked; the audit log, run(), dispatch_link() and verify_chain()
are all real -- the idempotency logic under test is dispatch_link()'s, and
it must survive a fresh process (a new AuditLog object over the same file).
"""

from unittest.mock import MagicMock, patch

from scripts.run_batch import main
from src.audit_log import AuditLog

_CASE = {
    "case_id": "RCV-RPL-1",
    "split": "development",
    "bucket": "BENIGN",
    "customer_reply": "ok, will sort it out",  # no keywords -> rules arm routes RECOVER
    "expected_outcome": "RECOVERY_ELIGIBLE",
    "authoring_method": "human_written",
    "merchant_reference_id": "REBOUND-RCV-RPL-1",
    "razorpay_context": {
        "event_id": "evt_x", "payment_id": "pay_x", "order_id": "order_x",
        "payment_link_id": None, "merchant_invoice_reference": "INV-x",
    },
}


def _fake_client():
    client = MagicMock()
    client.create_payment_link.return_value = {"id": "plink_1", "short_url": "https://rzp.io/i/x"}
    return client


def _created_count(audit_path):
    return sum(1 for r in AuditLog(audit_path).records() if r["event_type"] == "PAYMENT_LINK_CREATED")


def test_replaying_same_case_against_same_audit_path_creates_at_most_one_link(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # keep evidence/ and scratch_* writes out of the repo
    audit_path = tmp_path / "replay.jsonl"
    fake_client = _fake_client()

    with patch("scripts.run_batch._load_cases", return_value=[dict(_CASE)]), \
         patch("scripts.run_batch.RazorpayClient", return_value=fake_client):

        rc1 = main(["--interpreter=rules", "--split=dev", "--execute-links",
                    "--audit-path", str(audit_path), "--first-run"])
        assert rc1 == 0
        assert _created_count(audit_path) == 1

        # Replay: same case, same pinned audit path, fresh process (no --first-run).
        rc2 = main(["--interpreter=rules", "--split=dev", "--execute-links",
                    "--audit-path", str(audit_path)])
        assert rc2 == 0

    assert _created_count(audit_path) == 1, "replay created a second PAYMENT_LINK_CREATED event"
    assert fake_client.create_payment_link.call_count == 1, "replay hit the Razorpay create endpoint again"


def test_first_run_guard_still_blocks_recreating_the_log(tmp_path, monkeypatch):
    """The invariant relies on the second run APPENDING to the pinned log, not
    recreating it. If the --first-run guard regresses (lets a second run pass
    --first-run over an existing file, truncating it), the replay protection is
    silently gone -- so pin that guard here too."""
    monkeypatch.chdir(tmp_path)
    audit_path = tmp_path / "replay.jsonl"

    with patch("scripts.run_batch._load_cases", return_value=[dict(_CASE)]), \
         patch("scripts.run_batch.RazorpayClient", return_value=_fake_client()):
        main(["--interpreter=rules", "--split=dev", "--execute-links",
              "--audit-path", str(audit_path), "--first-run"])

        import pytest
        with pytest.raises(SystemExit):
            main(["--interpreter=rules", "--split=dev", "--execute-links",
                  "--audit-path", str(audit_path), "--first-run"])
