import hashlib
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import SMSMessage, Tenant
from app.services.retry import with_retry


class SMSService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send_confirmation(
        self,
        db: Session,
        tenant: Tenant,
        external_call_id: str,
        to_number: str,
        body: str,
    ) -> SMSMessage:
        existing = db.scalar(
            select(SMSMessage).where(
                SMSMessage.tenant_id == tenant.id,
                SMSMessage.external_call_id == external_call_id,
            )
        )
        if existing:
            return existing

        if all(
            (
                self.settings.twilio_account_sid,
                self.settings.twilio_auth_token,
                self.settings.twilio_from_number,
            )
        ):
            message_sid = await self._send_twilio(to_number, body)
            provider = "twilio"
        elif self.settings.demo_mode:
            message_sid = "demo-" + hashlib.sha256(
                f"{tenant.slug}:{external_call_id}:{to_number}".encode("utf-8")
            ).hexdigest()[:12]
            provider = "demo"
        else:
            raise RuntimeError(
                "Twilio is not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
                "and TWILIO_FROM_NUMBER or enable DEMO_MODE."
            )

        record = SMSMessage(
            tenant_id=tenant.id,
            external_call_id=external_call_id,
            provider=provider,
            message_sid=message_sid,
            to_number=to_number,
            body=body,
            status="sent" if provider == "twilio" else "simulated",
        )
        db.add(record)
        db.flush()
        return record

    async def _send_twilio(self, to_number: str, body: str) -> str:
        sid = str(self.settings.twilio_account_sid)
        auth = (sid, str(self.settings.twilio_auth_token))
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        encoded = urlencode(
            {"To": to_number, "From": self.settings.twilio_from_number, "Body": body}
        )

        async def operation() -> str:
            async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
                response = await client.post(
                    url,
                    content=encoded,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    auth=auth,
                )
                response.raise_for_status()
                return str(response.json()["sid"])

        return await with_retry(operation, self.settings.max_external_retries)
