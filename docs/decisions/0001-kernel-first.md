# ADR-0001: Build the kernel first, as a microkernel

- **Status:** Accepted
- **Date:** 2026-11-27

## Context
The blueprint has seven levels (physics → society). The review found that its value comes from the kernel ideas (stamped trust, metering, inhibition, continuity), while higher layers are mostly unproven metaphor.

## Decision
Start with a microkernel that owns only: clock, bus, energy metering, trust laws, persistence and trace. Everything else (sensing, acting, reasoning, defense, memory) is built as cells on top.

## Consequences
- A small, testable trusted core; higher layers can be tried and discarded cheaply.
- Value shows up later than with an LLM-first prototype.
- Higher layers must not reach around the membrane; if they need something, the kernel contract is extended deliberately.
