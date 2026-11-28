"""Cells and the membrane (Context) through which they touch the kernel."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from .signal import Kind, Signal, Trust

if TYPE_CHECKING:
    from .kernel import Kernel


class Cell:
    """An isolated, stateful actor stepped by the kernel once per tick.

    Subclasses set ``lineage`` and ``subscriptions`` (exact topics, ``prefix.*``
    or ``*``) and implement ``step``. ``memory`` is the cell's persistent
    matter: it must stay JSON-serializable.
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
        declassify: bool = False,
        accepts: Trust = Trust.WORLD,
        guards: Iterable[str] = (),
        organ: str | None = None,
        cooldown: int = 0,
    ) -> None:
        if trust >= Trust.KERNEL:
            raise ValueError("cells cannot hold KERNEL trust")
        self.name = name
        self.trust = trust  # ceiling: emitted signals never exceed it
        self.emits = frozenset(emits) if emits is not None else None  # None = any topic
        self.declassify = declassify  # operator grant; see ADR-0005
        # Receptor: excite signals below this trust are never delivered, so they
        # can't leave a taint residue in the cell (ADR-0010).
        self.accepts = accepts
        # Fail-closed guardian: matching excite topics pause when this cell is offline (ADR-0011).
        self.guards = tuple(guards)
        # Organ compartment membership and refractory cooldown (ADR-0012).
        self.organ = organ
        self.cooldown = max(0, int(cooldown))
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
        # ceiling, the least-trusted input it consumes this tick, or the
        # residue of anything it consumed before (it may still be in its matter).
        residue = kernel.taint.get(cell.name, cell.trust)
        self.trust = min([cell.trust, residue, *(s.trust for s in inbox)])
        # Risk charge conservation: output risk is at least the highest risk consumed.
        self.risk = max([0.0, *(s.risk for s in inbox)])

    @property
    def tick(self) -> int:
        return self._kernel.tick

    @property
    def fuel(self) -> float:
        """Remaining energy for this cell (sensed scarcity)."""
        return self._kernel.budgets[self._cell.name].remaining

    @property
    def hormones(self) -> dict[str, float]:
        """Global endocrine scalar fields (read-only snapshot)."""
        return dict(self._kernel.hormones)

    @property
    def mode(self) -> str:
        """Current whole-body operating posture."""
        return self._kernel.operating_mode

    def gradient(self, name: str) -> float:
        """Read local paracrine gradient intensity in this cell's organ compartment."""
        compartment = self._cell.organ or "body"
        return self._kernel.gradients.get(compartment, {}).get(name, 0.0)

    def emit_gradient(self, name: str, delta: float) -> float:
        """Emit a paracrine gradient delta into this cell's organ compartment."""
        return self._kernel._emit_gradient(self._cell, name, delta)

    def is_inhibited(self, topic: str) -> bool:
        """True while ``topic`` is paused by an inhibition."""
        return self._kernel.is_inhibited(topic)

    def is_vetoed(self, signal_id: int, topic: str) -> bool:
        """True while a live veto names this signal."""
        return self._kernel.is_vetoed(signal_id, topic)

    def emit(
        self, topic: str, payload: Any = None, *, ttl: int = 3, risk: float = 0.0, affinity: str = "*"
    ) -> Signal | None:
        effective_risk = max(self.risk, float(risk))
        return self._kernel._emit(
            self._cell, topic, payload, Kind.EXCITE, ttl, self.trust, risk=effective_risk, affinity=affinity
        )

    def emit_declassified(
        self,
        topic: str,
        payload: dict[str, Any],
        schema: dict[str, Any],
        *,
        ttl: int = 3,
        risk: float = 0.0,
        affinity: str = "*",
    ) -> Signal | None:
        """Emit at the cell's own trust, if granted and the payload fits a closed schema."""
        effective_risk = max(self.risk, float(risk))
        return self._kernel._declassify(
            self._cell, topic, payload, schema, ttl, self.trust, risk=effective_risk, affinity=affinity
        )

    def condense(self, mass_gain: float = 1.0) -> None:
        """E=mc^2: record condensation of computational energy into structural bound mass."""
        self._kernel._condense(self._cell, mass_gain)

    def inhibit(self, topic: str, *, ttl: int = 3, reason: str = "") -> Signal | None:
        """Pause excite signals on ``topic`` (wildcards allowed) for ``ttl`` ticks."""
        return self._kernel._emit(self._cell, topic, str(reason), Kind.INHIBIT, ttl, self.trust)

    def veto(self, topic: str, signal_ids: Iterable[int], *, ttl: int = 3, reason: str = "") -> Signal | None:
        """Cancel the named excite signals on ``topic``; other signals on the topic are untouched."""
        ids = sorted({int(i) for i in signal_ids})
        payload = {"veto": ids, "reason": str(reason)}
        return self._kernel._emit(self._cell, topic, payload, Kind.INHIBIT, ttl, self.trust)

    def spend(self, units: float, reason: str = "") -> bool:
        """Declare work (e.g. LLM tokens) against this cell's budget."""
        return self._kernel._spend(self._cell, units, reason)
