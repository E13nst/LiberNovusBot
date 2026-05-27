# ADR-001 Session-Centric Architecture

## Status

Accepted

## Context

Dream analysis quality degrades when each message is treated as an isolated event. The product requires longitudinal continuity and symbolic recurrence tracking.

## Decision

All core analytical flows are session-centric by default. Backend services own session lifecycle and continuity rules.

## Consequences

- improves longitudinal coherence of analysis;
- enforces backend ownership of lifecycle logic;
- requires strict session linkage for persisted dreams.
