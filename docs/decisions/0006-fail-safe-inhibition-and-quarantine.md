# ADR-0006: Fail-safe inhibition, pre-flight hold, and quarantine

- **Status:** Accepted
- **Date:** 2026-11-27

## Context
Defense cells read tainted inputs (the actions they inspect), so their own output is tainted. Under ADR-0003 that would make their vetoes subject to topic floors and silently blocked. Separately, a buggy cell could crash the whole kernel step, and an action could execute in the same tick that Defense first sees it.

## Decision
1. **Inhibit signals are exempt from topic floors.** Stopping is always allowed; the cell's emit capability still applies, so only cells granted a topic can veto it.
2. **Inhibition supports wildcards** (`action.*`), which gives Defense a one-signal lockdown.
3. **Motors hold every action for a pre-flight window** (default one tick) and check `is_inhibited` before executing.
4. **Cell steps are atomic.** If a cell raises, or leaves unserializable memory, its memory and emissions from that tick are rolled back, the cell is quarantined, and the kernel carries on. Operators release it with `revive`.

## Consequences
- A WORLD-derived signal can trigger a veto. That is a possible denial-of-service lever, and is accepted because it fails safe; rate-limit vetoes later if needed.
- Every action has at least one tick of latency.
- A crash costs one cell, not the organism; the trace records the error and which signals were rolled back.
