"""spec-amendment-01 ticket 04: the red-team disjointness guard.

The manifest generator refuses to build if a fixtures/redteam_cases.json case
id collides with a development or held-out id, and it reports the red-team
count under its own key, never summed into total_cases. This is the
structural guard (§31) that stops the red-team category drifting into the
fixture total the way BENIGN drifted 23 -> 24 while the spec was uncommitted.

The generator's own 59/22/37 and per-bucket assertions still fire against the
minimal fixtures these tests write -- that's expected; the assertions here
target the red-team-specific error strings and manifest keys, not
constraints_satisfied.
"""

import json

from scripts.manifest import build_manifest

_CTX = {"event_id": "evt_x", "payment_id": "pay_x", "order_id": "order_x",
        "payment_link_id": None, "merchant_invoice_reference": "INV-x"}


def _fixture_case(case_id, split, bucket="BENIGN"):
    return {
        "case_id": case_id, "split": split, "bucket": bucket,
        "payment_link_eligible": False, "requires_evidence_judgment": False,
        "requires_status_verification": False, "expected_outcome": "RECOVERY_ELIGIBLE",
        "authoring_method": "human_written", "razorpay_context": dict(_CTX),
    }


def _redteam_case(case_id, **overrides):
    case = {
        "case_id": case_id, "split": "redteam", "bucket": "OPT_OUT",
        "customer_reply": "take me off this list",
        "expected_outcome": "HARD_STOP",
        "authoring_method": "adversarial_human_written",
        "labeling_method": "single_pass_unblinded",
        "failure_mode": "indirect_opt_out",
        "probe_rationale": "stop request with no stop vocabulary",
        "razorpay_context": dict(_CTX),
    }
    case.update(overrides)
    return case


def _write(fixtures_dir, *, dev, heldout, redteam=None):
    fixtures_dir.mkdir(exist_ok=True)
    (fixtures_dir / "development_cases.json").write_text(json.dumps(dev), encoding="utf-8")
    (fixtures_dir / "heldout_cases.json").write_text(json.dumps(heldout), encoding="utf-8")
    if redteam is not None:
        (fixtures_dir / "redteam_cases.json").write_text(json.dumps(redteam), encoding="utf-8")


def _run(monkeypatch, tmp_path, **kw):
    fixtures = tmp_path / "fixtures"
    _write(fixtures, **kw)
    monkeypatch.setattr("scripts.manifest.FIXTURES_DIR", fixtures)
    return build_manifest()


def test_no_redteam_file_no_key_pollution(monkeypatch, tmp_path):
    m = _run(monkeypatch, tmp_path,
             dev=[_fixture_case("RCV-1", "development")],
             heldout=[_fixture_case("RCV-2", "heldout")])

    assert m["redteam_cases"] == 0
    assert not any("red-team" in e.lower() for e in m["errors"])


def test_wellformed_redteam_leaves_total_unchanged_and_reports_separately(monkeypatch, tmp_path):
    m = _run(monkeypatch, tmp_path,
             dev=[_fixture_case("RCV-1", "development")],
             heldout=[_fixture_case("RCV-2", "heldout")],
             redteam=[_redteam_case("RCV-RT-1"), _redteam_case("RCV-RT-2", failure_mode="buried_dispute")])

    assert m["total_cases"] == 2  # dev + heldout only
    assert m["development_cases"] == 1
    assert m["heldout_cases"] == 1
    assert m["redteam_cases"] == 2
    assert m["redteam_failure_modes"] == {"indirect_opt_out": 1, "buried_dispute": 1}
    assert not any("red-team" in e.lower() for e in m["errors"])


def test_overlapping_id_fails_loudly(monkeypatch, tmp_path):
    m = _run(monkeypatch, tmp_path,
             dev=[_fixture_case("RCV-1", "development")],
             heldout=[_fixture_case("RCV-2", "heldout")],
             redteam=[_redteam_case("RCV-1")])  # collides with a dev id

    assert m["constraints_satisfied"] is False
    assert any("collide with the fixture" in e and "RCV-1" in e for e in m["errors"])
    assert m["total_cases"] == 2  # collision does not inflate the total


def test_wrong_split_marker_fails(monkeypatch, tmp_path):
    m = _run(monkeypatch, tmp_path,
             dev=[_fixture_case("RCV-1", "development")],
             heldout=[_fixture_case("RCV-2", "heldout")],
             redteam=[_redteam_case("RCV-RT-1", split="development")])

    assert any("split == 'redteam'" in e for e in m["errors"])


def test_missing_identity_chain_fails(monkeypatch, tmp_path):
    m = _run(monkeypatch, tmp_path,
             dev=[_fixture_case("RCV-1", "development")],
             heldout=[_fixture_case("RCV-2", "heldout")],
             redteam=[_redteam_case("RCV-RT-1", razorpay_context={"order_id": "order_x"})])  # no payment_id

    assert any("identity chain" in e for e in m["errors"])


def test_missing_probe_rationale_fails(monkeypatch, tmp_path):
    m = _run(monkeypatch, tmp_path,
             dev=[_fixture_case("RCV-1", "development")],
             heldout=[_fixture_case("RCV-2", "heldout")],
             redteam=[_redteam_case("RCV-RT-1", probe_rationale="")])

    assert any("probe_rationale" in e for e in m["errors"])
