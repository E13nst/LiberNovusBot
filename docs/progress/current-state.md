# Current State

## Current focus

Analysis Orchestrator layer (JSON-first, multi-stage, provider-agnostic).

## Completed stable layers

- dream persistence;
- session lifecycle with inactivity auto-close;
- deterministic session summaries;
- Jungian prompt builder / prompt compiler;
- prompt contract and prompt validation foundation.

## Current constraints

- deterministic-first architecture;
- provider-agnostic integrations;
- JSON-only AI outputs with schema validation;
- backend owns business logic;
- session-centric analysis context.

## Explicitly postponed

- embeddings and vector databases;
- advanced Mini App UI flows;
- archetype graphing and symbolic graph engine;
- premature model-specific optimizations.

## Source-of-truth priority

If documents conflict, resolve by this order:

1. `docs/progress/current-state.md`;
2. relevant ADR files in `docs/decisions/`;
3. `docs/architecture/*.md`;
4. `TASKS.md` (tactical execution only).
