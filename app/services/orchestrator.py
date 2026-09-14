import json
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Appointment, CallTrace, CRMWrite, SMSMessage, Tenant
from app.schemas import CallResult, SimulatedCallRequest
from app.services.crm import CRMService
from app.services.intent import IntentRouter
from app.services.learning import LearningService
from app.services.llm import AnswerGenerator
from app.services.rag import RAGService
from app.services.sms import SMSService


class CallOrchestrator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.intent_router = IntentRouter()
        self.rag = RAGService()
        self.generator = AnswerGenerator(settings)
        self.crm = CRMService(settings)
        self.sms = SMSService(settings)
        self.learning = LearningService()

    async def handle(
        self,
        db: Session,
        tenant: Tenant,
        request: SimulatedCallRequest,
    ) -> CallResult:
        existing = db.scalar(
            select(CallTrace).where(
                CallTrace.tenant_id == tenant.id,
                CallTrace.external_call_id == request.external_call_id,
            )
        )
        if existing:
            return self._result_from_trace(db, existing, replayed=True)

        started = time.perf_counter()
        steps: list[dict[str, object]] = []
        intent = self.intent_router.classify(request.transcript)
        steps.append(
            {
                "step": "intent_routing",
                "intent": intent.name,
                "confidence": intent.confidence,
            }
        )

        chunks = self.rag.retrieve(db, tenant, request.transcript, top_k=3)
        steps.append(
            {
                "step": "retrieval",
                "documents": [chunk.document_id for chunk in chunks],
                "scores": [round(chunk.score, 4) for chunk in chunks],
            }
        )
        generated = await self.generator.answer(request.transcript, chunks)
        citations = [
            {"title": chunk.title, "source": chunk.source, "content": chunk.content[:180]}
            for chunk in chunks
            if chunk.score >= 0.18
        ]

        appointment: Appointment | None = None
        crm_write: CRMWrite | None = None
        sms: SMSMessage | None = None
        escalated = False
        status = "answered"
        answer = generated.text

        if intent.name == "appointment":
            appointment = Appointment(
                tenant_id=tenant.id,
                external_call_id=request.external_call_id,
                customer_name=request.customer_name,
                phone=request.caller_phone,
                service=request.service or "HVAC service visit",
                scheduled_for=request.requested_time or "next available slot",
                status="confirmed",
            )
            db.add(appointment)
            db.flush()
            steps.append({"step": "appointment_created", "appointment_id": appointment.id})
            crm_write = await self.crm.upsert_contact(
                db,
                tenant,
                request.external_call_id,
                request.customer_name,
                request.caller_phone,
                intent.name,
            )
            steps.append(
                {
                    "step": "crm_upsert",
                    "provider": crm_write.provider,
                    "contact_id": crm_write.contact_id,
                }
            )
            confirmation = (
                f"{tenant.name}: your {appointment.service} is booked for "
                f"{appointment.scheduled_for}. Reply HELP if you need assistance."
            )
            sms = await self.sms.send_confirmation(
                db,
                tenant,
                request.external_call_id,
                request.caller_phone,
                confirmation,
            )
            steps.append(
                {
                    "step": "sms_confirmation",
                    "provider": sms.provider,
                    "message_id": sms.message_sid,
                    "status": sms.status,
                }
            )
            if sms.provider == "demo":
                answer = (
                    f"Demo booking created for {appointment.service} at "
                    f"{appointment.scheduled_for}. CRM and SMS actions were simulated."
                )
            else:
                answer = (
                    f"Your {appointment.service} is booked for {appointment.scheduled_for}. "
                    "I sent a confirmation text."
                )
            status = "booked"
        elif intent.name == "emergency":
            escalated = True
            status = "escalated"
            answer = (
                "This may be an emergency. Please move to a safe location. "
                "I am transferring you to the on-call technician now."
            )
            steps.append({"step": "human_escalation", "queue": "on-call"})
        elif intent.name in {"unknown", "reschedule"} or not citations:
            escalated = True
            status = "escalated"
            self.learning.register_unresolved(db, tenant, request.transcript)
            steps.append({"step": "learning_queue", "reason": "unsupported_or_unimplemented"})
            answer = (
                "I do not have enough approved information to complete that safely. "
                "I am transferring you to a team member."
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        now = datetime.now(timezone.utc)
        trace = CallTrace(
            tenant_id=tenant.id,
            external_call_id=request.external_call_id,
            caller_phone=request.caller_phone,
            transcript=request.transcript,
            intent=intent.name,
            confidence=intent.confidence,
            status=status,
            answer=answer,
            citations_json=json.dumps(citations),
            steps_json=json.dumps(steps),
            started_at=now,
            completed_at=now,
            latency_ms=latency_ms,
            input_tokens=generated.input_tokens,
            output_tokens=generated.output_tokens,
            cost_usd=generated.cost_usd,
            appointment_id=appointment.id if appointment else None,
            crm_write_id=crm_write.id if crm_write else None,
            sms_id=sms.id if sms else None,
            escalated=escalated,
        )
        db.add(trace)
        db.commit()
        return self._result_from_trace(db, trace, replayed=False)

    @staticmethod
    def _result_from_trace(db: Session, trace: CallTrace, replayed: bool) -> CallResult:
        appointment = db.get(Appointment, trace.appointment_id) if trace.appointment_id else None
        crm_write = db.get(CRMWrite, trace.crm_write_id) if trace.crm_write_id else None
        sms = db.get(SMSMessage, trace.sms_id) if trace.sms_id else None
        return CallResult(
            external_call_id=trace.external_call_id,
            intent=trace.intent,
            confidence=trace.confidence,
            status=trace.status,
            answer=trace.answer,
            citations=json.loads(trace.citations_json),
            appointment_id=appointment.id if appointment else None,
            crm_contact_id=crm_write.contact_id if crm_write else None,
            sms_message_id=sms.message_sid if sms else None,
            escalated=trace.escalated,
            latency_ms=trace.latency_ms,
            input_tokens=trace.input_tokens,
            output_tokens=trace.output_tokens,
            cost_usd=trace.cost_usd,
            replayed=replayed,
        )
