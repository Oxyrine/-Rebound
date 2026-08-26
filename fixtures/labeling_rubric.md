# Labeling Rubric

Governs delayed self-relabeling (§21): label pass 1 now, wait 48+ hours, relabel pass 2 blind (no sight of pass 1 labels or model output), compare, resolve every disagreement against this document — never against memory of the first pass. Report intra-rater agreement as `__/22` on the held-out set.

Every rule below is anchored to real fixture cases, not invented examples, so a labeler can check their reading against a concrete instance.

## Explicit opt-out

Customer directly asks to stop being contacted — "don't message me," "remove my number," "not interested," stated as a request about future contact, not just annoyance at being contacted once. Anchors: RCV-011 ("Please don't contact me"), RCV-012 ("Please remove my number. Don't message me."), RCV-013 ("I'm not interested in your product" — final word, after already having complained to a manager). All three are HARD_STOP.

Frustration alone ("why do you keep messaging me") without a stop request is not opt-out — it's a candidate for AMBIGUOUS or DISPUTE depending on what else is said.

## Dispute / refund

Customer says the charge itself is wrong: wrong item, damaged item, unauthorized, wants it reversed. Anchors: RCV-004 ("This is not what I ordered... Please take it back"), RCV-005 ("charge pathi already complaint pannitten" — already filed a complaint about the charge), RCV-006 ("item... damaged... I want to refund this"). All HARD_STOP.

Distinguish from a payment claim: a dispute says the charge is *wrong*; a payment claim says the charge already *succeeded*. A message can be both (multi-signal) — see precedence below.

## Payment claim (already-paid)

Customer asserts they already paid — a factual claim, verifiable against `razorpay_context.payment_id` / `order_id` for *this* case only (§16). Split into two labeling outcomes, not one:

- **True claims** (verification will find it captured): RCV-016, RCV-017, RCV-014 — all confident, specific ("I have already paid this yesterday itself... check your records"). Ground truth: `ALREADY_PAID_CLOSED`.
- **False claims** (verification will find it unpaid/pending, or the claim references a different invoice): RCV-019, RCV-018 — same confident tone, but RCV-018 goes on to volunteer an invoice number ("It's 5 3 6 5 1 2") that a real system would check against *this* case's identifiers. Ground truth: `HUMAN_REVIEW`, not `ALREADY_PAID_CLOSED` — a claim alone never closes a case; only a verified status does (§16's core rule: *"the model identifies evidence, Razorpay determines truth"*).

A labeler cannot verify payment status by reading text — that's what makes this bucket about the *interpreter's* job (flag the claim) rather than the *labeler's* job (decide if it's true). Label the claim as present; `expected_outcome` already encodes the verification result from fixture authoring.

## Promise-to-pay (specificity gate)

A promise counts as **dated** — and pauses contact until that date — only if it names a specific day-of-week, calendar date, or a clearly bounded near-term window (e.g. "by tomorrow evening"). Relative or vague terms — "soon," "later," "this week" with no day named — do **not** qualify; recovery continues.

- Dated, pauses: RCV-022 ("...by Friday...", `PAUSE_UNTIL_DATE`), RCV-059 ("will pay you on Thursday for sure", `PAUSE_UNTIL_DATE` — added deliberately as the isolated single-signal proof case; RCV-022 alone was multi-signal and couldn't distinguish this rule from "only pauses in combination").
- Vague, does not pause: RCV-045 ("sure will pay soon"), RCV-054 ("will pay by evening") — both stay `RECOVERY_ELIGIBLE`.

This is the boundary most likely to drift across the 48-hour gap. If a message is genuinely ambiguous about specificity (e.g. "by tonight" — same-day, but does name a bound), default to **not dated** — the gate favors continuing recovery over pausing on a promise that isn't verifiable, consistent with the project not being a debt-collection system that leans on soft promises.

## Ambiguity requiring review

Message doesn't resolve to any of the above even after reading it in full — no stop signal, no clear payment claim, no dated promise, but also not clearly benign. Anchors: RCV-034, RCV-035, RCV-032 — all Tamil replies that defer or stall ("I'll figure it out," "wait a bit, I'll tell you myself") without stating a position. Ground truth: `HUMAN_REVIEW` in every case in this bucket. If in doubt whether something is ambiguous vs. one of the named categories above, ambiguous is the conservative default — it costs a review, not a wrong stop or a wrong recovery.

## Support notes vs. customer text

Support notes are additional evidence, not an override authority. They don't unconditionally beat customer text either direction — they feed into the same precedence rule below like any other signal. If a support note surfaces a *more* conservative signal than the customer's own words (e.g. customer text reads as a plain payment claim, but a support note says the call was about a duplicate-charge dispute — the exact combination in the spec's own §12 example), the more conservative signal wins, same as it would if the customer had said it directly. A support note never downgrades a stop signal already present in customer text.

## Multi-signal precedence

When a case carries more than one signal, apply the precedence table (§15) as written: the **earliest-listed** signal that is present wins, regardless of what else is also true of the message. Do not average, do not pick the "main" signal by feel — take the first match, top to bottom:

`MALFORMED_OR_DUPLICATE → VERIFIED_PAYMENT_STATUS → EXPLICIT_OPT_OUT → DISPUTE_OR_REFUND → SUSPICIOUS_INSTRUCTION → LOW_CONFIDENCE → AMBIGUOUS/CONFLICTING → PROMISE_TO_PAY → RECOVERY_ELIGIBLE`

Worked example: RCV-022 contains both a dated promise ("by Friday") and near-miss instruction-shaped wording ("ignore my last message"). The instruction-shaped wording does **not** match the deterministic pre-screen (`pre_screen_expected: false` — it says "last message," not "previous"/"prior," so Layer 1 correctly stays silent per §19's pinned regex specificity). With no `SUSPICIOUS_INSTRUCTION` match, the next applicable rung is `PROMISE_TO_PAY` → `PAUSE_UNTIL_DATE`. This is why the rule is "first matching rung," not "most severe-sounding text" — the near-miss wording never becomes a signal at all here, because it never actually matches the deterministic pattern.

By construction, this ordering is always at least as conservative as any single signal taken alone, because stop/dispute/opt-out sit above pause/recover in the table.
