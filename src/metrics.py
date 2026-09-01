"""Batch metrics -- §24. Pure functions over the list of per-case result
dicts run_batch.py produces (plus the raw audit log for operational
counts). No I/O, no invented numbers -- every value here is computed from
real records passed in; a caller with no run yet has nothing to pass.

Present in this order, per §24: recovery funnel -> safety outcomes ->
hard-stop matrix -> operational reliability. The rules-vs-LLM comparison
(§23) is two separate runs of this same module, compared by the caller --
not this module's job -- except divergence_analysis() below, which is the
per-case half of that comparison: it takes both arms' result maps and
reports every case the two interpreters routed differently. A tie in the
aggregate counts still produces a populated divergence list; that is the
point -- "the arms tie" is only a null result if you cannot see which
cases they disagreed on.
"""

from collections import Counter

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


# --- §23 divergence analysis -------------------------------------------------
#
# Conservatism ordering of routes, used ONLY to decide which arm was the
# safer of two DIFFERENT routes on the same case. Higher = more conservative
# = suppresses/pauses/escalates rather than proceeding to collect. This is
# the same ordering §15's precedence table encodes and §24's hard-stop
# matrix leans on (_STILL_SAFE_ROUTES); it is not a new notion of
# correctness -- the frozen ground truth (gt_hard_stop) rides along in every
# divergence row so the reader judges correctness themselves.
_ROUTE_CONSERVATISM = {
    "STOP": 3,
    "VERIFY": 2, "PAUSE": 2, "REVIEW": 2,
    "RECOVER": 1, "LINK_QUOTA_GUARD": 1,
}


def _divergence_class(route_a: str, route_b: str, label_a: str, label_b: str) -> str:
    """Given two DIFFERENT routes, name the safer arm, or say both landed in
    the same safety tier by different rungs / both proceeded."""
    tier_a = _ROUTE_CONSERVATISM.get(route_a, 0)
    tier_b = _ROUTE_CONSERVATISM.get(route_b, 0)
    if tier_a > tier_b:
        return label_a
    if tier_b > tier_a:
        return label_b
    if tier_a >= 2:
        return "both_safe_different_rung"
    if tier_a == 1:
        return "both_unsafe"
    return "unclassified"


def divergence_analysis(arms: dict, replies: dict) -> dict:
    """Per-case rules-vs-LLM divergence (§23).

    `arms` maps an arm label ("rules_dev", "llm_dev", ...) to that arm's
    {case_id: result} map. The first two entries in iteration order are
    compared -- the caller passes them in a deterministic order (sorted
    evidence filenames). `replies` maps case_id -> customer_reply, joined
    from the fixtures by the caller so customer text never rides in the
    pipeline result records.

    Returns a dict with:
      - arms_compared: [label_a, label_b]
      - divergent: one row per case the two arms routed differently, each
        carrying case_id, bucket, customer_reply (full text -- the caller
        truncates for display), gt_hard_stop, routes {label: route},
        safer_arm
      - counts: Counter of safer_arm over the divergent rows
      - n_divergent, n_shared

    Fewer than two arms -> {"insufficient_arms": n, ...} with an empty
    divergent list. Never a fabricated or empty-implying-agreement table.
    Identical routing on every shared case -> divergent == [], which is a
    real reported outcome, not an error.
    """
    labels = list(arms)
    if len(labels) < 2:
        return {
            "insufficient_arms": len(labels),
            "arms_compared": labels,
            "divergent": [],
            "counts": {},
            "n_divergent": 0,
            "n_shared": 0,
        }

    label_a, label_b = labels[0], labels[1]
    arm_a, arm_b = arms[label_a], arms[label_b]
    shared = sorted(set(arm_a) & set(arm_b))

    divergent = []
    for cid in shared:
        route_a = arm_a[cid]["route"]
        route_b = arm_b[cid]["route"]
        if route_a == route_b:
            continue
        rec = arm_a[cid]
        divergent.append({
            "case_id": cid,
            "bucket": rec.get("bucket"),
            "customer_reply": replies.get(cid) or "",
            "gt_hard_stop": rec.get("gt_hard_stop"),
            "routes": {label_a: route_a, label_b: route_b},
            "safer_arm": _divergence_class(route_a, route_b, label_a, label_b),
        })

    return {
        "arms_compared": [label_a, label_b],
        "divergent": divergent,
        "counts": dict(Counter(d["safer_arm"] for d in divergent)),
        "n_divergent": len(divergent),
        "n_shared": len(shared),
    }


def format_divergence(divergence: dict, *, max_reply_chars: int = 80) -> str:
    """Render divergence_analysis() output as a markdown section. The message
    column is truncated to max_reply_chars; full text stays in the JSON
    artifact the caller writes."""
    header = "=== §23 Divergence analysis"
    if "insufficient_arms" in divergence:
        n = divergence["insufficient_arms"]
        return f"{header} ===\n_Not computed: {n} arm result file(s) found, exactly 2 required._"

    label_a, label_b = divergence["arms_compared"]
    lines = [f"{header} ({label_a} vs {label_b}) ==="]

    rows = divergence["divergent"]
    if not rows:
        lines.append(f"_Arms agreed on all {divergence['n_shared']} shared cases; no divergences._")
        return "\n".join(lines)

    lines.append(
        f"{divergence['n_divergent']} of {divergence['n_shared']} shared cases diverged. "
        f"Safer arm: {divergence['counts']}"
    )
    lines.append("")
    lines.append(f"| case | bucket | GT hard stop | {label_a} | {label_b} | safer | message |")
    lines.append("|---|---|---|---|---|---|---|")
    for d in rows:
        reply = " ".join(d["customer_reply"].split())
        if len(reply) > max_reply_chars:
            reply = reply[: max_reply_chars - 1] + "…"
        lines.append(
            f"| {d['case_id']} | {d['bucket']} | {d['gt_hard_stop']} | "
            f"{d['routes'][label_a]} | {d['routes'][label_b]} | {d['safer_arm']} | {reply} |"
        )
    return "\n".join(lines)
