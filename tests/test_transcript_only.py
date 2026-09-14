from sqlalchemy import select

from app.db import SessionLocal
from app.models import Appointment


def test_transcript_only_booking_infers_service_and_time(client):
    response = client.post(
        "/v1/calls/simulate",
        json={
            "tenant_slug": "northstar-hvac",
            "external_call_id": "call-transcript-only-1",
            "caller_phone": "+12125550123",
            "transcript": "Hi, my AC stopped working. I need an AC diagnostic Thursday at 2 PM.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "booked"
    assert payload["appointment_id"]
    assert payload["crm_contact_id"].startswith("demo-")
    assert payload["sms_message_id"].startswith("demo-")

    with SessionLocal() as db:
        appointment = db.scalar(
            select(Appointment).where(
                Appointment.external_call_id == "call-transcript-only-1"
            )
        )
        assert appointment is not None
        assert appointment.phone == "+12125550123"
        assert appointment.service == "AC diagnostic"
        assert appointment.scheduled_for == "Thursday at 2 PM"
        assert appointment.customer_name == "Caller"
