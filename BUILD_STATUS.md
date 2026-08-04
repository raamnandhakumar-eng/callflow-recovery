# Build status

## Verified locally

- Complete booking path through the orchestration API
- Grounded FAQ response with citation
- Emergency escalation
- Unsupported-question escalation
- Human approval into the knowledge base
- Regression-case creation
- Idempotent replay with one appointment, CRM write, and SMS record
- Vapi `tool-calls` adapter request and response contract
- Persisted metrics and server-rendered outcomes dashboard
- Six automated tests, 85% application coverage

## Runs in mock mode without credentials

- CRM writes receive deterministic mock contact IDs
- SMS messages receive deterministic mock message IDs
- Answer generation is deterministic and costs $0
- SQLite replaces PostgreSQL for local testing

## Requires external credentials for a live deployment

- Vapi or Retell phone number
- Public HTTPS deployment
- PostgreSQL with pgvector
- HubSpot private-app token
- Twilio credentials and sender number
- Optional OpenAI API key

## Claims boundary

This is a verified production-style vertical slice. It is not yet a customer production deployment. Do not claim real calls, real bookings, real cost measurements, recovered revenue, or a real incident until those events occur on connected infrastructure.
