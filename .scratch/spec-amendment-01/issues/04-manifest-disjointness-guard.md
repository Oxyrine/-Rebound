# 04: Manifest disjointness guard

**What to build:** The manifest generator gains a structural guarantee that red-team cases can never drift into the 59-case fixture total the way earlier categories drifted — a machine check, not a note to be careful.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] When the red-team fixture file is present, the generator asserts: red-team case ids are disjoint from development and held-out ids; every red-team case carries the redteam split marker
- [ ] The fixture total stays computed from development plus held-out only; the red-team count is reported under a separate key, never summed into the total
- [ ] Violations append to the existing error list and fail the generator loudly, the same mechanism as the existing held-out-count check
- [ ] Red-team cases are loaded on a separate path that does not run the fixed-bucket-set validation (which hard-rejects any bucket outside the evaluation set); that loader validates the identity chain and the four extra fields instead
- [ ] Absence of the file is handled gracefully: no red-team key, no error
- [ ] First manifest test file, at the manifest-generator seam: an overlapping id appends a disjointness error; a well-formed file leaves the fixture total unchanged and reports the count separately. The fixtures directory is pointed at a temporary directory via the same attribute-patching style used in the batch-runner tests
