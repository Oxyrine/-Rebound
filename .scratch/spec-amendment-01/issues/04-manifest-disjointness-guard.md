# 04: Manifest disjointness guard

**What to build:** The manifest generator gains a structural guarantee that red-team cases can never drift into the 59-case fixture total the way earlier categories drifted — a machine check, not a note to be careful.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] When the red-team fixture file is present, the generator asserts: red-team case ids are disjoint from development and held-out ids; every red-team case carries the redteam split marker
- [x] The fixture total stays computed from development plus held-out only; the red-team count is reported under a separate key, never summed into the total
- [x] Violations append to the existing error list and fail the generator loudly, the same mechanism as the existing held-out-count check
- [x] Red-team cases are loaded on a separate path that does not run the fixed-bucket-set validation (which hard-rejects any bucket outside the evaluation set); that loader validates the identity chain and the four extra fields instead
- [x] Absence of the file is handled gracefully: no red-team key, no error
- [x] First manifest test file, at the manifest-generator seam: an overlapping id appends a disjointness error; a well-formed file leaves the fixture total unchanged and reports the count separately. The fixtures directory is pointed at a temporary directory via the same attribute-patching style used in the batch-runner tests

## Answer

Resolved in commit e17575e. `scripts/manifest.py` gains `load_redteam_cases()` + `validate_redteam_case_shape()` + a disjointness block in `build_manifest()`; `redteam_cases` / `redteam_failure_modes` keys added, never summed into `total_cases`. `tests/test_manifest.py` (6 cases, first manifest test file). `fixtures/manifest.json` regenerated. 133 pass.
