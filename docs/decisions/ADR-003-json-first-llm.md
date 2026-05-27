# ADR-003 JSON-First LLM Outputs

## Status

Accepted

## Context

Freeform prose outputs are difficult to validate and unsafe for machine-driven orchestration.

## Decision

All LLM outputs used by backend services must be JSON-only and schema-validated before downstream usage.

## Consequences

- enables robust parsing and validation;
- simplifies orchestration contracts;
- improves provider independence and failure handling.
