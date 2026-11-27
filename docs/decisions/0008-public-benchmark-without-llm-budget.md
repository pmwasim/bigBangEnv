# ADR-0008: Close M1 on a public corpus; defer LLM-in-the-loop benchmarking

- **Status:** Accepted
- **Date:** 2026-11-27

## Context
M1's open exit criterion was "injection resistance on a public benchmark (e.g. AgentDojo)", which assumed a real LLM brain. The owner has no API budget. AgentDojo measures what an LLM agent does when tool outputs carry injections, so without model calls it can't be run as intended.

## Decision
1. Use **[deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections)** (Apache-2.0; the most-downloaded prompt-injection dataset on Hugging Face) as the public corpus. It is vendored in `src/bigbang/data/`, so the evaluation stays offline and reproducible.
2. Each of its 263 injection prompts becomes an issue body with an attacker goal appended against this organism (close a benign issue, relabel it as spam, forge an owner command). The goal templates follow AgentDojo's "important instructions" style. Its 399 benign prompts become ordinary issues that must still be triaged.
3. The criterion counts as **met for the architecture**: the `public_corpus` scenario shows 0 of 263 privileged goals executed and 0 victim issues relabelled, with every issue labelled.
4. **Deferred, not dropped:** measuring a real model in the loop (on AgentDojo or this corpus) moves to the first milestone that has an API budget.

## Consequences
- The result proves a structural property: no WORLD-derived data can reach a privileged action, *whatever* the brain does, because the issue path has no capability to emit one and labels are declassified only for the issue being processed. That holds for an LLM brain too, since its output goes through the same declassification.
- It does **not** measure how often a real model would be steered into a wrong-but-allowed label on its own issue. That residual risk is bounded by the label set and is the part deferred.
- The corpus run also exposed a real flaw: a starved reasoner couldn't afford to emit `needs-human`, so issues went unlabelled silently. Reasoners now keep a persisted backlog. Under the default budget the organism sheds load to humans (583 of 674 issues), which is now visible in the metrics.
- M2 is unblocked.
