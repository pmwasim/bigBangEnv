# ADR-0017: Autonomous Genome Evolution and Live Domain Sensors

- **Status:** Accepted
- **Date:** 2026-11-28

## Context

With Physics, Chemistry, Homeostasis, Stem Mitosis/Apoptosis, and Society (`Skin`, Reputation, Territory Mutex, Backpressure) active through ADR-0016, two final roadmap layers remained:
1. **Genetics & Evolution**: `Genome` hyperparameters (`myelin_min_support`, `myelin_min_span`, `myelin_shadow_needed`) were fixed defaults rather than evolving through benchmarked natural selection while keeping safety invariants strictly immutable.
2. **Live Domain Sensors**: VM 300 organisms needed deterministic stdlib telemetry adapters capable of converting real host/container resource signals (CPU load, memory, root disk usage) into typed `world.reagent` / `world.issue` impulses.

## Decision

1. **Bounded Genome Evolution (`src/bigbang/evolution.py`)**:
   - `mutate_genome()` generates deterministic candidate variants over plastic operational parameters (`myelin_min_support`, `myelin_min_span`, `myelin_shadow_needed`, `fuel`, `regen`) while locking `forbidden_verbs`, `allowed_labels`, and trust invariants so evolution can never erode security boundaries.
   - `evaluate_genome()` scores candidates against offline safety + workload benchmarks (`FitnessScore`: accuracy, energy efficiency, `toxicity_ph`, safety violations). Any policy violation disqualifies the variant (`fitness = -inf`).
   - `evolve_generation()` runs elitist selection across generations and returns the fittest verified `Genome`.
2. **Live Domain Telemetry Sensors (`src/bigbang/apps/sensors.py`, `cli.py`, `deploy/bigbang-mesh.py`)**:
   - `collect_host_snapshot()` gathers POSIX/Linux host health metrics (`load_1m`, `mem_used_pct`, `disk_used_pct`, `uptime_s`) using pure stdlib + `/proc`.
   - `snapshot_to_signals()` converts resource pressure anomalies into paired stoichiometric Chemistry reagents (`symptom` + `context` on `world.reagent`) or diagnostic `world.issue` records.
   - Adds `bigbang evolve` and `bigbang probe` CLI subcommands plus `bigbang-mesh probe` for live Incus host/tier health probing.

## Consequences

- Organisms can adapt epigenetic/genomic hyperparameters across generations without ever relaxing safety invariants.
- Real infrastructure metrics enter the membrane seamlessly as typed Chemistry/World inputs.
