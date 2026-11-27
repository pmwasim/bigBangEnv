# bigBangEnv

**A runtime where agents *live* rather than *run*.**

Today's "AI agents" are stateless reasoning engines in a loop, with safety bolted on from outside. bigBangEnv starts from the other end: boot the environment and the agent *together* — the **Big Bang** — and couple them through one explicit contract, the **membrane**. The kernel owns the laws (identity, trust, energy, time); cells own their state and choices.

> The biology (cells, organs, bodies) is our vocabulary. The engineering underneath is an operating system for agents. See the [glossary](docs/VISION.md#glossary--metaphor--engineering).

## Status

**M0 — Genesis kernel (in progress).** No LLM yet; the kernel primitives exist and are tested:

| Law | Where |
|---|---|
| Deterministic heartbeat (ticks), full event trace | `Kernel.step`, `Kernel.trace` |
| Kernel-stamped trust; cells can't forge sender or authority | `Signal`, `Trust` |
| Taint propagation: output trust = min(cell ceiling, inputs consumed) | `Context.trust` |
| Trust floors per topic, emit capabilities per cell | `Kernel.require`, `Cell(emits=...)` |
| Metered energy, sensed by cells; dormancy when exhausted | `Budget`, `Context.fuel` |
| First-class inhibition (veto) | `Context.inhibit` |
| External kill switch, snapshot/restore | `Kernel.halt`, `Kernel.snapshot` |

## Quick start

```bash
pip install -e ".[dev]"
pytest
python examples/first_light.py
```

`first_light.py` sends an owner command and a prompt-injection attempt through the same cell. The kernel lets the owner's command through and blocks the injection — no prompt filtering involved.

## Docs

- [Vision](docs/VISION.md) — definition, thesis, values, guardrail principles, glossary
- [Brainstorm](docs/BRAINSTORM.md) — valuable ideas, directional possibilities, design forks, open questions
- [Architecture (M0)](docs/ARCHITECTURE.md) — the kernel contract as built
- [Roadmap](docs/ROADMAP.md) — milestones M0–M4 with exit criteria
- [Decisions](docs/decisions/) — architecture decision records
- [Review v0](docs/review-v0.md) — critical review of the original blueprint
- [Origin](docs/origin/gemini-conversation.md) — the conversation the idea came from

## Layout

```
src/bigbang/    kernel, cells, signals
tests/          kernel law tests
examples/       runnable demos
docs/           vision, brainstorm, roadmap, ADRs, origin
```
