# Capability Milestone: Session Summary

## Outcome

Deterministic session summary layer is available as a stable aggregation capability.

## Includes

- summary rebuild from persisted session material;
- deterministic field extraction;
- idempotent behavior for repeated rebuilds;
- no AI dependency in summary computation.

## Invariants

- summaries are derived artifacts, not raw source data;
- deterministic services remain testable and explainable;
- outputs can be reused by prompt compilation and reasoning layers.
