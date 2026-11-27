# ADR-0003: Authority ladder with kernel-stamped taint propagation

- **Status:** Accepted
- **Date:** 2026-11-27

## Context
The blueprint tagged all external input as "untrusted world matter", which wrongly includes the owner's own instructions. Prompt injection works because today's agents can't tell who said what once text is in the context.

## Decision
- Trust is an ordered ladder: `WORLD < USER < OPERATOR < OWNER < KERNEL`.
- The kernel stamps trust on every signal; cells cannot construct signals.
- A cell's output trust = `min(cell ceiling, trust of inputs it consumed this tick)`.
- Topics can require a minimum trust (`Kernel.require`). Signals below it are blocked and logged.
- `KERNEL` trust is never granted to a cell or to outside input.

## Consequences
- Injected text cannot cause an action on a protected topic, whatever it says.
- **Taint explosion:** a cell that mixes WORLD and OWNER input in one tick produces WORLD output. Useful work on untrusted data will need an explicit, audited *declassification* mechanism (open question for M1).
- Granularity is per tick per cell, which is coarse; finer-grained tracking (per payload field) may be needed.
