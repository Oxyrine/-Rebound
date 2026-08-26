"""Append-only, tamper-evident audit log.

Not tamper-*proof*. Three failure modes, named rather than hidden:

1. No key, no external anchor. Any suffix of the file can be rewritten
   with recomputed hashes and will verify clean (see
   test_suffix_rewrite_is_not_detectable). A cheap future anchor is
   pinning the tip hash into a git-tracked file; not built here because
   there is no real chain to anchor until the Day 9 batch run.
2. No fsync. A crash between append() returning and the OS flushing the
   write loses the last record entirely. This is losing a record, not
   corrupting one — the chain that remains still verifies clean, so
   verification cannot detect that it happened.
3. Single-writer, no locking. Concurrent appends from two processes can
   interleave.

Every record is hashed in full (minus its own entry_hash), not over an
enumerated field list, so an added top-level key can't sneak past
verification unhashed.
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

GENESIS_PREV_HASH = "0" * 64


def _hash(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "entry_hash"}
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class AuditLog:
    def __init__(self, path):
        self.path = Path(path)

    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def append(self, case_id: str, event_type: str, payload: dict, timestamp=None) -> dict:
        # ponytail: re-reads the file to find the tip on every call, O(n^2)
        # over a batch. Trivial at fixture scale (hundreds of records); a
        # cached tip would go stale the moment a second writer opens this
        # path, which is the same single-writer ceiling as the file itself.
        existing = self.records()
        seq = len(existing)
        prev_hash = existing[-1]["entry_hash"] if existing else GENESIS_PREV_HASH

        record = {
            "seq": seq,
            "timestamp": timestamp or datetime.now().astimezone().isoformat(),
            "case_id": case_id,
            "event_type": event_type,
            "payload": payload,
            "prev_hash": prev_hash,
        }
        record["entry_hash"] = _hash(record)

        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record


def verify_chain(path) -> tuple[bool, list[str]]:
    problems = []
    path = Path(path)
    if not path.exists():
        return True, problems

    with open(path, encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]

    prev_hash = GENESIS_PREV_HASH
    for i, line in enumerate(lines):
        try:
            rec = json.loads(line)
            seq, entry_hash, rec_prev_hash = rec["seq"], rec["entry_hash"], rec["prev_hash"]
        except (json.JSONDecodeError, KeyError) as e:
            problems.append(f"line {i}: unreadable record ({type(e).__name__})")
            prev_hash = None
            continue

        if seq != i:
            problems.append(f"seq {i}: seq field says {seq}")
        if rec_prev_hash != prev_hash:
            problems.append(f"seq {i}: prev_hash does not match preceding entry")
        if entry_hash != _hash(rec):
            problems.append(f"seq {i}: entry_hash mismatch")

        prev_hash = entry_hash

    return not problems, problems


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "verify":
        print("usage: python -m src.audit_log verify <path>", file=sys.stderr)
        raise SystemExit(2)

    ok, problems = verify_chain(sys.argv[2])
    for p in problems:
        print(p)
    print("OK" if ok else f"TAMPERED ({len(problems)} problem(s))")
    raise SystemExit(0 if ok else 1)
