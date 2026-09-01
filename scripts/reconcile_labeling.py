"""Reconciles labeling pass 1 vs pass 2 and freezes held-out ground truth
-- ticket 09, §21.

Intra-rater agreement is the signal: if the same human, blind, twice,
doesn't agree with themselves, that case's ground truth isn't solid
enough to hold a held-out evaluation to. Never compares against
heldout_cases.json's own expected_outcome (the original, AI-authored
draft written on Day 1) -- that's not the point. The point is whether the
human's own judgment is stable, independent of what that first draft said.

Where pass 1 and pass 2 agree, that's the frozen label -- no further
input needed. Where they disagree, this script does NOT resolve it: it
writes both labels and both reasonings side by side into
heldout_ground_truth_frozen.json and stops short of freezing, because
that call belongs to the person who made both judgments, applying
labeling_rubric.md themselves. Fill in "final_label" for each
disagreement and re-run to complete the freeze.

CAVEAT (found during pass-2 review, 2026-09-01): labeling_rubric.md's own
Payment-claim section states a labeler cannot verify payment status by
reading text -- razorpay_context carries no status field, only the
identity chain. The rubric compensates by naming worked anchor cases
(RCV-014 true, RCV-018 false, etc.) whose ground truth it spells out, so a
labeler pattern-matches against a taught example rather than guessing.
RCV-015 is an ALREADY_PAID_TRUE held-out case the rubric names nowhere --
no anchor, no calibration -- and its one textual cue ("order number 563"
not matching this case's real order_id) is the SAME shape of signal the
rubric calls out as the false-claim tell in RCV-018, yet RCV-015's
authored outcome is true. A pass1==pass2 agreement on an unanchored
ALREADY_PAID_* case is pattern consistency, not a verified judgment, and
must not be silently absorbed into the intra-rater number as if it were.
_unanchored_payment_claim_cases() below flags any such case generically
(derived by grepping the rubric for named case ids, not hardcoded to
RCV-015) and the caveat is written into the frozen output, disclosed
rather than fixed -- the case is still labeled and still frozen if the
passes agree; the caveat says what that agreement does and doesn't mean.

Run: python3 -m scripts.reconcile_labeling
"""

import json
import re
import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
FROZEN_PATH = FIXTURES_DIR / "heldout_ground_truth_frozen.json"

# The two buckets labeling_rubric.md's own "Payment claim" section says
# cannot be resolved from text -- razorpay_context has no status field.
_TEXT_UNVERIFIABLE_BUCKETS = {"ALREADY_PAID_TRUE", "ALREADY_PAID_FALSE"}


def _rubric_anchored_case_ids() -> set[str]:
    """Case ids labeling_rubric.md names as worked examples. Read at
    reconciliation time only -- never surfaced to a labeler mid-pass, and
    never used to alter a label, only to flag which ALREADY_PAID_* cases
    had no textual calibration available."""
    rubric_path = FIXTURES_DIR / "labeling_rubric.md"
    if not rubric_path.exists():
        return set()
    return set(re.findall(r"RCV-\d+", rubric_path.read_text(encoding="utf-8")))


def unanchored_payment_claim_cases(case_ids) -> list[str]:
    """Of the given case ids, which are ALREADY_PAID_TRUE/FALSE cases the
    rubric names no anchor for. Cross-references heldout_cases.json for
    bucket only -- reconciliation runs after both passes are complete, so
    this reads no ground truth a labeler hasn't already finished with."""
    heldout_path = FIXTURES_DIR / "heldout_cases.json"
    if not heldout_path.exists():
        return []
    by_id = {c["case_id"]: c for c in json.loads(heldout_path.read_text(encoding="utf-8"))}
    anchored = _rubric_anchored_case_ids()
    return sorted(
        cid for cid in case_ids
        if by_id.get(cid, {}).get("bucket") in _TEXT_UNVERIFIABLE_BUCKETS and cid not in anchored
    )


def _load_worksheet(pass_num: int) -> dict:
    path = FIXTURES_DIR / f"labeling_pass{pass_num}_worksheet.json"
    if not path.exists():
        raise SystemExit(
            f"{path.name} not found -- pass {pass_num} hasn't been done yet."
            + (" Run scripts/generate_labeling_worksheet.py --pass 2, 48h+ after pass 1." if pass_num == 2 else "")
        )
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    pass1 = _load_worksheet(1)
    pass2 = _load_worksheet(2)

    p1_by_id = {c["case_id"]: c for c in pass1["cases"]}
    p2_by_id = {c["case_id"]: c for c in pass2["cases"]}

    if p1_by_id.keys() != p2_by_id.keys():
        raise SystemExit("Case sets differ between pass 1 and pass 2 -- aborting.")

    unlabeled_1 = [cid for cid, c in p1_by_id.items() if not c.get("your_label")]
    unlabeled_2 = [cid for cid, c in p2_by_id.items() if not c.get("your_label")]
    if unlabeled_1 or unlabeled_2:
        raise SystemExit(f"Incomplete: pass 1 missing {len(unlabeled_1)}, pass 2 missing {len(unlabeled_2)}.")

    # Pick up final_label decisions from a previous run of this script, if any.
    prior_resolutions = {}
    if FROZEN_PATH.exists():
        prior = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))
        for d in prior.get("disagreements", []):
            if d.get("final_label"):
                prior_resolutions[d["case_id"]] = d["final_label"]

    total = len(p1_by_id)
    agreed = {}
    disagreements = []
    raw_agreement_count = 0
    resolved_this_pass = 0
    for case_id, c1 in p1_by_id.items():
        c2 = p2_by_id[case_id]
        if c1["your_label"] == c2["your_label"]:
            agreed[case_id] = c1["your_label"]
            raw_agreement_count += 1
            continue
        if case_id in prior_resolutions:
            agreed[case_id] = prior_resolutions[case_id]
            resolved_this_pass += 1
            continue
        disagreements.append(
            {
                "case_id": case_id,
                "pass1_label": c1["your_label"],
                "pass1_reasoning": c1["your_reasoning"],
                "pass2_label": c2["your_label"],
                "pass2_reasoning": c2["your_reasoning"],
                "final_label": None,
            }
        )

    print(f"Intra-rater agreement (raw pass1==pass2, before any manual resolution): {raw_agreement_count}/{total}")
    if resolved_this_pass:
        print(f"Manually resolved via final_label: {resolved_this_pass}")

    unanchored = unanchored_payment_claim_cases(p1_by_id.keys())
    if unanchored:
        print(f"\nCAVEAT -- text-unresolvable, no rubric anchor: {unanchored}")
        print("labeling_rubric.md names no worked example for these ALREADY_PAID_*")
        print("cases, and the rubric itself says payment status cannot be verified")
        print("by reading text. Any pass1==pass2 agreement on them is pattern")
        print("consistency, not a verified judgment -- do not read the intra-rater")
        print("number as solid for this subset.")

    frozen = len(disagreements) == 0
    out = {
        "intra_rater_agreement": f"{raw_agreement_count}/{total}",
        "ground_truth": agreed if frozen else None,
        "disagreements": disagreements,
        "unanchored_payment_claim_caveats": unanchored,
        "frozen": frozen,
    }
    FROZEN_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    if not frozen:
        print(f"\n{len(disagreements)} unresolved disagreement(s) -- see {FROZEN_PATH.name}.")
        print("Resolve each against fixtures/labeling_rubric.md, fill in \"final_label\", then re-run:")
        for d in disagreements:
            print(f"  {d['case_id']}: pass1={d['pass1_label']!r} vs pass2={d['pass2_label']!r}")
        return 1

    print(f"\nAll {total} cases resolved. Ground truth frozen: {FROZEN_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
