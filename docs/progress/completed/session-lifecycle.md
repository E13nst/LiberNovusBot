# Capability Milestone: Session Lifecycle

## Outcome

Session-aware intake and lifecycle management are implemented in backend services.

## Includes

- session resolution during dream intake;
- one active analytical context behavior;
- inactivity-based auto-close behavior;
- lifecycle logic isolated from bot/client layers.

## Invariants

- every dream belongs to a session;
- lifecycle is backend-owned;
- session continuity is preserved for longitudinal analysis.
