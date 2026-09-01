"""spec-amendment-01 ticket 05: the adversarial red-team probe runner.

Runs fixtures/redteam_cases.json through both interpreter arms and writes a
report whose disclosure block is the first content in the file. This is a
PROBE, not a measurement: the cases are author-written, single-pass,
unblinded, held outside the 59-case fixture, and establish no accuracy
claim. Failures are reported as found (ADR 0005).

Deliberately a separate entry point, never a --split value on run_batch:
link execution is hard-wired off here and not exposed as a flag, so a
stray argument can never turn this into the incident run_batch.py's header
documents (a fall-through that created real Payment Links for real
DISPUTE_REFUND / OPT_OUT cases).

    python -m scripts.run_redteam
"""

import json
import sys
from collections import Counter
from pathlib import Path

from scripts.run_batch import _get_interpreter, _ROUTE_TO_OUTCOME
from scripts.run_batch import run as run_arm
from src.audit_log import AuditLog
from src.razorpay_client import RazorpayClient

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
EVIDENCE_DIR = Path("evidence")

ARMS = ("rules", "llm")

_DISCLOSURE = (
    "> **Disclosure — read before any result below.**\n"
    "> These cases are adversarial probes authored by the system's own author,\n"
    "> single-pass labelled with no blind protocol. They are **not** part of the\n"
    "> 59-case evaluation fixture, **not** held out, and establish **no accuracy\n"
    "> claim**. They exist to characterise known semantic failure modes of the\n"
    "> interpreter; failures are reported as found and are not fixed in response\n"
    "> (ADR 0005). Raw counts only — no percentages, no recall/precision.\n"
)


def _load_cases():
    path = FIXTURES_DIR / "redteam_cases.json"
    if not path.exists():
        sys.exit(f"{path} not found — author the cases first (spec-amendment-01 ticket 03).")
    return json.loads(path.read_text(encoding="utf-8"))


def _outcome(result: dict) -> str:
    """The 6-way outcome an arm's route resolves to for this case."""
    if result["route"] == "VERIFY":
        return result.get("resolved_outcome") or "VERIFY_PAYMENT_STATUS"
    return _ROUTE_TO_OUTCOME.get(result["route"], result["route"])


def run_probe(cases, client) -> dict:
    """Run every case through both arms. Link execution is off, structurally.
    Returns {arm: {case_id: result}}."""
    out = {}
    for arm in ARMS:
        interpret = _get_interpreter(arm)
        log = AuditLog(Path(f"scratch_redteam_{arm}.jsonl"))
        results = run_arm(
            [dict(c) for c in cases], interpret, log, client,
            gt_map={}, execute_links=False, is_llm=(arm == "llm"),
        )
        out[arm] = {r["case_id"]: r for r in results}
    return out


def format_report(cases, arms: dict) -> str:
    by_id = {c["case_id"]: c for c in cases}
    lines = ["# Red-team adversarial probe", "", _DISCLOSURE, "",
             f"{len(cases)} cases. Link execution: disabled (this runner cannot create a link).", "",
             "## Per case", "",
             "| case | failure mode | intended | rules → | rules | llm → | llm |",
             "|---|---|---|---|---|---|---|"]
    diverged = {arm: [] for arm in ARMS}
    for cid, case in by_id.items():
        intended = case["expected_outcome"]
        row = [cid, case.get("failure_mode", "?"), intended]
        for arm in ARMS:
            got = _outcome(arms[arm][cid])
            match = "matches" if got == intended else "**diverges**"
            row += [got, match]
            if got != intended:
                diverged[arm].append((cid, case.get("failure_mode", "?"), intended, got))
        lines.append("| " + " | ".join(row) + " |")

    lines += ["", "## Where each arm diverged from the intended label", ""]
    for arm in ARMS:
        d = diverged[arm]
        lines.append(f"**{arm}** — {len(d)} of {len(cases)} diverged"
                     + (":" if d else "."))
        for cid, mode, intended, got in d:
            lines.append(f"- {cid} ({mode}): intended {intended}, got {got}")
        lines.append("")

    lines += ["## By failure mode", "",
              "| failure mode | rules diverged | llm diverged |", "|---|---|---|"]
    modes = list(dict.fromkeys(c.get("failure_mode", "?") for c in cases))
    for mode in modes:
        ids = [c["case_id"] for c in cases if c.get("failure_mode") == mode]
        counts = []
        for arm in ARMS:
            n = sum(1 for cid in ids if _outcome(arms[arm][cid]) != by_id[cid]["expected_outcome"])
            counts.append(f"{n}/{len(ids)}")
        lines.append(f"| {mode} | {counts[0]} | {counts[1]} |")
    return "\n".join(lines) + "\n"


def main():
    cases = _load_cases()
    client = RazorpayClient()
    arms = run_probe(cases, client)

    EVIDENCE_DIR.mkdir(exist_ok=True)
    for arm in ARMS:
        (EVIDENCE_DIR / f"redteam_results_{arm}.json").write_text(
            json.dumps(arms[arm], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    report_path = EVIDENCE_DIR / "redteam_report.md"
    report_path.write_text(format_report(cases, arms), encoding="utf-8")
    print(f"Wrote {report_path} ({len(cases)} cases, both arms, no links created)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
