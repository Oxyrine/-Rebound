# 02: CLI Idempotency Guards

**What to build:** Safe execution boundaries in `run_batch.py` that prevent accidental quota burn or evidence overwrites. Implements the `--audit-path` and `--first-run` flags and their hard-fail logic.

**Blocked by:** 01: CLI Testability Seam

**Status:** resolved

- [x] Add `--audit-path` flag to CLI. Enforce that it is required if `--execute-links` is used.
- [x] Add `--first-run` flag to CLI. Enforce that if `--audit-path` doesn't exist, `--first-run` must be present.
- [x] Enforce that if `--first-run` is passed but the audit log file *already* exists, the script hard-fails (e.g. `SystemExit`) to prevent accidental overwrite/append.
- [x] Write unit tests using the `main(argv=...)` seam from Ticket 01 to verify these flag interactions.
