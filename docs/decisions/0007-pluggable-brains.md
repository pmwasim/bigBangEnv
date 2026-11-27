# ADR-0007: Pluggable brains with graceful degradation

- **Status:** Accepted
- **Date:** 2026-11-27

## Context
Value V3 says the LLM is an organ, not the organism, and V7 says losing it must not collapse the system. Evaluation must also run offline and deterministically.

## Decision
- Reasoning cells call a `Brain` (`classify(title, body, labels) -> Thought`). Implementations: `RuleBrain` (deterministic keywords), `OfflineBrain` (always down) and `ClaudeBrain` (Anthropic SDK; default `claude-opus-5-5` at `effort: "low"`, with server-side refusal fallbacks enabled).
- Any brain failure (API error, refusal, malformed reply, label outside the allowed set) raises `BrainUnavailable`. The reasoner then labels the issue `needs-human` instead of guessing.
- The brain's output is never trusted directly: its label still goes through declassification (ADR-0005), so a manipulated model can only choose among approved labels.
- Brain cost is declared to the kernel via `Context.spend` (tokens converted to energy units), and the reasoner checks `ctx.fuel` against a reserve before thinking.

## Consequences
- The organism runs with no network and no API key; the evaluation is reproducible.
- Replay (`bigbang replay`) is only exact with deterministic brains; Claude-backed runs are traced but not replayable.
- Real-model quality and cost are not yet measured: that needs an API key and a budget decision from the owner.
