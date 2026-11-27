# ADR-0004: Discrete, deterministic ticks

- **Status:** Accepted
- **Date:** 2026-11-27

## Context
The blueprint lists a fork between a global heartbeat and purely interrupt-driven execution. Observability (principle P3) and replayable experiments matter most in the early milestones.

## Decision
The kernel advances in discrete ticks. Outside events are queued and delivered on the next tick; cells are stepped in a fixed order; emissions become visible one tick later.

## Consequences
- Identical inputs produce identical traces, which enables replay, diffing and regression tests.
- Latency is at least one tick, and idle cells still pay a step cost (the "always-beating" choice).
- Revisit if latency or idle cost becomes a real constraint: options include sleeping cells woken by subscriptions, or a variable tick rate.
