"""scripts/resume_evidence_run.py -- OPERATIONAL RECOVERY WRAPPER (Path B).

Not part of REBOUND's evaluated behavior. The Day-9 --execute-links evidence
run (LLM arm, --split=all) hit Razorpay rate limiting twice -- 5 Payment
Links per rolling window, ~3s pacing did not help -- creating 10 links
across two sessions before the third burst was blocked.

DECISION (Path B): stop creating links. The central Track 03 result (LLM 0
unsafe misses vs rules 9) comes from the 59-case ROUTING evaluation, which
does not depend on link creation. The 10 links already demonstrate the full
chain end to end. This wrapper therefore:

  - finishes the remaining LLM interpretations, ONCE per case
  - does NOT call dispatch_link for anything (no further creation attempts)
  - still calls the frozen verify_payment_claim for VERIFY routes (a
    read-only status GET, part of the routing evaluation, not the
    rate-limited create endpoint)
  - appends to the existing audit log, never --first-run, never truncates
  - reconstructs evidence/run_results_llm_all.json from the complete audit
    history, tagging interpretation_session 1|2, counting the 10
    PAYMENT_LINK_CREATED events as created links and marking every other
    RECOVER case link_status NOT_ATTEMPTED_RATE_LIMITED

Frozen & untouched: LLM prompt, policy engine, rules interpreter, main
fixture, confidence threshold, razorpay_client, link_dispatch, metrics,
audit_log. Audit history: append only. No dispatch_link calls.

Cases already interpreted keep their session-1/session-2 routing exactly;
their per-case stop_signals/confidence were never persisted (only route +
matched_rung), so those are reconstructed from the rung where it uniquely
implies a signal, else left empty with reconstructed_from_audit=True.

Run once:  python -m scripts.resume_evidence_run
"""

import json
import sys
import time
from pathlib import Path

from scripts.run_batch import (
    _ROUTE_TO_OUTCOME,
    _frozen_ground_truth,
    _get_interpreter,
    _load_cases,
)
from src.audit_log import AuditLog, verify_chain
from src.instruction_detector import is_suspicious
from src.payment_verifier import verify_payment_claim
from src.policy_engine import CONFIDENCE_THRESHOLD, route
from src.structured_prechecks import check

AUDIT_PATH = Path("evidence/run_all.jsonl")
RESULTS_PATH = Path("evidence/run_results_llm_all.json")
SPLIT = "all"
EXPECTED_LINKS = 10  # created across sessions 1+2 before rate limiting; frozen for Path B

_RUNG_IMPLIES_SIGNAL = {
    "VERIFIED_PAYMENT_STATUS": ["PAYMENT_ALREADY_MADE_CLAIM"],
    "EXPLICIT_OPT_OUT": ["EXPLICIT_OPT_OUT"],
    "DISPUTE_OR_REFUND": ["DISPUTE_OR_REFUND"],
    "AMBIGUOUS_OR_CONFLICTING": ["AMBIGUOUS_OR_CONFLICTING"],
    "PROMISE_TO_PAY": ["PROMISE_TO_PAY"],
}


def _fail(msg):
    print(f"\nRESUME ABORTED -- {msg}", file=sys.stderr)
    print("No recovery attempted. Inspect evidence/run_all.jsonl and re-baseline.", file=sys.stderr)
    raise SystemExit(1)


def _records():
    return AuditLog(AUDIT_PATH).records()


def _preflight(all_ids):
    if not AUDIT_PATH.exists():
        _fail(f"{AUDIT_PATH} does not exist -- nothing to resume.")
    ok, problems = verify_chain(AUDIT_PATH)
    if not ok:
        _fail(f"audit chain does not verify: {problems}")

    audit = _records()
    policy = [r for r in audit if r["event_type"] == "POLICY_DECISION"]
    proc_ids = [r["case_id"] for r in policy]
    created = [r for r in audit if r["event_type"] == "PAYMENT_LINK_CREATED"]

    n = len(proc_ids)
    if not (25 <= n < 59):
        _fail(f"{n} POLICY_DECISION events -- expected a partial run in [25, 59).")
    if len(set(proc_ids)) != n:
        dups = [c for c in set(proc_ids) if proc_ids.count(c) > 1]
        _fail(f"duplicate POLICY_DECISION for: {dups}")
    if proc_ids != all_ids[:n]:
        _fail("processed cases are not a clean prefix of _load_cases('all').")
    if len(created) != EXPECTED_LINKS:
        _fail(f"expected exactly {EXPECTED_LINKS} PAYMENT_LINK_CREATED, found {len(created)}.")
    if len({r['case_id'] for r in created}) != len(created):
        _fail("a case has >1 PAYMENT_LINK_CREATED.")

    remaining = all_ids[n:]
    print("PRE-FLIGHT: PASS")
    print(f"  processed: {n}/59 (clean prefix)   links: {len(created)}   chain: valid   no duplicate POLICY_DECISION")
    print(f"  remaining interpretations: {len(remaining)}   (NO link creation for any of them)")
    return proc_ids, remaining, len(created)


def _interpret_one(case, log, client, interpret, seen, gt_map):
    """Mirror scripts.run_batch.run()'s per-case body, MINUS the RECOVER ->
    dispatch_link branch. No link is ever created here."""
    cid = case["case_id"]
    event = {"case_id": cid, "razorpay_context": case["razorpay_context"], "dispute_open": False}
    precheck = check(event, seen)
    time.sleep(1)  # is_llm pacing, as in run()
    seen.add(cid)

    result = {
        "case_id": cid,
        "bucket": case["bucket"],
        "fixture_expected_outcome": case.get("expected_outcome"),
        "gt_hard_stop": (gt_map[cid] == "HARD_STOP") if cid in gt_map
        else (case.get("expected_outcome") == "HARD_STOP"),
        "has_frozen_ground_truth": cid in gt_map,
        "stop_signals": [],
        "confidence": None,
        "link_status": None,
        "link_amount_paise": None,
        "link_completed": False,
        "resolved_outcome": None,
        "interpretation_session": 2,
    }

    if not precheck.ok:
        result["route"] = "STOP"
        result["matched_rung"] = "MALFORMED_OR_DUPLICATE_EVENT"
        log.append(cid, "POLICY_DECISION", {"route": "STOP", "matched_rung": result["matched_rung"]})
        return result

    try:
        ao = interpret(cid, case.get("customer_reply"))
    except Exception as exc:  # noqa: BLE001 -- Chaos condition 2 territory, as in run()
        result["route"] = "STOP"
        result["matched_rung"] = "INTERPRETER_OUTPUT_REJECTED"
        log.append(cid, "INTERPRETER_OUTPUT_REJECTED", {"error": repr(exc)})
        return result

    result["stop_signals"] = ao.stop_signals
    result["confidence"] = ao.confidence
    pre_screen_matched = is_suspicious(case.get("customer_reply") or "")
    # quota_available is irrelevant here (no dispatch) but route() takes it;
    # pass True so a RECOVER stays RECOVER rather than LINK_QUOTA_GUARD.
    decision = route(ao, precheck, pre_screen_matched=pre_screen_matched,
                     quota_available=True, confidence_threshold=CONFIDENCE_THRESHOLD)
    result["route"] = decision.route
    result["matched_rung"] = decision.matched_rung
    log.append(cid, "POLICY_DECISION", {"route": decision.route, "matched_rung": decision.matched_rung})

    if decision.route == "VERIFY":
        ctx = case["razorpay_context"]
        verification = verify_payment_claim(client, order_id=ctx["order_id"], claimed_payment_id=ctx.get("payment_id"))
        result["resolved_outcome"] = verification.outcome
        log.append(cid, "PAYMENT_CLAIM_VERIFIED", {"outcome": verification.outcome, "reason": verification.reason})
        print(f"    {cid}: VERIFY -> {verification.outcome}")
    else:
        result["resolved_outcome"] = _ROUTE_TO_OUTCOME.get(decision.route)
        if decision.route == "RECOVER":
            print(f"    {cid}: RECOVER (no link -- Path B)")

    return result


def _postflight(all_ids, links_before):
    ok, problems = verify_chain(AUDIT_PATH)
    if not ok:
        _fail(f"audit chain does not verify after completion: {problems}")
    audit = _records()
    policy = [r for r in audit if r["event_type"] == "POLICY_DECISION"]
    created = [r for r in audit if r["event_type"] == "PAYMENT_LINK_CREATED"]
    pids = [r["case_id"] for r in policy]

    if len(pids) != 59:
        _fail(f"expected 59 POLICY_DECISION events, found {len(pids)}.")
    if set(pids) != set(all_ids) or len(set(pids)) != 59:
        _fail("the 59 POLICY_DECISION case ids are not exactly the 59 fixture ids.")
    if len(pids) != len(set(pids)):
        _fail("duplicate POLICY_DECISION after completion.")
    if len(created) != links_before:
        _fail(f"PAYMENT_LINK_CREATED count changed ({links_before} -> {len(created)}) -- Path B must not create links.")
    if len({r['case_id'] for r in created}) != len(created):
        _fail("a case has >1 PAYMENT_LINK_CREATED.")

    print("\nPOST-FLIGHT: PASS")
    print(f"  59 unique cases   59 policy decisions   no duplicates   chain: valid")
    print(f"  PAYMENT_LINK_CREATED: {len(created)} (unchanged -- no further creation attempts)")


def _reconstruct(all_cases, live_results):
    gt_map = _frozen_ground_truth(SPLIT)
    all_ids = [c["case_id"] for c in all_cases]
    session1 = set(all_ids[:25])
    audit = _records()
    by_case = {}
    for r in audit:
        by_case.setdefault(r["case_id"], []).append(r)
    linked = {r["case_id"] for r in audit if r["event_type"] == "PAYMENT_LINK_CREATED"}

    out = {}
    for case in all_cases:
        cid = case["case_id"]
        if cid in live_results:
            res = dict(live_results[cid])
        else:
            evts = by_case.get(cid, [])
            pd = next((e for e in evts if e["event_type"] == "POLICY_DECISION"), None)
            if pd is None:
                _fail(f"no POLICY_DECISION for {cid} during reconstruction.")
            rung = pd["payload"]["matched_rung"]
            pcv = next((e for e in evts if e["event_type"] == "PAYMENT_CLAIM_VERIFIED"), None)
            res = {
                "case_id": cid,
                "bucket": case["bucket"],
                "fixture_expected_outcome": case.get("expected_outcome"),
                "gt_hard_stop": (gt_map[cid] == "HARD_STOP") if cid in gt_map
                else (case.get("expected_outcome") == "HARD_STOP"),
                "has_frozen_ground_truth": cid in gt_map,
                "stop_signals": list(_RUNG_IMPLIES_SIGNAL.get(rung, [])),
                "confidence": None,
                "link_status": None,
                "link_amount_paise": None,
                "link_completed": False,
                "route": pd["payload"]["route"],
                "matched_rung": rung,
                "resolved_outcome": (pcv["payload"]["outcome"] if pcv
                                     else _ROUTE_TO_OUTCOME.get(pd["payload"]["route"])),
                "reconstructed_from_audit": True,
            }
        res["interpretation_session"] = 1 if cid in session1 else 2

        if cid in linked:
            res["link_status"] = "CREATED"
            res["link_amount_paise"] = 100  # NOMINAL_TEST_AMOUNT_PAISE
        elif res["route"] == "RECOVER":
            res["link_status"] = "NOT_ATTEMPTED_RATE_LIMITED"
        out[cid] = res
    return out


def main():
    all_cases = _load_cases(SPLIT)
    all_ids = [c["case_id"] for c in all_cases]
    if len(all_ids) != 59:
        _fail(f"_load_cases('all') returned {len(all_ids)} cases, expected 59.")
    case_by_id = {c["case_id"]: c for c in all_cases}

    proc_ids, remaining, links_before = _preflight(all_ids)

    from src.razorpay_client import RazorpayClient
    interpret = _get_interpreter("llm")
    log = AuditLog(AUDIT_PATH)
    client = RazorpayClient()
    gt_map = _frozen_ground_truth(SPLIT)

    print(f"\nCOMPLETING {len(remaining)} interpretations (no link creation)")
    seen = set(proc_ids)
    live = {}
    for cid in remaining:
        live[cid] = _interpret_one(case_by_id[cid], log, client, interpret, seen, gt_map)

    _postflight(all_ids, links_before)

    print("\nRECONSTRUCTING evidence/run_results_llm_all.json from the complete audit history")
    results = _reconstruct(all_cases, live)
    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    from collections import Counter
    routes = Counter(r["route"] for r in results.values())
    s1 = sum(1 for r in results.values() if r["interpretation_session"] == 1)
    created = sum(1 for r in results.values() if r.get("link_status") == "CREATED")
    rl = sum(1 for r in results.values() if r.get("link_status") == "NOT_ATTEMPTED_RATE_LIMITED")
    print(f"  59 cases  ({s1} session-1, {59 - s1} session-2)")
    print(f"  routes: {dict(routes)}")
    print(f"  links: {created} CREATED, {rl} RECOVER cases NOT_ATTEMPTED_RATE_LIMITED")
    print("\nNEXT: verify artifact, browser-checkout the 10 links, run_batch --reconcile-only,")
    print("      run rules arm dry, generate_metrics. Do not assume validity before that.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
