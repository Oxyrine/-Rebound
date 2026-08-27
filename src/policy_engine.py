"""Deterministic policy engine (§15's precedence table).

Emits a *routing* decision only -- STOP/PAUSE/REVIEW/VERIFY/RECOVER, the
five routes in the §11 architecture diagram -- not the fixture's six-way
terminal label (RECOVERY_ELIGIBLE/HARD_STOP/HUMAN_REVIEW/ALREADY_PAID_CLOSED/
VERIFY_PAYMENT_STATUS/PAUSE_UNTIL_DATE). ALREADY_PAID_CLOSED in particular
only exists after a VERIFY route resolves against a real Razorpay status --
that's payment_verifier.py's job, not this engine's. This engine stays pure
precedence logic: no I/O, no network, no mutable state of its own. Anything
cross-cutting (pre-screen match, quota availability) is a parameter, not
something the engine looks up itself.

Interpreter stop_signals vocabulary this engine understands (the "Day 3"
freeze deferred from typed_boundary.py): PAYMENT_ALREADY_MADE_CLAIM,
EXPLICIT_OPT_OUT, DISPUTE_OR_REFUND, AMBIGUOUS_OR_CONFLICTING,
PROMISE_TO_PAY. Unrecognized signals fall through rather than erroring --
an interpreter emitting a signal outside this vocabulary should degrade,
not crash the batch.
"""

from dataclasses import dataclass

from src.structured_prechecks import PrecheckResult
from src.typed_boundary import AgentOutput

# Frozen by ticket 08's sweep (scripts/threshold_sweep.py, dev set only,
# before heldout was touched): 0.50-0.80 all left one case
# (RCV-034, an AMBIGUOUS-bucket reply the interpreter's own signal
# detection missed that run, confidence 0.85) silently routed to RECOVER
# -- an "unsafe miss," never mind accuracy. 0.90 is the lowest threshold
# that catches it (0 unsafe misses, 34/37 accuracy); 0.95 buys nothing
# further (still 0 unsafe misses) at a higher over-caution cost (4 cases
# vs 2). Passed as a parameter, not looked up internally, so re-sweeping
# later doesn't require touching this function's signature.
CONFIDENCE_THRESHOLD = 0.9


@dataclass(frozen=True)
class RoutingDecision:
    case_id: str
    route: str  # STOP | PAUSE | REVIEW | VERIFY | RECOVER | LINK_QUOTA_GUARD
    matched_rung: str
    reason: str
    evidence_refs: list[str]


def route(
    agent_output: AgentOutput,
    precheck: PrecheckResult,
    pre_screen_matched: bool,
    quota_available: bool = True,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> RoutingDecision:
    case_id = agent_output.case_id
    signals = agent_output.stop_signals
    refs = agent_output.evidence_refs

    def decide(route_value, rung, reason):
        return RoutingDecision(case_id, route_value, rung, reason, refs)

    if not precheck.ok:
        return decide("STOP", "MALFORMED_OR_DUPLICATE_EVENT", precheck.reason)

    if "PAYMENT_ALREADY_MADE_CLAIM" in signals:
        return decide("VERIFY", "VERIFIED_PAYMENT_STATUS", "payment claim requires status fetch")

    if "EXPLICIT_OPT_OUT" in signals:
        return decide("STOP", "EXPLICIT_OPT_OUT", "customer asked not to be contacted")

    if "DISPUTE_OR_REFUND" in signals:
        return decide("STOP", "DISPUTE_OR_REFUND", "charge itself is disputed")

    # Layer 3 (agent_output.suspected_injection) is measured, not
    # authoritative (§19): it cannot force review on its own. Only the
    # deterministic Layer-1 pre-screen can.
    if pre_screen_matched:
        return decide("REVIEW", "SUSPICIOUS_INSTRUCTION_DETECTED", "deterministic pre-screen matched")

    # Chaos condition 3 (§22): a stop_signal asserted with nothing in
    # evidence_refs to back it is a schema-consistency failure, not a
    # signal to route on. Purely a function of agent_output's own fields,
    # so it's checked here rather than threaded in as a parameter.
    if signals and not refs:
        return decide("REVIEW", "EVIDENCE_REFS_MISSING", "stop signal asserted without evidence_refs")

    if agent_output.confidence < confidence_threshold:
        return decide("REVIEW", "LOW_CONFIDENCE", f"confidence {agent_output.confidence} below threshold")

    if "AMBIGUOUS_OR_CONFLICTING" in signals:
        return decide("REVIEW", "AMBIGUOUS_OR_CONFLICTING", "no signal resolves cleanly")

    if "PROMISE_TO_PAY" in signals:
        return decide("PAUSE", "PROMISE_TO_PAY", "dated promise to pay")

    if quota_available:
        return decide("RECOVER", "RECOVERY_ELIGIBLE", "no stop signal, quota available")

    return decide("LINK_QUOTA_GUARD", "RECOVERY_ELIGIBLE", "no stop signal, quota exhausted")
