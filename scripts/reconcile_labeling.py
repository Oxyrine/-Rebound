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

Run: python3 -m scripts.reconcile_labeling
"""

import json
import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
FROZEN_PATH = FIXTURES_DIR / "heldout_ground_truth_frozen.json"


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

    frozen = len(disagreements) == 0
    out = {
        "intra_rater_agreement": f"{raw_agreement_count}/{total}",
        "ground_truth": agreed if frozen else None,
        "disagreements": disagreements,
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
