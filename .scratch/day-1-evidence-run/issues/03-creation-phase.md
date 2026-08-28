# 03: Creation Phase: Pacing, Results Persistence & Ground Truth Segregation

**What to build:** Modifies the primary run of `run_batch.py` to pause 1s between LLM calls, strips out inline reconciliation, and saves all outputs as a dictionary to `evidence/run_all_results.json`. Also adds the `_frozen_ground_truth(split)` helper and attaches both the pass-2 frozen label (`gt_hard_stop`) and the day-1 label (`fixture_expected_outcome`) to each case in the results.

**Blocked by:** None (can start immediately).

**Status:** resolved

- [x] Add `time.sleep(1)` inside the LLM evaluation loop in `run_batch.py`.
- [x] Remove any inline reconciliation (checking link status immediately) during the creation run.
- [x] Add `_frozen_ground_truth(split)` to load frozen labels.
- [x] Modify the loop to attach both `gt_hard_stop` (frozen) and `fixture_expected_outcome` (day-1) to the case result object.
- [x] Accumulate case results into a dictionary keyed by `case_id` and persist it to `evidence/run_all_results.json` at the end of the run.
