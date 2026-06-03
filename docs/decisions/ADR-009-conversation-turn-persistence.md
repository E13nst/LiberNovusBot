# ADR-009 Conversation Turn Persistence

## Status

Accepted

## Context

Dream text, dialogue turns, and structured memory are different domain concepts. Treating every user message as a new `dreams` row breaks follow-up exploration and pollutes the journal.

## Decision

Introduce `conversation_turns` as the canonical record of user/assistant messages within a session:

- optional `dream_id` when the turn relates to a specific dream episode;
- `turn_type` and `role` for routing and presentation;
- assistant turns store dialogue output reference metadata, not duplicate full memory blobs.

Dream rows remain immutable raw dream material. Background memory links to `dream_id`.

## Consequences

- Ingress must persist user turns before or with assistant replies.
- Policy Engine routes side effects; it does not replace turn persistence.
- Mini App journal can show dream + dialogue excerpts + structured memory.
