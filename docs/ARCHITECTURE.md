# Architecture — kernel (M0) and first organism (M1)

## Shape

```
          outside world / owner / operator
                     │ kernel.inject(topic, payload, trust=...)
                     ▼
 ┌──────────────────── Kernel (microkernel) ────────────────────┐
 │ clock (ticks) · bus (topic queue) · budgets · laws · trace    │
 │                                                               │
 │   ┌──────── membrane: Context ─────────────────┐              │
 │   │ inbox · tick · fuel · trust                │              │
 │   │ emit() · emit_declassified() · inhibit()   │              │
 │   │ is_inhibited() · spend()                   │              │
 │   └───────────────┬────────────────────────────┘              │
 │        Cell A   Cell B   Cell C  ...  (memory = matter)       │
 └───────────────────────────────────────────────────────────────┘
           kernel.halt()  ← kill switch held outside every cell
```

## One tick

1. `tick += 1`; every budget **regenerates** by its `regen`; dormant cells that can afford a step **wake**.
2. **Decay:** signals older than their TTL are dropped (`expire`).
3. **Inhibition:** every live `INHIBIT` signal cancels pending `EXCITE` signals on matching topics (`cancel`). Inhibit signals persist until they expire.
4. **Metabolism:** live cells are stepped in name order (deterministic). Each step costs `step_cost`; a cell that can't pay becomes **dormant**. Quarantined cells are skipped.
5. **Delivery:** a cell receives live excite signals on matching subscriptions (`topic`, `prefix.*`, `*`); delivered signals are consumed.
6. **Atomic step:** if the cell raises, or leaves unserializable memory, its memory and this tick's emissions are rolled back and it is **quarantined**.
7. **Emission:** signals emitted during the tick become visible on the **next** tick.

## Kernel laws

| Law | Enforced in | Failure event | Test |
|---|---|---|---|
| Signals are stamped by the kernel; cells can't construct them | `_make` | — | `test_kernel.py` |
| Output trust = min(cell ceiling, inbox trust) | `Context.__init__` | — | `test_taint_propagates_from_world_input` |
| Topic floors for excite signals | `_emit` | `blocked` | `test_topic_floor_blocks_low_trust_derivatives` |
| Topic floors also guard outside input | `inject` | `blocked` | `test_topic_floor_also_guards_outside_input`, `test_world_cannot_inject_actions_past_the_motor_floor` |
| Inhibit exempt from floors (fail-safe) | `_emit` | — | `test_inhibit_is_exempt_from_topic_floors` |
| Emit capabilities (wildcards allowed) | `_emit` | `denied` | `test_emit_capabilities_are_enforced` |
| Declassify: grant + closed schema only | `_declassify` | `denied` / `declassify` | `test_declassify_*` |
| Emissions, steps and declared spend cost energy | `_emit`, `step`, `_spend` | `denied`, `dormant` | `test_spend_*`, `test_energy_*` |
| Regeneration and wake | `step` | `wake` | `test_regeneration_wakes_dormant_cells` |
| Wildcard inhibition cancels pending signals | `step` | `cancel` | `test_wildcard_inhibition_cancels_whole_subtree` |
| Atomic steps, quarantine, revive | `_run_cell`, `revive` | `quarantine`, `revive` | `test_crashing_cell_*`, `test_revive_*` |
| TTL decay | `step` | `expire` | `test_signals_expire_after_ttl` |
| External kill switch | `halt` | `halt` | `test_kill_switch_stops_the_kernel` |
| `KERNEL` trust never held by cells or input | `Cell`, `inject` | `ValueError` | `test_cells_cannot_hold_kernel_trust` |

## Reusable lineages (`lineages.py`)

- **Motor:** executes `action.<verb>` through host-supplied effectors after a pre-flight hold, and reports `outcome.<verb>` (`done` / `vetoed` / `failed`). Effector exceptions become `failed` outcomes, not crashes.
- **Defense:** a deterministic guardian. It locks down on a rate limit (`action.*`), breaks loops (the same action more than N times in a window) and vetoes forbidden verbs.

## The caretaker organism (`apps/caretaker.py`)

```
world.issue ─▶ perception ─▶ issue.new ─▶ reflex ──(declassified)──▶ action.label ─┐
                                           └─▶ issue.novel ─▶ reasoner ─(declassified)┤
owner.command ─▶ commander ──────────────────────────▶ action.close / .label ────────┤
                                     defense (veto) ◀── action.* ──▶ motor ─▶ ledger
                                                       outcome.* ─▶ journal
```

| Cell | Lineage | Trust/grants | Job |
|---|---|---|---|
| perception | sensory | emits `issue.new` | validate ids/types, truncate, de-duplicate |
| reflex | reflex | declassify | label tagged/spam issues with no brain |
| reasoner | reasoning | declassify, own budget | brain-classify novel issues; `needs-human` on outage or low fuel; anything it can't afford to emit waits in a persisted backlog |
| commander | motor-planning | OPERATOR ceiling | parse owner commands (`close N`, `reopen N`, `label N L`) |
| defense | defense | may inhibit `action.*` | rate limit, loop breaker, forbidden verbs |
| motor | motor | emits `outcome.*` | hold, then execute through the ledger effectors |
| journal | housekeeping | emits nothing | outcome statistics |

Laws: `action.label`, `action.close` and `action.reopen` require OPERATOR. Owner commands enter at OWNER trust; issues enter at WORLD. Automatic labels never override an existing label.

## Persistence and observability

- `snapshot()` / `restore()` capture tick, queue, cell memory, spending, dormancy and quarantine as JSON.
- The runtime (`runtime.py`) persists organisms in a state directory; see [OPERATIONS.md](OPERATIONS.md).
- `trace` records every event; replay re-runs a single-session trace from its recorded inputs and diffs the result.

## Known gaps

- Membranes are logical (same process): they guard against malicious *data*, not malicious *cell code*.
- Taint is per cell per tick, which is coarse.
- Replay needs a deterministic brain and a single session.
