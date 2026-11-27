# bigBangEnv — Roadmap

Each milestone maps to levels of the original Genesis-to-Body blueprint. **No milestone starts until the previous one meets its exit criteria** (principle P5).

## M0 — Genesis kernel *(Levels 0 + 2)* — **in progress**

Kernel primitives with no LLM involved.

- [x] Deterministic tick scheduler (heartbeat)
- [x] Cells with persistent, serializable state (matter)
- [x] Per-cell energy budget, readable by the cell; dormancy on exhaustion
- [x] Topic bus with kernel-stamped trust and TTL decay
- [x] Taint propagation: emitted trust = min(cell ceiling, inputs consumed this tick)
- [x] Trust floors per topic (capability law)
- [x] Emit capabilities per cell
- [x] First-class inhibition (veto cancels pending signals for its TTL)
- [x] External kill switch (`halt`) and full event trace
- [x] Snapshot / restore
- [ ] Trace replay tool (re-run from a snapshot and diff traces)
- [ ] Cell exceptions isolated (a crashing cell is quarantined, not the kernel)

**Exit criteria:** test suite green; two runs from the same inputs produce identical traces; crashing and exhausted cells cannot affect other cells.

## M1 — Three lineages + Defense *(Level 3, partial)*

- Sensor, Motor, Reasoner (Claude-backed) cell base classes
- Defense cell running outside the reasoner, holding inhibit authority
- Pluggable cost model (tokens → energy units)
- One real use case (see BRAINSTORM §5.1)

**Exit criteria:**
- Injection resistance measured on a public agent-injection benchmark (e.g. AgentDojo), compared with a plain tool-loop baseline
- With the LLM disabled, the system keeps running safely on reflexes and the Defense cell
- Cost per task is reported for every run

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
