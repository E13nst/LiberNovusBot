# Capability Milestone: Dream Intake and Storage

## Outcome

Dream intake pipeline persists incoming user dream messages in backend storage.

## Includes

- Telegram input transport to backend endpoint;
- dream persistence in PostgreSQL;
- initial PUBLIC/AUTH split support;
- baseline service and router wiring for intake.

## Invariants

- raw dream text is stored as source material;
- persistence is backend-owned;
- transport layer does not own business logic.
