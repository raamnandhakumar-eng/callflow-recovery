import json
import math
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import (
    Appointment,
    CallTrace,
    CRMWrite,
    FAQSuggestion,
    KnowledgeDocument,
    SMSMessage,
    Tenant,
)
from app.schemas import (
    CallResult,
    DocumentIngestRequest,
    MetricsResponse,
    SimulatedCallRequest,
    SuggestionApprovalRequest,
)
from app.services.learning import LearningService
from app.services.orchestrator import CallOrchestrator
from app.services.rag import RAGService

router = APIRouter()
settings = get_settings()
orchestrator = CallOrchestrator(settings)
rag_service = RAGService()
learning_service = LearningService()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def get_tenant(db: Session, slug: str) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Unknown tenant: {slug}")
    return tenant


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/v1/calls/simulate", response_model=CallResult)
async def simulate_call(
    payload: SimulatedCallRequest,
    db: Session = Depends(get_db),
) -> CallResult:
    tenant = get_tenant(db, payload.tenant_slug)
    return await orchestrator.handle(db, tenant, payload)


@router.post("/v1/webhooks/vapi")
async def vapi_webhook(
    payload: dict[str, object],
    x_vapi_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Handle Vapi server events, including synchronous custom tool calls."""
    if settings.vapi_webhook_secret and x_vapi_secret != settings.vapi_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid Vapi webhook secret")

    message = payload.get("message")
    if not isinstance(message, dict):
        raise HTTPException(status_code=422, detail="Missing Vapi message object")
    if message.get("type") != "tool-calls":
        return {"received": True, "message_type": message.get("type")}

    raw_calls = message.get("toolCallList", [])
    if not isinstance(raw_calls, list):
        raise HTTPException(status_code=422, detail="Invalid toolCallList")
    call = message.get("call") if isinstance(message.get("call"), dict) else {}
    customer = message.get("customer") if isinstance(message.get("customer"), dict) else {}
    results: list[dict[str, str]] = []

    for raw_call in raw_calls:
        if not isinstance(raw_call, dict):
            continue
        tool_call_id = str(raw_call.get("id", ""))
        name = str(raw_call.get("name", ""))
        parameters = raw_call.get("parameters")
        if not isinstance(parameters, dict):
            parameters = {}
        if name != "handle_customer_request":
            results.append(
                {
                    "toolCallId": tool_call_id,
                    "result": json.dumps({"error": f"Unsupported tool: {name}"}),
                }
            )
            continue

        call_request = SimulatedCallRequest(
            tenant_slug=str(parameters.get("tenant_slug", settings.default_tenant_slug)),
            external_call_id=str(
                call.get("id") or parameters.get("external_call_id") or tool_call_id
            ),
            caller_phone=str(
                parameters.get("caller_phone")
                or customer.get("number")
                or call.get("customerNumber")
                or "+10000000000"
            ),
            customer_name=str(parameters.get("customer_name", "Caller")),
            transcript=str(parameters.get("transcript", "")),
            requested_time=(
                str(parameters["requested_time"])
                if parameters.get("requested_time")
                else None
            ),
            service=str(parameters["service"]) if parameters.get("service") else None,
        )
        tenant = get_tenant(db, call_request.tenant_slug)
        outcome = await orchestrator.handle(db, tenant, call_request)
        results.append(
            {
                "toolCallId": tool_call_id,
                "result": json.dumps(outcome.model_dump(), sort_keys=True),
            }
        )
    return {"results": results}


@router.post("/v1/knowledge/documents")
def ingest_document(
    payload: DocumentIngestRequest,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    tenant = get_tenant(db, payload.tenant_slug)
    document_id = rag_service.ingest(
        db,
        tenant,
        payload.title,
        payload.source,
        payload.content,
    )
    db.commit()
    return {"document_id": document_id}


@router.get("/v1/learning/{tenant_slug}/suggestions")
def list_suggestions(
    tenant_slug: str,
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    tenant = get_tenant(db, tenant_slug)
    suggestions = db.scalars(
        select(FAQSuggestion)
        .where(FAQSuggestion.tenant_id == tenant.id)
        .order_by(FAQSuggestion.count.desc(), FAQSuggestion.id.desc())
    ).all()
    return [
        {
            "id": item.id,
            "question": item.representative_question,
            "count": item.count,
            "status": item.status,
        }
        for item in suggestions
    ]


@router.post("/v1/learning/{tenant_slug}/suggestions/{suggestion_id}/approve")
def approve_suggestion(
    tenant_slug: str,
    suggestion_id: int,
    payload: SuggestionApprovalRequest,
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    tenant = get_tenant(db, tenant_slug)
    suggestion = db.get(FAQSuggestion, suggestion_id)
    if not suggestion or suggestion.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if suggestion.status == "approved":
        return {
            "status": "already_approved",
            "document_id": suggestion.approved_document_id or 0,
        }
    document = learning_service.approve(db, tenant, suggestion, payload.answer)
    db.commit()
    return {"status": "approved", "document_id": document.id}


@router.get("/v1/traces/{tenant_slug}")
def traces(
    tenant_slug: str,
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    tenant = get_tenant(db, tenant_slug)
    rows = db.scalars(
        select(CallTrace)
        .where(CallTrace.tenant_id == tenant.id)
        .order_by(CallTrace.id.desc())
        .limit(100)
    ).all()
    return [
        {
            "external_call_id": row.external_call_id,
            "intent": row.intent,
            "status": row.status,
            "latency_ms": row.latency_ms,
            "cost_usd": row.cost_usd,
            "escalated": row.escalated,
            "steps": json.loads(row.steps_json),
        }
        for row in rows
    ]


@router.get("/v1/metrics/{tenant_slug}", response_model=MetricsResponse)
def metrics(tenant_slug: str, db: Session = Depends(get_db)) -> MetricsResponse:
    tenant = get_tenant(db, tenant_slug)
    rows = db.scalars(select(CallTrace).where(CallTrace.tenant_id == tenant.id)).all()
    calls = len(rows)
    bookings = sum(1 for row in rows if row.status == "booked")
    escalations = sum(1 for row in rows if row.escalated)
    latencies = sorted(row.latency_ms for row in rows)
    p95_index = max(0, math.ceil(len(latencies) * 0.95) - 1) if latencies else 0
    p95_latency = latencies[p95_index] if latencies else 0
    total_cost = sum(row.cost_usd for row in rows)
    crm_count = db.scalar(
        select(func.count(CRMWrite.id)).where(CRMWrite.tenant_id == tenant.id)
    ) or 0
    sms_count = db.scalar(
        select(func.count(SMSMessage.id)).where(SMSMessage.tenant_id == tenant.id)
    ) or 0
    baseline_lost = calls * tenant.baseline_lost_call_rate
    recovered_revenue = bookings * tenant.average_booking_value
    return MetricsResponse(
        tenant_slug=tenant.slug,
        calls=calls,
        bookings=bookings,
        booking_rate=bookings / calls if calls else 0.0,
        escalations=escalations,
        escalation_rate=escalations / calls if calls else 0.0,
        p95_latency_ms=p95_latency,
        total_cost_usd=round(total_cost, 6),
        cost_per_call_usd=round(total_cost / calls, 6) if calls else 0.0,
        cost_per_booking_usd=round(total_cost / bookings, 6) if bookings else 0.0,
        crm_completion_rate=crm_count / bookings if bookings else 0.0,
        sms_completion_rate=sms_count / bookings if bookings else 0.0,
        estimated_recovered_revenue_usd=round(recovered_revenue, 2),
        baseline_expected_lost_calls=round(baseline_lost, 2),
    )


@router.get("/dashboard/{tenant_slug}", response_class=HTMLResponse)
def dashboard(
    request: Request,
    tenant_slug: str,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    tenant = get_tenant(db, tenant_slug)
    metric_data = metrics(tenant_slug, db)
    traces_data = traces(tenant_slug, db)
    suggestions = list_suggestions(tenant_slug, db)
    documents = db.scalar(
        select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.tenant_id == tenant.id
        )
    ) or 0
    appointments = db.scalar(
        select(func.count(Appointment.id)).where(Appointment.tenant_id == tenant.id)
    ) or 0
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "tenant": tenant,
            "metrics": metric_data,
            "traces": traces_data,
            "suggestions": suggestions,
            "documents": documents,
            "appointments": appointments,
        },
    )
