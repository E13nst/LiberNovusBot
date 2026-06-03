# ADR-008 Dual Contract: DialogueTurnV1 and StructuredDreamMemoryV1

## Status

Accepted

## Context

User-facing Telegram experience must be a living reflective dialogue. Backend still needs validated structured artifacts for admin, journal, and long-term pattern discovery.

A single `DreamAnalysisV1` report object was incorrectly used as both canonical memory and user-visible output.

## Decision

Split LLM contracts:

1. **DialogueTurnV1** — user-facing companion turn (`assistant_message` plus metadata). Validated JSON; prose lives inside the contract field, not as freeform transport.
2. **StructuredDreamMemoryV1** — background dream-scoped memory (motifs, figures, emotional field, amplification candidates, compensation hypotheses, open questions). Persisted asynchronously; not pushed to chat by default.

## Consequences

- ADR-003 (JSON-first) remains valid for both contracts.
- Dialogue path may call LLM synchronously at ingress; memory enrichment stays async.
- `session_analyses` may remain for legacy/debug; new canonical per-dream memory uses `dream_memories`.
