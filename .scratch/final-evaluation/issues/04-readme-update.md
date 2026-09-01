# 04: README Update

Type: task
Status: resolved
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

## Answer

Done (commit 6ed3dc4). Results section rewritten as two separate claims -- routing evaluation (59/59, complete) and operational execution (10 links, rate-limited) -- never one clean funnel. Real numbers throughout, §21 13/22, injection 3/3 & 0/5, §25 reliability, red-team disclosure, spec-drift + rate-limit process notes. Wording: 'the LLM produced zero unsafe misses in the hard-stop matrix, while the rules baseline produced nine'.
