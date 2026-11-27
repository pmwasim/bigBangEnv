# ADR-0011: Fail-closed guardians and bounded infinite-run metabolism

- **Status:** Accepted
- **Date:** 2026-11-28

## Context

Two structural gaps prevented `bigBangEnv` from safely running continuously as an autonomous long-lived organism:

1. **Guardian bypass during dormancy or quarantine (PR #1 / #4 open finding).** `Kernel.step()` marked an `EXCITE` signal as `delivered` as soon as *any* awake subscriber matched it. When a guardian cell (`Defense`) slept for even one tick (`fuel < step_cost`) or entered `quarantined`, `Motor` consumed `action.*` signals from `kernel.queue`, erasing them before `Defense` woke up, and executed them unchecked on a later tick. That violated value V7 (*graceful degradation must fail safe, never fail open*).
2. **Unbounded state and quadratic polling over infinite runs.**
   - `Kernel.trace` remained in RAM after `Runner.save()` flushed it to `trace.jsonl`, leaking memory linearly with uptime (~260,000 objects/day at 1 tick/sec).
   - `Host._pull_files()` re-globbed `issues_dir` and performed linear `in list` scans against `ingested_files` every tick (`O(N^2)` over time).
   - `Perception.memory["seen"]` used linear `in list` scans and grew unboundedly in `snapshot.json`.
   - `Ledger._record()` rewrote the entire `ledger.json` synchronously on every single action.

## Decision

1. **Fail-closed guardians (`Cell.guards` / `Kernel.guard`).**
   - A cell may declare `guards=("topic.*", ...)` (or be registered via `Kernel.guard(topic, cell_name)`).
   - Whenever any guarding cell is `dormant`, `quarantined`, or cannot pay its `step_cost` on the current tick, the kernel automatically holds matching `EXCITE` signals in the queue (`hold`, without aging) and reports `is_inhibited(topic) == True` so motors pause pending actions until the guardian recovers.
   - `Defense` in the caretaker organism guards `"action.*"`.
2. **Bounded metabolism and O(1) runtime flushing.**
   - `Kernel` maintains cumulative `stats` (`events` counts and `work_energy`), persisted in `snapshot()` and restored in `restore()`, plus `Kernel.drain_trace()` so `Runner.save()` frees flushed trace records from RAM while `report()` remains exact.
   - `Perception` uses an in-memory `_seen_set` for O(1) lookup, tracks `seen_total`, and supports a bounded `max_seen` LRU window (default `10_000`) so `snapshot.json` stays bounded.
   - `Host` caches directory `(st_mtime_ns, st_ctime_ns)` and `_ingested_set` to avoid redundant directory scans and linear list lookups.
   - `Ledger` supports `auto_flush=False` (used by `Runner` and flushed atomically in `Runner.save()`).
   - `Runner.run()` installs a `SIGTERM` handler that triggers an orderly `kernel.halt("SIGTERM")` and final `save()`.

## Consequences

- Losing a guardian cell pauses guarded pathways instead of dropping safety checks.
- Long-running `--forever` daemons run with O(1) trace RAM, bounded snapshot dedup state, and orderly shutdown under `systemd`.
- Direct in-memory `Kernel` unit tests still see full `kernel.trace` unless `drain_trace()` is called.
