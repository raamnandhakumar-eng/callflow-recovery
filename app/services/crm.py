import hashlib
import json

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import CRMWrite, Tenant
from app.services.retry import with_retry


class CRMService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def upsert_contact(
        self,
        db: Session,
        tenant: Tenant,
        external_call_id: str,
        customer_name: str,
        phone: str,
        intent: str,
    ) -> CRMWrite:
        existing = db.scalar(
            select(CRMWrite).where(
                CRMWrite.tenant_id == tenant.id,
                CRMWrite.external_call_id == external_call_id,
            )
        )
        if existing:
            return existing

        payload = {
            "properties": {
                "firstname": customer_name,
                "phone": phone,
                "lifecyclestage": "lead",
            },
            "callflow_metadata": {"last_intent": intent},
        }
        if self.settings.hubspot_access_token:
            contact_id = await self._hubspot_upsert(phone, {"properties": payload["properties"]})
            provider = "hubspot"
        elif self.settings.demo_mode:
            contact_id = "demo-" + hashlib.sha256(
                f"{tenant.slug}:{phone}".encode("utf-8")
            ).hexdigest()[:12]
            provider = "demo"
        else:
            raise RuntimeError(
                "HubSpot is not configured. Set HUBSPOT_ACCESS_TOKEN or enable DEMO_MODE."
            )

        record = CRMWrite(
            tenant_id=tenant.id,
            external_call_id=external_call_id,
            provider=provider,
            contact_id=contact_id,
            payload_json=json.dumps(payload, sort_keys=True),
        )
        db.add(record)
        db.flush()
        return record

    async def _hubspot_upsert(self, phone: str, payload: dict[str, object]) -> str:
        headers = {
            "Authorization": f"Bearer {self.settings.hubspot_access_token}",
            "Content-Type": "application/json",
        }

        async def operation() -> str:
            async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
                search = await client.post(
                    "https://api.hubapi.com/crm/v3/objects/contacts/search",
                    headers=headers,
                    json={
                        "filterGroups": [
                            {"filters": [{"propertyName": "phone", "operator": "EQ", "value": phone}]}
                        ],
                        "limit": 1,
                    },
                )
                search.raise_for_status()
                results = search.json().get("results", [])
                if results:
                    contact_id = str(results[0]["id"])
                    update = await client.patch(
                        f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}",
                        headers=headers,
                        json=payload,
                    )
                    update.raise_for_status()
                    return contact_id
                create = await client.post(
                    "https://api.hubapi.com/crm/v3/objects/contacts",
                    headers=headers,
                    json=payload,
                )
                create.raise_for_status()
                return str(create.json()["id"])

        return await with_retry(operation, self.settings.max_external_retries)
