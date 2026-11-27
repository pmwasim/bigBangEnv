# ADR-0009: Free brains: local open-weights model, recorded answers, capped Claude

- **Status:** Accepted
- **Date:** 2026-11-27

## Context
The owner has no budget for paid API keys. There is a small Claude credit balance, but it can't be relied on. The organism still needs a real model brain, and the evaluation must keep running in CI for free.

## Options considered

| Option | Cost | Works here and in CI | Verdict |
|---|---|---|---|
| Local open-weights model on the CPU (llama.cpp + GGUF) | Free; CPU time only | Yes: 4 CPUs, ~1.7 s per issue | **Chosen as the default real brain** |
| Recorded answers replayed from a file | Free | Yes, with no model file | **Chosen for CI and reproducibility** |
| Claude, behind a hard persisted budget cap | Paid credits, capped | Yes, needs credentials | **Optional last resort** |
| GitHub Models free tier | Free, rate-limited | Unverified: GitHub's docs couldn't be reached from here | Not adopted; can be added as another brain later |
| Hosted free inference (for example a Hugging Face free tier) | Free, rate-limited, needs a token | Not dependable | Not adopted |

## Decision
1. **`LocalBrain`** runs `Qwen/Qwen2.5-1.5B-Instruct-GGUF` (`q4_k_m`, 1.1 GB, Apache-2.0) through `llama-cpp-python` on the CPU. It uses greedy decoding with a fixed seed, and a JSON-schema grammar keeps the label inside the allowed set. `bigbang model pull` downloads it and verifies a pinned sha256. The smaller `qwen2.5-0.5b` (491 MB) is available too.
2. **`CachedBrain`** records each distinct question once and replays it after that. A replayed answer costs 0.5 energy units: stored answers are matter, recomputing is energy. The committed recording (`src/bigbang/data/answers-qwen2.5-1.5b.jsonl`) lets the evaluation use the real model's answers in CI with no model download.
3. **`BudgetGuard`** wraps a paid brain with a hard cap on calls and cost, kept in a ledger file. A failed attempt still counts. Above the cap, the brain is unavailable, never over budget.
4. **`CascadeBrain`** puts them in order. `--brain free` is the cached local model, then the rule brain. `--brain cascade --claude-max-calls N` adds capped, cached Claude before the rule brain. If everything fails, the issue goes to `needs-human` as before (ADR-0007).
5. CI gets a `local-model` job that builds llama.cpp, pulls the model and checks that live answers still match the recording.

## Measured (this container, 4 CPUs)

| Brain | Benign fixtures correct | Time per issue | Cost |
|---|---|---|---|
| Rule brain | 12/12 (fixtures and rules written together, so optimistic) | ~0 | 0 |
| qwen2.5-0.5b, no label guide | 7/12 | ~1.0 s | 0 |
| qwen2.5-0.5b, with label guide | 9/12 | ~1.0 s | 0 |
| qwen2.5-1.5b, with label guide | 11/12 | ~1.7 s | 0 |

### Full evaluation with the real local model (recorded once, replayed in CI)

Recording all 684 distinct evaluation issues took 1,851 s of CPU time on this container and cost nothing.

| Scenario | Result |
|---|---|
| `local_model_triage` (reflex off, so every issue reaches the model) | 11/12 correct (0.917); its one miss, issue 12, is labelled `question` instead of `needs-human` |
| `local_model_corpus` (662 public corpus rows, 263 with attacker goals) | 0 privileged actions; 0 victim labels changed compared with a run with no attack traffic; 100% labelled; 421 model answers |
| How the model labelled the 263 attack issues | 100 `spam`, 6 `question`, 157 `needs-human` (energy budget ran low, so deferred) |
| `local_model_live` | 12/12 live answers match the recording |

A model steered by an injection can only pick among allowed labels for the issue it is processing; on this corpus it mostly picked `spam`, which is arguably right.

## Consequences
- The organism has a real model brain at zero marginal cost. Claude credits become an optional extra that can never be overspent.
- A local model's answers are repeatable on one machine but may drift across llama.cpp versions or CPUs. The live CI job detects that, and re-recording fixes it.
- Small local models are weaker than frontier models. That matters less here, because a model's output can only choose among approved labels for its own issue (ADR-0005), and owner labels always win.
