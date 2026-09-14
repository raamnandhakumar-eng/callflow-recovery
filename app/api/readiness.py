from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db

router = APIRouter()
settings = get_settings()


@router.get("/ready")
def readiness(db: Session = Depends(get_db)) -> JSONResponse:
    database_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        database_ok = False

    integrations = {
        "database": database_ok,
        "voice": bool(settings.vapi_webhook_secret),
        "crm": bool(settings.hubspot_access_token),
        "sms": bool(
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_from_number
        ),
        "llm": bool(settings.openai_api_key),
    }

    if settings.demo_mode:
        ready = database_ok
        status = "ready_for_recruiter_demo" if ready else "not_ready"
    else:
        ready = database_ok and integrations["voice"] and integrations["crm"] and integrations["sms"]
        status = "ready_for_live_traffic" if ready else "not_ready"

    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": status,
            "mode": "demo" if settings.demo_mode else "live",
            "integrations": integrations,
            "simulated_actions": (
                [name for name in ("crm", "sms") if not integrations[name]]
                if settings.demo_mode
                else []
            ),
        },
    )
