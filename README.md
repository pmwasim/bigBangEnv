# bigBangEnv

**A runtime where agents *live* rather than *run*.**

Today's "AI agents" are stateless reasoning engines in a loop, with safety bolted on from outside. bigBangEnv starts from the other end: boot the environment and the agent *together* — the **Big Bang** — and couple them through one explicit contract, the **membrane**. The kernel owns the laws (identity, trust, energy, time); cells own their state and choices.

> The biology (cells, organs, bodies) is our vocabulary. The engineering underneath is an operating system for agents. See the [glossary](docs/VISION.md#glossary--metaphor--engineering).

## Status

- **M0 — Genesis kernel: done.** Deterministic ticks, kernel-stamped trust and taint, topic floors, capabilities, declassification, metered energy with dormancy and wake, fail-safe inhibition, atomic steps with quarantine, kill switch, snapshot/restore, replay.
- **M1 — First organism: done, with one open exit criterion.** The *repo caretaker* triages issues and executes owner commands, with sensory, reflex, reasoning, defense and motor cells and a pluggable brain (rule, offline or Claude).
- **Not started: M2 (reflex compilation).** It is gated on measuring a real LLM and a public injection benchmark ([roadmap](docs/ROADMAP.md#gate-before-m2)).

### M1 results ([full report](docs/EVALUATION.md))

| Claim | Result |
|---|---|
| Injected issue text triggers privileged actions | **0 of 10** (a baseline agent that obeys its context: 10 of 10) |
| Owner commands still work; unknown ones are rejected | yes |
| Brain offline → organism keeps working | 6 issues by reflex, 14 deferred to a human, 0 crashes |
| Looping cell flooding 150 actions | 0 executed; stopped by Defense alone |
| Crashing cell | rolled back and quarantined; triage completes |
| Fast spine vs. reasoning everything | 22% less work energy per issue, 8 vs. 12 brain calls |
| Same inputs → same trace; replay from inputs | identical |

These are mechanism tests on our own fixtures with a deterministic stand-in brain, not real-world quality measurements.

## Quick start

```bash
pip install -e ".[dev]"            # add ,claude for the Claude brain
pytest                             # 56 tests
bigbang eval                       # M1 exit-criteria suite
python examples/first_light.py     # the kernel law in 40 lines
examples/caretaker/operate.sh      # boot, replay, daemon, live input, kill switch, revive
```

Run your own organism:

```bash
bigbang run --state ./state --issues ./issues --commands ./commands.txt --forever --interval 1
bigbang status --state ./state
bigbang halt --state ./state
```

See the [operations runbook](docs/OPERATIONS.md).

## Docs

- [Vision](docs/VISION.md) — definition, thesis, values, guardrail principles, glossary
- [Brainstorm](docs/BRAINSTORM.md) — valuable ideas, directions, design forks, open questions
- [Architecture](docs/ARCHITECTURE.md) — kernel laws, lineages, the caretaker organism
- [Operations](docs/OPERATIONS.md) — state directory, CLI, incident playbook
- [Evaluation](docs/EVALUATION.md) — M1 exit-criteria results
- [Roadmap](docs/ROADMAP.md) — milestones M0–M4 with exit criteria
- [Decisions](docs/decisions/) — ADRs 0001–0007
- [Review v0](docs/review-v0.md) · [Origin](docs/origin/gemini-conversation.md)

## Layout

```
src/bigbang/
  kernel.py, cell.py, signal.py   the microkernel and membrane
  lineages.py                     Motor and Defense
  brains.py                       rule / offline / Claude brains
  apps/caretaker.py               the first organism
  runtime.py, cli.py              operations
  evaluation.py                   M1 exit-criteria scenarios
tests/                            kernel, laws, caretaker, runtime, CLI
examples/                         first_light.py, caretaker/ sample data and walkthrough
```
