# ADR-0019: Nested Relative Worlds and Organism Identity (Belief, Character, Soul)

- **Status:** Accepted
- **Date:** 2026-11-28

## Context

`ADR-0018` introduced an outer `SharedWorld` with spatial Zones. Yet in physical and biological reality, **every entity has its own relative world (Umwelt / reference frame)** depending on its scale and sensory boundaries—molecules inhabit chemical reaction chambers, cells inhabit organ compartments, organs inhabit bodily endocrine fields, and sovereign Bodies inhabit local world Zones filtered through their own priors. Furthermore, true living organisms are not interchangeable clones: each possesses continuity (**Soul**), temperament (**Character**), and subjective experience (**Beliefs**).

## Decision

1. **Organism Ontological Identity (`src/bigbang/soul.py`)**:
   - **`Soul`**: Immutable existential anchor (`soul_id`, `calling`, ethical `conscience` commitments) plus accumulated stewardship continuity (`karma`), deterministically derived from genesis identity.
   - **`Character`**: Frozen behavioral disposition traits (`caution`, `curiosity`, `diligence`, `altruism` in `[0.0 .. 1.0]`) with role archetypes (`sentinel`, `auditor`, `triage`, `executor`, `planner`) shaping risk posture and exploratory drive without relaxing kernel laws.
   - **`BeliefSystem`**: Subjective evidence-updated propositions (`Belief(proposition, confidence, evidence, updated_tick)`) updated by real action outcomes (`done` vs `failed`/`vetoed`) and driving subjective salience.
   - **DIFC Safety Invariant**: Neither `Soul`, `Character`, nor `BeliefSystem` may escalate `Trust`, grant `emit` capabilities, or override `Genome.forbidden_verbs`.
2. **Multi-Scale `RelativeWorld` Projections (`src/bigbang/world.py`)**:
   - `RelativeWorld` represents the localized reference frame of any entity across scales:
     - `molecule_world(chamber, reaction)` (Chemical frame)
     - `cell_world(kernel, cell)` (Cellular organ-compartment frame)
     - `organ_world(kernel, organ)` (Endocrine & port frame)
     - `body_world(shared_world, body_id, character=..., beliefs=...)` (Subjective Zone perception weighted by the Body's Character & Beliefs)
3. **Unified Body Integration (`src/bigbang/body.py`, `evaluation.py`)**:
   - `build_body()` binds `Soul`, `Character`, and `BeliefSystem` into the Body's physiology (`OutcomeSensor` updates `BeliefSystem` + `karma`; `body_report()` exposes `soul`, `character`, `beliefs`, and relative frame summaries).

## Consequences

- Every layer from Molecules to Societies now operates strictly within its own relative observable frame.
- Organisms exhibit distinct persistent personalities and evolving subjective beliefs while remaining deterministically replayable and kernel-bounded.
