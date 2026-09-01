# 06: Replay / idempotency regression test

**What to build:** A regression test that locks the payment-link at-most-one guarantee against the specific failure the project already hit once — a stray re-run creating a second link.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] One test asserts the replay invariant: for a fixed case and a fixed pinned audit path, running the pipeline twice never produces more than one payment-link-created event
- [x] It is a deterministic or parameterised regression test, not property-based, and is named as a replay/idempotency invariant rather than a property test unless generated inputs are actually used
- [x] It is exercised at the batch-runner CLI seam, calling the argv-injectable entry point twice against one pinned audit path. Prior art: the existing CLI-seam test that proves the entry point accepts an argv list directly, and the chaos-mock test for timeout-after-creation reconciliation
- [x] It lives in the idempotency test file the repository-structure section always claimed existed

## Answer

Resolved in commit 9aa75c2. `tests/test_idempotency.py`: `main(argv=)` called twice against one pinned audit path with a faked Razorpay client but real `AuditLog`/`run()`/`dispatch_link()`/`verify_chain()` — asserts exactly one `PAYMENT_LINK_CREATED` and one `create_payment_link` call after the replay. Second test pins the `--first-run` guard. 135 pass. (Also: gitignored generated `evidence/` run outputs — commit d4bec70.)
