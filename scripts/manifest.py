import json
import sys
from collections import Counter
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

REQUIRED_BUCKETS = {
    "DISPUTE_REFUND", "OPT_OUT", "ALREADY_PAID_TRUE", "ALREADY_PAID_FALSE",
    "INJECTION", "NEAR_MISS", "AMBIGUOUS", "MULTI_SIGNAL", "BENIGN",
}

HARD_STOP_JUDGMENT_BUCKETS = {"DISPUTE_REFUND", "OPT_OUT", "MULTI_SIGNAL"}

# Per-bucket minimum DEVELOPMENT case counts.
# These reflect the actual target fixture sizes (see spec Part IV, section 20),
# not a blanket rule -- small buckets (e.g. ALREADY_PAID_FALSE has only 2 cases
# total) cannot have 3 dev examples without violating the bucket's own total.
MIN_DEV_PER_BUCKET = {
    "DISPUTE_REFUND": 3,
    "OPT_OUT": 3,
    "ALREADY_PAID_TRUE": 2,
    "ALREADY_PAID_FALSE": 1,
    "INJECTION": 2,
    "NEAR_MISS": 3,
    "AMBIGUOUS": 2,
    "MULTI_SIGNAL": 1,
    "BENIGN": 0,
}


def load_cases(filename):
    path = FIXTURES_DIR / filename
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_case_shape(case, errors):
    required_fields = [
        "case_id", "split", "bucket", "payment_link_eligible",
        "requires_evidence_judgment", "requires_status_verification",
        "expected_outcome", "authoring_method",
    ]
    for field in required_fields:
        if field not in case:
            errors.append(f"{case.get('case_id', '???')}: missing field '{field}'")

    if case.get("bucket") not in REQUIRED_BUCKETS:
        errors.append(f"{case.get('case_id')}: invalid bucket '{case.get('bucket')}'")

    ctx = case.get("razorpay_context", {})
    if case.get("bucket") != "ALREADY_PAID_FALSE" and not ctx.get("order_id"):
        errors.append(f"{case.get('case_id')}: missing order_id in razorpay_context")


# spec-amendment-01 ticket 04. Red-team probe cases (fixtures/redteam_cases.json)
# are held OUTSIDE the 58/59-case fixture -- never in dev, never held-out, never
# summed into total_cases. This is the structural guard (§31) that stops the
# category drifting into the total the way BENIGN drifted 23 -> 24: the manifest
# refuses to build if a red-team id collides with a fixture id. Red-team cases
# skip validate_case_shape (which hard-rejects any bucket outside REQUIRED_BUCKETS
# and is tuned to the fixture's field set); they get their own shape check for the
# §12 identity chain plus the four red-team-only fields.
def load_redteam_cases():
    return load_cases("redteam_cases.json")


def validate_redteam_case_shape(case, errors):
    cid = case.get("case_id", "???")
    if case.get("split") != "redteam":
        errors.append(f"{cid}: red-team case must have split == 'redteam', got {case.get('split')!r}")
    for field in (
        "case_id", "bucket", "customer_reply", "expected_outcome",
        "authoring_method", "labeling_method", "failure_mode", "probe_rationale",
    ):
        if not case.get(field):
            errors.append(f"{cid}: red-team case missing/empty field '{field}'")
    ctx = case.get("razorpay_context", {})
    if not ctx.get("order_id") or not ctx.get("payment_id"):
        errors.append(f"{cid}: red-team case missing identity chain (needs order_id + payment_id)")


def build_manifest():
    dev = load_cases("development_cases.json")
    heldout = load_cases("heldout_cases.json")
    all_cases = dev + heldout
    redteam = load_redteam_cases()

    errors = []
    for case in all_cases:
        validate_case_shape(case, errors)

    ids = [c["case_id"] for c in all_cases]
    dupes = [i for i, count in Counter(ids).items() if count > 1]
    if dupes:
        errors.append(f"Duplicate case_ids: {dupes}")

    # Red-team disjointness -- the structural guard. Red-team cases are NOT
    # added to all_cases, so total/dev/heldout counts and every downstream
    # number stay anchored to the fixture. Their only interaction with the
    # manifest is this check.
    if redteam:
        for case in redteam:
            validate_redteam_case_shape(case, errors)
        rt_ids = [c["case_id"] for c in redteam]
        overlap = sorted(set(ids) & set(rt_ids))
        if overlap:
            errors.append(f"Red-team case_ids collide with the fixture: {overlap}")
        rt_dupes = [i for i, count in Counter(rt_ids).items() if count > 1]
        if rt_dupes:
            errors.append(f"Duplicate red-team case_ids: {rt_dupes}")

    total = len(all_cases)
    heldout_count = len(heldout)
    dev_count = len(dev)

    bucket_counts = Counter(c["bucket"] for c in all_cases)
    dev_bucket_counts = Counter(c["bucket"] for c in dev)
    heldout_bucket_counts = Counter(c["bucket"] for c in heldout)

    heldout_hard_stops = sum(
        1 for c in heldout if c["bucket"] in HARD_STOP_JUDGMENT_BUCKETS
    )
    heldout_benign = heldout_bucket_counts.get("BENIGN", 0)
    link_eligible = sum(1 for c in all_cases if c.get("payment_link_eligible"))

    # 59, not the spec's original 58: RCV-059 was added deliberately on Day 2
    # to give the PROMISE_TO_PAY specificity-gate rule (a dated promise pauses,
    # a vague one doesn't) an isolated, single-signal proof case. Without it,
    # the only PAUSE_UNTIL_DATE example (RCV-022) is also MULTI_SIGNAL, so the
    # rule and "pauses only in combination" were indistinguishable on the data.
    if total != 59:
        errors.append(f"Total cases = {total}, expected 59")
    if heldout_count != 22:
        errors.append(f"Held-out count = {heldout_count}, expected 22")
    if dev_count != 37:
        errors.append(f"Development count = {dev_count}, expected 37")

    for bucket, minimum in MIN_DEV_PER_BUCKET.items():
        actual = dev_bucket_counts.get(bucket, 0)
        if actual < minimum:
            errors.append(f"Bucket '{bucket}' has only {actual} dev cases, need >={minimum}")

    if heldout_hard_stops < 8:
        errors.append(f"Held-out hard-stop judgment cases = {heldout_hard_stops}, need >=8")
    if heldout_benign < 7:
        errors.append(f"Held-out benign cases = {heldout_benign}, need >=7")
    if link_eligible > 28:
        errors.append(f"Link-eligible cases = {link_eligible}, exceeds 28-link cap")

    manifest = {
        "total_cases": total,
        "development_cases": dev_count,
        "heldout_cases": heldout_count,
        "bucket_counts": dict(bucket_counts),
        "development_bucket_counts": dict(dev_bucket_counts),
        "heldout_bucket_counts": dict(heldout_bucket_counts),
        "heldout_hard_stop_judgment_cases": heldout_hard_stops,
        "heldout_benign_cases": heldout_benign,
        "payment_link_eligible_total": link_eligible,
        # Reported separately, never summed into total_cases (spec-amendment-01 #04).
        "redteam_cases": len(redteam),
        "redteam_failure_modes": dict(Counter(c.get("failure_mode") for c in redteam)),
        "constraints_satisfied": len(errors) == 0,
        "errors": errors,
    }
    return manifest


if __name__ == "__main__":
    manifest = build_manifest()

    out_path = FIXTURES_DIR / "manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(json.dumps(manifest, indent=2))

    if not manifest["constraints_satisfied"]:
        print("\nMANIFEST CONSTRAINTS FAILED - fix fixtures before proceeding.", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nManifest constraints satisfied.")
        sys.exit(0)