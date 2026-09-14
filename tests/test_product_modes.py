import asyncio

import pytest
from sqlalchemy import select

from app.config import Settings
from app.db import SessionLocal
from app.models import Tenant
from app.services.crm import CRMService
from app.services.sms import SMSService


def test_recruiter_demo_readiness(client):
    response = client.get("/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready_for_recruiter_demo"
    assert payload["mode"] == "demo"
    assert payload["integrations"]["database"] is True
    assert "crm" in payload["simulated_actions"]
    assert "sms" in payload["simulated_actions"]


def test_strict_mode_rejects_missing_crm_credentials():
    settings = Settings(
        demo_mode=False,
        hubspot_access_token=None,
        twilio_account_sid=None,
        twilio_auth_token=None,
        twilio_from_number=None,
    )
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == "northstar-hvac"))
        assert tenant is not None
        with pytest.raises(RuntimeError, match="HubSpot is not configured"):
            asyncio.run(
                CRMService(settings).upsert_contact(
                    db,
                    tenant,
                    "strict-crm-test",
                    "Jordan Lee",
                    "+12125550123",
                    "appointment",
                )
            )


def test_strict_mode_rejects_missing_sms_credentials():
    settings = Settings(
        demo_mode=False,
        hubspot_access_token=None,
        twilio_account_sid=None,
        twilio_auth_token=None,
        twilio_from_number=None,
    )
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == "northstar-hvac"))
        assert tenant is not None
        with pytest.raises(RuntimeError, match="Twilio is not configured"):
            asyncio.run(
                SMSService(settings).send_confirmation(
                    db,
                    tenant,
                    "strict-sms-test",
                    "+12125550123",
                    "Test confirmation",
                )
            )
