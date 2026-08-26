from pydantic import BaseModel, ConfigDict, Field


class AgentOutput(BaseModel):
    """The entire permitted output surface for the evidence interpreter.

    extra="forbid" is the structural guarantee: any field not listed here —
    amount, discount, waiver, refund, payment_link_url, execution_action,
    retry_time, customer-facing message text, policy overrides, tool/action
    names, or anything not yet imagined — is rejected at construction, not
    by convention. A value crosses from the interpreter into the engine
    exactly once, through this schema.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    customer_state: str = Field(min_length=1)
    stop_signals: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)
    requires_human_review: bool
    suspected_injection: bool
