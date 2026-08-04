import os
from pathlib import Path

import pytest

TEST_DB = Path("/tmp/callflow_recovery_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("HUBSPOT_ACCESS_TOKEN", None)
os.environ.pop("TWILIO_ACCOUNT_SID", None)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Tenant  # noqa: E402
from app.services.rag import RAGService  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        tenant = Tenant(
            slug="northstar-hvac",
            name="Northstar Heating & Air",
            baseline_lost_call_rate=0.4,
            average_booking_value=300.0,
        )
        db.add(tenant)
        db.flush()
        RAGService().ingest(
            db,
            tenant,
            "Service policy",
            "test-policy.md",
            (
                "Standard diagnostic visits start at $129. "
                "Appointments are available Monday through Saturday."
            ),
        )
        db.commit()
        assert db.scalar(select(Tenant).where(Tenant.slug == "northstar-hvac"))
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
