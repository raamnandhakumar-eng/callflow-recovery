# Incident 001: replay created duplicate downstream actions

## Status

Template until a live integration produces a real incident. Replace this file with the actual event before presenting it as production experience.

## Expected behavior

A retried or replayed voice webhook should return the original outcome without creating a second appointment, CRM write, or SMS message.

## Failure mode to test

The voice provider times out after the backend completes the CRM write, then retries the webhook with the same call ID.

## Control implemented

- `external_call_id` is unique per tenant in the trace, appointment, CRM-write, and SMS tables.
- The orchestrator returns an existing trace immediately on replay.
- Downstream adapters check their local idempotency record before issuing an external request.
- The synthetic runner supports `--replay` to prove the behavior.

## Evidence required before calling this resolved

- Run the same call ID twice.
- Confirm one appointment row.
- Confirm one CRM-write row.
- Confirm one SMS row.
- Capture the provider retry log and dashboard trace.
