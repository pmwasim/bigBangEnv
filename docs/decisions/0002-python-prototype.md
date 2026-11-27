# ADR-0002: Prototype in Python

- **Status:** Accepted (reversible)
- **Date:** 2026-11-27

## Context
M0–M2 are experiments whose job is to test claims (injection resistance, graceful degradation, reflex cost savings). The fastest path to LLM integration and benchmarks matters more than raw performance or memory safety.

## Decision
Write the prototype in Python (≥ 3.11), with no runtime dependencies in the kernel.

## Consequences
- Fast iteration; the Anthropic SDK and agent benchmarks are readily available.
- Membranes are logical, not hardware-enforced; a malicious *cell implementation* could bypass the kernel. Acceptable while every cell is our own code.
- Revisit before running third-party cells or needing hard isolation: candidates are a Rust kernel, or WASM/microVM cell isolation.
