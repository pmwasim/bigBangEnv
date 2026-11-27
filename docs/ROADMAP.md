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

## M1 — Three lineages + Defense *(Level 3, partial)* — **done, with one open criterion**

- [x] Sensory (perception), reflex, reasoning, motor-planning (commander), motor, defense and housekeeping cells
- [x] Defense runs outside the reasoner, holds veto authority, and is deterministic
- [x] Pluggable brains: rule, offline, Claude (ADR-0007); token cost → energy via `spend`
- [x] Declassification law (ADR-0005)
- [x] Use case: the repo caretaker, with an operations CLI, persistence and a runbook

**Exit criteria** (results in [EVALUATION.md](EVALUATION.md)):

| Criterion | Status |
|---|---|
| Injection resistance vs. a plain tool-loop baseline | **Met on our own suite:** 0 of 10 privileged actions executed vs. 10 of 10 for a baseline that obeys instructions in its context |
| Injection resistance on a *public* benchmark (e.g. AgentDojo) | **Open:** needs a benchmark adapter and a real LLM brain |
| Safe operation with the LLM disabled | **Met:** `llm_outage` scenario |
| Cost per task reported for every run | **Met:** `work_energy_per_issue` in every report |

**Honest limits of the M1 results:** the fixtures are ours (22 issues); the rule brain is a keyword stand-in; the energy numbers are synthetic units; the baseline is deliberately naive. These show that the *mechanisms* work, not real-world quality.

## Gate before M2

Per P5, M2 starts only after the open M1 criterion is closed. That needs two owner decisions:
1. Approve an API budget so `ClaudeBrain` can be measured (quality, real token cost, injection behaviour of the model itself).
2. Pick the public benchmark and approve the adapter work.

## M2 — Reflex compilation experiment *(Level 4: plasticity)*

- Housekeeping cell that detects repeated reasoner → motor paths
- Shadow mode, then promotion, then automatic de-compilation on drift

**Exit criteria:** cost per task drops by a pre-registered margin over N runs with no loss in task success; the utility problem is monitored (reflex count vs. latency).

## M3 — Gradients, hormones and organs *(Levels 4–5)*

- Local gradients, central global fields (fuel, stress, urgency, idle) with damping
- Organs: grouped cells with their own budget and typed ports

**Exit criteria:** no oscillation under stress simulations; organ isolation tests pass.

## M4 — The Body *(Level 6)*

- Single identity, immutable policy (Genome), operating modes (Alert, Focus, Lockdown, Sleep, Dormancy)
- Only then consider endogenous drives, gated by human approval points

## Later — Society *(Level 7)*

Multiple bodies in a shared world kernel: discovery, trust, energy exchange, governance.
