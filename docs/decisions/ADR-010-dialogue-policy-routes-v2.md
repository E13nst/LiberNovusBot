# ADR-010 Dialogue Policy Routes v2 (Dialogue-First)

## Status

Accepted

## Context

ADR-006 introduced deterministic routing with `ROUTE_REFLECTION`, `ROUTE_CLARIFICATION`, `ROUTE_SESSION_CONTINUE`, and `ROUTE_NOOP`. That model assumed reflection = persist dream + enqueue session analysis + async report delivery.

Dialogue-first architecture requires different side effects per route.

## Decision

Supersede reflection/continue semantics with:

| Route | Side effects |
|-------|----------------|
| `ROUTE_SAFETY` | Fixed safety response; no dream; no LLM symbolic analysis; no memory job |
| `ROUTE_NOOP` | No outbound content |
| `ROUTE_CLARIFICATION` | Short clarifying outbound message |
| `ROUTE_NEW_DREAM` | Persist dream; user turn; synchronous dialogue reply; enqueue dream memory job |
| `ROUTE_DIALOGUE_TURN` | User turn; synchronous dialogue reply; no new dream unless policy explicitly chose new dream |

Policy remains pure for semantic interpretation; safety uses deterministic heuristics only.

## Consequences

- Updates ADR-006 implementation note; route enum changes are breaking.
- `dialogue_policy_traces` continue to audit decisions at ingress.
- Legacy `ROUTE_REFLECTION` / `ROUTE_SESSION_CONTINUE` removed from engine (no backwards compatibility required).
