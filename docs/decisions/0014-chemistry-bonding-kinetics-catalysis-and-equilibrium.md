# ADR-0014: Chemical bonding, reaction kinetics, catalysis, and equilibrium

- **Status:** Accepted
- **Date:** 2026-11-28

## Context

`bigBangEnv` now spans Physics (`Signal`, conserved `ChargeVector`, multi-form `Budget` energy/entropy, spacetime `Coord`, and four forces in ADR-0013) and Biology (`Molecule`, `Cell`, `Organ`, `Genome`, `Body` in ADR-0012). The bridge between physical atoms (`Signal`) and biological cells/molecules is **Chemistry**:

1. Real-world observations rarely arrive as one complete, self-contained JSON payload. Often a `symptom` signal and a `context` (or `evidence`) signal must **covalently bond** into a composite `Molecule` before triggering action.
2. State transitions should respect **activation energy ($E_a$)** barriers so scarce energy cannot fire expensive synthesis arbitrarily.
3. **Catalysts** (such as M2-compiled reflex patterns or domain templates) lower $E_a$ without being consumed.
4. **Le Chatelier equilibrium** provides natural chemical backpressure: when downstream product concentration saturates, forward synthesis slows automatically.

## Decision

1. **Chemistry Module (`src/bigbang/chemistry.py`)**:
   - `Reaction`: defines exact stoichiometric `reactants` (`dict[str, int]`), synthesized `product`, `activation_energy` ($E_a$), `enthalpy`, and `max_product_concentration`.
   - `Catalyst`: reduces effective $E_a$ for matching reactions (`ea_reduction` factor) without being consumed.
   - `ReactionChamber`: JSON-serializable reagent pool enforcing:
     - Reagent TTL decay.
     - Stoichiometric bonding when all required reactants are present.
     - Conservation of authority (`min(Trust)`) and risk (`max(risk)`) across bonded reagents.
     - Activation energy & Le Chatelier backpressure checks.
   - `toxicity_ph(dropped, accepted)`: measurable compartment buffer metric ($0.0\text{–}1.0$) tracking malformed/noisy ingress pressure.
2. **Body Integration (`src/bigbang/body.py`)**:
   - Add `SynthesisCell` (`perception.synthesis`) inside `PerceptionOrgan`, subscribing to `world.reagent` and `chemistry.catalyze`, emitting bonded compounds onto `_organ.perception.parsed`.
   - `MyelinCompiler` promotions emit `chemistry.catalyze` events so compiled reflexes act as zero-consumption catalysts in the organism's chemistry.
   - `body_report()` exposes `chemistry` metrics (`reactions`, `catalysts`, `reagents_queued`, `toxicity_ph`).

## Consequences

- `bigBangEnv` completes the Physics → Chemistry → Biology emergence chain while keeping single-issue `world.issue` ingestion and all 111 prior tests unchanged.
- Correlated multi-signal inputs can bond dynamically inside `PerceptionOrgan` with full provenance and risk conservation.
