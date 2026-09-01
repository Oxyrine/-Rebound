"""Reconciliation's unanchored-payment-claim caveat.

labeling_rubric.md's own Payment-claim section says a labeler cannot verify
payment status by reading text, and compensates by naming worked anchor
cases whose ground truth it spells out. A case in ALREADY_PAID_TRUE/FALSE
that the rubric names nowhere has no textual calibration -- found for real
in the held-out fixture at RCV-015 during pass-2 review. Any pass1==pass2
agreement on such a case is pattern consistency, not a verified judgment,
and reconcile_labeling.py must say so rather than freezing it silently
indistinguishable from an anchored case.
"""

import json

from scripts.reconcile_labeling import unanchored_payment_claim_cases

_CTX = {"event_id": "e", "payment_id": "p", "order_id": "o",
        "payment_link_id": None, "merchant_invoice_reference": "INV-x"}


def _heldout_case(case_id, bucket):
    return {"case_id": case_id, "split": "heldout", "bucket": bucket,
            "customer_reply": "x", "expected_outcome": "X",
            "authoring_method": "human_written", "razorpay_context": dict(_CTX)}


def _write(tmp_path, monkeypatch, *, rubric_text, heldout_cases):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "labeling_rubric.md").write_text(rubric_text, encoding="utf-8")
    (fixtures / "heldout_cases.json").write_text(json.dumps(heldout_cases), encoding="utf-8")
    monkeypatch.setattr("scripts.reconcile_labeling.FIXTURES_DIR", fixtures)


def test_named_already_paid_case_is_not_flagged(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch,
           rubric_text="Payment claim. True: RCV-014. False: RCV-018.",
           heldout_cases=[_heldout_case("RCV-014", "ALREADY_PAID_TRUE")])

    assert unanchored_payment_claim_cases(["RCV-014"]) == []


def test_unnamed_already_paid_case_is_flagged(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch,
           rubric_text="Payment claim. True: RCV-014. False: RCV-018.",
           heldout_cases=[_heldout_case("RCV-015", "ALREADY_PAID_TRUE")])

    assert unanchored_payment_claim_cases(["RCV-015"]) == ["RCV-015"]


def test_non_payment_claim_buckets_never_flagged_even_if_unnamed(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch,
           rubric_text="Payment claim. True: RCV-014.",
           heldout_cases=[_heldout_case("RCV-020", "DISPUTE_REFUND")])

    # DISPUTE_REFUND is not a bucket the rubric disclaims text-resolvability
    # for -- only ALREADY_PAID_TRUE/FALSE are, so an unnamed dispute case is
    # not a caveat here even though it isn't in the rubric text either.
    assert unanchored_payment_claim_cases(["RCV-020"]) == []


def test_missing_rubric_or_heldout_file_is_not_an_error(tmp_path, monkeypatch):
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    monkeypatch.setattr("scripts.reconcile_labeling.FIXTURES_DIR", fixtures)

    assert unanchored_payment_claim_cases(["RCV-015"]) == []


def test_real_fixture_flags_exactly_rcv_015():
    """Integration check against the actual repo fixtures -- pins the real
    finding, not just the synthetic mechanism."""
    import pathlib
    fixtures_dir = pathlib.Path(__file__).parent.parent / "fixtures"
    heldout = json.loads((fixtures_dir / "heldout_cases.json").read_text(encoding="utf-8"))
    ids = [c["case_id"] for c in heldout]

    assert unanchored_payment_claim_cases(ids) == ["RCV-015"]
