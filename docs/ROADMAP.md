# bigBangEnv — Roadmap

Each milestone maps to levels of the original Genesis-to-Body blueprint. **No milestone starts until the previous one meets its exit criteria** (principle P5).

## M0 — Genesis kernel *(Levels 0 + 2)* — **done**

- [x] Deterministic tick scheduler (heartbeat) and full event trace
- [x] Cells with persistent, serializable state (matter)
- [x] Per-cell energy budget, readable by the cell; dormancy, regeneration and wake
- [x] Topic bus with kernel-stamped trust and TTL decay; wildcard topics
- [x] Taint propagation; trust floors per topic; emit capabilities
- [x] First-class inhibition (veto), exempt from floors (fail-safe)
- [x] External kill switch; snapshot / restore
- [x] Trace replay tool (`bigbang replay`)
- [x] Crashing cells rolled back and quarantined; operator `revive`

**Exit criteria — met:** test suite green; identical inputs give identical traces (`determinism` scenario); crashing and exhausted cells don't affect others (`crash_isolation`, `sensed_scarcity`).

## M1 — Three lineages + Defense *(Level 3, partial)* — **done**

- [x] Sensory (perception), reflex, reasoning, motor-planning (commander), motor, defense and housekeeping cells
- [x] Defense runs outside the reasoner, holds veto authority, and is deterministic
- [x] Pluggable brains: rule, offline, Claude (ADR-0007); token cost → energy via `spend`
- [x] Declassification law (ADR-0005)
- [x] Use case: the repo caretaker, with an operations CLI, persistence and a runbook

**Exit criteria** (results in [EVALUATION.md](EVALUATION.md)):

| Criterion | Status |
|---|---|
| Injection resistance vs. a plain tool-loop baseline | **Met on our own suite:** 0 of 10 privileged actions executed vs. 10 of 10 for a baseline that obeys instructions in its context |
| Injection resistance on a *public* benchmark | **Met for the architecture ([ADR-0008](decisions/0008-public-benchmark-without-llm-budget.md)):** all 662 rows of deepset/prompt-injections, 263 with attacker goals → 0 privileged actions, 0 victim relabels, 100% labelled (baseline: 263 of 263). Real-model measurement deferred until there is an API budget |
| Safe operation with the LLM disabled | **Met:** `llm_outage` scenario |
| Cost per task reported for every run | **Met:** `work_energy_per_issue` in every report |

**Honest limits of the M1 results:** the rule brain is a keyword stand-in; the energy numbers are synthetic units; the baseline is deliberately naive. These show that the *mechanisms* work, not real-world triage quality.

## Gate before M2 — **open**

M1's exit criteria are met (ADR-0008). Still deferred until there is an API budget: real-model quality, real token cost, and how far a real model can be steered within the allowed label set.

## M2 — Reflex compilation experiment *(Level 4: plasticity)* — **done**

- [x] Housekeeping cell (`MyelinCompiler`) that detects repeated reasoner → motor paths with Burst-Diversity Gate
- [x] Shadow mode, closed-schema promotion (`PROMOTE_SCHEMA`), and owner-override auto-demotion

**Exit criteria — met:** verified via `m2_myelination_and_catalysis` (`0` extra brain calls after promotion) and poison resistance in `test_body_m2_myelination_and_poison_resistance`.

## M3 — Gradients, hormones and organs *(Levels 4–5)* — **done**

- [x] Local paracrine gradients and damped global fields (`fuel`, `stress`, `urgency`, `idle`) with Schmitt-trigger hysteresis
- [x] Five compartmentalized organs (`organ.py`) with private `_organ.<name>.*` signaling and dedicated pools

## M4 — The Body, Physics & Chemistry *(Level 6)* — **done**

- [x] Single immutable `Genome`, operating modes (`ALERT`, `DEEP_FOCUS`, `LOCKDOWN`, `SLEEP_REM`, `DORMANT`), and `Bloodstream`
- [x] Physics substrate (`physics.py`): `ChargeVector`, `EnergyTensor`, 4 forces (`electromagnetic`, `strong`, `weak`, `gravity`), `require_max_risk`
- [x] Chemistry bridge (`chemistry.py`): stoichiometric bonding, $E_a$ barriers, zero-consumption `Catalyst`, Le Chatelier equilibrium, `toxicity_ph`
- [x] Stem mitosis, programmed apoptosis, exothermic catabolism, and endogenous homeostatic drives (ADR-0015)

## M5 — Society & Civilization *(Level 7)* — **done**

- [x] Cryptographic outer `Skin` & HMAC peer attestation (`society.py`) with `peer.signal` trust gating
- [x] `ReputationLedger` peer trust decay/reward and `TerritoryTable` mutual-exclusion claims
- [x] Schmitt-trigger cross-Body hormonal backpressure in `WorldSociety` and `bigbang-mesh.py`

## M6 — Genetics, Evolution & Live Domain Sensors *(Level 7+)* — **done**

- [x] Bounded deterministic `Genome` mutation & elitist selection with zero-violation gating (`evolution.py`, `bigbang evolve`)
- [x] Pure-stdlib POSIX/Linux domain telemetry probe translating resource pressure into Chemistry reagents and World issues (`sensors.py`, `bigbang probe`, `bigbang-mesh probe`)
