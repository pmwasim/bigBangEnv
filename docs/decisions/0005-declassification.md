# ADR-0005: Declassification only through closed schemas

- **Status:** Accepted
- **Date:** 2026-11-27

## Context
ADR-0003 made taint strict: anything derived from WORLD input stays WORLD, so it can never reach a topic with an OPERATOR floor. Useful work on untrusted data (labelling an issue from its text) needs an audited way back up.

## Decision
- A cell may emit at its own trust ceiling, ignoring inbox taint, only through `Context.emit_declassified(topic, payload, schema)`.
- The cell needs an operator grant (`Cell(declassify=True)`).
- The payload must match a **closed schema**: exact field set; each field is a bounded non-negative `int`, a `bool`, or a member of a finite set (at most 64 choices). Free-form strings can never be declassified.
- Every declassification is logged (`declassify` event with the from/to trust and payload).

## Consequences
- Injected text can, at worst, choose among a finite set of outcomes the operator already approved (for example, picking the wrong label for *its own* issue). It cannot invent actions, targets or text.
- Which value gets chosen is still influenced by untrusted data, so declassification is a deliberate, reviewable grant, not a default.
- Values a cell copies through, such as the issue id, are only as trustworthy as the sensor that validated them. In the caretaker, Perception validates ids; a cell could still mislabel the issue it is processing, but no other issue.
