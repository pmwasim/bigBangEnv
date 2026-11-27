# ADR-0012: Molecules, paracrine gradients, endocrine hormones, organs, and unified body

- **Status:** Accepted
- **Date:** 2026-11-28

## Context

Milestones M0 and M1 proved the microkernel (`Kernel`), membrane (`Context`), differentiated cell lineages (`Perception`, `Reflex`, `Reasoner`, `Commander`, `Defense`, `Motor`, `Journal`), and bounded endurance (`ADR-0011`). However, the architecture still lacked the intermediate emergence layers defined in the Genesis Specification:

1. **Molecules**: `cell.memory` was an untyped dictionary with no per-entry provenance or TTL decay.
2. **Paracrine & Endocrine Signaling**: Cells could only communicate via point-to-point topic `Signal`s; there were no local compartment gradients (`friction`) or global damped hormonal scalars (`fuel`, `stress`, `urgency`, `idle`).
3. **Compartmentalized Organs**: The caretaker wired 7 cells flatly in one room without organ membranes, typed input/output ports, or dedicated organ energy pools.
4. **Unified Body & Myelination**: There was no immutable `Genome`, no circadian operating modes (`ALERT`, `DEEP_FOCUS`, `LOCKDOWN`, `SLEEP_REM`, `DORMANT`), and no closed-schema M2 reflex compilation during idle/REM cycles.

## Decision

1. **Molecules (`bigbang.matter`)**: Introduce `Molecule` (typed key/value compound carrying per-entry `Trust` provenance, `born` tick, `ttl`, and `hits`) and `MatterStore` (deterministic TTL decay, O(1) lookup, bounded capacity).
2. **Three-Channel Signaling Physics (`bigbang.kernel`, `bigbang.cell`)**:
   - *Directed Impulses*: Existing `Signal` topic bus with refractory `Cell.cooldown`.
   - *Local Gradients (Paracrine)*: `Context.emit_gradient(name, delta)` and `Context.gradient(name)` scoped to `cell.organ` compartment, decaying deterministically each tick (`× 0.8`).
   - *Global Hormones (Endocrine)*: Kernel-computed damped scalars `{fuel, stress, urgency, idle}` exposed read-only via `Context.hormones`, driving `Kernel.operating_mode` transitions through Schmitt-trigger hysteresis.
3. **Compartmentalized Organs (`bigbang.organ`)**: Introduce `Organ` wrapping a bounded set of cells behind declared `in_ports` and `out_ports`, private internal topic isolation (`_organ.<name>.*`), and a shared organ energy pool modulated by the bloodstream.
4. **Unified Body, Genome & M2 Myelination (`bigbang.body`)**:
   - `Genome` (frozen dataclass) defines immutable identity, role, allowed labels/capabilities, and safety thresholds.
   - Five vital organs: `PerceptionOrgan`, `ActionOrgan`, `MemoryOrgan` (with `MyelinCompiler` using closed-schema `sig_id` declassification and burst-diversity gating per M2), `DefenseOrgan`, and `DeliberationOrgan`.
   - Circadian operating modes (`ALERT`, `DEEP_FOCUS`, `LOCKDOWN`, `SLEEP_REM`, `DORMANT`) dynamically shift organ regen weights and activate REM consolidation during `SLEEP_REM`.

## Consequences

- `bigBangEnv` realizes the full emergence stack (`Atoms/Signals -> Molecules -> Cells -> Organs -> Body`) in pure Python standard library (`dependencies = []`).
- Existing M0/M1 `caretaker` behavior, deterministic replay, and all M1 evaluation metrics remain unchanged.
- Multi-container deployments (`bigbang-mesh`) can instantiate distinct, specialized 5-organ `Body` instances connected via attested peer ports rather than cloned caretaker scripts.
