# ADR-005 PostgreSQL as Source of Truth

## Status

Accepted

## Context

Distributed state across bot memory, caches, and clients causes inconsistency in session and analysis history.

## Decision

PostgreSQL is the only source of truth for persistent domain data. Clients, bots, and transient stores are non-authoritative.

## Consequences

- consistent recovery and audit paths;
- clearer ownership boundaries in backend;
- stricter persistence discipline for new features.
