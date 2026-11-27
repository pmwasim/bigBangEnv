"""Molecules & Matter: structured, provenance-tagged, decaying state primitives.

Implements the Compute-Storage Equivalence (E=mc^2): expensive reasoning
expenditures condense into structured persistent molecules, while transient
working molecules decay automatically after their TTL.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .signal import Trust


@dataclass
class Molecule:
    """One structured unit of persistent or transient cell matter."""

    key: str
    value: Any
    trust: Trust
    born: int
    ttl: int | None = None  # None = consolidated long-term matter; int = working scratchpad
    hits: int = 0

    def expired(self, tick: int) -> bool:
        return self.ttl is not None and (tick - self.born) > self.ttl

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["trust"] = self.trust.name
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Molecule:
        return cls(
            key=data["key"],
            value=data["value"],
            trust=Trust[data["trust"]],
            born=int(data["born"]),
            ttl=data.get("ttl"),
            hits=int(data.get("hits", 0)),
        )


class MatterStore:
    """Bounded, JSON-serializable collection of Molecules with TTL decay."""

    def __init__(self, *, max_molecules: int = 512) -> None:
        self.max_molecules = max_molecules
        self._items: dict[str, Molecule] = {}

    def put(
        self,
        key: str,
        value: Any,
        *,
        trust: Trust,
        tick: int,
        ttl: int | None = None,
    ) -> Molecule:
        mol = Molecule(key=key, value=value, trust=trust, born=tick, ttl=ttl)
        if key in self._items:
            del self._items[key]
        self._items[key] = mol
        self._enforce_cap()
        return mol

    def get(self, key: str, tick: int | None = None) -> Molecule | None:
        mol = self._items.get(key)
        if mol is None:
            return None
        if tick is not None and mol.expired(tick):
            del self._items[key]
            return None
        mol.hits += 1
        return mol

    def consolidate(self, key: str) -> bool:
        """Freeze a transient working molecule into permanent matter (ttl=None)."""
        mol = self._items.get(key)
        if mol is None:
            return False
        mol.ttl = None
        return True

    def decay(self, tick: int) -> int:
        """Remove all molecules whose TTL has elapsed. Returns pruned count."""
        expired = [k for k, m in self._items.items() if m.expired(tick)]
        for k in expired:
            del self._items[k]
        return len(expired)

    def _enforce_cap(self) -> None:
        while len(self._items) > self.max_molecules:
            # Evict oldest transient molecule first, else oldest entry
            transient = next((k for k, m in self._items.items() if m.ttl is not None), None)
            victim = transient if transient is not None else next(iter(self._items))
            del self._items[victim]

    def __len__(self) -> int:
        return len(self._items)

    def items(self) -> list[Molecule]:
        return list(self._items.values())

    def to_list(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self._items.values()]

    @classmethod
    def from_list(cls, raw: list[dict[str, Any]], *, max_molecules: int = 512) -> MatterStore:
        store = cls(max_molecules=max_molecules)
        for item in raw:
            mol = Molecule.from_dict(item)
            store._items[mol.key] = mol
        store._enforce_cap()
        return store
