# ADR-004 Provider Abstraction

## Status

Accepted

## Context

Provider lock-in and provider-specific response handling inside domain logic increase migration cost and architectural fragility.

## Decision

Integrate LLM vendors only through provider abstractions. Domain/business logic must not depend on provider-specific SDKs or response formats.

## Consequences

- easier provider switching and hybrid setups;
- cleaner separation of concerns;
- requires adapter and contract discipline for each provider.
