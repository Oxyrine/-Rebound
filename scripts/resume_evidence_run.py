"""scripts/resume_evidence_run.py -- OPERATIONAL RECOVERY WRAPPER.

Not part of REBOUND's evaluated behavior. The Day-9 --execute-links evidence
run (LLM arm, --split=all) hit a Razorpay 429 rate limit after creating 5
Payment Links, on case 26 of 59. This wrapper completes that run:

  - WITHOUT re-interpreting the 25 cases session 1 already established.
    Gemini is non-deterministic (RCV-028 already routed differently between
    the dry run and session 1); reinterpreting would make the final dataset
    "25 cases @ T1 + 34 cases @ T2" instead of "59 cases, one interpretation
    each".
  - WITHOUT modifying any frozen component. It imports and calls the frozen
    functions unchanged: _get_interpreter / check / route / is_suspicious /
    quota_available / verify_payment_claim / dispatch_link / verify_chain /
    AuditLog. It mirrors run()'s per-case logic exactly for the 34 remaining
    cases.
  - Appends to the existing audit log. Never truncates, never --first-run.
  - Paces ~3s between ACTUAL link-creation API calls (not between cases).

Steps:
  1. assert exact session-1 state (25 cases, 5 links, valid chain, no
     duplicate POLICY_DECISION) -- fail loudly otherwise
  2. resume the single dispatch the 429 interrupted: session-1 RECOVER case
     with no link (RCV-047), via frozen dispatch_link()
  3. interpret + route + dispatch the remaining 34 cases, once each,
     mirroring run()
  4. assert completed invariants (59 unique cases, 59 policy decisions,
     <=28 links, no duplicate link per case, valid chain)
  5. reconstruct evidence/run_results_llm_all.json from the combined audit
     history, tagging interpretation_session 1|2, counting every
     PAYMENT_LINK_CREATED (either session) as a created link

Frozen & untouched: LLM prompt, policy engine, rules interpreter, main
fixture, confidence threshold, razorpay_client, link_dispatch, metrics,
audit_log. Audit history: append only.

Run once:  python -m scripts.resume_evidence_run
"""

import json
import sys
import time
from pathlib import Path

from scripts.run_batch import (
    NOMINAL_TEST_AMOUNT_PAISE,
    _ROUTE_TO_OUTCOME,
    _frozen_ground_truth,
    _get_interpreter,
    _load_cases,
)
from src.audit_log import AuditLog, verify_chain
from src.instruction_detector import is_suspicious
from src.link_dispatch import dispatch_link, quota_available
from src.payment_verifier import verify_payment_claim
from src.policy_engine import CONFIDENCE_THRESHOLD, route
from src.structured_prechecks import check

AUDIT_PATH = Path("evidence/run_all.jsonl")
RESULTS_PATH = Path("evidence/run_results_llm_all.json")
SPLIT = "all"
LINK_PACING_SECONDS = 3
API_CALL_STATUSES = {"CREATED", "UNKNOWN"}  # dispatch_link actually hit the create endpoint

# Session-1 per-case stop_signals were never persisted (only route + matched_rung
# went to the audit log). Where the rung uniquely implies a signal, reconstruct it
# so operational_reliability's "claims detected by interpreter" stays correct;
# elsewhere leave it empty and mark the case reconstructed_from_audit.
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


def _audit_records():
    return AuditLog(AUDIT_PATH).records()


def _preflight(all_ids):
    if not AUDIT_PATH.exists():
        _fail(f"{AUDIT_PATH} does not exist -- nothing to resume.")

    ok, problems = verify_chain(AUDIT_PATH)
    if not ok:
        _fail(f"audit chain does not verify: {problems}")

    audit = _audit_records()
    policy = [r for r in audit if r["event_type"] == "POLICY_DECISION"]
    proc_ids = [r["case_id"] for r in policy]
    created = [r for r in audit if r["event_type"] == "PAYMENT_LINK_CREATED"]

    if len(proc_ids) != 25:
        _fail(f"expected 25 POLICY_DECISION events, found {len(proc_ids)} -- state is not the known session-1 baseline.")
    if len(set(proc_ids)) != 25:
        _fail(f"a case has >1 POLICY_DECISION: {[c for c in set(proc_ids) if proc_ids.count(c) > 1]}")
    if proc_ids != all_ids[:25]:
        _fail("session-1 case ids are not the exact first-25 prefix of _load_cases('all').")
    if len(created) != 5:
        _fail(f"expected exactly 5 PAYMENT_LINK_CREATED, found {len(created)}.")
    if len({r['case_id'] for r in created}) != 5:
        _fail("a case has >1 PAYMENT_LINK_CREATED.")

    session1_ids = proc_ids
    remaining_ids = all_ids[25:]
    if set(remaining_ids) != set(all_ids) - set(session1_ids):
        _fail("remaining case set is not exactly (all - session1).")
    if len(remaining_ids) != 34:
        _fail(f"expected 34 remaining cases, computed {len(remaining_ids)}.")

    routes = {r["case_id"]: r["payload"]["route"] for r in policy}
    linked = {r["case_id"] for r in created}
    s1_recover_no_link = [cid for cid in session1_ids if routes[cid] == "RECOVER" and cid not in linked]

    print("PRE-FLIGHT: PASS")
    print(f"  session-1 cases: 25   links: 5   chain: valid   no duplicate POLICY_DECISION")
    print(f"  interrupted dispatch to resume: {s1_recover_no_link or 'none'}")
    print(f"  remaining cases to interpret: {len(remaining_ids)}")
    return session1_ids, remaining_ids, s1_recover_no_link


def _process_one(case, log, client, interpret, seen):
    """Exact mirror of scripts.run_batch.run()'s per-case body."""
    case_id = case["case_id"]
    event = {"case_id": case_id, "razorpay_context": case["razorpay_context"], "dispute_open": False}
    precheck = check(event, seen)
    time.sleep(1)  # is_llm pacing, as in run()
    seen.add(case_id)

    gt_map = _process_one.gt_map
    result = {
        "case_id": case_id,
        "bucket": case["bucket"],
        "fixture_expected_outcome": case.get("expected_outcome"),
        "gt_hard_stop": (gt_map[case_id] == "HARD_STOP") if case_id in gt_map
        else (case.get("expected_outcome") == "HARD_STOP"),
        "has_frozen_ground_truth": case_id in gt_map,
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
        log.append(case_id, "POLICY_DECISION", {"route": "STOP", "matched_rung": result["matched_rung"]})
        return result

    try:
        ao = interpret(case_id, case.get("customer_reply"))
    except Exception as exc:  # noqa: BLE001 -- Chaos condition 2 territory, as in run()
        result["route"] = "STOP"
        result["matched_rung"] = "INTERPRETER_OUTPUT_REJECTED"
        log.append(case_id, "INTERPRETER_OUTPUT_REJECTED", {"error": repr(exc)})
        return result

    result["stop_signals"] = ao.stop_signals
    result["confidence"] = ao.confidence
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
    elif decision.route == "RECOVER":
        dispatch = dispatch_link(
            log, client, case_id=case_id, amount_paise=NOMINAL_TEST_AMOUNT_PAISE,
            reference_id=case["merchant_reference_id"], description=f"REBOUND {case_id}",
        )
        result["link_status"] = dispatch.status
        result["link_amount_paise"] = NOMINAL_TEST_AMOUNT_PAISE if dispatch.status == "CREATED" else None
        result["resolved_outcome"] = _ROUTE_TO_OUTCOME[decision.route]
        print(f"    {case_id}: RECOVER -> dispatch {dispatch.status}")
        if dispatch.status in API_CALL_STATUSES:
            time.sleep(LINK_PACING_SECONDS)
    else:
        result["resolved_outcome"] = _ROUTE_TO_OUTCOME.get(decision.route)

    return result


def _postflight(all_ids):
    ok, problems = verify_chain(AUDIT_PATH)
    if not ok:
        _fail(f"audit chain does not verify after resume: {problems}")

    audit = _audit_records()
    policy = [r for r in audit if r["event_type"] == "POLICY_DECISION"]
    created = [r for r in audit if r["event_type"] == "PAYMENT_LINK_CREATED"]
    pids = [r["case_id"] for r in policy]

    if len(pids) != 59:
        _fail(f"expected 59 POLICY_DECISION events, found {len(pids)}.")
    if set(pids) != set(all_ids) or len(set(pids)) != 59:
        _fail("the 59 POLICY_DECISION case ids are not exactly the 59 fixture ids.")
    if len(created) > 28:
        _fail(f"{len(created)} PAYMENT_LINK_CREATED events -- exceeds the 28-link quota.")
    if len({r['case_id'] for r in created}) != len(created):
        _fail("a case has >1 PAYMENT_LINK_CREATED after resume.")

    print("\nPOST-FLIGHT: PASS")
    print(f"  59 unique cases   59 policy decisions   {len(created)} links (<=28)   no duplicate link   chain: valid")


def _reconstruct_results(all_cases, session1_ids, session2_results):
    gt_map = _frozen_ground_truth(SPLIT)
    audit = _audit_records()
    by_case = {}
    for r in audit:
        by_case.setdefault(r["case_id"], []).append(r)
    linked = {r["case_id"] for r in audit if r["event_type"] == "PAYMENT_LINK_CREATED"}

    out = {}
    for case in all_cases:
        cid = case["case_id"]
        if cid in session2_results:
            res = dict(session2_results[cid])
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
                "interpretation_session": 1,
                "reconstructed_from_audit": True,
            }
        if cid in linked:
            res["link_status"] = "CREATED"
            res["link_amount_paise"] = NOMINAL_TEST_AMOUNT_PAISE
        out[cid] = res
    return out


def main():
    all_cases = _load_cases(SPLIT)
    all_ids = [c["case_id"] for c in all_cases]
    case_by_id = {c["case_id"]: c for c in all_cases}
    if len(all_ids) != 59:
        _fail(f"_load_cases('all') returned {len(all_ids)} cases, expected 59.")

    session1_ids, remaining_ids, s1_recover_no_link = _preflight(all_ids)

    from src.razorpay_client import RazorpayClient
    interpret = _get_interpreter("llm")
    log = AuditLog(AUDIT_PATH)
    client = RazorpayClient()
    _process_one.gt_map = _frozen_ground_truth(SPLIT)

    print("\nSTEP 2: resume the interrupted session-1 dispatch(es)")
    for cid in s1_recover_no_link:
        case = case_by_id[cid]
        dispatch = dispatch_link(
            log, client, case_id=cid, amount_paise=NOMINAL_TEST_AMOUNT_PAISE,
            reference_id=case["merchant_reference_id"], description=f"REBOUND {cid}",
        )
        print(f"  {cid}: dispatch {dispatch.status}")
        if dispatch.status in API_CALL_STATUSES:
            time.sleep(LINK_PACING_SECONDS)

    print(f"\nSTEP 3: interpret + route + dispatch the {len(remaining_ids)} remaining cases (one pass each)")
    seen = set(session1_ids)
    session2_results = {}
    for cid in remaining_ids:
        session2_results[cid] = _process_one(case_by_id[cid], log, client, interpret, seen)

    _postflight(all_ids)

    print("\nSTEP 5: reconstruct evidence/run_results_llm_all.json from the combined audit history")
    results = _reconstruct_results(all_cases, session1_ids, session2_results)
    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    s1 = sum(1 for r in results.values() if r["interpretation_session"] == 1)
    s2 = sum(1 for r in results.values() if r["interpretation_session"] == 2)
    created_total = sum(1 for r in results.values() if r.get("link_status") == "CREATED")
    print(f"  wrote {len(results)} case results  ({s1} session-1, {s2} session-2)  {created_total} links CREATED")
    print("\nNEXT: verify the artifact, run the browser checkouts, then run_batch --reconcile-only,")
    print("      then generate_metrics. Do NOT assume the evidence is valid before that.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
