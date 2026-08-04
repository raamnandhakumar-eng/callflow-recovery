from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    baseline_lost_call_rate: Mapped[float] = mapped_column(Float, default=0.35)
    average_booking_value: Mapped[float] = mapped_column(Float, default=275.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(500), default="manual")
    content: Mapped[str] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tenant: Mapped[Tenant] = relationship()


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (UniqueConstraint("tenant_id", "external_call_id", name="uq_appointment_call"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    external_call_id: Mapped[str] = mapped_column(String(120))
    customer_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(40))
    service: Mapped[str] = mapped_column(String(160))
    scheduled_for: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CRMWrite(Base):
    __tablename__ = "crm_writes"
    __table_args__ = (UniqueConstraint("tenant_id", "external_call_id", name="uq_crm_call"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    external_call_id: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(40))
    contact_id: Mapped[str] = mapped_column(String(120))
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SMSMessage(Base):
    __tablename__ = "sms_messages"
    __table_args__ = (UniqueConstraint("tenant_id", "external_call_id", name="uq_sms_call"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    external_call_id: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(40))
    message_sid: Mapped[str] = mapped_column(String(120))
    to_number: Mapped[str] = mapped_column(String(40))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="sent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CallTrace(Base):
    __tablename__ = "call_traces"
    __table_args__ = (UniqueConstraint("tenant_id", "external_call_id", name="uq_trace_call"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    external_call_id: Mapped[str] = mapped_column(String(120), index=True)
    caller_phone: Mapped[str] = mapped_column(String(40))
    transcript: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(60))
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40))
    answer: Mapped[str] = mapped_column(Text, default="")
    citations_json: Mapped[str] = mapped_column(Text, default="[]")
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    crm_write_id: Mapped[int | None] = mapped_column(ForeignKey("crm_writes.id"), nullable=True)
    sms_id: Mapped[int | None] = mapped_column(ForeignKey("sms_messages.id"), nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class FAQSuggestion(Base):
    __tablename__ = "faq_suggestions"
    __table_args__ = (UniqueConstraint("tenant_id", "cluster_key", name="uq_suggestion_cluster"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    cluster_key: Mapped[str] = mapped_column(String(120))
    representative_question: Mapped[str] = mapped_column(Text)
    count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    suggested_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_documents.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RegressionCase(Base):
    __tablename__ = "regression_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    utterance: Mapped[str] = mapped_column(Text)
    expected_intent: Mapped[str] = mapped_column(String(60))
    expected_contains: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
