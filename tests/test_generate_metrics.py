"""Regression tests for generate_metrics.py's §21 ground-truth reporting.

Two bugs caught in review: (1) the frozen-vs-fixture comparison ran over
all 59 cases including 37 dev cases that trivially "agree" with themselves
(no frozen label exists for them), padding the number with wins never
earned -- fixed by scoping to has_frozen_ground_truth cases only. (2) the
comparison was mislabeled "intra-rater disagreement", which is a DIFFERENT
number (pass 1 vs pass 2, sourced from heldout_ground_truth_frozen.json's
own intra_rater_agreement field) -- conflating the two is exactly what
§21's taxonomy forbids.
"""

import json

from scripts.generate_metrics import main


def _write_results(path, cases):
    path.write_text(json.dumps({c["case_id"]: c for c in cases}), encoding="utf-8")


def _result(case_id, *, gt_hard_stop, fixture_expected_outcome, has_frozen_ground_truth, route="RECOVER"):
    return {
        "case_id": case_id, "bucket": "BENIGN", "route": route, "matched_rung": "X",
        "resolved_outcome": None, "link_status": None, "link_amount_paise": None, "link_completed": False,
        "gt_hard_stop": gt_hard_stop, "stop_signals": [],
        "fixture_expected_outcome": fixture_expected_outcome,
        "has_frozen_ground_truth": has_frozen_ground_truth,
    }


def test_frozen_vs_fixture_comparison_excludes_dev_cases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    # Isolate from the real repo's fixtures/ (whose frozen file may or may
    # not exist depending on labeling progress) -- this test only cares
    # about finding #2's scoping, not finding #1.
    monkeypatch.setattr("scripts.generate_metrics.FIXTURES_DIR", tmp_path / "fixtures")

    # 2 dev cases (no frozen label -- must be excluded) + 1 held-out case
    # with a real frozen label that DISAGREES with the fixture.
    cases = [
        _result("RCV-DEV-1", gt_hard_stop=True, fixture_expected_outcome="HARD_STOP", has_frozen_ground_truth=False),
        _result("RCV-DEV-2", gt_hard_stop=False, fixture_expected_outcome="RECOVERY_ELIGIBLE", has_frozen_ground_truth=False),
        _result("RCV-HO-1", gt_hard_stop=False, fixture_expected_outcome="HARD_STOP", has_frozen_ground_truth=True),
    ]
    _write_results(evidence / "run_results_llm_all.json", cases)

    assert main() == 0
    report = (evidence / "metrics_report.md").read_text(encoding="utf-8")

    # n=1, not n=3 -- the two dev cases must not pad the denominator.
    assert "held-out only, n=1" in report
    assert "0/1 agree, 1 discrepancy" in report


def test_taxonomy_numbers_are_labeled_distinctly_not_conflated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "heldout_ground_truth_frozen.json").write_text(
        json.dumps({"intra_rater_agreement": "20/22", "frozen": True}), encoding="utf-8"
    )
    # FIXTURES_DIR is derived from __file__ (repo-anchored), not cwd -- chdir
    # alone won't redirect it to the fake fixtures dir above.
    monkeypatch.setattr("scripts.generate_metrics.FIXTURES_DIR", fixtures)
    _write_results(evidence / "run_results_llm_all.json", [
        _result("RCV-HO-1", gt_hard_stop=True, fixture_expected_outcome="HARD_STOP", has_frozen_ground_truth=True),
    ])

    assert main() == 0
    report = (evidence / "metrics_report.md").read_text(encoding="utf-8")

    # Finding #1 (pass1 vs pass2) and finding #2 (frozen vs fixture) must
    # both appear, each under its own label -- never a single collapsed
    # "intra-rater disagreement" line describing finding #2's number.
    assert "1. Intra-rater agreement (pass 1 vs pass 2" in report
    assert "20/22" in report
    assert "2. Frozen ground truth vs Day-1 fixture authoring" in report
    assert "intra-rater disagreement" not in report.split("2. Frozen ground truth")[1].split("\n")[0]


def test_divergence_section_appears_with_two_arms(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.setattr("scripts.generate_metrics.FIXTURES_DIR", tmp_path / "fixtures")

    rules = [_result("RCV-1", gt_hard_stop=True, fixture_expected_outcome="HARD_STOP",
                     has_frozen_ground_truth=False, route="RECOVER")]
    llm = [_result("RCV-1", gt_hard_stop=True, fixture_expected_outcome="HARD_STOP",
                   has_frozen_ground_truth=False, route="STOP")]
    _write_results(evidence / "run_results_rules_dev.json", rules)
    _write_results(evidence / "run_results_llm_dev.json", llm)

    assert main() == 0
    report = (evidence / "metrics_report.md").read_text(encoding="utf-8")

    assert "§23 Divergence analysis (llm_dev vs rules_dev)" in report
    assert "1 of 1 shared cases diverged" in report
    assert (evidence / "divergence.json").exists()


def test_divergence_not_computed_with_single_arm(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.setattr("scripts.generate_metrics.FIXTURES_DIR", tmp_path / "fixtures")

    _write_results(evidence / "run_results_llm_dev.json", [
        _result("RCV-1", gt_hard_stop=False, fixture_expected_outcome="RECOVERY_ELIGIBLE",
                has_frozen_ground_truth=False),
    ])

    assert main() == 0
    report = (evidence / "metrics_report.md").read_text(encoding="utf-8")

    assert "§23 Divergence analysis" in report
    assert "Not computed: 1 arm result file(s) found" in report
    assert not (evidence / "divergence.json").exists()
