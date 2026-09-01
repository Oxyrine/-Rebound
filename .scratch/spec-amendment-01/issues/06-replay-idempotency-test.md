# 06: Replay / idempotency regression test

**What to build:** A regression test that locks the payment-link at-most-one guarantee against the specific failure the project already hit once — a stray re-run creating a second link.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] One test asserts the replay invariant: for a fixed case and a fixed pinned audit path, running the pipeline twice never produces more than one payment-link-created event
- [ ] It is a deterministic or parameterised regression test, not property-based, and is named as a replay/idempotency invariant rather than a property test unless generated inputs are actually used
- [ ] It is exercised at the batch-runner CLI seam, calling the argv-injectable entry point twice against one pinned audit path. Prior art: the existing CLI-seam test that proves the entry point accepts an argv list directly, and the chaos-mock test for timeout-after-creation reconciliation
- [ ] It lives in the idempotency test file the repository-structure section always claimed existed
