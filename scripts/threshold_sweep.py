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
from src.metrics import hard_stop_matrix
from src.policy_engine import route
from src.structured_prechecks import check
from src.typed_boundary import AgentOutput

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CACHE_PATH = Path(__file__).parent / "dev_interpretations.json"
REPORT_PATH = Path(__file__).parent / "threshold_sweep_report.md"

SWEEP_VALUES = [round(0.50 + 0.05 * i, 2) for i in range(10)]  # 0.50 .. 0.95

# §25's own required table -- exactly these four, not the full diagnostic
# sweep above. Recomputed from SWEEP_VALUES' results, not a second sweep.
REQUIRED_TABLE_THRESHOLDS = [0.50, 0.65, 0.75, 0.85]

# §25's two required disclosures, verbatim.
DISCLOSURE_COARSE = (
    "With ~5–7 dev hard-stop cases the sweep is coarse — a step "
    "function with a handful of points, not a smooth curve and not a knee."
)
DISCLOSURE_NOT_CALIBRATED = (
    "This is a model-reported confidence operating threshold, not a "
    "calibrated probability threshold. We do not claim these scores are "
    "calibrated probabilities; the sweep is a pragmatic method for "
    "choosing a review boundary on development data."
)

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
    review_count = 0  # denominator for §25's automation rate
    matrix_input = []  # feeds hard_stop_matrix() for §25's recall/precision

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

        if decision.route == "REVIEW":
            review_count += 1
        # bucket/gt_hard_stop mirror src/metrics.py's own dev-derivation
        # (no frozen labels exist for dev -- §25 never touches heldout).
        matrix_input.append({
            "bucket": case["bucket"],
            "gt_hard_stop": case["expected_outcome"] == "HARD_STOP",
            "route": decision.route,
        })

    total = sum(1 for c in dev if "error" not in cache.get(c["case_id"], {"error": True}))
    matrix = hard_stop_matrix(matrix_input)
    return {
        "threshold": threshold,
        "matched": matched,
        "total": total,
        "unsafe_misses": unsafe_misses,
        "over_caution": over_caution,
        # §25 columns -- automation rate is a whole-dev-set fraction (n=37,
        # legitimately a percentage); recall/precision are scoped to the
        # same hard-stop-judgment buckets §24 uses (small n, raw counts).
        "automation_rate": (total - review_count) / total if total else 0.0,
        "recall_num": matrix["true_stop"],
        "recall_den": matrix["true_stop"] + matrix["missed_stop"],
        "precision_num": matrix["true_stop"],
        "precision_den": matrix["true_stop"] + matrix["false_stop"],
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

    _write_report(results, best)
    # § mangles silently (not a crash, just garbled bytes) on this cp1252
    # console -- same hazard class as the rest of the repo, ASCII-only here.
    print(f"\nWrote {REPORT_PATH} (spec section 25 table + required disclosures)")


def _write_report(results: list[dict], best: dict) -> None:
    by_threshold = {r["threshold"]: r for r in results}
    lines = [
        "# §25 confidence threshold sweep",
        "",
        "All cells `[from run]` -- recomputed offline from `dev_interpretations.json`, zero API calls.",
        "",
        "| Threshold | Automation rate | Recall | Precision |",
        "|---|---|---|---|",
    ]
    for t in REQUIRED_TABLE_THRESHOLDS:
        r = by_threshold[t]
        recall = f"{r['recall_num']}/{r['recall_den']}" if r["recall_den"] else "n/a"
        precision = f"{r['precision_num']}/{r['precision_den']}" if r["precision_den"] else "n/a"
        lines.append(f"| {t:.2f} | {r['automation_rate']:.0%} | {recall} | {precision} |")
    lines += [
        "",
        f"**Selected: {best['threshold']}**, frozen before held-out evaluation "
        f"(`CONFIDENCE_THRESHOLD` in `src/policy_engine.py`).",
        "",
        f"> {DISCLOSURE_COARSE}",
        "",
        f"> {DISCLOSURE_NOT_CALIBRATED}",
    ]
    # ₹/em-dash-adjacent non-ASCII content -- same cp1252 hazard as
    # everywhere else in this repo. Write UTF-8, never console-print it.
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
