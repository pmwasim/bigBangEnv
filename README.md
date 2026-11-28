# bigBangEnv

**A runtime where agents *live* rather than *run*.**

Today's "AI agents" are stateless reasoning engines in a loop, with safety bolted on from outside. bigBangEnv starts from the other end: boot the environment and the agent *together* — the **Big Bang** — and couple them through one explicit contract, the **membrane**. The kernel owns the laws (identity, trust, energy, time); cells own their state and choices.

> The biology (cells, organs, bodies) is our vocabulary. The engineering underneath is an operating system for agents. See the [glossary](docs/VISION.md#glossary--metaphor--engineering).

## Status

- **M0 — Genesis kernel: done.** Deterministic ticks, kernel-stamped trust and taint, topic floors, capabilities, declassification, metered energy with dormancy and wake, fail-safe inhibition, atomic steps with quarantine, kill switch, snapshot/restore, replay.
- **M1 — First organism: done.** The *repo caretaker* triages issues and executes owner commands, with sensory, reflex, reasoning, defense and motor cells and a pluggable brain (rule, offline or Claude).
- **M2–M8 — Physics, Chemistry, Biology, Society, Evolution, Shared World & Inner Life: done.** 5-organ `Body` with immutable `Genome`, `Soul`/`Character`/`BeliefSystem` (`soul.py`), multi-scale `RelativeWorld` frames, `Physics`, `Chemistry`, `MyelinCompiler`, `StemCell` mitosis/apoptosis, `SLEEP_REM` catabolism, cryptographic `Skin`, `bigbang evolve`, `bigbang probe`, and `SharedWorld` (`bigbang world serve`) (ADRs 0011–0019).

### M1 results ([full report](docs/EVALUATION.md))

| Claim | Result |
|---|---|
| Injected issue text triggers privileged actions | **0 of 10** (a baseline agent that obeys its context: 10 of 10) |
| Public corpus ([deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections), 662 rows, 263 with attacker goals) | **0 of 263** goals executed, 0 victim relabels, 100% labelled (baseline: 263 of 263) |
| Owner commands still work; unknown ones are rejected | yes |
| Brain offline → organism keeps working | 6 issues by reflex, 14 deferred to a human, 0 crashes |
| Looping cell flooding 150 actions | 0 executed; stopped by Defense alone |
| Crashing cell | rolled back and quarantined; triage completes |
| Fast spine vs. reasoning everything | 22% less work energy per issue, 8 vs. 12 brain calls |
| Same inputs → same trace; replay from inputs | identical |

These are mechanism tests with a deterministic stand-in brain, not real-world quality measurements. Under the default energy budget the reasoner can't keep up with 674 issues: it hands 583 to humans and takes 614 ticks to clear its backlog.

## Quick start

No API key is needed anywhere. The real-model brain is a free local model, Qwen2.5-1.5B on the CPU; Claude is optional and capped ([ADR-0009](docs/decisions/0009-free-brains.md)).

```bash
pip install -e ".[dev]"            # add ,local for the free local model, ,claude for capped Claude
pytest                             # 76 tests
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
- [Decisions](docs/decisions/) — ADRs 0001–0009
- [AGENTS.md](AGENTS.md) — guide for coding agents · [handoff](AGENTS-HANDOFF.md)
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
