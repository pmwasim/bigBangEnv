"""Cells and the membrane (Context) through which they touch the kernel."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from .signal import Kind, Signal, Trust

if TYPE_CHECKING:
    from .kernel import Kernel


class Cell:
    """An isolated, stateful actor stepped by the kernel once per tick.

    Subclasses set ``lineage`` and ``subscriptions`` and implement ``step``.
    ``memory`` is the cell's persistent matter: it must stay JSON-serializable.
    """

    lineage: str = "generic"
    subscriptions: tuple[str, ...] = ()
    step_cost: float = 1.0

    def __init__(
        self,
        name: str,
        *,
        trust: Trust = Trust.OPERATOR,
        emits: Iterable[str] | None = None,
    ) -> None:
        if trust >= Trust.KERNEL:
            raise ValueError("cells cannot hold KERNEL trust")
        self.name = name
        self.trust = trust  # ceiling: emitted signals never exceed it
        self.emits = frozenset(emits) if emits is not None else None  # None = any topic
        self.memory: dict[str, Any] = {}

    def step(self, ctx: Context) -> None:  # pragma: no cover - abstract
        raise NotImplementedError


class Context:
    """The membrane: everything a cell may see or do during one tick."""

    def __init__(self, kernel: Kernel, cell: Cell, inbox: list[Signal]) -> None:
        self._kernel = kernel
        self._cell = cell
        self.inbox = inbox
        # Taint propagation: output can be no more trusted than the cell's
        # ceiling or the least-trusted input it consumed this tick.
        self.trust = min([cell.trust, *(s.trust for s in inbox)])

    @property
    def tick(self) -> int:
        return self._kernel.tick

    @property
    def fuel(self) -> float:
        """Remaining energy for this cell (sensed scarcity)."""
        return self._kernel.budgets[self._cell.name].remaining

    def is_inhibited(self, topic: str) -> bool:
        return self._kernel.is_inhibited(topic)

    def emit(self, topic: str, payload: Any = None, *, ttl: int = 3) -> Signal | None:
        return self._kernel._emit(self._cell, topic, payload, Kind.EXCITE, ttl, self.trust)

    def inhibit(self, topic: str, *, ttl: int = 3, reason: str = "") -> Signal | None:
        return self._kernel._emit(self._cell, topic, reason, Kind.INHIBIT, ttl, self.trust)
