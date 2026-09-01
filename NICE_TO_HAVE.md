# NICE_TO_HAVE

Enhancements considered for REBOUND and deliberately declined, with reasons. The scope
boundary is a decision, not an omission — this file is the record of it.

## Declined

| Enhancement | Why not |
|---|---|
| **Latency / token-cost metrics per case** | Not Track 03's bar (measured recovery, escalation, stopping rules, audit trail). Adds instrumentation surface for a number the panel did not ask for. The "interpreter only touches residual ambiguous text" claim (§11) is worth quantifying — how many cases actually reached the LLM — but that is one line in the metrics report, not a metrics subsystem. |
| **Manual-review simulation** | Would produce another self-graded number with no independent signal, and sitting it next to the red-team probe dilutes that probe's honesty (see ADR 0005). |
| **HTML dashboard** | Contradicts SPEC.md §27's explicit cut: "console output + one plain HTML table." Highest effort, lowest necessity — the numbers are the deliverable, not the chrome. |
| **Automated README generation** | Too much infrastructure for the submission window. The manual check — grep each number in the README, confirm it appears in an `evidence/` file the code wrote — satisfies §31's traceability requirement at a fraction of the cost. |
| **Playwright checkout automation** | Already cut in §27. Automating mock-bank clicks is plumbing validation, not recovery. One manual checkout in the video. |

## Stretch items (spec-amendment-01 ticket 09) — do only on genuine slack

These are real improvements, not declined on merit — declined only if time runs out.
They are never a dependency of the core divergence analysis (ticket 02).

- **Divergence taxonomy** — a `divergence_type` label (`lexical_gap` / `semantic_composition`
  / `ambiguity_resolution`) on each row of the rules-vs-LLM divergence table. Deepens the
  §23 narrative from *what* diverged to *why*.
- **Confidence reliability check** — compare reported confidence buckets with observed
  correctness on the development set, to show *why* 0.9 is a review boundary rather than a
  probability. Named explicitly as **not** a formal calibration assessment (§25 already
  carries that disclosure honestly; this only sharpens it). Plain text table or a single
  matplotlib PNG — no new charting dependency.

If either is not reached, it stays here, declined for time, not for merit.
