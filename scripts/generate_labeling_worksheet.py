"""Generates a blind labeling worksheet from heldout_cases.json -- §21.
Ground-truth fields (bucket, recovery_eligible, payment_link_eligible,
requires_evidence_judgment, requires_status_verification,
pre_screen_expected, expected_outcome, authoring_method, labeling_method)
are stripped -- only what a human labeler should actually see survives:
case_id, split, customer_reply, merchant_reference_id, razorpay_context.

Pass 1 already exists (fixtures/labeling_pass1_worksheet.json). Run this
for pass 2, after pass 1 is complete and 48+ hours have elapsed:

    python3 -m scripts.generate_labeling_worksheet --pass 2

Refuses to overwrite an existing worksheet for the requested pass number.
"""

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
IST = timezone(timedelta(hours=5, minutes=30))

KEEP_FIELDS = ["case_id", "split", "customer_reply", "merchant_reference_id", "razorpay_context"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pass", type=int, required=True, dest="pass_num", choices=[1, 2])
    args = parser.parse_args()

    out_path = FIXTURES_DIR / f"labeling_pass{args.pass_num}_worksheet.json"
    if out_path.exists():
        raise SystemExit(f"{out_path.name} already exists -- refusing to overwrite. Delete it first if you mean to.")

    heldout = json.loads((FIXTURES_DIR / "heldout_cases.json").read_text(encoding="utf-8"))
    cases = []
    for case in heldout:
        stripped = {k: case[k] for k in KEEP_FIELDS}
        stripped["your_label"] = None
        stripped["your_reasoning"] = None
        cases.append(stripped)

    worksheet = {
        "instructions": (
            "Blind label. For each case, read only the fields present "
            "(customer_reply, razorpay_context, etc.) and the rubric at "
            "labeling_rubric.md. Fill your_label with one of: "
            "RECOVERY_ELIGIBLE, HARD_STOP, HUMAN_REVIEW, ALREADY_PAID_CLOSED, "
            "VERIFY_PAYMENT_STATUS, PAUSE_UNTIL_DATE. "
            + (
                "Do not look at your pass 1 answers or heldout_cases.json while doing this."
                if args.pass_num == 2
                else "Do not look at heldout_cases.json while doing this. Save, then wait 48+ hours before pass 2."
            )
        ),
        "pass": args.pass_num,
        "started_at": datetime.now(IST).isoformat(),
        "cases": cases,
    }

    out_path.write_text(json.dumps(worksheet, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path.name}: {len(cases)} cases, pass {args.pass_num}.")


if __name__ == "__main__":
    main()
