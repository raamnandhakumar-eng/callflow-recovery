from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Tenant
from app.services.rag import RAGService

TENANTS = [
    {
        "slug": "northstar-hvac",
        "name": "Northstar Heating & Air",
        "baseline_lost_call_rate": 0.38,
        "average_booking_value": 325.0,
        "documents": [
            (
                "Service and pricing policy",
                "operations/service-policy.md",
                """Northstar provides heating and cooling service across Manhattan and Brooklyn. Standard diagnostic visits start at $129. The final repair price is quoted after diagnosis and customer approval.

Northstar offers appointments Monday through Saturday from 8:00 AM to 7:00 PM. After-hours emergency calls are transferred to the on-call technician.

For suspected gas leaks, smoke, sparking, or active flooding, callers should move to a safe location and contact emergency services when appropriate before waiting for a technician.""",
            ),
            (
                "Booking policy",
                "operations/booking-policy.md",
                """A booking requires the caller's name, phone number, requested service, and preferred time. The system must create the appointment before claiming it is confirmed.

Every confirmed booking must create or update a CRM contact and send an SMS confirmation. Replayed calls must not create duplicate appointments, CRM writes, or SMS messages.""",
            ),
        ],
    },
    {
        "slug": "harbor-dental",
        "name": "Harbor Dental Group",
        "baseline_lost_call_rate": 0.29,
        "average_booking_value": 210.0,
        "documents": [
            (
                "Dental office FAQ",
                "operations/dental-faq.md",
                """Harbor Dental accepts new-patient appointments Monday through Friday. Emergency dental pain is routed to the clinical triage queue.

The office can provide general insurance participation information, but final coverage and patient responsibility must be confirmed by the insurer.""",
            )
        ],
    },
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    rag = RAGService()
    with SessionLocal() as db:
        for item in TENANTS:
            tenant = db.scalar(select(Tenant).where(Tenant.slug == item["slug"]))
            if not tenant:
                tenant = Tenant(
                    slug=item["slug"],
                    name=item["name"],
                    baseline_lost_call_rate=item["baseline_lost_call_rate"],
                    average_booking_value=item["average_booking_value"],
                )
                db.add(tenant)
                db.flush()
                for title, source, content in item["documents"]:
                    rag.ingest(db, tenant, title, source, content)
        db.commit()
    print("Seeded tenants and approved knowledge documents.")


if __name__ == "__main__":
    main()
