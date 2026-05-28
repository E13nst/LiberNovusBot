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
