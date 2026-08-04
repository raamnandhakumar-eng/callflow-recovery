# Discovery notes

## Stated problem

The customer says, "We are losing inbound calls because the front desk is too busy."

## Questions asked before proposing a build

- Which calls are considered lost: unanswered, abandoned, after-hours, or unresolved?
- Which intents create revenue, safety, or compliance risk?
- Where are appointments recorded today?
- What must be true before the system may say an appointment is confirmed?
- Which answers require approved source material?
- What is the human escalation path during and after business hours?
- Which system is the source of truth for customer identity and appointment status?
- What is an acceptable voice-response latency?
- What is the average value of a recovered booking?

## Actual constraint found

The operating problem is not simply answering more calls. It is completing a reliable chain of work:

1. recognize intent quickly;
2. answer only from approved knowledge;
3. create the appointment in the system of record;
4. update the CRM without duplication;
5. send confirmation;
6. escalate unsafe or unsupported requests;
7. record the outcome so the customer can see what changed.

A pleasant voice response without those state changes is still a failed deployment.

## Initial scope decision

The first release supports three workflows:

- appointment booking;
- emergency routing;
- grounded FAQ answers.

Rescheduling is deliberately escalated until the calendar source-of-truth integration supports safe modification and conflict checks.
