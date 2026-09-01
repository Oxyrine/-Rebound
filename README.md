# REBOUND

**A bounded revenue-recovery engine for failed payments.** REBOUND identifies
recovery-eligible cases and executes recovery through Razorpay Payment Links. Its
evidence layer exists to prevent recovery actions that are unsafe, unnecessary, or
inappropriate.

Razorpay AI Buildathon 2026 · Track 03 (AI Revenue Recovery) · solo submission.

> **Numbers below marked `[from run]` are placeholders** until the Day-9 evidence
> run populates them from `evidence/metrics_report.md`. Nothing in this README is
> hand-typed once that run exists — every figure traces to a file the code wrote.

---

## What it does

A `payment.failed` webhook tells you a payment failed. It cannot tell you the
customer already paid, is disputing the charge, asked you to stop, or promised to
pay Friday. REBOUND reads the unstructured, code-mixed, occasionally adversarial
customer reply attached to a recovery case and decides what to do next:

```
Failed payment event
      │
Structured pre-checks           ← no LLM: dedupe, dispute flag, identity chain
      │
Suspicious-instruction pre-screen ← no LLM: known instruction-shaped evidence
      │
   ┌──┴──┐
 RULES  LLM                       ← the experiment (§23): only this layer changes
   └──┬──┘
Typed boundary                    ← the model's entire permitted output surface
      │
Deterministic policy engine       ← §15 precedence, most conservative wins
      │
 STOP · PAUSE · REVIEW · VERIFY · RECOVER
                        │          │
                  Razorpay      Payment Link
                   status       (Test Mode)
                        │          │
                     audit + metrics
```

Structured checks run first, so the interpreter only touches residual ambiguous
text — this minimizes cost, latency, and hallucination exposure.

**Governing rule:** a value crosses from the interpreter into the engine exactly
once, through a validated schema. After that point no language model touches the
arithmetic, the amount, or the action.

---

## Results

*On the held-out evaluation fixture (22 cases). Regenerate with
`python -m scripts.run_batch --interpreter=llm --split=all --execute-links` then
`python -m scripts.generate_metrics`.*

### 1. Batch recovery funnel

```
59 cases evaluated
      → [from run] recovery-eligible
      → [from run] Payment Link attempts
      → [from run] created
      → [from run] completed
```

Completed Test Mode value: **₹[from run]** — execution proof, not commercial
impact. Test Mode transactions are dummy transactions with no real money.

### 2. Safety outcomes

```
STOPPED: [from run]   PAUSED: [from run]   HUMAN REVIEW: [from run]   NO ACTION: [from run]
```

Evidence-judgment hard-stop matrix (dispute + opt-out + multi-signal only —
already-paid cases are excluded because a deterministic API call settles them, and
including them would pad recall with wins the model did not earn):

|  | GT: hard stop | GT: no hard stop |
|---|---|---|
| System hard-stopped | [from run] | **[from run]** false stop |
| System did not hard-stop | **[from run]** missed stop | [from run] correct non-stop |

> On this held-out fixture, REBOUND identified [from run] / [from run] required
> hard stops as STOP specifically. The denominator is intentionally small (8) and
> does not establish production-level model accuracy.

### 3. Evidence interpretation — rules vs LLM (§23)

We held the fixture, policy, execution, and safety controls constant and changed
only the evidence interpreter.

| Method | Hard-stop recall | False stops | Automation rate | Human-review rate |
|---|---|---|---|---|
| Rules baseline | [from run] | [from run] | [from run] | [from run] |
| LLM semantic | [from run] | [from run] | [from run] | [from run] |

Per-case divergence — every case the two arms routed differently, with which arm
was safer and (where authored) the mechanism — is in
`evidence/metrics_report.md` and `evidence/divergence.json`. **A tie in the
aggregate counts is still a reported result:** the per-case table shows where the
two interpreters actually disagreed.

### 4. Operational reliability

```
duplicates prevented: [from run]   UNKNOWN reconciled: [from run]   quota blocks: [from run]
payment claims: verified by engine [from run] vs detected by interpreter [from run]
chaos conditions contained: 7/7 (tests/test_chaos_mock.py)
```

### 5. Adversarial probe (not a measurement)

These are two separate evidence streams, and they stay separate:

```
59-case fixture              6 red-team probes
      │                            │
quantitative evaluation      known semantic failure modes
      │                            │
 rules vs LLM                qualitative characterization
      │                            │
 divergence analysis         limitations / non-claims
      │
 AI performance evidence
```

Six hand-written cases, one per targeted semantic failure mode (indirect opt-out,
dispute buried in polite text, negated payment claim, hedged promise with no date,
multi-signal with the hard stop buried last, code-mixed sarcasm). **Not** part of
the 59-case fixture, **not** held out, labelled single-pass and unblinded.
Full report: `evidence/redteam_report.md`.

| | diverged from the author's label |
|---|---|
| Rules baseline | 5 of 6 |
| LLM semantic | 0 of 6 |

**The correct reading:** in six author-written adversarial probes targeting
specified semantic failure modes, the LLM matched the author's labels on all six
cases, while the rules baseline diverged on five. These probes are not part of the
59-case fixture, were labelled in a single unblinded pass, and establish no
accuracy claim.

Four of the six (indirect opt-out, buried dispute, multi-signal-last, sarcasm)
show a qualitative pattern worth naming: a literal/lexical reading routes toward
recovery, a contextual reading routes toward a safety-preserving stop or review.
That is evidence the semantic layer can recognise meaning a deliberately simple
lexical baseline misses — a *qualitative* complement to the quantitative
rules-vs-LLM table above, not a substitute for it.

**On the 0/6 result, left deliberately uncomfortable rather than smoothed over:**
these six probes did not expose an LLM failure. That does not establish
robustness — the probe was author-written, single-pass, and intentionally small.
No further cases were added after seeing this result: searching for a case that
makes the LLM fail, having already observed the first six did not, would turn the
probe into informal adversarial tuning and undercut the epistemic discipline this
amendment exists to demonstrate. The six are frozen.

### Confidence threshold (§25) — swept, not asserted

Swept on the development set only, frozen at **0.9** before held-out was touched
(`scripts/threshold_sweep_report.md`, `CONFIDENCE_THRESHOLD` in
`src/policy_engine.py`).

| Threshold | Automation | Recall | Precision |
|---|---|---|---|
| 0.50 | 92% | 8/9 | 8/8 |
| 0.65 | 92% | 8/9 | 8/8 |
| 0.75 | 92% | 8/9 | 8/8 |
| 0.85 | 89% | 8/9 | 8/8 |

> With ~5–7 dev hard-stop cases the sweep is coarse — a step function with a
> handful of points, not a smooth curve and not a knee. This is a model-reported
> confidence operating threshold, **not a calibrated probability threshold**.

---

## The two classes of safety

**Structural safety — deterministically containable.** Wrong field, malformed
output, wrong case ID, low confidence, duplicate event, API timeout, quota
exceeded, structured-flag contradiction. Everything in this repo addresses this
class: the typed boundary rejects an amount or an action at construction; the
precedence engine is pure; `UNIQUE(case_id)` in the audit log makes link creation
idempotent under replay; the hash-chained audit log is tamper-**evident**.

**Semantic safety — cannot be structurally eliminated.** The model misreads a
genuine dispute, misses an indirectly expressed opt-out, misinterprets ambiguous
Hinglish, or confidently returns `RECOVERY_ELIGIBLE` on a real dispute. **The
held-out evaluation is the only empirical instrument on this class**, and its
denominator is 8. The typed boundary prevents *action* injection, not
*classification* error: a well-formed `{"customer_state": "RECOVERY_ELIGIBLE",
"confidence": 0.94}` on a message that means "I dispute this charge" passes every
structural check and is still the wrong decision. The Chaos Mock proves
containment of malformed and contradicted output; it does **not** prove the system
catches every confident semantic misclassification.

Acknowledging this distinction is the honest position, and it is where a panel
should push hardest.

---

## Payment verification — "the model identifies evidence, Razorpay determines truth"

A `payment.failed` webhook can be followed by `payment.captured` for the *same*
transaction (late authorisation; a UPI retry with the correct PIN). So an
"already paid" claim is frequently literally true — and checkable, **but only
against the payment and order identifiers on this recovery case**. The interpreter
detects that a claim was made (confidence + evidence refs only — it does not
adjudicate); the engine does a deterministic status fetch against
`razorpay_context.payment_id` / `order_id`. If the claim references a *different*
identifier, it routes to human review, not a status fetch. The interpreter is
scored only on detecting the claim; whether payment occurred is the engine's call,
reported separately.

---

## Suspicious-instruction detector

A **deterministic suspicious-instruction detector** that forces human review for
known instruction-shaped evidence (role tokens like `system:`, patterns like
`ignore previous`, `set confidence`, `mark as`). It runs **before the LLM call**
and cannot be overridden by interpreter output. It is **not** "injection
prevention" — it is a unit-tested guard on known patterns: [from run] known
patterns caught, [from run] near-misses flagged. Injection is fourth in the threat
hierarchy, behind missed dispute/opt-out (the real risk), uncertain money-moving
actions, and semantically wrong output.

---

## Business positioning

REBOUND is not a startup replacing Razorpay's retry, Payment Link, or merchant
communication surfaces. It is a Razorpay-native recovery engine that sits *before*
existing recovery rails, using customer context to suppress, verify, pause, or
route risky cases before an action executes — a bounded evidence-to-policy layer
for the information those rails do not interpret.

---

## Explicit non-claims

- Not a loan recovery or debt collection system.
- Not an autonomous discount negotiator — no waivers, no settlements.
- Not an autonomous refund system. Not a card-updater.
- **Not real money** — Razorpay Test Mode only, labelled on every output surface.
- **No regulatory compliance claim.** Contact limits are merchant-configured
  product safeguards, not certified compliance.
- Subscriptions and mandates are **out of scope** — detected (`DETECTED_SCOPE_OUT`)
  and refused, not partially implemented. We verified the Test Mode constraints
  (3-day token expiry; halted-period invoices are a Dashboard-only manual action)
  and chose not to pretend to support a flow the environment cannot exercise.
- **Hinglish is tested; Tamil is not.** Tamil and other code-mixed Indian
  languages are architecturally in scope — the prompt accepts them as untrusted
  evidence — but are untested in this prototype. The fixture is Hinglish-dominant
  due to author verification constraints.
- The evaluation demonstrates architecture and failure behaviour; it does not
  establish production-level model accuracy.

---

## Why only Payment Links?

A narrow intervention surface is a choice. Most named interventions — reminder,
checkout recovery, B2B receivables, alternate-payment-method — terminate in the
same artifact, a Payment Link. The two genuinely distinct rails (subscription
retry orchestration, mandate renewal) are separate state machines and correctly
excluded. Track 03 rewards decision quality over breadth: why, when, and whether
you touch an endpoint at all. See `docs/adr/0001-payment-links-only.md`.

---

## Ground-truth labeling (§21)

```
Method:                Single-author delayed double-labeling
Intra-rater agreement: [from run] / 22
Limitation:            No independent second annotator was available. Delayed
                       relabeling measures consistency with oneself, not
                       correctness.
```

Pass 1 and pass 2 are labelled blind, 48+ hours apart, with no sight of the
model's output or the fixture's own draft labels. Where the two passes agree, that
is the frozen label; disagreements are resolved by the labeller against
`fixtures/labeling_rubric.md`, never against memory of the first pass.
`scripts/reconcile_labeling.py` produces `fixtures/heldout_ground_truth_frozen.json`.

**A second, narrower limitation, found during pass-2 review:** the rubric's own
Payment-claim section states that a labeller cannot verify payment status by
reading text — `razorpay_context` carries no status field — and compensates by
naming worked anchor cases (e.g. RCV-014 true, RCV-018 false) whose ground truth
it spells out, so the labeller pattern-matches against a taught example rather
than guessing. One held-out `ALREADY_PAID_TRUE` case, **RCV-015, has no anchor**
— and its one available textual cue reads, by the rubric's own pattern, like the
*false*-claim tell, while its authored outcome is true. `reconcile_labeling.py`
flags any such unanchored case automatically (`unanchored_payment_claim_cases()`,
derived by cross-referencing the rubric's named cases, never hardcoded) and
records it in the frozen output as `unanchored_payment_claim_caveats`: the case is
still labelled and still frozen if the two passes agree, but that agreement is
disclosed as pattern consistency, not a verified judgment.

---

## A note on this repository's own process

The locked build specification (`docs/SPEC.md`) governed the first ten tickets
while it existed only in conversation — it was committed to the repo late, and by
then the code had drifted from it: the fixture is 59 cases (not the spec's 58,
`RCV-059` was added for the promise-to-pay specificity gate), the local link cap is
28 (not 30), the policy engine has a tenth precedence rung, and the `src/` layout
was never built as drawn. The drift was caught by diffing the spec against
`scripts/manifest.py`'s output and `ls`, not by review — and it is reconciled in
`docs/SPEC.md` with dated annotations rather than silently corrected. This is the
same "don't assert consistency, check it" discipline the Chaos Mock and the typed
boundary apply, turned on the spec itself.

---

## Layout

| Path | What |
|---|---|
| `src/` | interpreters (rules, llm), typed boundary, policy engine, payment verifier, link dispatch (+ quota guard + reconcile), audit log, metrics |
| `scripts/` | `manifest.py` (constraint satisfaction, not reporting), `run_batch.py`, `run_redteam.py`, `generate_metrics.py`, `threshold_sweep.py`, labeling tools |
| `fixtures/` | 37 development + 22 held-out cases, 6 red-team probe cases (held separate), generated `manifest.json`, labeling rubric |
| `docs/` | `SPEC.md` (the locked spec + drift annotations), `adr/` (5 decision records), `agents/` |
| `tests/` | 145 tests |
| `evidence/` | run outputs (generated); `redteam_report.md` committed |

Every module corresponds to a visible demo moment, a measured output, or a
safety-critical test.

---

## Setup

Built and tested on **CPython 3.14.0 (Windows)**. Every text I/O path sets
`encoding="utf-8"` explicitly — on this interpreter
`locale.getpreferredencoding(False)` is `cp1252`, not `utf-8` (PEP 686's
UTF-8-by-default lands in 3.15). The fixture contains real Tamil and Hinglish
text; an implicit-encoding `open()` would fail on the first non-ASCII case.

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest tests/ -v
```

A live evidence run needs Razorpay Test Mode keys in `.env`
(`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`) and, for the LLM arm, `GEMINI_API_KEY`.
