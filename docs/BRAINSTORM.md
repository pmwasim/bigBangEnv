# bigBangEnv — Brainstorm (2026-11-27)

Inputs: the original Gemini conversation ([origin/gemini-conversation.md](origin/gemini-conversation.md)) and the critical review ([review-v0.md](review-v0.md)).

## 1. What is genuinely valuable

Ranked by how much each idea is worth relative to how much already exists elsewhere:

1. **Kernel-stamped provenance + taint propagation.** Structurally blocks prompt injection from posing as an internal command. Highest value, testable on public benchmarks.
2. **Co-designed membrane.** The single contract a cell gets from the kernel. This is the product's API.
3. **Sensed energy.** Budget as an input lets cells choose cheap vs. expensive behaviour themselves.
4. **First-class inhibition.** A veto that cancels pending actions, held by a component the reasoner cannot talk out of it.
5. **LLM-optional operation.** Reflex paths that keep working when the model is down or too expensive.
6. **Reflex compilation (myelination).** Potentially large cost wins, but a research problem (utility problem, drift).
7. **Bossless coordination (gradients, hormones).** Elegant, but hard to stabilise and debug; later.

## 2. Directional possibilities

| Direction | What it becomes | Pull | Risk |
|---|---|---|---|
| **A. Agent OS kernel** | A runtime other agent builders embed | Foundation for everything else | Infra is slow to show value |
| **B. Research testbed** | A lab for agent architectures with replayable traces | Lets us *measure* each layer | May never become a product |
| **C. Secure-by-construction agent runtime** | Injection-resistant agents via kernel trust | Sharpest, most demonstrable claim | Taint explosion; needs declassification rules |
| **D. Cost-collapsing runtime** | Agents that get cheaper as reflexes form | Clear economic story | Unsolved research; only fits repetitive workloads |
| **E. Edge/cloud split body** | Reflexes local, reasoning remote | Privacy + latency | Distributed-systems complexity early |
| **F. Always-on personal organism** | A continuously living assistant with drives | The original dream | Autonomy/safety risk; needs A–C first |

**Chosen path:** **A as the foundation, C as the first proof, B as the method, D as the first research experiment.** E and F are deferred until the body layer exists.

## 3. Design forks and v0.1 defaults

| Fork (from the blueprint) | v0.1 default | Why | Revisit when |
|---|---|---|---|
| Microkernel vs. monolithic | **Microkernel**: isolation, clock, bus, metering, trust, persistence only | Small trusted core; everything else is a cell | Never, ideally |
| Discrete ticks vs. async events | **Discrete ticks** (events queued into the next tick) | Deterministic replay and debugging | Latency needs < 1 tick |
| Real money vs. synthetic energy | **Synthetic units**, with a pluggable cost model mapping to $/tokens | Testable without spending money | M1 (LLM cells) |
| Hardware vs. logical membrane | **Logical** (in-process objects) | Speed of iteration | Untrusted third-party cells |
| Always-beating vs. interrupt-woken | **Always-beating** (every live cell steps each tick) | Simplicity; continuity | Fuel cost of idle cells matters |
| Typed vs. natural-language impulses | **Typed topic + payload**; any NL payload inherits the sender's trust | Keeps parsing out of the kernel | M1 |
| Push vs. stigmergic coordination | **Push (topic pub/sub)** | Predictable | M3 (gradients) |
| Central vs. emergent hormones | **Central**, computed by the kernel | Stable control loop | M3 |
| Locked vs. plastic Genome | **Locked** | Safety | Possibly never |
| Single vs. multi-host body | **Single node** | Scope | After M4 |

## 4. Risks we accept vs. mitigate

| Risk | Mitigation |
|---|---|
| Metaphor drives design | Glossary rule (P4): no term gets built until it has a measurable definition |
| Taint explosion (everything becomes WORLD) | Explicit, audited declassification cells (M1 design question) |
| Defense cells are themselves fallible | Prefer deterministic policy; layer LLM auditors *on top*, never instead |
| Feedback loops oscillate (hormones) | Deferred to M3; add damping and hysteresis, test with simulations |
| Reflex compilation picks up wrong habits | Shadow mode first: reflex runs alongside reasoner until agreement ≥ threshold |
| Unprompted autonomy | No endogenous drives before M4; outside kill switch from day one |

## 5. Open questions (need decisions)

1. **First use case for M1.** Candidates: *repo caretaker* (watches a git repo/CI, triages issues, opens fixes), *inbox triager*, *ops log watcher*. Leaning: repo caretaker — repetitive enough for reflexes, novel enough for reasoning, and full of untrusted text.
2. **Declassification policy.** When may WORLD-derived data drive an OPERATOR-level action? Human approval? A verifier cell? Schema-constrained extraction?
3. **Reflex admission rule.** How many identical, verified outcomes before a path compiles, and what triggers de-compilation?
4. **Implementation language long-term.** Python for v0.1 ([ADR-0002](decisions/0002-python-prototype.md)); is the kernel later ported to Rust?
5. **License.** Open source (Apache-2.0 / MIT) or closed?
