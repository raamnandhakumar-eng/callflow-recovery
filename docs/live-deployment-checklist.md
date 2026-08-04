# Live deployment checklist

## Milestone 0: de-risk voice

- [ ] Deploy the API over HTTPS.
- [ ] Create the Vapi custom tool.
- [ ] Attach the tool to an inbound assistant.
- [ ] Place one call that triggers `handle_customer_request`.
- [ ] Confirm the tool result is spoken correctly.
- [ ] Record actual tool latency and any timeout.

## Milestone 1: complete real path

- [ ] Provision PostgreSQL with pgvector.
- [ ] Connect a HubSpot sandbox.
- [ ] Connect Twilio SMS.
- [ ] Book an appointment through a real call.
- [ ] Confirm exactly one appointment, CRM record, SMS, and trace.
- [ ] Replay the Vapi event and prove no duplicate side effects.

## Milestone 2: production evidence

- [ ] Run at least 30 synthetic calls.
- [ ] Record p50 and p95 latency.
- [ ] Record model and telephony cost per call and booking.
- [ ] Measure unsupported-answer and escalation rates.
- [ ] Replace the incident template with a real incident.
- [ ] Capture screenshots of the provider logs and dashboard.

## Milestone 3: external pilot

- [ ] Recruit one real service business or operational user.
- [ ] Document the stated problem and discovery findings.
- [ ] Establish a before-period baseline.
- [ ] Run limited live traffic with human fallback.
- [ ] Report measured outcomes without extrapolating beyond the pilot.
