# bigBangEnv — Vision

## One-line definition

**bigBangEnv is a runtime where agents *live* rather than *run*: the environment (kernel) and the agent are booted together — the "Big Bang" — and coupled through one explicit contract, the *membrane*.**

## The problem

What the industry calls an "AI agent" today is a stateless reasoning engine inside a control loop, wired to tools and stitched-on memory. Concretely:

| Primitive | What agents have today |
|---|---|
| **Matter** (state) | Ephemeral prompt text; evaporates when the session ends |
| **Energy** (compute) | Blind; an outside framework hard-caps steps and pulls the plug |
| **Space** (environment) | Borrowed human environments poked through adapters |
| **Time** (execution) | Turn-based; frozen between prompts |
| **Forces** (laws) | Split across five vendors; safety bolted on after incidents |

The industry is building smarter *cells in a vacuum* (better prompts, bigger models) while separately bolting *cages* around them (sandboxes, guardrails). Neither side was designed to talk to the other.

## The thesis

1. **Agent and runtime must be co-designed.** A cell cannot be defined without its environment, and vice versa. The design object is the *membrane* between them — the agent equivalent of a syscall interface.
2. **Laws belong in the kernel, not in the prompt.** Who said something (provenance), what something may do (capabilities), and how much it may spend (energy) are enforced by the runtime, so no text — however clever — can rewrite them.
3. **The LLM is an organ, not the organism.** Reasoning is one expensive, mostly-dormant specialization. Sensing, acting, defending and housekeeping are cheaper, separate, and often deterministic.
4. **Complexity is earned, layer by layer.** Atoms → cells → organs → body. Each layer must be stable and *measured* before the next is built on it.

## Core values (what we keep from the original idea)

| # | Value | In engineering terms |
|---|---|---|
| V1 | **Co-defined membrane** | One contract between agent cells and kernel: identity, state, clock, budget, laws |
| V2 | **Provenance by physics** | The kernel stamps every signal's trust; derived signals inherit the *lowest* trust of their inputs |
| V3 | **LLM as organ** | Reasoning cells are one lineage among several; dormant by default |
| V4 | **Sensed scarcity** | Remaining budget is an input every cell can read, not just an external kill |
| V5 | **Continuity in time** | Cells live across ticks with persistent state, without needing a prompt |
| V6 | **Inhibition is first-class** | "Wait" pauses pending action and "veto" cancels a named action; both are kernel primitives |
| V7 | **Graceful degradation** | Losing the LLM must degrade to safe reflexes, not collapse |
| V8 | **Learning by compilation** | Repeated reasoning can harden into cheap reflexes *(research track)* |

## Guardrail principles (added after review)

- **P1 — Humans hold the outside switch.** A kill switch and audit trail live *outside* any agent body. Nothing inside can disable them.
- **P2 — Explicit authority ladder.** `KERNEL > OWNER > OPERATOR > USER > WORLD`. Owner instructions are not "untrusted world matter".
- **P3 — Observable by default.** Every tick produces a replayable trace. Emergent behaviour is only acceptable if it is debuggable.
- **P4 — Metaphor is a glossary, not a spec.** Every biological term must map to a measurable engineering definition before it is built.
- **P5 — Gall's law.** Ship the smallest system that works, then grow it. No layer is built before the one below passes its exit criteria.

## Glossary — metaphor → engineering

| Metaphor | Engineering meaning in bigBangEnv |
|---|---|
| Big Bang / Genesis | Kernel boot that instantiates clock, bus, budgets, state and laws atomically |
| Membrane | The kernel ↔ cell contract (`Context` object in code) |
| Cell | An isolated, stateful actor stepped by the kernel each tick |
| Lineage | Cell type (sensor, motor, reasoner, defense, housekeeping, spawner) |
| Matter | Persistent, serializable cell state |
| Energy / Fuel | Metered budget units charged for steps and emissions |
| Tick / Heartbeat | One deterministic scheduler round |
| Impulse | A typed, kernel-stamped signal on a topic |
| Inhibition | A signal that pauses pending signals on a topic for its TTL; paused signals don't age and resume when it lifts |
| Veto | An inhibit signal that names signal ids and cancels exactly those |
| Taint residue | The lowest trust a cell has consumed; its later emissions can't exceed it (only declassification can) |
| Receptor | A cell's `accepts` trust: excite input below it is absorbed at delivery and leaves no residue |
| Graded release | Motor resumes paused actions at an average rate (`resume_per_tick`, possibly fractional) once an inhibition lifts, with no burst after idle time |
| Provenance / Taint | The trust level stamped on a signal by the kernel |
| Declassification | Emitting at a cell's own trust despite tainted input; granted cells and closed-schema payloads only |
| Quarantine | A cell rolled back and suspended after raising; released by `revive` |
| Regeneration / Wake | Per-tick budget refill; a dormant cell wakes when it can afford a step |
| Fast spine / Reflex | Deterministic cells that act without waking the reasoner |
| Pre-flight hold | Motors wait one tick before acting so Defense can veto |
| Gradient *(later)* | Shared local state other cells can sense without being addressed |
| Hormone *(later)* | Kernel-computed global scalar (fuel, stress, urgency, idle) |
| Myelination *(later)* | Compiling a verified reasoning path into a deterministic reflex |
| Organ *(later)* | A bounded group of cells with its own budget and typed ports |
| Body *(later)* | A unified identity + immutable policy (Genome) + operating modes |
| Society *(later)* | Many bodies sharing one world kernel |

## Non-goals (for now)

- Building a general multi-agent framework or another prompt-chaining library.
- Self-modifying goals, evolving Genomes, or "immortal" bodies.
- Distributed / multi-host bodies.
- Competing on raw model intelligence.
