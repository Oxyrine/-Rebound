"""Watch REBOUND decide one case, step by step -- the readable version of
scripts/run_batch.py for demos and the video. Dry run: never creates a
payment link, never calls Razorpay (VERIFY cases show the route only).

    python -m scripts.demo                 # 3 illustrative cases, rules arm
    python -m scripts.demo RCV-023         # one case by id
    python -m scripts.demo RCV-023 --llm   # LLM arm (needs GEMINI_API_KEY)

Mirrors run()'s per-case body; the decision path is identical.
"""

import argparse
import json
import sys
from pathlib import Path

from src.instruction_detector import is_suspicious
from src.policy_engine import CONFIDENCE_THRESHOLD, route
from src.structured_prechecks import check

sys.stdout.reconfigure(encoding="utf-8")

CASES = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "development_cases.json").read_text(encoding="utf-8")
)
BY_ID = {c["case_id"]: c for c in CASES}
DEFAULT_TRIO = ["RCV-016", "RCV-023", "RCV-011"]  # already-paid claim / multi-signal / opt-out
EVIDENCE_LOG = Path(__file__).parent.parent / "evidence" / "run_all.jsonl"


def evidence_note(case_id):
    """What this case actually did in the frozen evidence run -- the created
    link, or how the VERIFY status-check resolved -- so the demo shows the
    real outcome, not just the routing decision."""
    if not EVIDENCE_LOG.exists():
        return None
    created = status = verified = None
    for line in EVIDENCE_LOG.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("case_id") != case_id:
            continue
        et = e["event_type"]
        if et == "PAYMENT_LINK_CREATED":
            created = e["payload"]
        elif et == "PAYMENT_LINK_RECONCILED":
            status = e["payload"].get("status")
        elif et == "PAYMENT_CLAIM_VERIFIED":
            verified = e["payload"]
    if created:
        tail = f", reconciled: {status}" if status else ""
        return f'created a real Test Mode link: {created["short_url"]}  ({created["payment_link_id"]}{tail})'
    if verified:
        return f'Razorpay status-check resolved to {verified["outcome"]} ({verified.get("reason", "")})'
    return None

ROUTE_MEANING = {
    "STOP": "do nothing, close the case -- contacting this customer is wrong",
    "PAUSE": "hold until the promised date, then reassess",
    "REVIEW": "hand to a human -- too ambiguous or too risky to automate",
    "VERIFY": "check the real payment status at Razorpay before deciding",
    "RECOVER": "safe to send a Test Mode Payment Link",
    "LINK_QUOTA_GUARD": "would recover, but the local link quota is used up",
}


def show(case, interpret):
    cid = case["case_id"]
    print(f"\n{'='*66}\n{cid}   bucket={case['bucket']}")
    print(f'  customer reply: "{(case.get("customer_reply") or "").strip()}"')

    event = {"case_id": cid, "razorpay_context": case["razorpay_context"], "dispute_open": False}
    precheck = check(event, set())
    print(f"\n  1. structured pre-checks (no LLM) : {'ok' if precheck.ok else 'FAIL -> ' + precheck.reason}")
    if not precheck.ok:
        print(f"     -> STOP ({ROUTE_MEANING['STOP']})")
        return "STOP"

    ao = interpret(cid, case.get("customer_reply"))
    print(f"  2. interpreter ({interpret.__module__.split('.')[-1]})")
    print(f"       stop_signals : {ao.stop_signals or '[]'}")
    print(f"       confidence   : {ao.confidence}")

    pre_screen = is_suspicious(case.get("customer_reply") or "")
    print(f"  3. suspicious-instruction pre-screen : {'matched' if pre_screen else 'clear'}")

    decision = route(
        ao, precheck, pre_screen_matched=pre_screen,
        quota_available=True, confidence_threshold=CONFIDENCE_THRESHOLD,
    )
    print(f"  4. policy engine : {decision.route}  (rung: {decision.matched_rung})")
    print(f"\n  -> {decision.route}: {ROUTE_MEANING.get(decision.route, '?')}")
    note = evidence_note(cid)
    if note:
        print(f"     in the evidence run: {note}")
    print(f"     fixture-authored answer for comparison: {case.get('expected_outcome')}")
    return decision.route


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("case_ids", nargs="*", help="case ids; default = 3 illustrative cases")
    ap.add_argument("--llm", action="store_true", help="use the LLM arm (needs GEMINI_API_KEY)")
    args = ap.parse_args(argv)

    if args.llm:
        from src.llm_interpreter import interpret
    else:
        from src.rules_interpreter import interpret

    ids = args.case_ids or DEFAULT_TRIO
    for cid in ids:
        if cid not in BY_ID:
            print(f"unknown case id {cid!r} -- pick from {', '.join(list(BY_ID)[:5])}, ...", file=sys.stderr)
            return 1
        show(BY_ID[cid], interpret)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
