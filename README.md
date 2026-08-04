# CallFlow Recovery

**A complete forward-deployed vertical slice:** caller intent → approved knowledge → appointment → CRM → SMS → persisted outcome.

CallFlow Recovery is a production-style reference deployment for a service business that believes it is "losing calls." The build treats the real problem as a chain of business-state changes, not as a conversational demo.

## Working path

1. Receive a real Vapi webhook or a synthetic call.
2. Route intent with a fast local classifier.
3. Retrieve tenant-approved knowledge from PostgreSQL and pgvector.
4. Produce a concise grounded answer with citations.
5. Create an appointment before claiming success.
6. Upsert the customer in HubSpot, or use the deterministic mock adapter.
7. Send a Twilio SMS confirmation, or use the deterministic mock adapter.
8. Persist the full trace, cost, latency, and final outcome.
9. Surface unresolved questions for human approval.
10. Turn approved answers into knowledge and regression cases.

## Why this is not a chatbot demo

- A booking is successful only when the appointment row exists.
- Replayed webhooks return the original result and do not duplicate downstream actions.
- Unsupported requests escalate instead of receiving fabricated answers.
- Metrics come from persisted traces and integration records.
- The dashboard reports booking conversion, p95 latency, cost per booking, CRM/SMS completion, and estimated recovered revenue.

## Architecture

```mermaid
flowchart LR
    A[Caller / Vapi] --> B[FastAPI orchestrator]
    B --> C[Intent router]
    B --> D[RAG service]
    D --> E[(PostgreSQL + pgvector)]
    B --> F[Appointment]
    B --> G[HubSpot]
    B --> H[Twilio SMS]
    B --> I[(Trace and outcome store)]
    I --> J[Outcomes dashboard]
    I --> K[Learning-loop queue]
    K --> D
```

## Run locally with SQLite and mock integrations

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
python scripts/seed.py
uvicorn app.main:app --reload
```

In a second terminal:

```bash
python scripts/run_scenarios.py --replay
```

Open:

- API docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8000/dashboard/northstar-hvac`

## Run with PostgreSQL and pgvector

```bash
cp .env.example .env
docker compose up --build
```

The Compose deployment uses `pgvector/pgvector:pg16` and automatically seeds two tenants.

## Connect real infrastructure

### Vapi

Create the custom function from `config/vapi-tool.json`, attach its ID using `config/vapi-assistant.json`, and configure a secured server credential. The Vapi adapter accepts `tool-calls` events and returns results keyed by `toolCallId`. The synthetic runner exercises the same orchestration service used by the voice adapter.

### HubSpot

Set `HUBSPOT_ACCESS_TOKEN`. Without it, the system uses a deterministic mock CRM ID. The live adapter searches by phone before create/update, while the local workflow record protects replay idempotency.

### Twilio

Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`. Without them, the system records a deterministic mock message SID.

### OpenAI

Set `OPENAI_API_KEY` to use a live model for grounded answer generation. Without it, a deterministic generator keeps tests and demos reproducible. Token and cost fields are persisted in either mode.

## Synthetic scenarios

The runner includes:

- appointment booking;
- price question;
- after-hours emergency;
- unresolved knowledge gap;
- optional replay of the booking call to prove idempotency.

```bash
python scripts/run_scenarios.py --base-url http://localhost:8000 --replay
```

## Learning loop

An unsupported call creates a clustered FAQ suggestion. Approving it:

- creates an approved knowledge document;
- marks the suggestion approved;
- creates a regression case;
- allows the next matching call to answer from the new source.

This is intentionally human-gated. The system does not silently promote model-generated content into customer-facing knowledge.

## Tests

```bash
ruff check .
pytest --cov=app --cov-report=term-missing
```

The integration tests prove the complete mocked vertical slice, grounded retrieval, idempotent replay, persisted metrics, and learning-loop approval.

## Production evidence to collect next

The repository is runnable without paid infrastructure, but the portfolio claim becomes materially stronger after these real steps:

1. connect a Vapi or Retell number;
2. place and record real calls;
3. connect a HubSpot sandbox;
4. send a real Twilio confirmation;
5. deploy PostgreSQL with pgvector;
6. record p50/p95 latency and cost per booking;
7. replace `docs/incident-report.md` with a genuine incident from the live deployment.

Do not describe the project as a customer production deployment until a real external user depends on it.

## Documentation

- [`docs/discovery-notes.md`](docs/discovery-notes.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/integration-playbook.md`](docs/integration-playbook.md)
- [`docs/cost-playbook.md`](docs/cost-playbook.md)
- [`docs/incident-report.md`](docs/incident-report.md)
- [`docs/live-deployment-checklist.md`](docs/live-deployment-checklist.md)
- [`BUILD_STATUS.md`](BUILD_STATUS.md)
