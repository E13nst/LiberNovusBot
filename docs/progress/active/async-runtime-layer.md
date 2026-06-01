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
- Runtime never mutates persisted `session_analyses`.
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
- automatic recovery of stale `running` jobs;
- DB-level link between `analysis_jobs` and `session_analyses` (no `analysis_job_id` column yet).

Integration proof: `tests/runtime/test_concurrency_runtime.py`.

## Worker Boundaries

The worker is an execution shell only. It may acquire jobs, run the orchestrator boundary, requeue jobs, and mark terminal states.

The worker must not:

- load analysis input directly;
- build prompts;
- validate business schemas;
- decide continuation behavior;
- call providers directly;
- mutate persisted analyses;
- cache session data between jobs;
- keep in-memory job tracking between polling cycles.

Only `analysis_job_service` mutates `AnalysisJob` lifecycle fields. The orchestrator never writes to `AnalysisJob`.

## Orchestrator Boundary

Runtime calls `run_session_analysis(session_id, ...)`. The orchestrator owns input loading, prompt construction, provider call, response parsing, contract validation, thread resolution, and analysis persistence.

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

## Observability (#018)

Structured logs include:

- job acquisition: `worker_id`, `job_ids`, `acquired_at`, `lock_result`;
- worker execution: `worker_id`, `job_id`, `locked_by`, `provider`, `model`, `duration_ms`, `final_state`;
- executor outcome: `job_id`, `latency_ms`, `outcome`, `final_state`, `attempts`.

## Out Of Scope

- RabbitMQ;
- Redis;
- Celery;
- Kafka;
- WebSockets;
- streaming tokens;
- provider failover;
- distributed workers;
- embeddings/vector DB;
- semantic memory.
