# 01: Commit locked spec + reconcile drift

**What to build:** The locked build specification becomes a committed file in the repo, so a reader can see the document the project was actually built against; and the drift that accumulated while it lived only in conversation is reconciled against the code in a visible, annotated way.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `docs/SPEC.md` committed verbatim as supplied, in its own commit, with no edits
- [ ] Before that commit, the text is confirmed to be the final locked version via the late-revision markers named in the spec: thesis moved to the close, recovery-first evidence ordering, the reason-code-lookup rejection, the two-safety-classes framing superseding "four safeties", the identity chain marked mandatory, the two-arm table with every cell still a placeholder, the invented-numbers list
- [ ] A second commit reconciles known drift; each correction carries an inline dated annotation naming what the spec said, what the code does, and which is authoritative
- [ ] Drift items covered as a starting list: fixture size (59 / 37 development), benign bucket count (24), payment-link cap (28), the tenth precedence rung (evidence-refs-missing), the flat `src/` layout with no interpreters subpackage or standalone quota-guard / reconciliation / templates modules, and the typed-boundary example referencing a stop-signal string outside the frozen vocabulary
- [ ] A third commit corrects the repository-structure section to describe the repo as built, with a one-line note on where each originally-planned module's responsibility landed
- [ ] Every count in `docs/SPEC.md` agrees with the manifest generator's output, which is the authority
- [ ] Post-closure additions and drift-reconciliation corrections use visibly distinct annotation markers
- [ ] Sections downstream of any corrected count (the bucket table, the funnel line, the video script) are updated to match
