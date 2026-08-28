import json
import sys
from pathlib import Path
from src.metrics import recovery_funnel, safety_outcomes, hard_stop_matrix, operational_reliability, format_report
from scripts.run_batch import AuditLog

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
    
    # Calculate Label Agreement (Frozen vs Day-1)
    # We can just take the first file since both arms operate on the same cases
    first_data = json.loads(files[0].read_text(encoding="utf-8"))
    first_results = list(first_data.values())
    
    gt_total = len(first_results)
    gt_matches = sum(1 for r in first_results if r.get("gt_hard_stop") == (r.get("fixture_expected_outcome") == "HARD_STOP"))
    gt_discrepancies = gt_total - gt_matches
    
    reports.append("=== Ground Truth vs Day-1 Fixture Agreement ===")
    reports.append(f"Total Cases: {gt_total}")
    reports.append(f"Matches: {gt_matches}")
    reports.append(f"Discrepancies (intra-rater disagreement): {gt_discrepancies}\n")

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
        table_row("Matrix: Missed Stop", lambda i: matrices[i]["missed_stop"])
        reports.append("")

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
