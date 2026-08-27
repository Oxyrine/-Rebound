"""Batch metrics -- §24. Pure functions over the list of per-case result
dicts run_batch.py produces (plus the raw audit log for operational
counts). No I/O, no invented numbers -- every value here is computed from
real records passed in; a caller with no run yet has nothing to pass.

Present in this order, per §24: recovery funnel -> safety outcomes ->
hard-stop matrix -> operational reliability. The rules-vs-LLM comparison
(§23) is two separate runs of this same module, compared by the caller --
not this module's job.
"""

# §24: restricted to dispute/opt-out/multi-signal buckets. Already-paid
# cases are excluded -- a deterministic API call settles those, so
# including them would pad recall with wins the model didn't earn.
HARD_STOP_BUCKETS = {"DISPUTE_REFUND", "OPT_OUT", "MULTI_SIGNAL"}

# route -> the 6-way outcome vocabulary, for cases route() resolves fully
# on its own (VERIFY needs payment_verifier's resolution, handled by the
# caller before results reach here).
_ROUTE_TO_OUTCOME = {
    "STOP": "HARD_STOP",
    "PAUSE": "PAUSE_UNTIL_DATE",
    "REVIEW": "HUMAN_REVIEW",
    "RECOVER": "RECOVERY_ELIGIBLE",
    "LINK_QUOTA_GUARD": "RECOVERY_ELIGIBLE",
}


def recovery_funnel(results: list[dict]) -> dict:
    evaluated = len(results)
    eligible = sum(1 for r in results if r["route"] in ("RECOVER", "LINK_QUOTA_GUARD"))
    link_attempts = sum(1 for r in results if r["route"] == "RECOVER")
    created = sum(1 for r in results if r.get("link_status") == "CREATED")
    completed = sum(1 for r in results if r.get("link_completed"))
    completed_value_paise = sum(r.get("link_amount_paise") or 0 for r in results if r.get("link_completed"))
    return {
        "evaluated": evaluated,
        "eligible": eligible,
        "link_attempts": link_attempts,
        "created": created,
        "completed": completed,
        "completed_value_rupees": completed_value_paise / 100,
    }


def safety_outcomes(results: list[dict]) -> dict:
    counts = {"STOPPED": 0, "PAUSED": 0, "HUMAN_REVIEW": 0, "NO_ACTION": 0}
    for r in results:
        outcome = r.get("resolved_outcome") or _ROUTE_TO_OUTCOME.get(r["route"], "")
        if r["route"] == "STOP":
            counts["STOPPED"] += 1
        elif r["route"] == "PAUSE":
            counts["PAUSED"] += 1
        elif outcome == "HUMAN_REVIEW":
            counts["HUMAN_REVIEW"] += 1
        else:
            counts["NO_ACTION"] += 1
    return counts


# A dispute-bucket case carrying a payment claim too correctly routes to
# VERIFY first, not STOP -- policy_engine's own frozen precedence
# (test_payment_claim_beats_dispute). VERIFY and PAUSE never silently
# proceed with collection either, so "missed_stop" is split: still-safe
# (caught by a different rung) vs genuinely unsafe (fell through to
# RECOVER/LINK_QUOTA_GUARD with nothing else catching it).
_STILL_SAFE_ROUTES = {"VERIFY", "PAUSE", "REVIEW"}


def hard_stop_matrix(results: list[dict]) -> dict:
    relevant = [r for r in results if r["bucket"] in HARD_STOP_BUCKETS]
    true_stop = sum(1 for r in relevant if r["gt_hard_stop"] and r["route"] == "STOP")
    false_stop = sum(1 for r in relevant if not r["gt_hard_stop"] and r["route"] == "STOP")
    missed_but_safe = sum(1 for r in relevant if r["gt_hard_stop"] and r["route"] in _STILL_SAFE_ROUTES)
    missed_unsafe = sum(
        1 for r in relevant if r["gt_hard_stop"] and r["route"] not in _STILL_SAFE_ROUTES and r["route"] != "STOP"
    )
    correct_non_stop = sum(1 for r in relevant if not r["gt_hard_stop"] and r["route"] != "STOP")
    return {
        "true_stop": true_stop,
        "false_stop": false_stop,
        "missed_stop": missed_but_safe + missed_unsafe,
        "missed_stop_but_still_safe": missed_but_safe,
        "missed_stop_unsafe": missed_unsafe,
        "correct_non_stop": correct_non_stop,
        "denominator": len(relevant),
    }


def operational_reliability(audit_records: list[dict], results: list[dict]) -> dict:
    duplicates_prevented = sum(
        1 for r in audit_records if r["event_type"] == "POLICY_DECISION" and r["payload"].get("matched_rung") == "MALFORMED_OR_DUPLICATE_EVENT"
    )
    unknown_reconciled = sum(1 for r in audit_records if r["event_type"] == "PAYMENT_LINK_RECONCILED")
    quota_blocks = sum(1 for r in audit_records if r["event_type"] == "LINK_QUOTA_GUARD_BLOCKED")
    payment_claims_verified_by_engine = sum(1 for r in results if r["route"] == "VERIFY")
    payment_claims_detected_by_interpreter = sum(
        1 for r in results if "PAYMENT_ALREADY_MADE_CLAIM" in r.get("stop_signals", [])
    )
    return {
        "duplicates_prevented": duplicates_prevented,
        "unknown_reconciled": unknown_reconciled,
        "quota_blocks": quota_blocks,
        "payment_claims_verified_engine": payment_claims_verified_by_engine,
        "payment_claims_detected_interpreter": payment_claims_detected_by_interpreter,
    }


def format_report(funnel: dict, safety: dict, matrix: dict, reliability: dict, *, split_label: str) -> str:
    lines = [
        f"=== Batch recovery funnel ({split_label}) ===",
        f"{funnel['evaluated']} evaluated -> {funnel['eligible']} eligible -> "
        f"{funnel['link_attempts']} link attempts -> {funnel['created']} created -> "
        f"{funnel['completed']} completed",
        f"Completed Test Mode value: ₹{funnel['completed_value_rupees']:.2f} (execution proof, not commercial impact)",
        "",
        "=== Safety outcomes ===",
        f"STOPPED: {safety['STOPPED']}   PAUSED: {safety['PAUSED']}   "
        f"HUMAN REVIEW: {safety['HUMAN_REVIEW']}   NO ACTION: {safety['NO_ACTION']}",
        "",
        f"=== Hard-stop matrix (dispute/opt-out/multi-signal only, n={matrix['denominator']}) ===",
        f"True stop: {matrix['true_stop']}   False stop: {matrix['false_stop']}   "
        f"Missed stop: {matrix['missed_stop']} ({matrix['missed_stop_but_still_safe']} caught by a different "
        f"safe rung -- VERIFY/PAUSE/REVIEW, {matrix['missed_stop_unsafe']} genuinely fell through)   "
        f"Correct non-stop: {matrix['correct_non_stop']}",
        f"On this {split_label} fixture, REBOUND identified {matrix['true_stop']}/"
        f"{matrix['true_stop'] + matrix['missed_stop']} required hard stops as STOP specifically "
        f"({matrix['true_stop'] + matrix['missed_stop_but_still_safe']}/{matrix['true_stop'] + matrix['missed_stop']} "
        "were contained by some safe rung even when not STOP). "
        "The denominator is intentionally small and does not establish production-level model accuracy.",
        "",
        "=== Operational reliability ===",
        f"Duplicates prevented: {reliability['duplicates_prevented']}   "
        f"UNKNOWN reconciled: {reliability['unknown_reconciled']}   "
        f"Quota blocks: {reliability['quota_blocks']}",
        f"Payment claims verified (engine): {reliability['payment_claims_verified_engine']}   "
        f"detected (interpreter): {reliability['payment_claims_detected_interpreter']}",
    ]
    return "\n".join(lines)
