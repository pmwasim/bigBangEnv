"""The Genesis kernel: clock, bus, energy, trust laws, persistence and trace."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cell import Cell, Context
from .signal import Kind, Signal, Trust


class KernelHalted(RuntimeError):
    """Raised when stepping a kernel that was stopped by its kill switch."""


@dataclass
class Budget:
    capacity: float
    spent: float = 0.0

    @property
    def remaining(self) -> float:
        return self.capacity - self.spent

    def try_charge(self, amount: float) -> bool:
        if amount > self.remaining:
            return False
        self.spent += amount
        return True


class Kernel:
    """A microkernel for agent cells.

    Laws enforced here, never by prompts:
      * signals are stamped by the kernel (sender, trust, birth tick)
      * emitted trust = min(cell ceiling, trust of inputs consumed this tick)
      * topics can require a minimum trust (signals below it are blocked)
      * every step and emission costs energy; empty budgets mean dormancy
      * inhibit signals cancel pending excite signals on their topic for their TTL
      * signals expire after their TTL; the kill switch is held outside all cells
    """

    EMIT_COST = 1.0

    def __init__(self) -> None:
        self.tick = 0
        self.cells: dict[str, Cell] = {}
        self.budgets: dict[str, Budget] = {}
        self.dormant: set[str] = set()
        self.topic_floor: dict[str, Trust] = {}
        self.queue: list[Signal] = []
        self.trace: list[dict[str, Any]] = []
        self.halted = False
        self._outbox: list[Signal] = []
        self._next_id = 1
        self._log("genesis")

    # ----------------------------------------------------------- setup
    def spawn(self, cell: Cell, *, fuel: float = 100.0) -> Cell:
        if cell.name in self.cells:
            raise ValueError(f"cell {cell.name!r} already exists")
        self.cells[cell.name] = cell
        self.budgets[cell.name] = Budget(fuel)
        self._log("spawn", cell=cell.name, lineage=cell.lineage, trust=cell.trust.name, fuel=fuel)
        return cell

    def require(self, topic: str, trust: Trust) -> None:
        """Law: signals on ``topic`` need at least ``trust``."""
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

    # ------------------------------------------------------- heartbeat
    def step(self) -> None:
        if self.halted:
            raise KernelHalted("kernel was halted")
        self.tick += 1

        live: list[Signal] = []
        for signal in self.queue:
            if signal.expired(self.tick):
                self._log("expire", id=signal.id, topic=signal.topic)
            else:
                live.append(signal)

        inhibited = {s.topic for s in live if s.kind is Kind.INHIBIT}
        pending: list[Signal] = []
        for signal in live:
            if signal.kind is Kind.EXCITE and signal.topic in inhibited:
                self._log("cancel", id=signal.id, topic=signal.topic)
            else:
                pending.append(signal)

        delivered: set[int] = set()
        for name in sorted(self.cells):
            if self.halted:
                break
            if name in self.dormant:
                continue
            cell = self.cells[name]
            if not self.budgets[name].try_charge(cell.step_cost):
                self.dormant.add(name)
                self._log("dormant", cell=name)
                continue
            inbox = [
                s for s in pending if s.kind is Kind.EXCITE and s.topic in cell.subscriptions
            ]
            delivered.update(s.id for s in inbox)
            cell.step(Context(self, cell, inbox))

        # Delivered excite signals are consumed; inhibit signals persist
        # until they expire. New emissions become visible next tick.
        self.queue = [
            s for s in pending if s.kind is Kind.INHIBIT or s.id not in delivered
        ] + self._outbox
        self._outbox = []

    def run(self, ticks: int) -> None:
        for _ in range(ticks):
            if self.halted:
                break
            self.step()

    def is_inhibited(self, topic: str) -> bool:
        return any(
            s.kind is Kind.INHIBIT and s.topic == topic and not s.expired(self.tick)
            for s in self.queue + self._outbox
        )

    # -------------------------------------------------------- membrane
    def _emit(
        self, cell: Cell, topic: str, payload: Any, kind: Kind, ttl: int, trust: Trust
    ) -> Signal | None:
        if cell.emits is not None and topic not in cell.emits:
            self._log("denied", cell=cell.name, topic=topic, why="no capability")
            return None
        floor = self.topic_floor.get(topic)
        if floor is not None and trust < floor:
            self._log("blocked", cell=cell.name, topic=topic, trust=trust.name, needs=floor.name)
            return None
        if not self.budgets[cell.name].try_charge(self.EMIT_COST):
            self._log("denied", cell=cell.name, topic=topic, why="no fuel")
            return None
        signal = self._make(topic, payload, kind, cell.name, trust, ttl)
        self._outbox.append(signal)
        self._log("emit", **signal.to_dict())
        return signal

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
        self.dormant = set()
        for name, state in snap["cells"].items():
            self.cells[name].memory = json.loads(json.dumps(state["memory"]))
            self.budgets[name].spent = state["spent"]
            if state["dormant"]:
                self.dormant.add(name)
        self._log("restore", from_tick=snap["tick"])

    def save_trace(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            for record in self.trace:
                fh.write(json.dumps(record, default=str) + "\n")


def big_bang(*cells: Cell, fuel: float = 100.0) -> Kernel:
    """Boot a kernel and spawn the given cells in one step."""
    kernel = Kernel()
    for cell in cells:
        kernel.spawn(cell, fuel=fuel)
    return kernel
