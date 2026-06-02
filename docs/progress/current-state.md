# Current State

## Current focus

#017 in progress: async OpenAI runtime smoke. #022 closed: Real OpenAI E2E Smoke — synthetic Telegram webhook update -> `register_incoming_dream` -> `analysis_jobs` -> `AnalysisRuntimeWorker` -> real OpenAI -> `DreamAnalysisV1` -> `session_analyses` -> fake Telegram delivery. #020a closed the user-visible gap: every accepted dream message atomically enqueues one `analysis_job` via `dream_intake`. #021 delivered the Dream Interpretation Contract Layer (`dream_v1` canonical model + presentation mapper). #024 introduced a pure Dialogue Policy Engine contract (`services/dialogue_policy`) with deterministic routing-only decisions and no runtime/DB/Telegram wiring yet.

## Completed stable layers

- dream persistence;
- session lifecycle with inactivity auto-close;
- deterministic session summaries;
- Jungian prompt builder / prompt compiler;
- prompt contract and prompt validation foundation;
- analysis input aggregation (`analysis_input_service`);
- analysis contract + JSON validation (`analysis_contract`);
- analysis orchestrator with mock LLM provider;
- real provider abstraction layer (`LLMProvider`, provider registry, OpenAI Responses API transport, OpenAI-compatible transport);
- OpenAI provider: `AsyncOpenAI` only inside `OpenAILLMProvider`, SDK errors mapped to `ProviderTransportError` / `ProviderTerminalError` / `SDKUnexpectedError`;
- test-mode guards: registry hard-fail for non-mock providers, `AsyncOpenAI` construction blocked, process-level httpx network kill switch in pytest;
- raw response parsing gate (`response_parser.extract_json`) before schema enforcement;
- orchestrator-level retry policy for transient transport failures;
- session analysis persistence (`session_analyses` table);
- analysis threads + continuation layer (`analysis_threads`, `analysis_continuation_service`, `analysis_thread_service`);
- analysis state machine v2 (`analysis_state_machine_service`, `analysis_snapshot_service`, `analysis_policy`);
- dialogue policy engine v1 contract (`dialogue_policy`): structural/session-state routing only (`ROUTE_REFLECTION`, `ROUTE_CLARIFICATION`, `ROUTE_SESSION_CONTINUE`, `ROUTE_NOOP`), confidence fixed at `1.0`, no semantic interpretation;
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
| `test` | forced `mock` | forced disabled | hard fail for non-mock provider or HTTP client creation; no external LLM |
| `prod` | non-mock, requires `OPENAI_API_KEY` | required enabled | hard fail on misconfig at startup |

Safety guarantees:

- no silent fallback to mock for unknown providers;
- `prod` cannot boot without `OPENAI_API_KEY` or with `LLM_PROVIDER=mock`;
- in-process worker starts only after config + infra validation (`run_startup_validation`);
- config validation is pure (no network/DB calls); DB reachability check runs only at startup for `prod` + runtime enabled.

Makefile entrypoints: `local-up`, `api-only`, `runtime` / `worker` (in-process, not a separate service yet), `prod-check`, `reset-db`.

## OpenAI smoke test (#016)

Manual opt-in only; default `make test` / CI must not call OpenAI.

 Preconditions (all required):

- `RUN_OPENAI_SMOKE=true`
- `ENV_MODE=local`
- `LLM_PROVIDER=openai`
- `OPENAI_API_KEY` set (not the pytest placeholder)
- explicit marker selection: `pytest -m openai_smoke`

Cost guards:

- one shared short dream fixture in `tests/smoke/conftest.py`;
- exactly one real inference per smoke test;
- model from isolated `RuntimeConfig.default_model`;
- `LLM_MAX_ATTEMPTS=1` for smoke runs;
- token usage logged via provider metadata when returned.

Command:

```bash
make openai-smoke
```

(`OPENAI_API_KEY` and other vars are loaded from `.env`; requires outbound network to OpenAI.)

If parser or contract validation fails: do not change `analysis_contract`, do not add JSON repair, and do not weaken prompts in smoke work. Record the mismatch between prompt output and contract as the primary #016 finding.

Verified path (2026-06-01): `make openai-smoke` passed — one inference, contract-valid `session_analyses` row persisted. Smoke harness, guards, and orchestrator diagnostics remain the regression surface for this path.

## Async OpenAI runtime smoke (#017)

Extends #016 through the queue/worker path (no HTTP layer in pytest; uses `create_job` + `AnalysisRuntimeWorker`):

```text
create_job (queued)
  -> acquire (running)
  -> execute_analysis_job
  -> run_session_analysis
  -> OpenAI -> parser -> contract -> session_analyses
  -> job completed
```

Commands:

```bash
make openai-runtime-smoke   # runtime path only
make openai-smoke           # orchestrator + runtime smoke tests
```

Offline regression: `tests/runtime/test_analysis_runtime_single_job.py` (no double processing after completion).

Runtime executor logs `job_id`, `session_id`, `provider`, `model` before orchestrator; outcome log includes `latency_ms` and `outcome`.

## Runtime concurrency (#018)

Guarantees (PostgreSQL `SELECT … FOR UPDATE SKIP LOCKED` only):

- at-least-once job delivery;
- strict single-active execution per `analysis_jobs.id` while a worker holds the row as `running`;
- no concurrent execution of the same job by multiple workers;
- no duplicate provider invocation per successful execution path under worker contention (verified via integration tests with call counters).

Does **not** guarantee:

- exactly-once end-to-end execution;
- crash recovery for stale `running` jobs;
- duplicate prevention across process crashes after a job is marked `running`.

Traceability (#019): `session_analyses.analysis_job_id` links each runtime-produced analysis to exactly one `analysis_jobs.id`. Executor binds via `with_job_id` during assembly before persistence; sync/manual analyze path leaves it NULL. `session_analyses` stores final results only — attempts live on `analysis_jobs`. Retry preserves job identity (same `job.id`, incrementing attempts).

Offline regression: `tests/runtime/test_job_result_binding.py` (job binding, retry identity, idempotent reprocessing, write-once guard, concurrent cross-binding).

Offline regression (concurrency): `tests/runtime/test_concurrency_runtime.py` (dual-worker race, delayed double-acquire, stress-lite, crash edge, provider-call isolation, retry requeue race).

Structured logs: acquisition (`analysis_job_service`), batch/execution timing (`analysis_runtime_worker`), executor outcome (`analysis_runtime_executor`) with `worker_id`, `job_id`, `analysis_id`, `analysis_job_id`, `locked_by`, `final_state`, `duration_ms` / `latency_ms`.

## Delivery idempotency (#020)

- **Execution** = Postgres queue (`analysis_jobs`, `SKIP LOCKED`).
- **Result** = `session_analyses` (final persisted analysis only).
- **Delivery** = Redis side-effect guard + Telegram Bot API send.

Redis is used as a side-effect deduplication layer for delivery only (`delivery:key:{job_id}`, `SET NX EX 86400`). It is **not** part of execution or persistence semantics. No DB flag exists for delivery state.

Delivery runs after `mark_completed` as a best-effort side effect. Failure is logged but does not change job state. The system guarantees at-most-once Telegram delivery per `analysis_job_id`, not guaranteed delivery timing.

Worker remains stateless for execution; Redis gates delivery only.

Offline regression: `tests/runtime/test_telegram_delivery.py`.

## Dream intake → job wiring (#020a)

- **User-visible invariant:** if the user receives `Сон принят`, the backend persisted that dream message and enqueued exactly one queued `analysis_jobs` row for it.
- **Message-level invariant:** every accepted dream message creates exactly one queued analysis job (three messages → three jobs, even in the same session).
- **Atomic intake invariant:** dream persistence and job creation succeed together or the intake fails with no success response.
- **Enqueue location:** `services/dream_intake.py` (`register_incoming_dream`) — not runtime, worker, or executor.
- **Flow:** Telegram → `POST /dreams` → dream intake → dream save + `create_job` → runtime worker → analysis → delivery.

Offline regression: `tests/integration/test_dream_to_analysis_pipeline.py`, `tests/bot/test_dream_handler.py`, `tests/services/test_dream_intake.py`.

## Dream interpretation contract (#021)

- **Canonical model:** `DreamAnalysisV1` in `services/analysis/schema/dream_analysis_v1.py` — the only validated domain truth for new analyses.
- **Contract gate:** `analysis_contract.validate_analysis_output()` validates `DreamAnalysisV1` strictly; no version routing or legacy validation in contract.
- **Version selection:** orchestrator config sets `analysis_version = "dream_v1"`; contract does not own versioning.
- **Persistence:** `session_analyses.analysis_json` stores serialized `DreamAnalysisV1` via `model_dump()` after contract validation — versioned JSON blob, not DB-bound schema.
- **Semantic authority:** dream semantics are generated by the LLM under strict schema constraints; system performs parsing, validation, lifecycle, persistence, and presentation mapping only.
- **Presentation layer:** `LegacyMapperV1` in `services/analysis/dto/dream_analysis_legacy_mapper.py` maps canonical JSON to legacy API/Telegram fields at response boundaries only.
- **Telegram format:** structured sections (key thought, symbols, archetypes, insight) from canonical payload via `telegram_delivery_service`.
- **Prompt mode:** Dream Interpretation Mode in `prompt_contract.py` — JSON-only structural psycho-interpretation output.

Offline regression: `tests/services/test_dream_analysis_v1_schema.py`, `tests/services/test_analysis_contract.py`, `tests/services/test_dream_analysis_legacy_mapper.py`, `tests/services/test_presentation_service.py`, `tests/runtime/test_telegram_format.py`.

## Real OpenAI E2E smoke (#022)

Manual opt-in only; not part of default `make test` or CI.

Preconditions (all required):

- `RUN_OPENAI_E2E=true` (separate from `RUN_OPENAI_SMOKE`; E2E guard is stricter and does not alias smoke)
- `ENV_MODE=local`
- `LLM_PROVIDER=openai`
- `OPENAI_API_KEY` set (not the pytest placeholder)
- explicit marker: `pytest -m openai_e2e`

Input path:

- synthetic Telegram Bot API update JSON posted to in-process `POST /telegram/webhook`
- no Playwright, Telegram Web, real bot polling, or Telegram network calls

Cost / determinism guards:

- exactly one real OpenAI inference per E2E test (`LLM_MAX_ATTEMPTS=1`, `SingleInferenceOpenAIProvider`)
- at most one `OpenAILLMProvider` construction per E2E test session
- one dream -> one queued job -> one worker pass -> one analysis -> one fake delivery
- delivery via `runtime_delivery_overrides` + `RecordingTelegramDelivery` (no real Redis/Telegram network required when overrides are set)

Command:

```bash
make openai-e2e-smoke
```

Offline regression: `tests/integration/test_telegram_webhook_intake.py` (webhook -> dream + queued job, no OpenAI).

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
