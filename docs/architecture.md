# Architecture

```mermaid
sequenceDiagram
    participant Caller
    participant Voice as Vapi / synthetic runner
    participant API as FastAPI orchestrator
    participant RAG as Retrieval service
    participant DB as PostgreSQL + pgvector
    participant CRM as HubSpot adapter
    participant SMS as Twilio adapter

    Caller->>Voice: Spoken request
    Voice->>API: Call ID, transcript, caller metadata
    API->>API: Fast intent routing
    API->>RAG: Retrieve approved tenant knowledge
    RAG->>DB: Tenant-scoped vector search
    DB-->>RAG: Ranked chunks
    RAG-->>API: Context and citations
    API->>DB: Create appointment using call ID as idempotency key
    API->>CRM: Upsert contact
    CRM-->>API: Contact ID
    API->>SMS: Send confirmation
    SMS-->>API: Message SID
    API->>DB: Persist trace, cost, latency, outcome
    API-->>Voice: Grounded response and final state
```

## Production boundaries

- `external_call_id` is the workflow idempotency key.
- Every persistent table includes `tenant_id`.
- The agent cannot claim success before the appointment row exists.
- CRM and SMS operations check local idempotency records before external calls.
- Unsupported questions create a learning-loop suggestion instead of a fabricated answer.
- The dashboard reads persisted outcomes, not model self-reports.

## Retrieval

PostgreSQL deployments use the `pgvector/pgvector:pg16` image and a tenant-scoped `kb_chunks` table. SQLite test environments use the same chunking contract with deterministic local embeddings and lexical scoring.
