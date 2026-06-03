# ADR-006 Dialogue Policy Engine as Deterministic Router

## Status

Accepted

## Context

Current analysis flow already separates deterministic lifecycle decisions from LLM execution (`analysis_state_machine_service` vs orchestrator/provider layers). For dialogue turns, the system now needs a policy boundary that controls routing without introducing semantic interpretation in core services.

Without this boundary, decision logic risks being split across transport, reflection transformers, and delivery formatters, which weakens explainability and testability.

## Decision

Introduce `services/dialogue_policy` as a pure deterministic routing layer with:

- immutable contract types (`PolicyInput`, `PolicyDecision`);
- routing-only outputs (`ROUTE_REFLECTION`, `ROUTE_CLARIFICATION`, `ROUTE_SESSION_CONTINUE`, `ROUTE_NOOP`);
- structural and session-state input signals only (`is_empty`, `text_length`, `token_count`, `input_type`, `session_state`);
- fixed deterministic confidence (`1.0`) and opaque debug `reason_code`.

The Dialogue Policy Engine does not perform semantic dream interpretation and does not depend on DB, ORM, providers, Telegram transport, or reflection rendering.

## Consequences

- clarifies ownership: Policy routes, Reflection analyzes, Telegram renders;
- enables focused unit tests for routing contracts without network or database;
- preserves deterministic-first and provider-agnostic architecture boundaries.

Deferred scope (follow-up work):

- persistence of policy decisions for audit/replay;
- unified channel-level presentation alignment after routing integration.

## Implementation note (#025)

Production wiring is now introduced at ingress/runtime boundaries with these invariants:

- Policy is called exactly once per inbound message in ingress;
- runtime services consume `PolicyDecision` and must not re-invoke Policy;
- `ROUTE_REFLECTION` is the only stateful path (dream persistence + `analysis_job` enqueue);
- `ROUTE_CLARIFICATION`, `ROUTE_SESSION_CONTINUE`, `ROUTE_NOOP` are stateless in #025 (no dream row, no `analysis_job`);
- dialogue event persistence is deferred to a future memory layer (#026+), so Policy remains deterministic and non-event-sourced.

## Superseded by ADR-010

Route vocabulary and side-effect semantics from #025 are superseded by dialogue-first routes (`ROUTE_NEW_DREAM`, `ROUTE_DIALOGUE_TURN`, `ROUTE_SAFETY`). See [ADR-010-dialogue-policy-routes-v2.md](./ADR-010-dialogue-policy-routes-v2.md).
