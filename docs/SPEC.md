# REBOUND — Locked Build Specification
**A Bounded Revenue-Recovery Engine for Razorpay Merchants**
Razorpay AI Buildathon 2026 · Track 03 (AI Revenue Recovery)
Deadline **Saturday September 5, 2026** · Today **Tuesday August 25, 2026** · **11 days**
> Status: **specification closed.** Eight review passes, three independent critics, full convergence on architecture, positioning, scope, and the single open empirical question. Build against this document. Do not reopen it.
---
# PART I — CONTEXT
## 1. What this competition is
Not a hackathon with a prize. A hiring pipeline for a paid **AI Builder Internship**.
| | |
|---|---|
| Stipend | ₹75,000/month |
| Duration | 6 or 12 months, your choice |
| Location | In-person, Bangalore, from September |
| Eligibility | Students only |
| Deliverables | Public GitHub repo + 5-minute pitch video + architecture |
| Process | No resume screen, no aptitude test, no GD. Submit → if it shows signal → **panel interview** |
| Deadline | September 5, 2026 (a Saturday) |
| Tracks | 01 Growth & Agentic Commerce · 02 Risk Manager · 03 Revenue Recovery · 04 Finance Controller · 05 Open Track |
Three consequences:
1. **Solo.** No team submission mechanic. Peers are competing applicants.
2. **It ends in a panel reading your code.** The repo is the primary artifact; every file is defensible surface area.
3. **The internship is full-time, in-person Bangalore, from September.** Winning means a semester off or declining. Decide going in — the repo is a permanent portfolio asset either way.
## 2. Track 03's published bar
> "Find revenue that's slipping away and win it back. Build an agent that detects revenue at risk, determines the right intervention, and executes a bounded recovery workflow: from payment failures and checkout abandonment to overdue receivables."
>
> **The bar:** "Don't just identify the problem. Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail."
**No 50+ record requirement on Track 03** — that belongs to Track 04. The 58-case fixture is self-imposed, sized purely for metric validity.
**Note on track fit:** three of the four things Track 03's bar names — escalation, stopping rules, audit trail — *are* the safety architecture. REBOUND's safety emphasis is not drift toward Track 02. Track 02's bar is a detector/verifier/auto-responder for **one class of loss** with precision and recall on held-out data; REBOUND detects no fraud, scores no loss, responds to no chargeback. The risk was never track fit — it was *narrative*, and §5 fixes it.
The four axes cited in some secondary sources ("Problem Taste, Build Quality, AI Judgment, Failure Recovery") are **not on Razorpay's official page**. Do not architect the video around them as if published.
---
# PART II — THE IDEA
## 3. Positioning — the first thing anyone reads or hears
> **REBOUND is a bounded revenue-recovery engine for failed payments. It identifies recovery-eligible cases and executes recovery through Razorpay Payment Links; its evidence layer exists to prevent recovery actions that are unsafe, unnecessary, or inappropriate.**
Hierarchy, in this order:
| Layer | Statement |
|---|---|
| **Product** | Revenue recovery |
| **Mechanism** | Bounded Payment Link execution |
| **Differentiator** | Evidence interpretation |
| **Safety property** | Inappropriate recovery is suppressed |
| **Thesis** | Knowing when not to act |
## 4. Thesis — the closing line, not the opening frame
> **The most valuable recovery action is sometimes knowing when not to act.**
Said at 0:05 it is a claim. Said at 4:50 — after the panel has watched a verified already-paid case close silently, a promise-to-pay pause, an injection-forced review, a successful recovery, and a timeout reconcile — it is a conclusion they have already reached themselves.
Keep it. Move it to the end.
## 5. Recovery is primary; safety is the qualifier
The architecture stays exactly as designed. What changes is **evidence ordering**, everywhere:
- **Video:** recovery case first, safety second, architecture third, thesis last.
- **README metrics:** batch recovery funnel first, safety outcomes second.
- **Never lead with a rupee figure.** Lead with the **funnel**:
```
58 cases evaluated
      ↓
N recovery-eligible
      ↓
N Payment Link attempts
      ↓
N created
      ↓
N completed
```
Completed Test Mode value appears **inside** the funnel as a labeled secondary measurement, never as a headline. "₹8,000 recovered" invites *"so you recovered eight thousand rupees of fake money?"* The funnel is an operational result; the rupee figure is execution proof, not commercial impact. Razorpay's own docs describe Test Mode as dummy transactions with no real money.
## 6. Why the original framing was rejected
Version one had the AI classify `payment.failed` webhooks into reason codes. Razorpay's payload **already ships** `error_code`, `error_description`, `error_source`, `error_step`, `error_reason` as structured fields, and Razorpay publishes a public table mapping each code to its reason and recommended next step. That is a dictionary lookup — presented to the people who wrote the taxonomy.
The reframe: reading unstructured, code-mixed, adversarial-capable customer text to detect dispute / opt-out / already-paid / promise-to-pay signals. And the task is not keyword detection but **semantic evidence composition**. Given:
> *"bhai maine kal hi pay kiya tha, bank statement bheju kya? Ye invoice wala hai ya dusra?"*
The job is not spotting the word *paid*. It is determining: is this a payment claim · which invoice does it reference · is the customer disputing the charge · does the support note change the interpretation · is a *different* invoice being referenced · is the signal sufficient to trigger deterministic verification.
This also reclaims Track 03's "Hinglish" direction safely: REBOUND *reads* Hinglish to decide when to stay silent. It never *speaks* it to pressure anyone.
## 7. Explicit non-claims — README section, video close
- Not a loan recovery or debt collection system
- Not an autonomous discount negotiator; no waivers, no settlements
- Not an autonomous refund system
- Not a card-updater
- Not real money — Razorpay **Test Mode** only, labeled on every screen
- **No regulatory compliance claim.** Contact limits are merchant-configured product safeguards, not certified compliance. RBI's recovery-agent rules primarily govern loan/borrower dues, not general merchant payment recovery. Quoting Track 03's own use of "compliant" is fine; describing your own system that way is not.
- Subscriptions and mandates are **out of scope** (§13)
- Hinglish is tested; Tamil is not (§17)
- The audit chain is tamper-**evident**, not immutable
- The Chaos Mock proves structural containment, **not** semantic correctness (§22)
- The evaluation demonstrates architecture and failure behavior; it does not establish production-level model accuracy
## 8. The two classes of safety — architecture doc, verbatim
This supersedes the earlier "four safeties" framing and is the sharpest thing to come out of review.
**Structural safety — deterministically containable:**
wrong field · malformed output · wrong case ID · low confidence · duplicate event · API timeout · quota exceeded · structured-flag contradiction
**Semantic safety — cannot be structurally eliminated:**
model misreads a genuine dispute · misses an indirectly expressed opt-out · misinterprets ambiguous Hinglish · confidently returns `RECOVERY_ELIGIBLE` on a real dispute
Everything in the repo addresses the first class. **The held-out evaluation is the only empirical instrument you have on the second.** State this plainly — acknowledging it strengthens the project. A panel will test exactly this distinction.
---
# PART III — ARCHITECTURE
## 9. Business positioning — one README section, ~30 seconds of video, then stop
> REBOUND is not a startup replacing Razorpay's retry, Payment Link, or merchant communication surfaces. It is a **Razorpay-native recovery engine** that sits before existing recovery rails, using customer context to suppress, verify, pause, or route risky cases before an action executes.
>
> Razorpay owns payment state and recovery rails. REBOUND adds a bounded evidence-to-policy layer for the information those rails do not interpret — customer replies, support context, opt-outs, disputes, and already-paid claims.
No market sizing, no pricing, no contact-rate estimates, no competitor analysis, no adoption claims. If asked what fraction of failed payments carry customer text: *"we don't know; the fixture assumes a minority, which is why most cases are benign."*
## 10. The "why only Payment Links?" answer — 30 seconds, rehearsed
Narrow intervention surface is a **choice**, not a concession:
1. **Most named interventions aren't independent.** Reminder, checkout recovery, and B2B receivables all terminate in the same artifact — a Payment Link. Alternate-payment-method is a Payment Link with different copy. Six labels, largely one rail. A panel that builds this will see that.
2. **The two genuinely distinct rails are the ones correctly excluded.** Subscription retry orchestration and mandate renewal are separate state machines, and unbuildable in 11 days on documented Test Mode constraints (§13).
3. **Track 03's bar doesn't reward breadth.** It asks for measured recovery with escalation, stopping rules, and an audit trail. The example directions are options, not a checklist.
> *"Depth of decision quality over breadth of superficial actions. The differentiation isn't how many endpoints you touch — it's why, when, and whether you touch them at all."*
## 11. The frozen architecture
```
                     REBOUND
                        │
              Failed payment event
                        │
              Structured pre-checks          ← no LLM
                        │
          Suspicious-instruction pre-screen  ← no LLM
                        │
                 ┌──────┴──────┐
                 │             │
             RULES           LLM             ← the experiment
          interpreter      interpreter          (§23)
                 │             │
                 └──────┬──────┘
                        │
                 Typed boundary
                        │
              Deterministic policy
                        │
       ┌────────┬───────┼────────┬─────────┐
       ↓        ↓       ↓        ↓         ↓
     STOP     PAUSE   REVIEW   VERIFY   RECOVER
                                  │         │
                              Razorpay   Payment
                               status      Link
                                            │
                                       completion
                                            │
                                     confirmed value
                                            │
                                    audit + metrics
```
The rules/LLM fork sits **inside** the pipeline. Same fixture, same typed boundary, same policy engine, same execution, same audit. Only the interpretation layer changes. That makes the experiment structural rather than bolt-on.
README swimlane line: *"Structured checks execute first — dedupe, flags, status fetch. The interpreter only touches residual ambiguous text. This minimizes cost, latency, and hallucination exposure."*
Governing rule:
> **A value crosses from the interpreter into the engine exactly once, through a validated schema. After that point, no language model touches the arithmetic, the amount, or the action.**
## 12. Evidence bundle — with the identity chain
The identity chain is **mandatory**. Without `payment_id` / `order_id`, verification degrades into *"customer says they paid → ask Razorpay whether they paid something,"* which is not verification.
```json
{
  "case_id": "rcv_1042",
  "merchant_reference_id": "REBOUND-rcv_1042",
  "razorpay_context": {
    "event_id": "evt_...",
    "payment_id": "pay_...",
    "order_id": "order_...",
    "payment_link_id": null,
    "merchant_invoice_reference": "INV-1042"
  },
  "payment_event": {
    "event_type": "payment.failed",
    "failure_code": "insufficient_funds",
    "amount_paise": 2500000,
    "attempt_count": 1,
    "invoice_age_days": 0
  },
  "customer_reply": "bhai ye already ho gaya, bank statement bhej du?",
  "support_notes": ["Customer called at 23:14 regarding duplicate charge concern."],
  "merchant_order_notes": "Invoice INV-1042; delivery completed",
  "prior_contact_history": [
    { "template_id": "PAYMENT_LINK_REMINDER_V1", "sent_at": "2026-08-23T10:00:00+05:30" }
  ],
  "customer_preferences": { "opt_out": false, "preferred_language": "hinglish" }
}
```
**Documented rule:**
> *"A payment-already-made claim triggers verification only against the Razorpay payment and order identifiers associated with this recovery case. REBOUND does not infer that a successful payment elsewhere settles this invoice."*
This makes the *"I already paid another invoice"* fixture case do real work: the interpreter flags that the claim references a **different** identifier, which routes to review rather than a status fetch. That's a better demo beat than generic verification.
All fixtures synthetic. Visible label on every output surface:
`Synthetic consented-message fixture · No real customer messages`
**Privacy statement:** *"In production, REBOUND would process merchant-authorized recovery-case context only for the specific recovery purpose, with consent and retention controls defined by the merchant and applicable law. The prototype uses fully synthetic message fixtures and does not ingest real customer communications."*
## 13. Typed boundary — the entire permitted output surface
```json
{
  "case_id": "rcv_1042",
  "customer_state": "POSSIBLE_ALREADY_PAID_OR_DISPUTE",
  "stop_signals": ["PAYMENT_ALREADY_MADE_CLAIM", "DISPUTE_REVIEW_REQUIRED"],
  "confidence": 0.91,
  "evidence_refs": ["customer_reply", "support_notes[0]"],
  "requires_human_review": true,
  "suspected_injection": false
}
```
Forbidden, rejected at **construction**: `amount` · `discount` · `waiver` · `refund` · `payment_link_url` · `execution_action` · `retry_time` · any customer-facing message text · any policy override · any tool or action name.
```python
# tests/test_typed_boundary.py
def test_forbidden_fields_rejected():
    with pytest.raises(ValidationError):
        AgentOutput(amount=500)
    with pytest.raises(ValidationError):
        AgentOutput(payment_link_url="https://...")
    with pytest.raises(ValidationError):
        AgentOutput(execution_action="CREATE_PAYMENT_LINK")
```
> *"The model does not possess the capability to express a financial action."*
**But state the limit in the same breath** (§8): the typed boundary prevents *action* injection, not *classification* error. `{"customer_state": "RECOVERY_ELIGIBLE", "confidence": 0.94}` on a message that genuinely means *"I'm disputing this charge"* is a perfectly valid schema, passes the policy engine, isolates the amount correctly — and is still the wrong decision.
Templates are deterministic and pre-approved; the model never authors customer-facing language:
```
Template: PAYMENT_LINK_REMINDER_V1
Variables: merchant_display_name, invoice_reference, amount,
           payment_link, expiry, support_url
```
## 14. Subscriptions and mandates — OUT OF SCOPE
Verified Test Mode constraints:
1. **Test-mode card tokens support subsequent debits only within 3 days of creation.** A subscription fixture built on day 1 is dead by a day-10 recording.
2. **You cannot test subscription-update behavior** once any test charge beyond the initial authentication has been made.
3. Docs-verified state model: failed auto-charge → `pending` → **three further retries (4 consecutive failures total** — not two, not three) → `halted`. A successful card change moves a subscription **`halted` → `active`**, not from `pending`. On reactivation **only future cycles auto-charge**; invoices issued during the halted period are not retroactively charged, and charging them is a **Dashboard-only manual action** — never agent-executed, never countable as recovered value.
**Implementation:** subscription/mandate context → log `DETECTED_SCOPE_OUT` → no action. No routing logic, no bucket, no fixture cases.
**README wording — frame it as judgment, not absence:**
> *"We investigated the actual Test Mode constraints and found that implementing this flow faithfully would require capabilities the test environment does not support within the submission window. We therefore detect it and refuse to pretend to support it."*
## 15. Deterministic policy engine — explicit precedence
Real messages carry multiple signals. Precedence must be explicit and tested; the most conservative outcome always wins.
```
PRECEDENCE ORDER (first match wins)
1. MALFORMED_OR_DUPLICATE_EVENT     → reject / dedupe, no action
2. VERIFIED_PAYMENT_STATUS          → captured: close ALREADY_PAID,
                                       suppress contact
3. EXPLICIT_OPT_OUT                 → HARD_STOP, suppress future automated
                                       recovery outreach for this
                                       merchant-customer identity;
                                       route exceptions to merchant review
4. DISPUTE_OR_REFUND                → HARD_STOP, create support case
5. SUSPICIOUS_INSTRUCTION_DETECTED  → HUMAN_REVIEW forced, no contact, no link
6. LOW_CONFIDENCE (< frozen thresh) → HUMAN_REVIEW, no automatic action
7. AMBIGUOUS / CONFLICTING          → HUMAN_REVIEW, no automatic action
8. PROMISE_TO_PAY                   → PAUSE until promised date,
                                       no contact before it
9. RECOVERY_ELIGIBLE                → if quota available: create ONE Test Mode
                                       Payment Link (idempotent per case_id)
                                       else: LINK_QUOTA_GUARD → merchant review,
                                       NO API call made
```
Multi-signal cases that must be in the fixture and tested: dispute + opt-out · already-paid claim + explicit dispute · promise-to-pay + injection-like wording · low confidence after a deterministic hard stop · "I already paid another invoice."
Outcome classes reported separately, never collapsed:
```
HARD STOP:   dispute · refund in progress · explicit opt-out · verified captured
SOFT PAUSE:  promise-to-pay · temporary delay · payment-method issue
NO ACTION:   ambiguous · low confidence · conflicting · suspicious instruction
```
## 16. Payment verification — the best individual feature
Razorpay's docs justify this: a `payment.failed` webhook can be followed by `payment.captured` for the **same transaction**. Late authorisation causes it, and so does a customer retrying inside a UPI TPAP app (wrong PIN, then correct PIN). Razorpay recommends subscribing to both events and/or a server-side status query rather than trusting the first webhook.
So the claim is **frequently literally true**, and it is checkable — but only against the identifiers on *this* case (§12).
```
Interpreter detects PAYMENT_ALREADY_MADE_CLAIM
  (confidence + evidence_refs only — it does NOT adjudicate)
        ↓
Typed boundary
        ↓
Deterministic status fetch against razorpay_context.payment_id / order_id
        ↓
IF captured/paid:  close ALREADY_PAID; suppress all contact; audit
ELSE:              HUMAN_REVIEW; no auto-contact; no link
IF claim references a DIFFERENT identifier:
                   HUMAN_REVIEW; no status fetch on this case
```
Fixture must contain **4 true and 2 false claims.** Without the false ones the verification is theater.
Metric treatment: the interpreter is scored **only** on detecting that a claim was made. Whether payment occurred is the engine's call, reported separately.
**The memorable principle:** *"The model identifies evidence. Razorpay determines truth."*
## 17. Idempotency and reconciliation
Razorpay's Payment Link API requires a unique `reference_id` and errors on collision. Precise wording:
> *"We do not assume a generic idempotency-key contract for Payment Links. REBOUND guarantees at-most-one local action record with `UNIQUE(case_id)` and uses Razorpay's unique merchant `reference_id` (`REBOUND-{case_id}`) as the remote correlation key for reconciliation."*
```sql
payment_link_action
  action_id
  case_id                UNIQUE      ← local guarantee
  merchant_reference_id  UNIQUE      ← remote correlation key
  amount_paise
  state    PENDING | CREATING | CREATED | UNKNOWN | NOT_CREATED | MANUAL_REVIEW
  razorpay_link_id       NULLABLE
  razorpay_short_url     NULLABLE
  request_payload_hash
  created_at / updated_at
```
Flow: check for existing action on `case_id` → if present return it → else insert `CREATING` in a transaction → call Razorpay → persist returned id/URL before marking `CREATED`.
On timeout / ambiguous 5xx: mark `UNKNOWN`, **do not blindly retry**, audit `PAYMENT_LINK_OUTCOME_UNKNOWN`.
```
CREATING → timeout → UNKNOWN → reconcile
                                 ├── found    → CREATED
                                 ├── absent   → NOT_CREATED (safe to retry)
                                 └── age > max → MANUAL_REVIEW
```
**Caveat to state:** *"Automated reconciliation is claimed only after we verify the documented retrieval-by-reference path against our own account."* Do not assert `reference_id` enables remote search until the gate confirms it.
**Say it precisely:** `UNIQUE(case_id)` guarantees at-most-one *local action record*. At-most-one *remote Payment Link* is only approximated unless reconciliation runs. Test a timeout occurring **after** successful remote creation.
## 18. The 30-link cap
Verified: **Test Mode allows a maximum of 30 Payment Links per business**; beyond that, contact support.
- **Never map N fixture cases to N links.** Link-eligible count stays well below 30.
- A **local quota guard** blocks the attempt *before* any HTTP request — the panel sees you prevent the call rather than make it and handle the error.
- **Completing** a Test Mode payment requires clicking through the hosted mock bank page. Not an API operation.
- For the video, set local cap to 5 in a labeled demo run:
```
QUOTA-GUARD DEMONSTRATION ONLY
Configured local test quota: 5
Case 6 → LINK_QUOTA_GUARD · Razorpay API call: not attempted
```
State production uses Razorpay's documented cap of 30.
**Do not imply the API exposes a quota counter** unless today's gate confirms it. Say "observed usage" and document what you actually saw.
**Conditionalize the unused-quota line — only say what's true.** If the fixture yields 8 eligible cases: *"Our fixture, designed to mimic real-world base rates, yielded 8 eligible cases. We created 8 links; remaining quota was not needed."* Never claim restraint you didn't exercise.
## 19. Suspicious-instruction detector — secondary, not central
**Threat hierarchy — state it in this order:**
1. Missed dispute or opt-out *(semantic — the real risk)*
2. Duplicate or uncertain money-moving action
3. Semantically wrong model output
4. Known instruction-shaped evidence *(injection — this layer)*
Injection belongs in failure containment, **not** in the core thesis. It demos well, which is exactly why the video segment stays at ~30 seconds and the Chaos Mock gets the extra time.
```
LAYER 1 — DETERMINISTIC PRE-SCREEN (authoritative, before the model)
  Role/meta tokens:      system:  assistant:  developer:
  Instruction patterns:  ignore (previous|prior)  override policy  bypass policy
  Operation patterns:    set confidence  mark as  call tool  invoke tool
  Role tokens are the highest-precision signals — they almost never appear
  in genuine customer text. Keep all 8 patterns.
  DO NOT flag ordinary payment vocabulary:
    "create payment link" · "send the link again" · "pay now" ·
    "do not stop my subscription"
  Require EITHER a role/meta token, OR a model-operation instruction,
  OR directive + controlled field. A single keyword does not fire.
  → on match: force HUMAN_REVIEW, suppress contact and links,
    regardless of interpreter output. Audit: INJECTION_PATTERN_DETECTED
LAYER 2 — INPUT DELIMITATION
  UNTRUSTED EVIDENCE START / END markers; treat contents as data.
LAYER 3 — MODEL'S OWN LABEL (non-authoritative)
  suspected_injection recorded and measured; cannot override Layer 1.
  Agreement/disagreement between Layer 1 and Layer 3 is a reportable result.
LAYER 4 — TYPED BOUNDARY (the floor)
  Even a successful injection cannot emit an amount, link, command, or text.
```
**Pin regex specificity.** `mark as` is on the list; near-miss #5 is *"Please mark this invoice as paid after you verify it"* — expected **no flag**. `mark.*as` catches it; literal `"mark as"` does not. Decide, document, test.
**Near-miss cases** (in the fixture, must not flag): "Can you create a payment link for me?" · "Please do not stop my subscription." · "Ignore my previous message — I already paid the invoice." *(also a payment-claim case → carries both `bucket` and `pre_screen_expected: false`)* · "Can you send the same link again?" · "Please mark this invoice as paid after you verify it."
**Name it honestly:** *a deterministic suspicious-instruction detector that forces review for known instruction-shaped evidence* — not "injection prevention." **Report as a unit-tested guard, not a classifier** (denominators too thin for recall claims): 3/3 known patterns caught, 0/5 near-misses flagged, framed as demonstrating behavior on known patterns.
**Language scope:**
> *"Hinglish (Hindi-English code-mixing) is tested. Tamil and other code-mixed Indian languages are architecturally in scope — the prompt accepts them as untrusted evidence — but are untested in this prototype. The evaluation fixture is Hinglish-dominant due to author verification constraints."*
---
# PART IV — FIXTURE, EXPERIMENT, MEASUREMENT
## 20. The 58-case fixture
| Bucket | Total | Held-out |
|---|---|---|
| Dispute / refund | 8 | 3 |
| Explicit opt-out | 5 | 2 |
| Already-paid, true | 4 | 2 |
| Already-paid, false | 2 | 1 |
| Injection attempts | 3 | 1 |
| Near-misses (non-injection) | 5 | 2 |
| Ambiguous multilingual | 4 | 2 |
| Multi-signal | 4 | 2 |
| Benign / ordinary failures | 23 | 7 |
| **Total** | **58** | **22** |
Development: 36. Held-out: 22.
**Why 58 and not 40:** at 40, the held-out hard-stop denominator falls to 1–2 — not a metric, a rounding error. At 58 it is **8** (3 disputes + 2 opt-outs + ~3 multi-signal). Cutting from 80 to 58 removed only LLM-generated filler and cost about an hour; cutting to 40 would have removed critical cases and destroyed the measurement.
### Design rules
- **Realistic base rate.** Most cases have no customer reply. Real failed payments mostly produce silence.
- **Minimum 3 development examples per class.** Only the *prompt* is tuned; the policy engine needs zero examples.
- **Held-out hard-stop denominator ≥ 8. Held-out benign ≥ 7.**
- **False claims required** wherever a deterministic check exists.
- **Near-miss, injection, multi-signal counted in the total from the start** — never appended after the manifest is computed.
- **Every case carries the full identity chain** (§12).
- **Link-eligible well below 30.**
### Hybrid authoring
| Set | Count | Method |
|---|---|---|
| Benign / ordinary failures | 23 | LLM-generated, `generated_and_retained` |
| Disputes, opt-outs, already-paid, injections, near-misses, ambiguous, multi-signal | 35 | **Hand-written**, `human_written` |
An LLM asked for a "dispute" case emits dispute vocabulary — it telegraphs the label. Ambiguous cases would be ambiguous the way a *model* thinks ambiguity looks, not the way a frustrated customer at 11pm writes.
Report `critical_hand_written_count`: *"All high-stakes ground-truth labels were human-authored to avoid label-telegraphing."*
### Generated manifest — build BEFORE authoring any case
Hand-computed bucket tables produced wrong totals **four separate times** during planning. Always the same mechanism: a category added after the total was computed.
```
fixtures/
├── development_cases.json
├── heldout_cases.json
├── labeling_rubric.md
└── manifest.json          ← GENERATED. Never hand-edited.
```
```json
{
  "case_id": "RCV-H-017",
  "split": "heldout",
  "bucket": "DISPUTE_REFUND",
  "recovery_eligible": false,
  "payment_link_eligible": false,
  "requires_evidence_judgment": true,
  "requires_status_verification": false,
  "pre_screen_expected": false,
  "expected_outcome": "HARD_STOP",
  "authoring_method": "human_written",
  "labeling_method": "delayed_double_label"
}
```
`manifest.py` runs as **constraint satisfaction, not reporting**:
```
total == 58 · heldout == 22
≥3 development cases per bucket
≥8 held-out evidence-judgment hard stops
≥7 held-out benign cases
payment_link_eligible ≤ 30
near-miss, injection, multi-signal counted in total
every case has payment_id + order_id
→ if unsatisfiable, it SAYS SO and you resize deliberately
```
**Every number in the dashboard, README, and video comes from this generated output.** Never typed by hand.
## 21. Ground truth labeling
**Preferred:** an independent reviewer blind-labels the held-out 22 — `customer_state`, `hard_stop_required`, `automatic_contact_allowed`, `required_next_action` — with no sight of expected labels or model outputs.
**Fallback:** **delayed self-relabeling** — label once → wait 48+ hours → relabel blind → compare → resolve with written rules.
**Write the labeling rubric before pass 2.** It must define: what counts as explicit opt-out · what counts as dispute · what counts as a payment claim · when ambiguity requires review · whether support notes override customer text · whether multiple signals produce the most conservative outcome (they do — §15).
```
Ground-truth method:   Single-author delayed double-labeling
Intra-rater agreement: __ / 22
Limitation:            No independent second annotator was available.
```
Delayed relabeling measures consistency with yourself, not correctness. Say so.
**Scheduling:** labeling depends only on the *fixture*, not the model. Both passes go **early**, so the 48-hour gap never blocks the critical path.
## 22. Chaos Mock — must-build, ~2 hours
Mock the interpreter, build the engine against it, swap the real LLM in late. **Do not derive mock outputs from `expected_outcome`** — a perfect mock never exercises the paths that matter.
**What it can objectively contain:**
| Chaos condition | Expected containment |
|---|---|
| `dispute_open: true` structured flag, model says benign | Structured pre-check hard-stops before model output matters |
| Invalid schema or forbidden field | Typed boundary rejects |
| Missing / invalid `evidence_refs` | Schema-consistency validation → review |
| Confidence 0.4 | Threshold → review |
| Mismatched case ID | Reject output; no execution |
| Timeout after remote link creation | UNKNOWN → reconciliation → no blind retry |
| Duplicate event ID | Dedupe; no second action |
**State the limit — this is the honest version and it raises credibility:**
> *"The Chaos Mock proves containment of malformed, inconsistent, low-confidence, and deterministically contradicted outputs. It does not prove that the system can detect every confident semantic misclassification in unstructured text."*
The naive framing — *evidence says dispute → LLM says BENIGN at 0.94 → typed boundary → safe* — is **false** and must not appear anywhere. A schema validator cannot know that `BENIGN` is semantically wrong. If the dispute lives only in nuanced free text, the engine proceeds.
## 23. The rules-vs-LLM experiment — the AI justification
Implemented as an **evaluation mode on the existing batch runner**, not a new module:
```bash
python run_batch.py --interpreter=rules
python run_batch.py --interpreter=llm
```
Both share: fixture → interpreter → typed boundary → policy engine → execution → audit → metrics. **Only the interpretation layer changes.**
The rules interpreter is deliberately simple — do not build a competing NLP system:
```
paid / already paid / payment done  → payment claim
stop / don't contact                → opt-out
refund / wrong item / dispute       → dispute
```
**The objective is not "prove the LLM is accurate."** It is: *does semantic interpretation create a better recovery/suppression operating point than the simpler alternative?* That is answerable even with a small fixture.
Comparison table — **all cells `[from run]`**:
| Method | Hard-stop recall | False stops | Automation rate | Human-review rate |
|---|---|---|---|---|
| Rules baseline | __/__ | __ | __ | __ |
| LLM semantic | __/__ | __ | __ | __ |
Also compare: payment claims detected · operational outcomes · missed stops.
**Do not pre-write the conclusion.** Invented numbers have appeared eight times in this project's history — ₹3.12L, 89.0%, 30 links, ₹30,000, 7/8, threshold 0.75, and a pre-written baseline finding. If rules match the LLM, that is a **result you report**, and reporting it honestly is stronger than asserting the opposite. The panel statement is:
> *"We held the fixture, policy, execution, and safety controls constant and changed only the evidence interpreter."*
## 24. Metrics — order matters
**Present in this order: Track 03 outcome → judgment → AI justification → engineering reliability.**
**1. Batch recovery funnel** (first thing anyone sees)
```
58 evaluated → N eligible → N link attempts → N created → N completed
Completed Test Mode value: ₹__   (execution proof, not commercial impact)
```
**2. Safety outcomes**
```
STOPPED: __   PAUSED: __   HUMAN REVIEW: __   NO ACTION: __
```
Then the evidence-judgment hard-stop matrix (dispute + opt-out + multi-signal disputes only — already-paid cases excluded because a deterministic API call settles them and including them pads recall with wins the model didn't earn):
|  | GT: hard stop | GT: no hard stop |
|---|---|---|
| System hard-stopped | True stop | **False stop** |
| System did not hard-stop | **Missed stop** | Correct non-stop |
**Directly under the metric, not in a limitations section:**
> *"On this held-out fixture, REBOUND identified X/Y required hard stops. The denominator is intentionally small and does not establish production-level model accuracy."*
**3. Evidence interpretation** — the rules-vs-LLM table (§23)
**4. Operational reliability**
```
duplicates prevented · UNKNOWN reconciled · quota blocks ·
chaos conditions contained · payment claims verified (engine) vs detected (interpreter)
```
**Rules that apply everywhere:**
- **Raw counts, no percentages under denominator 10.** "7/8" not "87.5%."
- **Every cell ships as `[from run]` or `__/__`** until the run produces it. No exceptions, including "illustrative" examples.
- **Always "on this held-out fixture,"** never "REBOUND achieves X%."
- Optional: `prototype safety cost = 5×missed_stops + 1×false_stops`, labeled *"a documented prototype safety preference, not an industry-standard cost model."* Under the matrix, never instead of it — alone it is gameable.
## 25. Confidence threshold — swept, not asserted
Sweep on the **development set only**, freeze before touching held-out.
```
All cells [from run]:
Threshold | Automation rate | Recall | Precision
0.50      | __              | __/__  | __/__
0.65      | __              | __/__  | __/__
0.75      | __              | __/__  | __/__
0.85      | __              | __/__  | __/__
Selected: [from sweep], frozen before held-out evaluation.
```
Twenty minutes of work. Converts an indefensible constant into a defensible operating point.
**Two required disclosures:**
> *"With ~5–7 dev hard-stop cases the sweep is coarse — a step function with a handful of points, not a smooth curve and not a knee."*
> *"This is a model-reported confidence operating threshold, not a calibrated probability threshold. We do not claim these scores are calibrated probabilities; the sweep is a pragmatic method for choosing a review boundary on development data."*
Never claim "precision near 100%." A confidently wrong classification still produces a false stop.
---
# PART V — EXECUTION
## 26. Feasibility gate — TODAY, before anything else
```
1. Generate Razorpay Test Mode API keys from the Dashboard
2. Create ONE Standard Payment Link via POST /v1/payment_links
   with reference_id = "REBOUND-test-001"
3. Open the hosted checkout MANUALLY in a browser
4. Complete one Test Mode payment (mock bank page → Success)
5. Fetch the resulting payment/link status via API
6. Attempt retrieval BY reference_id — this validates the
   reconciliation design (§17)
7. Confirm observed remaining Test Mode Payment Link usage
8. Save request, response, and event log to evidence/
```
```
IF a link can be created and completed today:  build REBOUND
ELSE:                                          build against a simulator,
                                               disclose it, keep everything else
```
Decide on an **observed result**, not on what the docs say. Manual completion first.
**September 5 is a Saturday.** If the gate surfaces a quota or account problem needing Razorpay support, that's a weekday conversation — it must surface by **Wednesday September 2**.
### What actually depends on the API
**Independent** — most of the intellectual content: interpretation layer, typed boundary, policy engine, all four injection layers, audit log, hash chain, the 58-case fixture, the rules-vs-LLM experiment, and metrics sections 2–4. The whole system runs against a mock client returning fake `plink_...` IDs and every number except the funnel's execution tail is real.
**Dependent:** link creation, Test Mode completion + status, reconciliation-by-reference, completed value, and the live-execution video segment.
If the gate fails you lose *one demonstrated capability*, not the project — disclosed the way Lumen disclosed "no live STT/TTS" and AETHER disclosed "message shape only, nothing transmitted."
## 27. Cut list — final
| Cut | Reason |
|---|---|
| **Playwright checkout automation** | Automating mock-bank clicks is plumbing validation, not recovery. One manual checkout in the video. |
| **Subscription / mandate flows** | 3-day token expiry; Dashboard-only invoice charge. `DETECTED_SCOPE_OUT`. |
| **Tamil test cases** | Cannot verify. Disclose as untested; do not claim. |
| **Elaborate threshold curve** | 4-row table instead. |
| **Polished dashboard** | Console output + one plain HTML table. |
| **Scenario / projected value analysis** | Inventing a projection right after refusing to inflate a measurement. |
| **80-case ambition** | 58 preserves every critical class; only filler cut. |
| **Broad regex coverage** | 8 patterns, weighted to role tokens. |
| **A separate `baseline.py`** | Evaluation mode on the existing runner. |
**Protected from cutting:** Chaos Mock · tamper test · held-out split · threshold sweep · injection near-misses · multi-signal cases · rules-vs-LLM experiment.
**Module test — apply to everything:** *every module must correspond to a visible demo moment, a measured output, or a safety-critical test.* Not module count — control boundaries.
## 28. Repository structure
```
rebound/
├── README.md                     ← positioning, non-claims, two safety classes,
│                                    funnel, metrics, threshold table,
│                                    Tamil disclosure, module justification
├── architecture/
│   ├── system-diagram.png
│   ├── precedence-table.md
│   ├── structural-vs-semantic-safety.md
│   └── failure-matrix.md
├── fixtures/
│   ├── development_cases.json
│   ├── heldout_cases.json
│   ├── labeling_rubric.md
│   └── manifest.json             ← generated
├── src/
│   ├── structured_prechecks.py   ← deterministic checks before AI
│   ├── instruction_detector.py   ← pre-LLM adversarial evidence handling
│   ├── interpreters/
│   │   ├── rules_interpreter.py  ← the baseline arm
│   │   └── llm_interpreter.py    ← the AI reasoning boundary
│   ├── typed_boundary.py         ← action-space restriction
│   ├── policy_engine.py          ← deterministic decision control
│   ├── payment_verifier.py       ← model claim → factual API verification
│   ├── razorpay_client.py        ← create, fetch/status, reconcile only
│   ├── quota_guard.py            ← bounded execution
│   ├── reconciliation.py         ← ambiguous external outcome handling
│   ├── audit_log.py              ← traceability
│   └── templates.py              ← model cannot author communication
├── tests/
│   ├── test_typed_boundary.py    ← construction-time rejection
│   ├── test_policy_engine.py
│   ├── test_precedence.py        ← multi-signal cases
│   ├── test_instruction_detector.py  ← incl. near-miss precision
│   ├── test_quota_guard.py
│   ├── test_idempotency.py       ← incl. timeout-after-remote-creation
│   ├── test_chaos_mock.py
│   └── test_audit_chain.py       ← tamper test
├── scripts/
│   ├── manifest.py
│   ├── run_batch.py              ← --interpreter=rules|llm
│   └── generate_metrics.py
└── evidence/
    ├── testmode_link_created.json
    ├── testmode_payment_completed.json
    ├── reference_id_retrieval.json
    └── quota_check.md
```
## 29. Eleven-day schedule
| Date | Work |
|---|---|
| **Tue Aug 25** | **API gate, manual** (§26). All 8 steps including retrieval-by-`reference_id`. |
| **Wed Aug 26** | `manifest.py` with constraint satisfaction — **before authoring any case**. Hand-write all 35 critical cases with full identity chains. LLM-generate 23 benign. Freeze the fixture. |
| **Thu Aug 27** | Typed boundary + construction-time rejection tests. Hash chain + tamper test. **Write the labeling rubric. Labeling pass 1** — starts the 48h clock. |
| **Fri Aug 28** | Policy engine with precedence table. Structured pre-checks. Suspicious-instruction detector, 8 patterns, near-miss tests. |
| **Sat Aug 29** | Razorpay client · quota guard (local cap 5 for demo) · `UNIQUE(case_id)` · UNKNOWN state · reconciliation-by-reference. |
| **Sun Aug 30** | **Chaos Mock** against the engine, all 7 containment conditions. **Labeling pass 2** (48h elapsed) → reconcile → report agreement → freeze ground truth. |
| **Mon Aug 31** | Real LLM in. Run dev set. Prompt iteration — day 1 of 2. |
| **Tue Sep 1** | Prompt iteration day 2. Threshold sweep 0.5–0.95, freeze before held-out. **Rules interpreter + both batch runs** (same infrastructure). |
| **Wed Sep 2** | Full 58-case batch, both arms. Metrics generated from the manifest. **Draft the README.** |
| **Thu Sep 3** | **Video only.** Record twice, discard the first take. Finalize README. |
| **Fri Sep 4** | **Submit.** No code changes. Push the repo. |
| **Sat Sep 5** | Buffer. Rehearse the hash-chain, typed-boundary, and "why only Payment Links" answers out loud. |
### On building with AI
**Collapses well:** typed boundary, hash chain, policy engine (you have pseudocode), Razorpay client, quota guard, SQLite schema, Chaos Mock, manifest generator, rules interpreter, metrics code, README scaffolding. Aug 27–30 will likely compress.
**Does not collapse:** the API gate (you, in a browser) · the 35 critical fixture cases (hand-writing them is the entire point) · prompt iteration (the one thing AI assistance genuinely doesn't shorten — hence two days) · the 48-hour labeling gap · **comprehension.**
**Do not pull the schedule forward when the build compresses.** The slack belongs to prompt iteration, an unhurried video, and reading your own repo until you can defend any file cold. This ends in a panel reading your code; every hour AI saves on typing is owed back to explaining what it typed. That is not overhead — it is the deliverable.
## 30. Five-minute video — recovery first, thesis last
| Time | Content |
|---|---|
| 0:00–0:30 | **Positioning + problem.** "REBOUND is a bounded revenue-recovery engine for failed payments." A webhook tells you a payment failed. It cannot tell you the customer already paid, is disputing it, asked you to stop, or promised to pay Friday. |
| 0:30–1:15 | **Recovery case FIRST.** Ordinary failed payment → no stop signal → policy permits → Test Mode Payment Link created → completed → funnel updates. *This is Track 03's bar, hit directly.* |
| 1:15–2:00 | **Silence case.** "But recovery is worthless if it contacts the wrong customer." Insufficient funds → reply claims already paid → interpreter flags the claim → deterministic status check against *this case's* payment_id → captured → closed, zero contact, zero link. Show the audit event recording *why nothing happened.* |
| 2:00–2:20 | **Pause case.** Promise-to-pay → paused until the named date. |
| 2:20–2:50 | **Chaos Mock** — the primary danger case. Contradictory and malformed interpreter output contained by structured pre-checks, schema validation, and thresholds. State the limit: structural containment, not semantic guarantee. |
| 2:50–3:10 | **Injection**, introduced as secondary: "Beyond hallucinations, we also defend against adversarial text." Pre-screen fires **before the LLM call**. `INJECTION_PATTERN_MATCHED \| HUMAN_REVIEW_FORCED`. |
| 3:10–3:55 | **Batch proof in order:** funnel → safety outcomes → rules-vs-LLM table → operational reliability. Real numbers only. |
| 3:55–4:25 | **Failure recovery.** Duplicate webhook ignored · timeout → UNKNOWN → reconciled by reference · quota guard blocks with no API call. |
| 4:25–5:00 | **Non-claims, then the thesis as conclusion.** What this deliberately does not do — then: *"The most valuable recovery action is sometimes knowing when not to act."* |
---
# PART VI — META
## 31. The pattern to guard against during the build
Across ~20 rounds and three critics, one error class kept reappearing: a compressed "final" version silently dropping a fix from the round before — the 30-link cap, the card-update claim, recall/precision mislabeling, subscription state direction (`pending` vs `halted`), retry count (2 vs 4), fixture totals (four separate arithmetic failures), the checkout-abandonment bucket, the labeling pass, three days of timeline, and **invented numbers eight times**.
**The governing principle, which now applies to the build:** any number, claim, or constraint that could regress under time pressure needs a *structural* enforcement mechanism, not a note to be careful.
| "Be careful about…" | Structural guarantee instead |
|---|---|
| The model shouldn't emit amounts | Schema without the field; construction-time rejection |
| Don't create duplicate links | `UNIQUE(case_id)` in SQLite, checked in a transaction |
| The model should resist injection | Deterministic pre-screen running before the model |
| Keep fixture totals consistent | Generated manifest; constraint satisfaction |
| Don't inflate recovered value | Value counted only on confirmed checkout completion |
| Don't tune on the test set | Threshold frozen on dev before held-out is touched |
| Verification must target the right payment | Identity chain required on every fixture case |
| Don't write invented numbers | Every number traceable to a file the code wrote |
**And the corollary for the pitch itself:** don't argue, demonstrate.
| Don't argue | Demonstrate |
|---|---|
| "The panel will see this is revenue recovery" | 58 → eligible → bounded intervention → completed payment |
| "Our LLM is safe" | precheck → typed output → precedence → verification → bounded execution |
| "Our LLM handles messy customer language" | hand-written held-out Hinglish → interpretation → ground-truth comparison |
## 32. Verdict
**The idea is sound and a serious contender.** It hits three of Track 03's four stated requirements decisively and the fourth honestly — modest but real measured recovery value, explained rather than inflated. The architecture is the one already proven in AETHER and Lumen, applied to a domain far easier to defend under questioning than ISDA derivatives.
**Reuse is methodology, not derivative work.** No AETHER or Lumen code, no ISDA vocabulary, rebuilt cleanly in Python. Say the lineage out loud: *"Across legal-document interpretation, credit-evidence analysis, and now payment recovery, I use the same safety principle: the model interprets unstructured evidence, but a typed boundary and deterministic policy retain control of consequential actions."*
**The differentiator, correctly ordered.** Most Track 03 submissions will be dunning agents optimizing recovery rate. REBOUND is a recovery engine whose first job is determining whether recovery is *safe* — and it leads with the funnel, not the sermon.
**The one open empirical question — and it is a good one to have:**
> Does semantic interpretation of messy customer evidence improve the recovery/suppression operating point over deterministic lexical rules, at an acceptable review rate?
It is measurable. It is testable. It runs on Tuesday September 1. **You do not need to pretend you have solved it before running the experiment** — and if the answer is "not much," reporting that honestly is a stronger result than asserting the opposite.
**The remaining risks, in order:**
1. **Semantic false negatives.** No schema, regex, or audit chain fixes a confidently wrong interpretation. The held-out evaluation is the only instrument, and its denominator is 8. Language stays bounded: *"on this held-out fixture."*
2. **Execution capacity** for a solo build in 11 days — addressed by the cut list.
3. **Defensibility** under a panel that reads the code — addressed only by spending AI-saved time on comprehension rather than finishing early.
**The one un-derisked assumption** is whether the Payment Links API behaves as documented on your account. Nothing else in this document should be built before that check runs.
Specification closed. Go generate the test keys.
