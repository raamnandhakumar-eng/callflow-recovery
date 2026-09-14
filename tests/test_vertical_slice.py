import json

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Appointment, CRMWrite, FAQSuggestion, SMSMessage


def booking_payload(call_id: str = "call-book-1") -> dict[str, str]:
    return {
        "tenant_slug": "northstar-hvac",
        "external_call_id": call_id,
        "caller_phone": "+12125550123",
        "customer_name": "Jordan Lee",
        "transcript": "I need to book an appointment for an AC diagnostic.",
        "requested_time": "Thursday at 2 PM",
        "service": "AC diagnostic",
    }


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_full_booking_vertical_slice_and_idempotent_replay(client):
    first = client.post("/v1/calls/simulate", json=booking_payload())
    assert first.status_code == 200
    data = first.json()
    assert data["status"] == "booked"
    assert data["appointment_id"]
    assert data["crm_contact_id"].startswith("demo-")
    assert data["sms_message_id"].startswith("demo-")
    assert "simulated" in data["answer"].lower()
    assert data["replayed"] is False

    replay = client.post("/v1/calls/simulate", json=booking_payload())
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["appointment_id"] == data["appointment_id"]

    with SessionLocal() as db:
        assert db.scalar(select(func.count(Appointment.id))) == 1
        assert db.scalar(select(func.count(CRMWrite.id))) == 1
        assert db.scalar(select(func.count(SMSMessage.id))) == 1
        crm = db.scalar(select(CRMWrite))
        sms = db.scalar(select(SMSMessage))
        assert crm and crm.provider == "demo"
        assert sms and sms.provider == "demo" and sms.status == "simulated"


def test_grounded_faq_answer_has_citation(client):
    response = client.post(
        "/v1/calls/simulate",
        json={
            "tenant_slug": "northstar-hvac",
            "external_call_id": "call-faq-1",
            "caller_phone": "+12125550124",
            "customer_name": "Morgan",
            "transcript": "How much does a standard diagnostic visit cost?",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "$129" in data["answer"]
    assert data["citations"][0]["source"] == "test-policy.md"


def test_learning_loop_approves_knowledge_and_answers_next_call(client):
    question = "Do you service geothermal heat pumps in landmark buildings?"
    first = client.post(
        "/v1/calls/simulate",
        json={
            "tenant_slug": "northstar-hvac",
            "external_call_id": "call-gap-1",
            "caller_phone": "+12125550125",
            "customer_name": "Taylor",
            "transcript": question,
        },
    )
    assert first.status_code == 200
    assert first.json()["escalated"] is True

    suggestions = client.get("/v1/learning/northstar-hvac/suggestions").json()
    assert len(suggestions) == 1
    suggestion_id = suggestions[0]["id"]

    approved = client.post(
        f"/v1/learning/northstar-hvac/suggestions/{suggestion_id}/approve",
        json={
            "answer": (
                "Geothermal heat-pump visits require a specialist review before booking."
            )
        },
    )
    assert approved.status_code == 200

    second = client.post(
        "/v1/calls/simulate",
        json={
            "tenant_slug": "northstar-hvac",
            "external_call_id": "call-gap-2",
            "caller_phone": "+12125550126",
            "customer_name": "Taylor",
            "transcript": question,
        },
    )
    assert second.status_code == 200
    assert second.json()["status"] == "answered"
    assert "Geothermal" in second.json()["answer"]

    with SessionLocal() as db:
        suggestion = db.scalar(select(FAQSuggestion))
        assert suggestion and suggestion.status == "approved"


def test_metrics_use_persisted_outcomes(client):
    client.post("/v1/calls/simulate", json=booking_payload("call-book-metrics"))
    client.post(
        "/v1/calls/simulate",
        json={
            "tenant_slug": "northstar-hvac",
            "external_call_id": "call-emergency-1",
            "caller_phone": "+12125550127",
            "customer_name": "Casey",
            "transcript": "There is smoke from my furnace. This is an emergency.",
        },
    )
    response = client.get("/v1/metrics/northstar-hvac")
    assert response.status_code == 200
    metrics = response.json()
    assert metrics["calls"] == 2
    assert metrics["bookings"] == 1
    assert metrics["crm_completion_rate"] == 1.0
    assert metrics["sms_completion_rate"] == 1.0
    assert metrics["estimated_recovered_revenue_usd"] == 300.0


def test_vapi_tool_call_adapter_runs_vertical_slice(client):
    response = client.post(
        "/v1/webhooks/vapi",
        json={
            "message": {
                "type": "tool-calls",
                "call": {"id": "vapi-call-1"},
                "customer": {"number": "+12125550199"},
                "toolCallList": [
                    {
                        "id": "tool-call-1",
                        "name": "handle_customer_request",
                        "parameters": {
                            "tenant_slug": "northstar-hvac",
                            "customer_name": "Vapi Caller",
                            "caller_phone": "+12125550199",
                            "transcript": (
                                "I need to book an appointment for an AC diagnostic."
                            ),
                            "requested_time": "Friday at 10 AM",
                            "service": "AC diagnostic",
                        },
                    }
                ],
            }
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"][0]["toolCallId"] == "tool-call-1"
    result = json.loads(payload["results"][0]["result"])
    assert result["status"] == "booked"
    assert result["external_call_id"] == "vapi-call-1"
