"""Ticket 08: sweep policy_engine's confidence_threshold on the development
set only (§25/§21's frozen firewall -- heldout_cases.json is never read
here) and freeze CONFIDENCE_THRESHOLD before heldout is touched.

The LLM interpreter is called once per case and cached to
dev_interpretations.json -- routing is a pure function of the cached
AgentOutput, precheck, and pre_screen_matched, so sweeping ten threshold
values doesn't cost ten times the API calls. Re-run with --refresh to
regenerate the cache (e.g. after a prompt change).

Only threshold-sensitive routing changes across the sweep: every other
rung (STOP/VERIFY/EVIDENCE_REFS_MISSING/pre-screen) resolves before the
confidence check ever runs, so those cases are identical at every
threshold -- the confidence check only ever trades RECOVER/PAUSE for
REVIEW/LOW_CONFIDENCE, never the reverse.

Run: python3 -m scripts.threshold_sweep [--refresh]
"""

import json
import sys
import time
from pathlib import Path

from src.instruction_detector import is_suspicious
from src.llm_interpreter import interpret
from src.policy_engine import route
from src.structured_prechecks import check
from src.typed_boundary import AgentOutput

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CACHE_PATH = Path(__file__).parent / "dev_interpretations.json"

SWEEP_VALUES = [round(0.50 + 0.05 * i, 2) for i in range(10)]  # 0.50 .. 0.95

OUTCOME_TO_ROUTE = {
    "RECOVERY_ELIGIBLE": "RECOVER",
    "HARD_STOP": "STOP",
    "HUMAN_REVIEW": "REVIEW",
    "ALREADY_PAID_CLOSED": "VERIFY",
    "VERIFY_PAYMENT_STATUS": "VERIFY",
    "PAUSE_UNTIL_DATE": "PAUSE",
}


def _expected_route(case: dict) -> str:
    if case.get("requires_status_verification"):
        return "VERIFY"
    return OUTCOME_TO_ROUTE.get(case["expected_outcome"], "?")


def _build_cache(dev: list[dict]) -> dict:
    cache = {}
    for case in dev:
        case_id = case["case_id"]
        try:
            ao = interpret(case_id, case.get("customer_reply"))
        except Exception as exc:  # noqa: BLE001 -- recorded, not fatal to the sweep
            cache[case_id] = {"error": repr(exc)}
            continue
        cache[case_id] = {
            "customer_state": ao.customer_state,
            "stop_signals": ao.stop_signals,
            "confidence": ao.confidence,
            "evidence_refs": ao.evidence_refs,
            "requires_human_review": ao.requires_human_review,
            "suspected_injection": ao.suspected_injection,
        }
        time.sleep(1)  # stay under the 15 req/min free-tier cap
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    return cache


def _sweep_at(threshold: float, dev: list[dict], cache: dict) -> dict:
    seen_case_ids = set()
    matched = 0
    unsafe_misses = []  # needed caution, got RECOVER anyway -- the real danger
    over_caution = 0  # would have safely recovered, held back only by threshold

    for case in dev:
        case_id = case["case_id"]
        fields = cache.get(case_id, {})
        if "error" in fields:
            continue

        event = {"case_id": case_id, "razorpay_context": case["razorpay_context"], "dispute_open": False}
        precheck = check(event, seen_case_ids)
        seen_case_ids.add(case_id)

        ao = AgentOutput(case_id=case_id, **fields)
        pre_screen_matched = is_suspicious(case.get("customer_reply") or "")
        decision = route(ao, precheck, pre_screen_matched=pre_screen_matched, confidence_threshold=threshold)

        expected = _expected_route(case)
        if decision.route == expected:
            matched += 1
        elif expected != "RECOVER" and decision.route == "RECOVER":
            unsafe_misses.append(case_id)
        elif expected == "RECOVER" and decision.matched_rung == "LOW_CONFIDENCE":
            over_caution += 1

    total = sum(1 for c in dev if "error" not in cache.get(c["case_id"], {"error": True}))
    return {
        "threshold": threshold,
        "matched": matched,
        "total": total,
        "unsafe_misses": unsafe_misses,
        "over_caution": over_caution,
    }


def main():
    dev = json.loads((FIXTURES_DIR / "development_cases.json").read_text(encoding="utf-8"))

    refresh = "--refresh" in sys.argv
    if refresh or not CACHE_PATH.exists():
        cache = _build_cache(dev)
    else:
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    print(f"{'threshold':>9} {'accuracy':>10} {'unsafe_misses':>14} {'over_caution':>13}")
    results = []
    for t in SWEEP_VALUES:
        r = _sweep_at(t, dev, cache)
        results.append(r)
        print(f"{r['threshold']:>9} {r['matched']}/{r['total']:>7} {len(r['unsafe_misses']):>14} {r['over_caution']:>13}")

    # Freeze policy: minimize unsafe_misses first (never silently recover a
    # case that needed caution), then maximize accuracy, then prefer the
    # highest threshold among ties (more conservative -- more caution, not
    # less, when multiple thresholds score identically).
    best = min(results, key=lambda r: (len(r["unsafe_misses"]), -r["matched"], -r["threshold"]))
    print(f"\nChosen threshold: {best['threshold']} "
          f"(accuracy {best['matched']}/{best['total']}, "
          f"unsafe_misses={best['unsafe_misses']}, over_caution={best['over_caution']})")


if __name__ == "__main__":
    main()
