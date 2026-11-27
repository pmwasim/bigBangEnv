# ADR-0010: Inhibition pauses, vetoes name their target, taint leaves a residue

- **Status:** Accepted
- **Date:** 2026-11-27

## Context
The PR #1 review found three ways the organism lost or misstated things:

1. **Lockdown destroyed work.** Under ADR-0006 an inhibition cancelled every queued excite signal on its topic, and Motor counted any inhibited action as vetoed. A Defense lockdown (`action.*`) therefore discarded owner commands and unrelated triage for good. With default settings, 25 `close N` commands plus 3 `[bug]` issues ended with nothing closed and nothing labelled. That contradicts "never drop work" and lets a safety reflex silently override OWNER input.
2. **The loop breaker was topic-wide.** Three identical `label 9 bug` commands inhibited all of `action.label` for a window, so none of them, and no other issue's label, went through.
3. **Taint could be laundered through matter.** Output trust was the minimum over *this tick's* inbox. A cell that stored a WORLD payload and emitted it on a later tick with an empty inbox emitted it at its full ceiling. The persisted backlogs added for "never drop work" made that the normal pattern (Reflex re-emitted backlogged issue text at OPERATOR).

Biology uses graded, local and temporary inhibition; destruction is targeted. Provenance in a cell doesn't evaporate between heartbeats.

## Decision
1. **Inhibition pauses.** A live inhibit holds matching excite signals in the queue: they are not delivered, and the ticks they spend held don't count toward their TTL (`Signal.held`). When the inhibition lifts they are delivered as usual. The kernel logs `hold` once per signal.
2. **A veto names its target.** `Context.veto(topic, ids)` emits an inhibit whose payload lists signal ids. It cancels exactly those signals (logged `cancel`), on topics matching its topic, and never pauses anything else. `is_inhibited(topic)` ignores vetoes; `is_vetoed(id, topic)` answers for them. Like any inhibit, a veto is exempt from topic floors and still needs the emit capability for its topic.
3. **Motor** keeps an inhibited action waiting instead of vetoing it. It resumes paused actions once the inhibition lifts, at most `resume_per_tick` per tick (graded release; the caretaker sets it to Defense's own sustained rate, `max_actions // window`). An action paused longer than `patience` ticks (default 100) gives up with an `expired` outcome, so nothing disappears without a report. Only a veto discards an action.
4. **Defense** keeps the lockdown as a pause, vetoes forbidden verbs by id, and makes the loop breaker veto only the copies of one action (same topic and payload) beyond `max_repeats` within the window.
5. **Taint residue.** The kernel keeps, per cell, the lowest trust it has consumed in a committed step (`Kernel.taint`, persisted in snapshots). A cell's emissions are bounded by that residue as well as by its ceiling and this tick's inbox. A rolled-back step leaves no residue. Declassification (ADR-0005) remains the only way to emit above it.
6. **Receptors.** A cell may declare `accepts`, the lowest trust it will take in. Excite signals below it are absorbed at delivery (logged `blocked`, `why="receptor"`) and leave no residue. The caretaker's Commander accepts OWNER only.

## Consequences
- A lockdown now delays work instead of deleting it. A runaway flood is still contained: its copies are vetoed by the loop breaker, held signals come back as a wave that re-trips the rate limit, and resumed work trickles out at the paced rate.
- The loop breaker lets the first `max_repeats` copies of an action run (the runaway evaluation now executes 2 of 150 instead of 0), and stops the rest without touching other work.
- A paused queue can grow while an inhibition lasts. That is bounded by the senders' energy and by Motor's `patience`.
- Taint is now pessimistic: a cell that ever consumed WORLD input stays WORLD-tainted unless it declassifies through a closed schema. A cell that must keep full trust should refuse low-trust input with a receptor rather than read it.
- Snapshots gain an optional `taint` per cell and Motor/Defense memory gain fields; snapshots without them still restore.
