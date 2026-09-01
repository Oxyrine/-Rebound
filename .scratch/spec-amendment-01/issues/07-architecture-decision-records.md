# 07: Architecture Decision Records

**What to build:** A concise map of the project's load-bearing decisions, so a panel reading the repo can follow the reasoning without reconstructing it from the spec.

**Blocked by:** 01 — the precedence ADR must reference the reconciled tenth rung correctly, which depends on the drift reconciliation landing first.

**Status:** ready-for-agent

- [ ] Short ADRs (context, decision, consequences) created under the docs ADR directory that the domain-docs consumer rules already point at
- [ ] Topics: payment links as the sole intervention surface; the typed boundary and its stated limit (prevents action injection, not classification error); the precedence ordering; the deliberately minimal rules interpreter; the decision to report rather than fix probe failures
- [ ] The precedence ADR separates the original nine-rung design (context) from the conservative ordering decision (decision) from the tenth rung found during reconciliation (implementation note), so it does not misrepresent the tenth rung as original intent
- [ ] The report-rather-than-fix ADR states that the author chose not to improve a number they could have improved, and why that was the right call
