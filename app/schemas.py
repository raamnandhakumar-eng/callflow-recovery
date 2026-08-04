from pydantic import BaseModel, Field


class SimulatedCallRequest(BaseModel):
    tenant_slug: str = "northstar-hvac"
    external_call_id: str = Field(min_length=3, max_length=120)
    caller_phone: str = Field(min_length=7, max_length=40)
    customer_name: str = "Caller"
    transcript: str = Field(min_length=3)
    requested_time: str | None = None
    service: str | None = None


class CallResult(BaseModel):
    external_call_id: str
    intent: str
    confidence: float
    status: str
    answer: str
    citations: list[dict[str, str]]
    appointment_id: int | None = None
    crm_contact_id: str | None = None
    sms_message_id: str | None = None
    escalated: bool
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    replayed: bool = False


class DocumentIngestRequest(BaseModel):
    tenant_slug: str
    title: str
    source: str = "manual"
    content: str = Field(min_length=10)


class SuggestionApprovalRequest(BaseModel):
    answer: str = Field(min_length=10)


class MetricsResponse(BaseModel):
    tenant_slug: str
    calls: int
    bookings: int
    booking_rate: float
    escalations: int
    escalation_rate: float
    p95_latency_ms: int
    total_cost_usd: float
    cost_per_call_usd: float
    cost_per_booking_usd: float
    crm_completion_rate: float
    sms_completion_rate: float
    estimated_recovered_revenue_usd: float
    baseline_expected_lost_calls: float
