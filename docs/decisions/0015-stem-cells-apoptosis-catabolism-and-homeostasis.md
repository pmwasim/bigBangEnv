# ADR-0015: Stem Cells, Programmed Apoptosis, Catabolism, and Homeostasis

- **Status:** Accepted
- **Date:** 2026-11-28

## Context

`bigBangEnv` established the Physics substrate (`physics.py`), Chemical synthesis (`chemistry.py`), persistent `MatterStore`, five compartmentalized Organs (`organ.py`), and a unified `Body` (`body.py`). However, the Body still lacked three physiological mechanisms specified in the Genesis architectural model (§4 and §7):
1. The 6th cell archetype: **Stem Cells** capable of workload-driven mitosis and **programmed apoptosis** without leaking energy or breaking trust boundaries.
2. **Exothermic catabolism**: recovering partial computational fuel when transient molecules decay during `SLEEP_REM`.
3. **Endogenous homeostatic drives** (`goal_tension`, `epistemic_coherence`, `metabolic_efficiency`) reported systematically and driving proactive friction signaling on persistent outcome failures.

## Decision

1. **Kernel-Controlled Mitosis & Apoptosis (`kernel.py`, `cell.py`)**:
   - Only cells with `lineage == "stem"` may invoke `Context.spawn_worker(worker, fuel=..., reason=...)`.
   - Energy is strictly conserved: granting `fuel` charges the parent stem cell's `Budget`, and `Context.apoptosis()` reclaims the child's remaining unspent fuel back to the parent at step end.
   - Privilege is never escalated: ephemeral workers are pinned to `parent.organ`, have `declassify=False`, and have trust bounded by `min(worker.trust, parent.trust, parent_taint)`.
   - Snapshots tag ephemeral cells (`"ephemeral": True`) so `Kernel.restore()` resumes safely without failing on transient workers.
2. **Catabolism & Homeostatic Drives (`body.py`)**:
   - `MemoryConsolidator` recovers partial fuel (`ctx.recover_fuel`) during `SLEEP_REM` when decaying obsolete molecules, strictly bounded by `budget.spent` so total budget capacity never expands.
   - `DeliberationStem` spawns bounded ephemeral `BurstWorker` helpers when `urgency >= 0.35`, and workers self-terminate (`ctx.apoptosis`) after idle ticks drain the burst.
   - `body_report()` exposes `"homeostasis"` metrics (`goal_tension`, `epistemic_coherence`, `metabolic_efficiency`, `catabolized_fuel`, `active_ephemeral`, `mitoses`, `apoptoses`).
3. **Evaluation Expansion (`evaluation.py`)**:
   - Extend `bigbang eval` with deterministic offline checks for M2 myelination + catalysis (`m2_myelination_and_catalysis`), 5-organ Body sleep/homeostasis (`body_hormonal_homeostasis`), and stem mitosis + apoptosis (`stem_mitosis_and_apoptosis`).

## Consequences

- Energy and trust remain conservation laws even under dynamic cellular elasticity.
- The evaluation suite covers M1 caretaker invariants as well as M2–M4, Chemistry, and Stem/Apoptosis physiology.
