# Build status

## Recruiter demo status

The public application is designed to be usable without sign-in or external credentials. `DEMO_MODE=true` keeps the complete orchestration path runnable while clearly marking CRM and SMS actions as simulated when live credentials are absent.

Verified behavior:

- Complete appointment path through the orchestration API
- Grounded FAQ response with citation
- Emergency escalation
- Unsupported-question escalation
- Human approval into the knowledge base
- Regression-case creation
- Idempotent replay with one appointment, CRM write, and SMS record
- Vapi `tool-calls` adapter request and response contract
- Persisted metrics and server-rendered outcomes dashboard
- `/ready` deployment-readiness endpoint
- Demo/live integration boundary tests
- **13 automated tests passing**
- **87% application test coverage**
- Ruff lint checks passing in GitHub Actions

## Explicit demo mode

When live credentials are absent and `DEMO_MODE=true`:

- CRM writes use deterministic `demo-*` contact IDs and provider `demo`
- SMS writes use deterministic `demo-*` message IDs, provider `demo`, and status `simulated`
- Customer-facing demo results state that CRM and SMS actions were simulated
- Answer generation is deterministic when no OpenAI key is configured
- The public Render configuration uses SQLite demo storage and reseeds the demo tenant on startup

The demo does not present simulated HubSpot or Twilio actions as real external sends.

## Strict live mode

Set `DEMO_MODE=false` for live traffic. In strict mode the workflow fails closed when required downstream credentials are missing instead of fabricating successful actions.

Live infrastructure requires:

- Vapi or another supported voice provider and phone number
- Public HTTPS endpoint
- Durable database, preferably PostgreSQL
- HubSpot private-app token for live CRM writes
- Twilio credentials and sender number for live SMS
- Optional OpenAI API key for live model generation

## Claims boundary

This is a verified production-style AI workflow and an interactive recruiter demo. It is not yet a customer production deployment. Do not claim real external CRM writes, real SMS delivery, customer production usage, recovered revenue, or production incidents until those events occur on connected infrastructure.
