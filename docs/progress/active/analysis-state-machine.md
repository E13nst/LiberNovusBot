# Analysis State Machine v2 (#012)

## Status

Implemented.

## Architecture

```text
continuation orchestration
  -> SnapshotBuilderService (read-only ORM -> DTO)
  -> resolve_thread_decision (pure)
  -> normalized_transition (static action template mapping)
  -> apply_transition_tx (executor-only thread service)
```

## Layer responsibilities

- `analysis_snapshot_service`: only ORM boundary for state machine inputs; read-only.
- `analysis_state_machine_service`: pure decision over immutable snapshots.
- `analysis_policy`: pure helpers (`is_thread_fresh`, `is_session_closed`, UTC helpers).
- `analysis_continuation_service`: orchestration, bounded re-resolve (max 1), transaction coordination.
- `analysis_thread_service`: transition executor only; no policy branching.

## Thread lifecycle

- `active`: can receive analysis writes when freshness rules allow.
- `idle`: stale thread; never continued; new thread created on next write.
- `closed`: terminal; never reused.

## Rule precedence

1. `session_closed`
2. `thread_closed`
3. 72h freshness (`analysis_threads.last_activity_at`)
4. `mode=continue` advisory only

## Decision contract

```text
DecisionDTO:
  action: CONTINUE | CREATE_NEW | MARK_IDLE | CLOSE_AND_CREATE_NEW
  target_thread_id: UUID | null
  metadata: opaque debug only
  confidence: 1.0
```

## Invariants

- one `active` thread per session (partial unique index)
- one `is_latest=true` per `thread_id`
- `last_activity_at` updated only on successful analysis persistence
- GET `/analysis` is read-only grouping; no state mutation

## Concurrency

- apply uses savepoint/transaction boundary per attempt
- on conflict: rebuild snapshot, re-run decision once
- second conflict: `StateMachineConcurrencyError`

## Out of scope

- LLM provider changes
- prompt compiler changes
- contract/parser changes
