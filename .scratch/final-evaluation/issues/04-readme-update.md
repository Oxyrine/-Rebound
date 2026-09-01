# 04: README Update

Type: task
Status: in-progress (draft done, numbers blocked on 03)
Blocked by: 03

**What to build:** 
The project's public `README.md` fully populated with the final, official performance numbers from the evidence run, pulling out the framings, disclosures, and module justifications distinct from the execution steps themselves.

**Blocked by:** 
03-final-evidence-run.md

- [ ] Extract real numbers from `evidence/metrics_report.md`
- [ ] Populate `README.md` with final numbers, framings, and disclosures

## Progress

`README.md` fully drafted (commit 445e0d4) to the §29 structure: recovery funnel first, safety second, rules-vs-LLM third, operational fourth, red-team probe fifth (fenced, with its disclosure). Two safety classes, "model identifies evidence / Razorpay determines truth", non-claims, why-only-Payment-Links, §21 method + limitation, §25 table (real dev numbers — already frozen), and the spec-drift methodology note.

Every metric is a `[from run]` placeholder except §25. Completing this ticket = substitute numbers from `evidence/metrics_report.md` once ticket 03 produces it. Also carries: the ticket-05 open question (LLM 0/6 on the red-team probe — ship the contrast, or add hand-written cases).
