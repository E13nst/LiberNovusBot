# ADR-007 Admin Observability and Prompt Versions

## Status

Accepted

## Context

#026 requires an internal admin console that can explain session flow across ingress policy, dream persistence, job enqueueing, and reflection output. ADR-006 deferred policy persistence, but the admin console needs a durable audit projection without making the policy engine stateful or DB-aware.

Prompt content also needs an auditable DB-backed version surface for admin editing, while runtime prompt compilation remains deterministic and file-backed until a later integration slice can be tested safely.

## Decision

Add two durable admin/audit tables:

- `dialogue_policy_traces`: persisted at the ingress boundary after Policy is called once and route execution succeeds. It stores raw-text-free `PolicyInput` projections, `PolicyDecision`, route/reason metadata, and execution outcome links such as `session_id`, `dream_id`, and `job_id`.
- `admin_prompt_versions`: insert-only prompt versions keyed by `prompt_type` and monotonic `version`, with one active version per `prompt_type`.

Expose admin projections through `services/admin/*` and `/admin/api/*`, protected by `X-Admin-Token`. The UI consumes `EventView` projections and does not depend on internal table shapes.

## Consequences

- Policy remains deterministic, pure, and provider/DB-free.
- Admin observability has a persistent audit path for route decisions and outcomes.
- Prompt edits are auditable and DB-backed, but runtime prompt compiler behavior is unchanged in #026.
- Raw inbound text is not stored in policy traces; reflection text remains in existing `dreams` rows and is exposed only behind admin auth.
