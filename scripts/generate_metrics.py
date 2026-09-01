import json
import sys
from pathlib import Path
from src.metrics import (
    recovery_funnel,
    safety_outcomes,
    hard_stop_matrix,
    operational_reliability,
    format_report,
    divergence_analysis,
    format_divergence,
)
from scripts.run_batch import AuditLog

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _load_replies():
    """case_id -> customer_reply, joined from the fixtures so customer text
    is never carried through the pipeline result records (§12)."""
    replies = {}
    for name in ("development_cases.json", "heldout_cases.json"):
        path = FIXTURES_DIR / name
        if path.exists():
            for case in json.loads(path.read_text(encoding="utf-8")):
                replies[case["case_id"]] = case.get("customer_reply") or ""
    return replies


def main():
    evidence_dir = Path("evidence")
    if not evidence_dir.exists():
        print("No evidence directory found.")
        return 1

    # Find the files (we expect llm_all and rules_all, or similar)
    # The user mentioned they might be called run_results_{interpreter}_{split}.json
    files = sorted(evidence_dir.glob("run_results_*.json"))
    if not files:
        print("No run_results_*.json found.")
        return 1

    audit_path = evidence_dir / "run_all.jsonl"
    audit_records = []
    if audit_path.exists():
        audit_records = AuditLog(audit_path).records()

    reports = []

    # §21's two DISTINCT numbers -- must never be collapsed into one line.
    # See fixtures/labeling_rubric.md and docs/adr/ for the full taxonomy.
    reports.append("=== §21 Ground-truth labeling (two separate findings) ===")

    # Finding #1: pass 1 vs pass 2 -- the actual intra-rater agreement metric.
    # Sourced from reconcile_labeling.py's own output, never recomputed here.
    frozen_path = FIXTURES_DIR / "heldout_ground_truth_frozen.json"
    if frozen_path.exists():
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
        reports.append(
            f"1. Intra-rater agreement (pass 1 vs pass 2, blind, 48h+ apart): "
            f"{frozen.get('intra_rater_agreement', '[not yet run]')}"
        )
    else:
        reports.append("1. Intra-rater agreement (pass 1 vs pass 2): [heldout_ground_truth_frozen.json not found]")

    # Finding #2: frozen ground truth vs the Day-1 fixture's own expected_outcome
    # -- did the original authoring instinct hold up under blind relabeling?
    # A DIFFERENT question from #1. Scoped to has_frozen_ground_truth cases
    # only (held-out) -- dev cases have no frozen label and would otherwise
    # trivially "agree" with themselves, padding the number with wins never
    # earned (same failure shape §24 already forbids for excluded buckets).
    first_data = json.loads(files[0].read_text(encoding="utf-8"))
    first_results = [r for r in first_data.values() if r.get("has_frozen_ground_truth")]

    gt_total = len(first_results)
    if gt_total:
        gt_matches = sum(
            1 for r in first_results
            if r["gt_hard_stop"] == (r.get("fixture_expected_outcome") == "HARD_STOP")
        )
        gt_discrepancies = gt_total - gt_matches
        reports.append(
            f"2. Frozen ground truth vs Day-1 fixture authoring (held-out only, n={gt_total}): "
            f"{gt_matches}/{gt_total} agree, {gt_discrepancies} discrepancy/ies"
        )
    else:
        reports.append("2. Frozen ground truth vs Day-1 fixture authoring: [no frozen held-out labels yet]")
    reports.append("")

    # §23 Two-Arm Table
    if len(files) == 2:
        reports.append("=== §23 Rules vs LLM Comparison ===")
        reports.append("| Metric | " + " | ".join(f.stem.replace("run_results_", "") for f in files) + " |")
        reports.append("|--------|" + "|".join("---" for _ in files) + "|")
        
        f_results = []
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            f_results.append(list(data.values()))
            
        funnels = [recovery_funnel(r) for r in f_results]
        safeties = [safety_outcomes(r) for r in f_results]
        matrices = [hard_stop_matrix(r) for r in f_results]
        
        def table_row(name, get_val):
            reports.append(f"| {name} | " + " | ".join(str(get_val(i)) for i in range(len(files))) + " |")
            
        table_row("Evaluated", lambda i: funnels[i]["evaluated"])
        table_row("Eligible", lambda i: funnels[i]["eligible"])
        table_row("Link Attempts", lambda i: funnels[i]["link_attempts"])
        table_row("Links Created", lambda i: funnels[i]["created"])
        table_row("Links Completed", lambda i: funnels[i]["completed"])
        table_row("Completed Value (₹)", lambda i: f"₹{funnels[i]['completed_value_rupees']:.2f}")
        table_row("Safety: STOPPED", lambda i: safeties[i]["STOPPED"])
        table_row("Safety: HUMAN_REVIEW", lambda i: safeties[i]["HUMAN_REVIEW"])
        table_row("Matrix: True Stop", lambda i: matrices[i]["true_stop"])
        table_row("Matrix: False Stop", lambda i: matrices[i]["false_stop"])
        # Split, not blanket "missed_stop" -- ticket 10 deliberately separated
        # "caught by a different safe rung" from "genuinely fell through"
        # (test_hard_stop_matrix_distinguishes_safe_from_unsafe_misses); a
        # single collapsed number here would undo that.
        table_row("Matrix: Missed Stop (still safe)", lambda i: matrices[i]["missed_stop_but_still_safe"])
        table_row("Matrix: Missed Stop (unsafe)", lambda i: matrices[i]["missed_stop_unsafe"])
        reports.append("")

    # §23 Divergence analysis -- per-case complement to the aggregate table.
    # A tie in the counts above is still a real finding once you can see
    # which cases the two interpreters disagreed on and which arm was safer.
    if len(files) == 2:
        arms_map = {
            f.stem.replace("run_results_", ""): json.loads(f.read_text(encoding="utf-8"))
            for f in files
        }
        divergence = divergence_analysis(arms_map, _load_replies())
    else:
        divergence = {"insufficient_arms": len(files), "arms_compared": [], "divergent": []}
    reports.append(format_divergence(divergence))
    reports.append("")
    if divergence.get("divergent"):
        (evidence_dir / "divergence.json").write_text(
            json.dumps(divergence["divergent"], indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # §24 Full Reports
    for f in files:
        arm_name = f.stem.replace("run_results_", "")
        data = json.loads(f.read_text(encoding="utf-8"))
        results = list(data.values())
        
        funnel = recovery_funnel(results)
        safety = safety_outcomes(results)
        matrix = hard_stop_matrix(results)
        reliability = operational_reliability(audit_records, results)
        
        rep = format_report(funnel, safety, matrix, reliability, split_label=arm_name)
        reports.append(f"## Full Report: {arm_name}\n")
        reports.append(rep)
        reports.append("\n" + "="*40 + "\n")

    out_file = evidence_dir / "metrics_report.md"
    out_file.write_text("\n".join(reports), encoding="utf-8")
    print(f"Generated {out_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
