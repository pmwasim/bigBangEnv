# Review v0 — the original Genesis-to-Body blueprint (2026-11-27)

**Verdict:** the diagnosis is strong and the core design idea is sound, but the blueprint is a vision rather than an architecture. About two-thirds of it is metaphor that still has to become engineering. The useful core is smaller than the six levels suggest, and it can be built.

## Scorecard (1–5)

| Dimension | Score | Why |
|---|---|---|
| Diagnosis of today's agents | 4.5 | No state between sessions, blind spending, turn-based execution, bolted-on safety: all real gaps |
| Core design idea | 4 | Co-designing the agent and its runtime through one boundary is the right move |
| Internal consistency | 3 | Signaling appears at Level 4, yet Level 2 cells already need it |
| Originality | 2.5–3 | Most pieces exist elsewhere; the new part is unifying them under one kernel |
| Technical specificity | 1.5 | Stress, Fuel, thresholds and Genome have no measurable definitions |
| Feasibility of a v0.1 | 3 | Only if cut down sharply |
| Safety | 2.5 | Good provenance ideas; self-direction adds risk without matching controls |
| Testability | 1 | No metrics, no target use case, no kill criteria |

## Strengths

1. The cell and kernel defined together, through a membrane (like a syscall interface).
2. Kernel-stamped provenance, so injected text can't pose as an internal command.
3. The LLM demoted to one dormant-by-default specialization.
4. Budget fed back as an input the agent senses.
5. Inhibition ("stop") as a first-class signal.
6. Graceful degradation when the LLM is unavailable.

## Weaknesses

1. **Metaphor drives the design.** Hormones, drives, circadian modes and mortality come from the story, not from requirements. Level 0's E=mc² mapping is decoration; Level 0 is an OS kernel.
2. **The source conversation never pushed back.** Gemini agreed with every step, and a repeated prompt produced two different, equally confident architectures.
3. **The hardest problems get one line each:**
   - reflex compilation: when is it safe, how to detect drift, and the *utility problem* known from Soar's chunking;
   - taint propagation: everything touched by untrusted text risks becoming tainted;
   - who watches the watchers (LLM immune cells are injectable; rule-based ones miss semantic attacks);
   - global feedback signals can oscillate without damping.
4. **No owner or authority structure.** The owner's own instructions were tagged "untrusted world matter".
5. **Autonomy without oversight.** The only kill switch lived inside the Body.
6. **Unsupported numbers and large complexity** ("90% brain-free"; 6 × 5 × 3 × 5 × 5 concepts before any value).
7. **Missing:** use case, metrics, observability, cross-organ consistency, memory migration, human interface.

## Prior art to borrow from

| Concept | Existing equivalent |
|---|---|
| Kernel, membrane, capabilities | Microkernels, capability OSes (seL4), AIOS |
| Cells, stem cells, apoptosis | Actor model, Erlang/OTP supervision trees |
| Fast spine vs. slow cortex | Brooks's subsumption architecture, dual-process theory |
| Myelination | Soar chunking, plan caching and distillation |
| Local gradients | Blackboard systems, stigmergy |
| Memory organ, sleep | MemGPT/Letta memory paging and background processing |

## How this repo responds

- Principles P1–P5 in [VISION.md](VISION.md) address weaknesses 1, 4, 5 and 6.
- [ADR-0003](decisions/0003-trust-ladder-and-taint.md) adds the authority ladder and makes taint explicit.
- [ROADMAP.md](ROADMAP.md) gives every milestone exit criteria and defers hormones, organs and drives.
