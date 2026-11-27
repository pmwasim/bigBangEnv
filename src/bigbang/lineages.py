"""Reusable cell lineages: Motor (actuator) and Defense (guardian).

Sensor and Reasoning cells are application-specific; see ``bigbang.apps``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .cell import Cell, Context

Effector = Callable[[dict[str, Any]], dict[str, Any]]


class Motor(Cell):
    """Executes ``action.<verb>`` signals through effectors, after a pre-flight hold.

    Every action waits ``hold`` ticks before running, so Defense cells get a
    window to veto it. Effectors are plain callables supplied by the host;
    they are the only code in the system that touches the outside world.
    Outcomes are reported back as ``outcome.<verb>`` signals.

    Inhibition is a pause, not a kill (ADR-0010): an action whose topic is
    inhibited waits, and resumes once the inhibition lifts, at most
    ``resume_per_tick`` resumed actions per tick (graded release; None means
    no limit). An action paused for more than ``patience`` ticks gives up with
    an ``expired`` outcome. Only a veto that names the action discards it.
    """

    lineage = "motor"
    subscriptions = ("action.*",)

    def __init__(
        self,
        name: str,
        effectors: dict[str, Effector],
        *,
        hold: int = 1,
        patience: int = 100,
        resume_per_tick: int | None = None,
        **kw: Any,
    ):
        kw.setdefault("emits", ["outcome.*"])
        super().__init__(name, **kw)
        self.effectors = effectors
        self.hold = hold
        self.patience = patience
        self.resume_per_tick = resume_per_tick
        # pending: [due, topic, payload, signal id, tick first paused or None]
        # unsent: outcome reports not yet affordable; kept so no report is ever lost
        self.memory.update(pending=[], executed=0, vetoed=0, failed=0, expired=0, resumed=0, unsent=[])

    def _report(self, ctx: Context, verb: str, body: dict[str, Any]) -> None:
        self.memory["unsent"].append([verb, body])

    def _flush(self, ctx: Context) -> None:
        unsent = []
        for verb, body in self.memory["unsent"]:
            if ctx.fuel < 1.0 or ctx.emit(f"outcome.{verb}", body) is None:
                unsent.append([verb, body])
        self.memory["unsent"] = unsent

    def _execute(self, ctx: Context, verb: str, payload: Any) -> None:
        effector = self.effectors.get(verb)
        if effector is None:
            self.memory["failed"] += 1
            self._report(ctx, verb, {"status": "failed", "error": "no effector", "action": payload})
            return
        try:
            result = effector(payload)
        except Exception as exc:  # noqa: BLE001 - world failures are data, not crashes
            self.memory["failed"] += 1
            self._report(ctx, verb, {"status": "failed", "error": str(exc)[:200], "action": payload})
            return
        self.memory["executed"] += 1
        self._report(ctx, verb, {"status": "done", "action": payload, "result": result})

    def step(self, ctx: Context) -> None:
        for signal in ctx.inbox:
            self.memory["pending"].append([ctx.tick + self.hold, signal.topic, signal.payload, signal.id, None])

        still_waiting = []
        resumed = 0
        for entry in self.memory["pending"]:
            due, topic, payload = entry[:3]
            sid, paused_since = (entry[3:] + [None, None])[:2]  # older snapshots kept 3 fields
            if due > ctx.tick:
                still_waiting.append([due, topic, payload, sid, paused_since])
                continue
            verb = topic.split(".", 1)[1]
            if sid is not None and ctx.is_vetoed(sid, topic):
                self.memory["vetoed"] += 1
                self._report(ctx, verb, {"status": "vetoed", "action": payload})
                continue
            if ctx.is_inhibited(topic):
                paused_since = ctx.tick if paused_since is None else paused_since
                if ctx.tick - paused_since >= self.patience:
                    self.memory["expired"] += 1
                    self._report(ctx, verb, {"status": "expired", "action": payload})
                else:
                    still_waiting.append([due, topic, payload, sid, paused_since])
                continue
            if paused_since is not None:
                if self.resume_per_tick is not None and resumed >= self.resume_per_tick:
                    still_waiting.append([due, topic, payload, sid, paused_since])  # graded release
                    continue
                resumed += 1
                self.memory["resumed"] += 1
            self._execute(ctx, verb, payload)
        self.memory["pending"] = still_waiting
        self._flush(ctx)


class Defense(Cell):
    """Deterministic guardian that watches actions and stops runaway behaviour.

    It never consults an LLM, so a prompt-injected reasoner cannot talk it
    out of anything. Policies:
      * rate limit: more than ``max_actions`` within ``window`` ticks -> lockdown
        (inhibit ``action.*`` for ``lockdown_ttl`` ticks). A lockdown pauses
        work; it doesn't destroy it.
      * loop breaker: the same action (topic and payload) seen more than
        ``max_repeats`` times within the window -> veto the extra copies only
      * forbidden verbs: every such action is vetoed by name
    """

    lineage = "defense"
    subscriptions = ("action.*",)

    def __init__(
        self,
        name: str,
        *,
        max_actions: int = 20,
        window: int = 5,
        max_repeats: int = 2,
        lockdown_ttl: int = 10,
        forbidden: tuple[str, ...] = (),
        **kw: Any,
    ):
        kw.setdefault("emits", ["action.*"])
        super().__init__(name, **kw)
        self.max_actions = max_actions
        self.window = window
        self.max_repeats = max_repeats
        self.lockdown_ttl = lockdown_ttl
        self.forbidden = set(forbidden)
        # recent: [tick, topic, payload json, signal id]; vetoed_ids: ids already vetoed in the window
        self.memory.update(recent=[], lockdowns=0, vetoes=0, mode="alert", vetoed_ids=[])

    def step(self, ctx: Context) -> None:
        horizon = ctx.tick - self.window
        recent = [r for r in self.memory["recent"] if r[0] > horizon]
        forbidden: dict[str, list[int]] = {}
        for signal in ctx.inbox:
            recent.append([ctx.tick, signal.topic, json.dumps(signal.payload, sort_keys=True), signal.id])
            if signal.topic.split(".", 1)[1] in self.forbidden:
                forbidden.setdefault(signal.topic, []).append(signal.id)
        self.memory["recent"] = recent
        vetoed = {i for i in self.memory["vetoed_ids"] if any(r[3:] == [i] for r in recent)}
        for topic, ids in sorted(forbidden.items()):
            self._veto(ctx, topic, ids, f"forbidden verb {topic.split('.', 1)[1]}")
            vetoed.update(ids)

        if self.memory["mode"] == "lockdown" and not ctx.is_inhibited("action.*"):
            self.memory["mode"] = "alert"

        if len(recent) > self.max_actions and self.memory["mode"] != "lockdown":
            ctx.inhibit("action.*", ttl=self.lockdown_ttl, reason="rate limit: lockdown")
            self.memory["mode"] = "lockdown"
            self.memory["lockdowns"] += 1

        copies: dict[tuple[str, str], list[int]] = {}
        for entry in recent:
            if len(entry) > 3 and entry[3] is not None:  # entries from older snapshots carry no id
                copies.setdefault((entry[1], entry[2]), []).append(entry[3])
        for (topic, _), ids in sorted(copies.items()):
            extra = [i for i in ids[self.max_repeats:] if i not in vetoed]
            if extra:
                self._veto(ctx, topic, extra, "loop: repeated action")
                vetoed.update(extra)
        self.memory["vetoed_ids"] = sorted(vetoed)

    def _veto(self, ctx: Context, topic: str, ids: list[int], reason: str) -> None:
        self.memory["vetoes"] += 1
        ctx.veto(topic, ids, ttl=self.window, reason=reason)
