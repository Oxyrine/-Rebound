"""Ticket 07: run the real LLM interpreter against the 37 development
cases and compare against ground truth. Dev only -- never touches
heldout_cases.json (§21's frozen firewall). Used to iterate the prompt;
not itself a frozen artifact.

Comparison is against a fixture-outcome -> route mapping, not an official
metric (that's ticket 10's job, after both interpreter arms exist):
    RECOVERY_ELIGIBLE   -> RECOVER (or LINK_QUOTA_GUARD; quota isn't live here)
    HARD_STOP           -> STOP
    HUMAN_REVIEW        -> REVIEW
    ALREADY_PAID_CLOSED -> VERIFY   (payment_verifier.py resolves the rest)
    VERIFY_PAYMENT_STATUS -> VERIFY
    PAUSE_UNTIL_DATE    -> PAUSE

Run: python3 -m scripts.run_dev_interpreter
"""

import json
import sys
import time
from pathlib import Path

from src.instruction_detector import is_suspicious
from src.llm_interpreter import interpret
from src.policy_engine import route
from src.structured_prechecks import check

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

OUTCOME_TO_ROUTE = {
    "RECOVERY_ELIGIBLE": "RECOVER",
    "HARD_STOP": "STOP",
    "HUMAN_REVIEW": "REVIEW",
    "ALREADY_PAID_CLOSED": "VERIFY",
    "VERIFY_PAYMENT_STATUS": "VERIFY",
    "PAUSE_UNTIL_DATE": "PAUSE",
}


def _event_for(case: dict) -> dict:
    return {
        "case_id": case["case_id"],
        "razorpay_context": case["razorpay_context"],
        "dispute_open": False,
    }


def main():
    dev = json.loads((FIXTURES_DIR / "development_cases.json").read_text(encoding="utf-8"))

    seen_case_ids = set()
    mismatches = []
    errors = []
    matched = 0

    for case in dev:
        case_id = case["case_id"]
        event = _event_for(case)
        precheck = check(event, seen_case_ids)
        seen_case_ids.add(case_id)

        # interpret() already retries transient 503/429s internally
        # (llm_interpreter._generate) -- a failure here means that
        # retry budget was exhausted, a real problem worth reporting.
        try:
            ao = interpret(case_id, case.get("customer_reply"))
        except Exception as exc:  # noqa: BLE001 -- reported, not swallowed
            errors.append((case_id, repr(exc)))
            continue
        time.sleep(1)  # stay comfortably under the 15 req/min free-tier cap

        pre_screen_matched = is_suspicious(case.get("customer_reply") or "")
        decision = route(ao, precheck, pre_screen_matched=pre_screen_matched)

        # requires_status_verification cases (ALREADY_PAID_TRUE/FALSE) are
        # correctly VERIFY at *this* pipeline stage regardless of their
        # eventual expected_outcome -- ALREADY_PAID_CLOSED and the
        # HUMAN_REVIEW that ALREADY_PAID_FALSE resolves to both only exist
        # after payment_verifier.py (ticket 05) runs, which this script
        # doesn't call. Mapping expected_outcome->route directly for those
        # cases would score a correct VERIFY as a miss.
        if case.get("requires_status_verification"):
            expected_route = "VERIFY"
        else:
            expected_route = OUTCOME_TO_ROUTE.get(case["expected_outcome"], "?")
        if decision.route == expected_route:
            matched += 1
        else:
            mismatches.append(
                {
                    "case_id": case_id,
                    "bucket": case["bucket"],
                    "expected_outcome": case["expected_outcome"],
                    "expected_route": expected_route,
                    "got_route": decision.route,
                    "matched_rung": decision.matched_rung,
                    "stop_signals": ao.stop_signals,
                    "confidence": ao.confidence,
                }
            )

    total = len(dev)
    print(f"{matched}/{total} matched expected route")
    if errors:
        print(f"{len(errors)} case(s) failed to get an interpretation:")
        for case_id, err in errors:
            print(f"  {case_id}: {err}")
    if mismatches:
        print(f"\n{len(mismatches)} mismatch(es):")
        for m in mismatches:
            print(
                f"  {m['case_id']} [{m['bucket']}] expected {m['expected_route']} "
                f"({m['expected_outcome']}), got {m['got_route']}/{m['matched_rung']} "
                f"(signals={m['stop_signals']}, confidence={m['confidence']})"
            )

    return 0 if not mismatches and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
