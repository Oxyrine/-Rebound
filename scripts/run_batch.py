"""Full batch runner -- ticket 10, §23/§24. One path for both interpreter
arms: fixture -> interpreter -> policy engine -> execution -> audit ->
metrics. Only the interpretation layer changes between
--interpreter=rules and --interpreter=llm.

--split=dev is the default and the only one usable right now: heldout's
ground truth isn't frozen yet (§21 -- ticket 09, gated by the user's two
blind labeling passes, not by anything in this script). --split=heldout
or --split=all refuse to run unless fixtures/heldout_ground_truth_frozen.json
exists with "frozen": true.

--execute-links actually POSTs to Razorpay to create payment links for
RECOVER decisions -- real, if harmless, Test Mode side effects. Off by
default. This repo's one "clean" Day 9 evidence run is the deliberate
exception; every dev-validation invocation should leave it off. VERIFY-
route payment-status checks always execute for real regardless -- they're
read-only GETs, no side effects, no quota cost.

Run: python3 -m scripts.run_batch --interpreter=llm [--split=dev] [--execute-links] [--limit N]
"""

import argparse
import json
import sys
from pathlib import Path

from src.audit_log import AuditLog, verify_chain
from src.instruction_detector import is_suspicious
from src.link_dispatch import dispatch_link, quota_available, reconcile_created_links
from src.metrics import format_report, hard_stop_matrix, operational_reliability, recovery_funnel, safety_outcomes
from src.payment_verifier import verify_payment_claim
from src.policy_engine import CONFIDENCE_THRESHOLD, route
from src.razorpay_client import RazorpayClient
from src.structured_prechecks import check

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Fixture cases don't carry a real invoice amount -- placeholder Test Mode
# value, same convention as tickets 04/06's live smoke tests. Revisit if
# the Day 9 evidence run wants a different, per-case-realistic amount.
NOMINAL_TEST_AMOUNT_PAISE = 100

_ROUTE_TO_OUTCOME = {
    "STOP": "HARD_STOP",
    "PAUSE": "PAUSE_UNTIL_DATE",
    "REVIEW": "HUMAN_REVIEW",
    "RECOVER": "RECOVERY_ELIGIBLE",
    "LINK_QUOTA_GUARD": "RECOVERY_ELIGIBLE",
}


def _frozen_ground_truth(split: str) -> dict:
    if split == "dev":
        return {}
    frozen_path = FIXTURES_DIR / "heldout_ground_truth_frozen.json"
    if not frozen_path.exists() or not json.loads(frozen_path.read_text(encoding="utf-8")).get("frozen"):
        raise SystemExit(
            f"--split={split} needs frozen held-out ground truth "
            f"(fixtures/heldout_ground_truth_frozen.json with \"frozen\": true) -- "
            f"see scripts/reconcile_labeling.py. Not ready yet (ticket 09)."
        )
    return json.loads(frozen_path.read_text(encoding="utf-8")).get("ground_truth", {})


def _load_cases(split: str) -> list[dict]:
    dev = json.loads((FIXTURES_DIR / "development_cases.json").read_text(encoding="utf-8"))
    if split == "dev":
        return dev
    heldout = json.loads((FIXTURES_DIR / "heldout_cases.json").read_text(encoding="utf-8"))
    return heldout if split == "heldout" else dev + heldout


def _get_interpreter(name: str):
    if name == "rules":
        from src.rules_interpreter import interpret
        return interpret
    if name == "llm":
        from src.llm_interpreter import interpret
        return interpret
    raise SystemExit(f"unknown --interpreter={name!r}, use 'rules' or 'llm'")


def run(cases: list[dict], interpret, log: AuditLog, client: RazorpayClient, gt_map: dict, *, execute_links: bool, is_llm: bool) -> list[dict]:
    results = []
    seen_case_ids = set()

    for case in cases:
        case_id = case["case_id"]
        event = {"case_id": case_id, "razorpay_context": case["razorpay_context"], "dispute_open": False}
        precheck = check(event, seen_case_ids)
        if is_llm:
            import time
            time.sleep(1)
        seen_case_ids.add(case_id)

        result = {
            "case_id": case_id,
            "bucket": case["bucket"],
            "fixture_expected_outcome": case.get("expected_outcome"),
            "gt_hard_stop": gt_map.get(case_id, case.get("expected_outcome") == "HARD_STOP"),
            "stop_signals": [],
            "link_status": None,
            "link_amount_paise": None,
            "link_completed": False,
            "resolved_outcome": None,
        }

        if not precheck.ok:
            result["route"] = "STOP"
            result["matched_rung"] = "MALFORMED_OR_DUPLICATE_EVENT"
            log.append(case_id, "POLICY_DECISION", {"route": "STOP", "matched_rung": result["matched_rung"]})
            results.append(result)
            continue

        try:
            ao = interpret(case_id, case.get("customer_reply"))
        except Exception as exc:  # noqa: BLE001 -- Chaos condition 2 territory; recorded, not fatal to the batch
            result["route"] = "STOP"
            result["matched_rung"] = "INTERPRETER_OUTPUT_REJECTED"
            log.append(case_id, "INTERPRETER_OUTPUT_REJECTED", {"error": repr(exc)})
            results.append(result)
            continue

        result["stop_signals"] = ao.stop_signals
        pre_screen_matched = is_suspicious(case.get("customer_reply") or "")
        decision = route(
            ao, precheck, pre_screen_matched=pre_screen_matched,
            quota_available=quota_available(log), confidence_threshold=CONFIDENCE_THRESHOLD,
        )
        result["route"] = decision.route
        result["matched_rung"] = decision.matched_rung
        log.append(case_id, "POLICY_DECISION", {"route": decision.route, "matched_rung": decision.matched_rung})

        if decision.route == "VERIFY":
            ctx = case["razorpay_context"]
            verification = verify_payment_claim(client, order_id=ctx["order_id"], claimed_payment_id=ctx.get("payment_id"))
            result["resolved_outcome"] = verification.outcome
            log.append(case_id, "PAYMENT_CLAIM_VERIFIED", {"outcome": verification.outcome, "reason": verification.reason})
        elif decision.route == "RECOVER" and execute_links:
            dispatch = dispatch_link(
                log, client, case_id=case_id, amount_paise=NOMINAL_TEST_AMOUNT_PAISE,
                reference_id=case["merchant_reference_id"], description=f"REBOUND {case_id}",
            )
            result["link_status"] = dispatch.status
            result["link_amount_paise"] = NOMINAL_TEST_AMOUNT_PAISE if dispatch.status == "CREATED" else None
            result["resolved_outcome"] = _ROUTE_TO_OUTCOME[decision.route]
        else:
            result["resolved_outcome"] = _ROUTE_TO_OUTCOME.get(decision.route)

        results.append(result)

    return results


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--interpreter", required=True, choices=["rules", "llm"])
    parser.add_argument("--split", default="dev", choices=["dev", "heldout", "all"])
    parser.add_argument("--execute-links", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--audit-path", default=None, help="defaults to a scratch .jsonl, gitignored")
    parser.add_argument("--first-run", action="store_true")
    args = parser.parse_args(argv)

    if args.execute_links and not args.audit_path:
        parser.error("--audit-path is required when --execute-links is used")

    audit_path = Path(args.audit_path) if args.audit_path else Path(f"scratch_batch_{args.interpreter}_{args.split}.jsonl")

    if args.audit_path:
        if not audit_path.exists() and not args.first_run:
            parser.error(f"Audit log '{audit_path}' does not exist. Pass --first-run to explicitly create it.")
        if audit_path.exists() and args.first_run:
            parser.error(f"--first-run was passed, but audit log '{audit_path}' already exists. Omit the flag to append, or move/rename the file.")

    gt_map = _frozen_ground_truth(args.split)
    cases = _load_cases(args.split)
    if args.limit:
        cases = cases[: args.limit]
    interpret = _get_interpreter(args.interpreter)
    log = AuditLog(audit_path)
    client = RazorpayClient()  # only used for VERIFY (always) and dispatch/reconcile (if --execute-links)

    results = run(cases, interpret, log, client, gt_map, execute_links=args.execute_links, is_llm=(args.interpreter == "llm"))

    evidence_dir = Path("evidence")
    evidence_dir.mkdir(exist_ok=True)
    run_all_results = {r["case_id"]: r for r in results}
    (evidence_dir / "run_all_results.json").write_text(json.dumps(run_all_results, indent=2), encoding="utf-8")


    ok, problems = verify_chain(audit_path)
    if not ok:
        print(f"AUDIT CHAIN VERIFICATION FAILED: {problems}", file=sys.stderr)
        return 1

    funnel = recovery_funnel(results)
    safety = safety_outcomes(results)
    matrix = hard_stop_matrix(results)
    reliability = operational_reliability(log.records(), results)

    label = f"{args.split} ({args.interpreter} interpreter, {'links executed' if args.execute_links else 'links NOT executed -- dry run'})"
    report = format_report(funnel, safety, matrix, reliability, split_label=label)

    # ₹ crashes a bare print() on this machine's cp1252 console (same
    # hazard documented in README.md's setup section) -- write the report
    # to a UTF-8 file and keep the console output ASCII-only.
    report_path = Path(f"scratch_batch_report_{args.interpreter}_{args.split}.txt")
    report_path.write_text(report, encoding="utf-8")

    print(f"Wrote {report_path} ({funnel['evaluated']} cases, {len(log.records())} audit records, chain verified clean)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
