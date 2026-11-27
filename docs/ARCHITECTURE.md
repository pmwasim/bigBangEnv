# Architecture — M0 Genesis kernel

## Shape

```
          outside world / owner / operator
                     │ kernel.inject(topic, payload, trust=...)
                     ▼
 ┌──────────────────── Kernel (microkernel) ────────────────────┐
 │ clock (ticks) · bus (topic queue) · budgets · laws · trace    │
 │                                                               │
 │   ┌──────── membrane: Context ────────┐                       │
 │   │ inbox · tick · fuel · trust       │                       │
 │   │ emit() · inhibit() · is_inhibited │                       │
 │   └───────────────┬───────────────────┘                       │
 │        Cell A   Cell B   Cell C  ...  (memory = matter)       │
 └───────────────────────────────────────────────────────────────┘
           kernel.halt()  ← kill switch held outside every cell
```

## One tick

1. `tick += 1`.
2. **Decay:** signals older than their TTL are dropped (`expire`).
3. **Inhibition:** every live `INHIBIT` signal cancels pending `EXCITE` signals on its topic (`cancel`). Inhibit signals persist until they expire.
4. **Metabolism:** cells are stepped in name order (deterministic). Each step costs `step_cost`; a cell that can't pay becomes **dormant**.
5. **Delivery:** a cell receives the live excite signals on its subscribed topics; delivered signals are consumed.
6. **Emission:** signals emitted during the tick go to an outbox and become visible on the **next** tick.

## Laws enforced in `_emit`

| Check | Failure event |
|---|---|
| Topic is in the cell's `emits` capability set (if set) | `denied` (no capability) |
| Stamped trust ≥ the topic's floor (`require`) | `blocked` |
| Cell can pay `EMIT_COST` | `denied` (no fuel) |

Stamped trust is `min(cell.trust, trust of every signal in this tick's inbox)`. A cell cannot raise it. `KERNEL` trust can never be held by a cell or claimed by outside input.

## Persistence and observability

- `snapshot()` / `restore()` capture tick, queue, cell memory, spending and dormancy as JSON.
- `trace` records every event (`genesis`, `spawn`, `law`, `inject`, `emit`, `blocked`, `denied`, `cancel`, `expire`, `dormant`, `halt`, `restore`); `save_trace()` writes JSONL.

## Known gaps (tracked in the roadmap)

- A cell that raises an exception currently crashes the kernel step (quarantine is planned).
- Membranes are logical (same process), so they are not a security boundary against malicious *code*, only against malicious *data*.
- No declassification path yet: WORLD-derived data can never reach an OPERATOR-floor topic.
