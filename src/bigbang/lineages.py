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
    """

    lineage = "motor"
    subscriptions = ("action.*",)

    def __init__(self, name: str, effectors: dict[str, Effector], *, hold: int = 1, **kw: Any):
        kw.setdefault("emits", ["outcome.*"])
        super().__init__(name, **kw)
        self.effectors = effectors
        self.hold = hold
        # unsent: outcome reports not yet affordable; kept so no report is ever lost
        self.memory.update(pending=[], executed=0, vetoed=0, failed=0, unsent=[])

    def _report(self, ctx: Context, verb: str, body: dict[str, Any]) -> None:
        self.memory["unsent"].append([verb, body])

    def _flush(self, ctx: Context) -> None:
        unsent = []
        for verb, body in self.memory["unsent"]:
            if ctx.fuel < 1.0 or ctx.emit(f"outcome.{verb}", body) is None:
                unsent.append([verb, body])
        self.memory["unsent"] = unsent

    def step(self, ctx: Context) -> None:
        for signal in ctx.inbox:
            self.memory["pending"].append([ctx.tick + self.hold, signal.topic, signal.payload])

        still_waiting = []
        for due, topic, payload in self.memory["pending"]:
            if due > ctx.tick:
                still_waiting.append([due, topic, payload])
                continue
            verb = topic.split(".", 1)[1]
            if ctx.is_inhibited(topic):
                self.memory["vetoed"] += 1
                self._report(ctx, verb, {"status": "vetoed", "action": payload})
                continue
            effector = self.effectors.get(verb)
            if effector is None:
                self.memory["failed"] += 1
                self._report(ctx, verb, {"status": "failed", "error": "no effector", "action": payload})
                continue
            try:
                result = effector(payload)
            except Exception as exc:  # noqa: BLE001 - world failures are data, not crashes
                self.memory["failed"] += 1
                self._report(ctx, verb, {"status": "failed", "error": str(exc)[:200], "action": payload})
                continue
            self.memory["executed"] += 1
            self._report(ctx, verb, {"status": "done", "action": payload, "result": result})
        self.memory["pending"] = still_waiting
        self._flush(ctx)


class Defense(Cell):
    """Deterministic guardian that watches actions and vetoes runaway behaviour.

    It never consults an LLM, so a prompt-injected reasoner cannot talk it
    out of anything. Policies:
      * rate limit: more than ``max_actions`` within ``window`` ticks -> lockdown
        (inhibit ``action.*`` for ``lockdown_ttl`` ticks)
      * loop breaker: the same action repeated more than ``max_repeats`` times
        within the window -> inhibit that verb
      * forbidden verbs: always inhibited
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
        self.memory.update(recent=[], lockdowns=0, vetoes=0, mode="alert")

    def step(self, ctx: Context) -> None:
        horizon = ctx.tick - self.window
        recent = [r for r in self.memory["recent"] if r[0] > horizon]
        for signal in ctx.inbox:
            recent.append([ctx.tick, signal.topic, json.dumps(signal.payload, sort_keys=True)])
            verb = signal.topic.split(".", 1)[1]
            if verb in self.forbidden:
                self._veto(ctx, signal.topic, f"forbidden verb {verb}")
        self.memory["recent"] = recent

        if self.memory["mode"] == "lockdown" and not ctx.is_inhibited("action.*"):
            self.memory["mode"] = "alert"

        if len(recent) > self.max_actions and self.memory["mode"] != "lockdown":
            ctx.inhibit("action.*", ttl=self.lockdown_ttl, reason="rate limit: lockdown")
            self.memory["mode"] = "lockdown"
            self.memory["lockdowns"] += 1
            return

        counts: dict[tuple[str, str], int] = {}
        for _, topic, body in recent:
            counts[(topic, body)] = counts.get((topic, body), 0) + 1
        for (topic, _), count in sorted(counts.items()):
            if count > self.max_repeats and not ctx.is_inhibited(topic):
                self._veto(ctx, topic, "loop: repeated action")

    def _veto(self, ctx: Context, topic: str, reason: str) -> None:
        self.memory["vetoes"] += 1
        ctx.inhibit(topic, ttl=self.window, reason=reason)
