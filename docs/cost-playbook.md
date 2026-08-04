# Cost and latency playbook

## What is measured

Each call trace records:

- input tokens;
- output tokens;
- model cost;
- end-to-end orchestration latency;
- final outcome;
- appointment, CRM, and SMS identifiers.

The dashboard derives cost per call and cost per booking from persisted traces.

## Hot-path decisions

- Route common intents with deterministic logic before using a large model.
- Retrieve only three compact chunks.
- Keep spoken answers short.
- Use approved static knowledge for frequent questions.
- Escalate when evidence is weak instead of paying for repeated generation attempts.
- Keep CRM and SMS work idempotent so retries do not create duplicate customer actions.

## Tradeoff to discuss

A larger model may produce smoother speech, but additional latency can increase caller interruption and abandonment. The initial deployment therefore favors a small model and narrow workflow tools. Model upgrades should be tested against booking completion, unsupported-claim rate, p95 latency, and cost per booking rather than answer style alone.
