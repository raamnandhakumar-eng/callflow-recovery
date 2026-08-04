# Integration playbook

## Vapi

1. Deploy the API over HTTPS.
2. Seed the tenant and approved knowledge.
3. Create the custom function tool from `config/vapi-tool.json`.
4. Replace `YOUR_PUBLIC_HOST` and attach the returned tool ID in `config/vapi-assistant.json`.
5. Configure a Vapi Custom Credential that sends `X-Vapi-Secret`, then set the same value in `VAPI_WEBHOOK_SECRET`.
6. The endpoint accepts Vapi `tool-calls` events and returns a `results` array keyed by `toolCallId`.
7. Place a real test call before adding CRM or SMS credentials.

## HubSpot

- Create a private app with contact read/write permissions.
- Set `HUBSPOT_ACCESS_TOKEN`.
- The adapter searches by phone, then updates or creates the contact.
- Local `crm_writes` records prevent duplicate writes when a call is replayed.

Only standard contact properties are sent to HubSpot. CallFlow-specific intent metadata stays in the local integration record.

## Twilio

- Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`.
- Trial accounts can send only to verified destinations.
- The adapter uses bounded retries and persists the returned message SID.

## Deployment sequence

1. Voice webhook with mocked downstream systems.
2. PostgreSQL and pgvector.
3. Twilio SMS.
4. HubSpot sandbox.
5. Synthetic regression suite.
6. Limited live traffic.
7. Dashboard review and failure-cluster approval.
