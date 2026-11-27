"""The Genesis kernel: clock, bus, energy, trust laws, persistence and trace."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cell import Cell, Context
from .signal import Kind, Signal, Trust

MAX_CHOICES = 64
MAX_INT = 2**31


class KernelHalted(RuntimeError):
    """Raised when stepping a kernel that was stopped by its kill switch."""


def topic_matches(pattern: str, topic: str) -> bool:
    """Exact match, ``*`` for everything, or ``prefix.*`` for a subtree."""
    if pattern in ("*", topic):
        return True
    return pattern.endswith(".*") and topic.startswith(pattern[:-1])


def validate_schema(payload: Any, schema: dict[str, Any]) -> str | None:
    """Check a declassified payload against a closed schema. Returns an error or None.

    Each schema value is ``int``, ``bool`` or a finite collection of allowed
    primitive values. Free-form strings can never be declassified.
    """
    if not isinstance(payload, dict) or set(payload) != set(schema):
        return "fields do not match schema"
    for key, rule in schema.items():
        value = payload[key]
        if rule is int:
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < MAX_INT:
                return f"{key}: not a bounded non-negative int"
        elif rule is bool:
            if not isinstance(value, bool):
                return f"{key}: not a bool"
        elif isinstance(rule, (set, frozenset, tuple, list)):
            if len(rule) > MAX_CHOICES:
                return f"{key}: too many choices"
            if not isinstance(value, (str, int, bool)) or value not in rule:
                return f"{key}: value not in allowed choices"
        else:
            return f"{key}: unsupported rule"
    return None


@dataclass
class Budget:
    capacity: float
    spent: float = 0.0
    regen: float = 0.0  # energy restored at the start of every tick

    @property
    def remaining(self) -> float:
        return self.capacity - self.spent

    def try_charge(self, amount: float) -> bool:
        if amount < 0 or amount > self.remaining:
            return False
        self.spent += amount
        return True

    def regenerate(self) -> None:
        if self.regen:
            self.spent = max(0.0, self.spent - self.regen)


class Kernel:
    """A microkernel for agent cells.

    Laws enforced here, never by prompts:
      * signals are stamped by the kernel (sender, trust, birth tick)
      * emitted trust = min(cell ceiling, trust of inputs consumed this tick)
      * topics can require a minimum trust; inhibit signals are exempt (fail-safe)
      * declassification only for granted cells and closed-schema payloads
      * every step, emission and declared spend costs energy; empty budgets mean dormancy
      * inhibit signals cancel pending excite signals on matching topics for their TTL
      * a cell that raises is rolled back and quarantined; the kernel keeps running
      * signals expire after their TTL; the kill switch is held outside all cells
    """

    EMIT_COST = 1.0

    def __init__(self) -> None:
        self.tick = 0
        self.cells: dict[str, Cell] = {}
        self.budgets: dict[str, Budget] = {}
        self.dormant: set[str] = set()
        self.quarantined: set[str] = set()
        self.topic_floor: dict[str, Trust] = {}
        self.queue: list[Signal] = []
        self.trace: list[dict[str, Any]] = []
        self.halted = False
        self._outbox: list[Signal] = []
        self._next_id = 1
        self._log("genesis")

    # ----------------------------------------------------------- setup
    def spawn(self, cell: Cell, *, fuel: float = 100.0, regen: float = 0.0) -> Cell:
        if cell.name in self.cells:
            raise ValueError(f"cell {cell.name!r} already exists")
        self.cells[cell.name] = cell
        self.budgets[cell.name] = Budget(fuel, regen=regen)
        self._log(
            "spawn", cell=cell.name, lineage=cell.lineage, trust=cell.trust.name,
            fuel=fuel, regen=regen, declassify=cell.declassify,
        )
        return cell

    def require(self, topic: str, trust: Trust) -> None:
        """Law: excite signals on ``topic`` need at least ``trust``."""
        self.topic_floor[topic] = trust
        self._log("law", topic=topic, min_trust=trust.name)

    # --------------------------------------------------- outside world
    def inject(
        self,
        topic: str,
        payload: Any = None,
        *,
        trust: Trust = Trust.WORLD,
        sender: str = "world",
        ttl: int = 3,
    ) -> Signal:
        """Entry point for input from outside the kernel. Delivered next tick."""
        if trust >= Trust.KERNEL:
            raise ValueError("outside input cannot claim KERNEL trust")
        signal = self._make(topic, payload, Kind.EXCITE, sender, trust, ttl)
        self.queue.append(signal)
        self._log("inject", **signal.to_dict())
        return signal

    def halt(self, reason: str = "") -> None:
        """External kill switch. No cell can call or undo this."""
        self.halted = True
        self._log("halt", reason=reason)

    def revive(self, name: str, *, refuel: float = 0.0) -> None:
        """Operator action: release a quarantined/dormant cell, optionally refuelling it."""
        budget = self.budgets[name]
        budget.spent = max(0.0, budget.spent - refuel)
        self.quarantined.discard(name)
        self.dormant.discard(name)
        self._log("revive", cell=name, refuel=refuel)

    # ------------------------------------------------------- heartbeat
    def step(self) -> None:
        if self.halted:
            raise KernelHalted("kernel was halted")
        self.tick += 1

        for name, budget in self.budgets.items():
            budget.regenerate()
            cell = self.cells[name]
            if name in self.dormant and budget.remaining >= cell.step_cost:
                self.dormant.discard(name)
                self._log("wake", cell=name)

        live: list[Signal] = []
        for signal in self.queue:
            if signal.expired(self.tick):
                self._log("expire", id=signal.id, topic=signal.topic)
            else:
                live.append(signal)

        inhibitors = [s.topic for s in live if s.kind is Kind.INHIBIT]
        pending: list[Signal] = []
        for signal in live:
            if signal.kind is Kind.EXCITE and any(topic_matches(p, signal.topic) for p in inhibitors):
                self._log("cancel", id=signal.id, topic=signal.topic)
            else:
                pending.append(signal)

        delivered: set[int] = set()
        for name in sorted(self.cells):
            if self.halted:
                break
            if name in self.dormant or name in self.quarantined:
                continue
            cell = self.cells[name]
            if not self.budgets[name].try_charge(cell.step_cost):
                self.dormant.add(name)
                self._log("dormant", cell=name)
                continue
            inbox = [
                s for s in pending
                if s.kind is Kind.EXCITE and any(topic_matches(p, s.topic) for p in cell.subscriptions)
            ]
            delivered.update(s.id for s in inbox)
            self._run_cell(cell, inbox)

        # Delivered excite signals are consumed; inhibit signals persist
        # until they expire. New emissions become visible next tick.
        self.queue = [
            s for s in pending if s.kind is Kind.INHIBIT or s.id not in delivered
        ] + self._outbox
        self._outbox = []

    def _run_cell(self, cell: Cell, inbox: list[Signal]) -> None:
        """Step one cell atomically: on exception, roll back its matter and emissions."""
        mark = len(self._outbox)
        try:
            saved = json.dumps(cell.memory)
            cell.step(Context(self, cell, inbox))
            json.dumps(cell.memory)  # matter must stay serializable
        except Exception as exc:  # noqa: BLE001 - isolation boundary
            rolled_back = [s.id for s in self._outbox[mark:]]
            del self._outbox[mark:]
            try:
                cell.memory = json.loads(saved)
            except NameError:  # memory was unserializable before the step
                cell.memory = {}
            self.quarantined.add(cell.name)
            self._log(
                "quarantine", cell=cell.name, error=f"{type(exc).__name__}: {exc}"[:300],
                rolled_back=rolled_back,
            )

    def run(self, ticks: int) -> None:
        for _ in range(ticks):
            if self.halted:
                break
            self.step()

    def is_inhibited(self, topic: str) -> bool:
        return any(
            s.kind is Kind.INHIBIT and topic_matches(s.topic, topic) and not s.expired(self.tick)
            for s in self.queue + self._outbox
        )

    # -------------------------------------------------------- membrane
    def _emit(
        self, cell: Cell, topic: str, payload: Any, kind: Kind, ttl: int, trust: Trust
    ) -> Signal | None:
        if cell.emits is not None and not any(topic_matches(p, topic) for p in cell.emits):
            self._log("denied", cell=cell.name, topic=topic, why="no capability")
            return None
        floor = self.topic_floor.get(topic)
        if kind is Kind.EXCITE and floor is not None and trust < floor:
            self._log("blocked", cell=cell.name, topic=topic, trust=trust.name, needs=floor.name)
            return None
        if not self.budgets[cell.name].try_charge(self.EMIT_COST):
            self._log("denied", cell=cell.name, topic=topic, why="no fuel")
            return None
        signal = self._make(topic, payload, kind, cell.name, trust, ttl)
        self._outbox.append(signal)
        self._log("emit", **signal.to_dict())
        return signal

    def _declassify(
        self, cell: Cell, topic: str, payload: Any, schema: dict[str, Any], ttl: int, tainted: Trust
    ) -> Signal | None:
        if not cell.declassify:
            self._log("denied", cell=cell.name, topic=topic, why="no declassify grant")
            return None
        error = validate_schema(payload, schema)
        if error:
            self._log("denied", cell=cell.name, topic=topic, why=f"schema: {error}")
            return None
        self._log("declassify", cell=cell.name, topic=topic, from_trust=tainted.name,
                  to_trust=cell.trust.name, payload=payload)
        return self._emit(cell, topic, payload, Kind.EXCITE, ttl, cell.trust)

    def _spend(self, cell: Cell, units: float, reason: str) -> bool:
        ok = self.budgets[cell.name].try_charge(units)
        self._log("spend" if ok else "denied", cell=cell.name, units=units, why=reason)
        return ok

    def _make(
        self, topic: str, payload: Any, kind: Kind, sender: str, trust: Trust, ttl: int
    ) -> Signal:
        signal = Signal(self._next_id, topic, payload, kind, sender, trust, self.tick, ttl)
        self._next_id += 1
        return signal

    # ------------------------------------------------ matter & history
    def _log(self, event: str, **data: Any) -> None:
        self.trace.append({"tick": self.tick, "event": event, **data})

    def snapshot(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "next_id": self._next_id,
            "halted": self.halted,
            "queue": [s.to_dict() for s in self.queue],
            "cells": {
                name: {
                    "memory": cell.memory,
                    "spent": self.budgets[name].spent,
                    "dormant": name in self.dormant,
                    "quarantined": name in self.quarantined,
                }
                for name, cell in self.cells.items()
            },
        }

    def restore(self, snap: dict[str, Any]) -> None:
        """Restore state into a kernel whose cells were spawned the same way."""
        missing = set(snap["cells"]) - set(self.cells)
        if missing:
            raise ValueError(f"cells not spawned: {sorted(missing)}")
        self.tick = snap["tick"]
        self._next_id = snap["next_id"]
        self.halted = snap["halted"]
        self.queue = [Signal.from_dict(s) for s in snap["queue"]]
        self.dormant, self.quarantined = set(), set()
        for name, state in snap["cells"].items():
            self.cells[name].memory = json.loads(json.dumps(state["memory"]))
            self.budgets[name].spent = state["spent"]
            if state["dormant"]:
                self.dormant.add(name)
            if state.get("quarantined"):
                self.quarantined.add(name)
        self._log("restore", from_tick=snap["tick"])

    def save_trace(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            for record in self.trace:
                fh.write(json.dumps(record, default=str) + "\n")


def big_bang(*cells: Cell, fuel: float = 100.0, regen: float = 0.0) -> Kernel:
    """Boot a kernel and spawn the given cells in one step."""
    kernel = Kernel()
    for cell in cells:
        kernel.spawn(cell, fuel=fuel, regen=regen)
    return kernel
