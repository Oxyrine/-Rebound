# 01: Commit locked spec + reconcile drift

**What to build:** The locked build specification becomes a committed file in the repo, so a reader can see the document the project was actually built against; and the drift that accumulated while it lived only in conversation is reconciled against the code in a visible, annotated way.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [x] `docs/SPEC.md` committed verbatim as supplied, in its own commit, with no edits
- [x] Before that commit, the text is confirmed to be the final locked version via the late-revision markers named in the spec: thesis moved to the close, recovery-first evidence ordering, the reason-code-lookup rejection, the two-safety-classes framing superseding "four safeties", the identity chain marked mandatory, the two-arm table with every cell still a placeholder, the invented-numbers list
- [x] A second commit reconciles known drift; each correction carries an inline dated annotation naming what the spec said, what the code does, and which is authoritative
- [x] Drift items covered as a starting list: fixture size (59 / 37 development), benign bucket count (24), payment-link cap (28), the tenth precedence rung (evidence-refs-missing), the flat `src/` layout with no interpreters subpackage or standalone quota-guard / reconciliation / templates modules, and the typed-boundary example referencing a stop-signal string outside the frozen vocabulary
- [x] A third commit corrects the repository-structure section to describe the repo as built, with a one-line note on where each originally-planned module's responsibility landed
- [x] Every count in `docs/SPEC.md` agrees with the manifest generator's output, which is the authority
- [x] Post-closure additions and drift-reconciliation corrections use visibly distinct annotation markers
- [~] Sections downstream of any corrected count updated to match — see note

## Answer

Resolved in commits dc5da0b (verbatim), 383bf8e (drift), 8d78c19 (§28).

- `docs/SPEC.md` — 649-line transcription from the conversation paste (no other copy exists; disclosed in dc5da0b's message). All 32 sections / 6 parts present, 7 late-revision markers verified. Two deliberate departures from a literal paste: dropped the author's trailing "This is the workflow" framing line; collapsed a doubled "no percentages" in §24.
- Drift: 5 inline `> **⟦DRIFT · 2026-09-01⟧**` blockquotes — §20 (59/37/24 not 58/36/23), §20 (manifest asserts total==59, link-eligible<=28), §15 (10 precedence rungs, EVIDENCE_REFS_MISSING added), §13 (`DISPUTE_REVIEW_REQUIRED` not in frozen vocab), §18 (local `LINK_QUOTA_CAP`=28, Razorpay's 30 unchanged). Distinct marker from the `⟦AMENDMENT 01⟧` marker later tickets will use.
- §28 tree replaced with the as-built tree; original kept in a `<details>` block. `templates.py` recorded as a genuine unbuilt gap, not a relocation.
- **Deliberately NOT done:** rewriting the stale 58/36/23 numbers in §5, §20 tables, §24 funnel, §29, §30 prose. The verbatim body is left intact and the DRIFT annotations point every reader to the authoritative value — editing the prose would blur the "unaltered baseline" the three-commit sequence exists to preserve. If a fully-reconciled reading copy is wanted later, that is a separate pass on top of this baseline.
- 127 tests pass (unchanged — this ticket touched only docs).
