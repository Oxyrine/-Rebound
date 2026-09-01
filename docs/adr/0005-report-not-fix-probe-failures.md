# ADR 0005: The red-team probe reports failures; it does not fix them

Status: accepted · 2026-09-01 · relates to SPEC.md §8, §22, §32; spec-amendment-01

## Context

SPEC.md §8 names confident semantic misclassification — the interpreter returning a valid,
well-formed output that is simply the wrong reading — as the one risk class no schema,
regex, or audit chain contains. The held-out evaluation is the only instrument on it, and
its relevant denominator is 8. spec-amendment-01 adds a second instrument: a small set of
hand-written adversarial cases (`fixtures/redteam_cases.json`) that deliberately attack the
interpreter's reading comprehension — indirect opt-outs, disputes buried in polite text,
negated payment claims, code-mixed sarcasm.

## Decision

When a red-team case makes the interpreter fail, the failure is **reported, not fixed**.
The interpreter, the prompt, the policy engine and every frozen threshold stay unchanged in
response to red-team results. `evidence/redteam_report.md` leads with a disclosure block —
author-written, single-pass, unblinded, establishes no accuracy claim, not part of the
fixture, not held out — and names which cases each arm got wrong.

## Rationale

Tuning the interpreter against the probe would turn the probe into a training set and
destroy its value as an independent instrument. The honest artifact is "here is what the
system does not catch, with examples," not a number massaged upward. A panel reading the
repo sees a decision *not* to improve a metric that could have been improved — which is the
point.

## Consequences

- The probe is structurally self-graded homework (same author writes and labels the cases),
  which is exactly what the blind double-labeling protocol (§21) exists to avoid. Its
  legitimacy rests entirely on being demoted to "probe, not measurement" loudly and
  repeatedly — in the report, in its own README section, and spoken aloud in the video.
- Raw counts only; no percentages, no recall or precision language.
- If the probe surfaces a fix worth making, it is logged for after the evaluation phase,
  never applied during it.
