# Async Runtime Layer

## Status

Implemented as capability #013.

## Execution Policy

`POST /sessions/{session_id}/analyze` remains compatibility/debug/manual execution only. It is fully synchronous and bypasses the runtime queue.

`POST /sessions/{session_id}/analyze-async` is the canonical production execution flow. It creates an immutable `AnalysisJob` execution record and returns immediately.

## Queue Invariants

- PostgreSQL table `analysis_jobs` is the only queue source of truth.
- Runtime is an at-least-once execution system.
- Duplicate execution is prevented only by persisted job state transitions.
- Runtime does not deduplicate jobs in #013; each enqueue creates a new job.
- `AnalysisJob` rows are immutable execution records except lifecycle/status fields, retry metadata, lock fields, and timestamps.
- `analysis_job_id` is assigned by executor before persistence as part of final analysis object construction; no other layer assigns or mutates it.
- `available_after` defaults to `created_at` for queued jobs.
- Acquisition ordering is `available_after ASC, created_at ASC, id ASC`.

## Concurrency Guarantees (#018)

The only concurrency control mechanism is PostgreSQL row locking in `acquire_available_jobs`:

```sql
SELECT … FROM analysis_jobs
WHERE status = 'queued' AND available_after <= now()
ORDER BY available_after, created_at, id
LIMIT N
FOR UPDATE SKIP LOCKED
```

Within one database transaction, selected rows transition `queued → running` with `locked_by` / `locked_at` before commit. Other workers skip locked rows.

Guaranteed:

- multiple in-process workers (distinct `worker_id`) may poll concurrently;
- each job has at most one active execution context at a time;
- a `running` job is not re-acquired until explicitly requeued (`running → queued` via `requeue`).

Not guaranteed (#018 scope):

- exactly-once execution across crashes;
- automatic recovery of stale `running` jobs.

## Execution Traceability (#019)

- `session_analyses.analysis_job_id` is a nullable indexed trace link from runtime result to `analysis_jobs.id`.
- No FK constraint in #019; optional enforcement later.
- `session_analyses` is a **final result table**, not an execution log. Attempts are tracked only in `analysis_jobs` (`attempts`, `max_attempts`, retry metadata).
- `analysis_job_id` is write-once per analysis row and executor-owned.
- Persistence/orchestrator APIs do not accept `analysis_job_id` as an external argument.
- Runtime executor uses two explicit phases:
  1. **Analysis assembly** — `prepare_session_analysis` → `build_session_analysis_row` → `with_job_id`
  2. **Persistence** — `persist_session_analysis_in_thread`
- Manual/sync `POST /sessions/{id}/analyze` leaves `analysis_job_id` NULL (no runtime job context).
- Retry requeue preserves the same `analysis_jobs.id`; attempts increment, successful path yields at most one bound analysis per job.

Integration proof: `tests/runtime/test_job_result_binding.py`.

Integration proof (concurrency): `tests/runtime/test_concurrency_runtime.py`.

## Worker Boundaries

The worker is an execution shell only. It may acquire jobs, run the orchestrator boundary, requeue jobs, and mark terminal states.

The worker must not:

- load analysis input directly;
- build prompts;
- validate business schemas;
- decide continuation behavior;
- call providers directly;
- assign `analysis_job_id` on `session_analyses`;
- cache session data between jobs;
- keep in-memory job tracking between polling cycles.

Only `analysis_job_service` mutates `AnalysisJob` lifecycle fields. The orchestrator never writes to `AnalysisJob`.

## Orchestrator Boundary

Runtime calls `prepare_session_analysis(session_id, ...)` through the executor boundary. The orchestrator owns input loading, prompt construction, provider call, response parsing, contract validation, and thread resolution. Runtime executor performs analysis assembly (`build_session_analysis_row`, `with_job_id`) and persistence as separate phases.

## Retry Semantics

Provider retry remains bounded in `analysis_policy_service` and handles transient provider instability.

Runtime retry handles execution-level failures only when the orchestrator/domain layer raises `RetryableAnalysisError`. Runtime uses delayed requeue by setting `available_after`.

Terminal failures are not retried:

- validation failures;
- schema violations;
- hallucinated output;
- deterministic contract failures;
- any unclassified exception.

`RetryableAnalysisError` and `NonRetryableAnalysisError` are defined in `services/runtime/runtime_types.py` for shared typing, but are raised only by orchestrator/domain code.

## Recovery And Cancellation

#013 does not support job cancellation.

Running jobs are not auto-recovered. If an executor crashes after a job is marked `running`, the job remains `running` until a future explicit recovery capability is designed.

On shutdown, the worker stops acquiring new jobs. Already running jobs are allowed to finish; #013 does not force terminate them.

## Task Discipline

Worker concurrency is bounded. Detached per-job `asyncio.create_task` usage is forbidden; execution must be awaited through bounded groups.

## Observability (#018 / #019)

Structured logs include:

- job acquisition: `worker_id`, `job_ids`, `acquired_at`, `lock_result`;
- worker execution: `worker_id`, `job_id`, `locked_by`, `provider`, `model`, `duration_ms`, `final_state`;
- executor outcome: `job_id`, `analysis_id`, `analysis_job_id`, `latency_ms`, `outcome`, `final_state`, `attempts`;
- delivery side effect (#020): `job_id`, `session_id`, `analysis_id`, `chat_id`, `delivery_success`, `delivery_skip_reason`.

## Delivery Idempotency (#020)

Redis is used as a side-effect deduplication layer for Telegram delivery only. It is **not** part of execution or persistence semantics.

- key: `delivery:key:{job_id}`;
- guard: `SET NX EX 86400` before Telegram send;
- hook: executor calls delivery **after** `mark_completed`; delivery failure does not affect job state;
- guarantee: at-most-once delivery per `analysis_job_id` (best-effort; no DB delivery flag).

Worker must remain stateless for execution. Redis is only used for delivery gating.

Integration proof: `tests/runtime/test_telegram_delivery.py`.

## Out Of Scope

- RabbitMQ;
- Redis for execution/queue state (delivery dedup only in #020);
- Celery;
- Kafka;
- WebSockets;
- streaming tokens;
- provider failover;
- distributed workers;
- embeddings/vector DB;
- semantic memory.
