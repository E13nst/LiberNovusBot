# Current State

## Current focus

Stabilization of DB-backed async analysis runtime on top of deterministic analysis orchestration, with explicit `ENV_MODE` safety boundaries for local/test/prod execution.

## Completed stable layers

- dream persistence;
- session lifecycle with inactivity auto-close;
- deterministic session summaries;
- Jungian prompt builder / prompt compiler;
- prompt contract and prompt validation foundation;
- analysis input aggregation (`analysis_input_service`);
- analysis contract + JSON validation (`analysis_contract`);
- analysis orchestrator with mock LLM provider;
- real provider abstraction layer (`LLMProvider`, provider registry, OpenAI, OpenAI-compatible transport);
- raw response parsing gate (`response_parser.extract_json`) before schema enforcement;
- orchestrator-level retry policy for transient transport failures;
- session analysis persistence (`session_analyses` table);
- analysis threads + continuation layer (`analysis_threads`, `analysis_continuation_service`, `analysis_thread_service`);
- analysis state machine v2 (`analysis_state_machine_service`, `analysis_snapshot_service`, `analysis_policy`);
- thread lifecycle statuses: `active`, `idle`, `closed` with `last_activity_at` freshness gate;
- pure decision layer + executor-only thread service + continuation orchestration with bounded re-resolve;
- write-only `is_latest` per thread (partial unique index);
- one `active` thread per session (partial unique index);
- analysis API: `POST /sessions/{id}/analyze?mode=auto|new|continue`, grouped `GET /sessions/{id}/analysis`;
- async analysis runtime: `POST /sessions/{id}/analyze-async`, `GET /analysis-jobs/{id}`, `GET /sessions/{id}/analysis-jobs`;
- DB-backed `analysis_jobs` queue with polling worker, bounded concurrency, delayed retry via `available_after`;
- sync `POST /sessions/{id}/analyze` remains compatibility/debug/manual execution only and bypasses runtime queue;
- async runtime path is the canonical production execution flow.
- runtime configuration layer (`services/config/runtime_config.py`): immutable `RuntimeConfig` as single source of truth;
- `ENV_MODE=local|test|prod` with startup validation split into config / infra / runtime guard layers;
- `settings.py` is a compatibility facade only (no decision logic);
- pytest forces `ENV_MODE=test` with mock provider and runtime worker disabled before app imports.

## Runtime modes (`ENV_MODE`)

| Mode | LLM provider | Runtime worker | Validation |
|------|--------------|----------------|------------|
| `local` | mock or real OpenAI / compatible | optional (`ANALYSIS_RUNTIME_ENABLED`) | relaxed; warnings for missing keys |
| `test` | forced `mock` | forced disabled | hard fail if overridden; no external LLM |
| `prod` | non-mock, requires `OPENAI_API_KEY` | required enabled | hard fail on misconfig at startup |

Safety guarantees:

- no silent fallback to mock for unknown providers;
- `prod` cannot boot without `OPENAI_API_KEY` or with `LLM_PROVIDER=mock`;
- in-process worker starts only after config + infra validation (`run_startup_validation`);
- config validation is pure (no network/DB calls); DB reachability check runs only at startup for `prod` + runtime enabled.

Makefile entrypoints: `local-up`, `api-only`, `runtime` / `worker` (in-process, not a separate service yet), `prod-check`, `reset-db`.

## Current constraints

- deterministic-first architecture;
- provider-agnostic integrations;
- JSON-only AI outputs with schema validation;
- strict contract enforcement (`analysis_contract`) with parser gate between transport and validation;
- backend owns business logic;
- session-centric analysis context;
- prompt generation owned exclusively by Prompt Compiler (`jungian_prompt_builder`);
- `is_latest` is write-only derived state (never computed on read endpoints);
- analysis history is insert-only (no upsert overwrite of prior runs).
- invariant-tightening migrations (`NOT NULL`, FK hardening) must include self-healing backfill for existing rows;
- runtime workers contain zero prompt/business/provider logic and call the orchestrator boundary only;
- `AnalysisJob` lifecycle fields are mutated only by runtime job service;
- runtime is at-least-once; stale `running` jobs are not auto-recovered in #013.

## Explicitly postponed

- embeddings and vector databases;
- advanced Mini App UI flows;
- archetype graphing and symbolic graph engine;
- premature model-specific optimizations;
- multi-stage reasoning pipeline beyond single-pass mock analysis.

## Source-of-truth priority

If documents conflict, resolve by this order:

1. `docs/progress/current-state.md`;
2. relevant ADR files in `docs/decisions/`;
3. `docs/architecture/*.md`;
4. `TASKS.md` (tactical execution only).
