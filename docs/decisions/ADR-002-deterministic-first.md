# ADR-002 Deterministic-First Processing

## Status

Accepted

## Context

Unbounded LLM usage introduces instability, weak reproducibility, and audit gaps. Core platform operations require predictable behavior.

## Decision

Any step that can be deterministic must be implemented deterministically before adding generative reasoning.

## Consequences

- improves auditability and reliability;
- reduces hallucination surface area;
- increases pressure to define clear deterministic contracts.
