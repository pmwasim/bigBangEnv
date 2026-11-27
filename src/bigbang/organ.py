"""Compartmentalized Organs: bounded cellular tissues with typed ports and energy pools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .cell import Cell

if TYPE_CHECKING:
    from .kernel import Kernel


@dataclass
class Organ:
    """A compartmentalized functional tissue within a unified Body.

    Enforces four structural laws (Genesis Spec §6):
      1. Private compartment isolation: internal signals use ``_organ.<name>.*``
         and paracrine gradients stay scoped to ``name``.
      2. Typed membrane ports: ``in_ports`` and ``out_ports`` declare the
         topics permitted across the organ boundary.
      3. Dedicated energy pool: total capacity/regen distributed across member cells.
      4. Localized homeostasis: member cells share local gradients before escalating.
    """

    name: str
    in_ports: tuple[str, ...] = ()
    out_ports: tuple[str, ...] = ()
    energy_pool: float = 1000.0
    base_regen: float = 4.0
    cells: list[tuple[Cell, float]] = field(default_factory=list)  # (cell, pool_share_weight)
    base_regens: dict[str, float] = field(default_factory=dict)

    def add_cell(self, cell: Cell, *, share: float = 1.0) -> None:
        cell.organ = self.name
        self.cells.append((cell, share))

    def mount(self, kernel: Kernel) -> None:
        """Spawn all member cells into the kernel with proportional pool allocations."""
        total_weight = sum(w for _, w in self.cells) or 1.0
        for cell, weight in self.cells:
            frac = weight / total_weight
            fuel = round(self.energy_pool * frac, 2)
            regen = round(self.base_regen * frac, 3)
            self.base_regens[cell.name] = regen
            kernel.spawn(cell, fuel=fuel, regen=regen)

    def scale_regen(self, kernel: Kernel, factor: float) -> None:
        """Modulate member cells' regeneration via the dynamic bloodstream."""
        for cell, _ in self.cells:
            base = self.base_regens.get(cell.name)
            if base is not None and cell.name in kernel.budgets:
                kernel.budgets[cell.name].regen = round(max(0.1, base * factor), 3)

    def summary(self, kernel: Kernel) -> dict[str, Any]:
        remaining = sum(kernel.budgets[c.name].remaining for c, _ in self.cells if c.name in kernel.budgets)
        capacity = sum(kernel.budgets[c.name].capacity for c, _ in self.cells if c.name in kernel.budgets)
        return {
            "cells": [c.name for c, _ in self.cells],
            "fuel_remaining": round(remaining, 1),
            "fuel_capacity": round(capacity, 1),
            "gradients": dict(kernel.gradients.get(self.name, {})),
            "in_ports": list(self.in_ports),
            "out_ports": list(self.out_ports),
        }
