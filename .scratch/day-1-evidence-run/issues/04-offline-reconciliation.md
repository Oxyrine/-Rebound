# 04: Offline Reconciliation Phase

**What to build:** Implements the new `--reconcile-only` flow in `run_batch.py`. It reads the JSON results dictionary, queries Razorpay for link statuses, updates the completed flags in place, and overwrites the file.

**Blocked by:** 03: Creation Phase: Pacing, Results Persistence & Ground Truth Segregation

**Status:** resolved

- [x] Add the `--reconcile-only` CLI flag.
- [x] If `--reconcile-only` is provided, skip the LLM evaluation case loop entirely.
- [x] Load the existing `evidence/run_all_results.json` dictionary into memory.
- [x] Query Razorpay (via `reconcile_created_links` or equivalent logic) for the status of the generated links.
- [x] Update the `link_completed` and/or `link_status` fields for each relevant case in the loaded dictionary.
- [x] Overwrite `evidence/run_all_results.json` with the patched dictionary.
