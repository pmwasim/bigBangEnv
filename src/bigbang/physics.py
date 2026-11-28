"""Cosmological physics primitives: charges, spacetime coordinates, and the four forces."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .signal import Trust


@dataclass(frozen=True)
class Coord:
    """3D spacetime coordinate: planar locality (x, y) and hierarchical scale depth (z)."""

    x: float = 0.0
    y: float = 0.0
    z: float = 1.0  # 0=cell, 1=organ, 2=body, 3=society

    def distance_to(self, other: Coord) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2)


@dataclass(frozen=True)
class ChargeVector:
    """Conserved multi-dimensional signal charge."""

    authority: Trust = Trust.WORLD
    valence: float = 1.0    # +1.0 excitatory, -1.0 inhibitory, 0.0 neutral
    risk: float = 0.0       # 0.0 (read/observe) .. 1.0 (irreversible external mutation)
    affinity: str = "*"     # receptor/flavor binding key


@dataclass(frozen=True)
class ForceTarget:
    """Physical state of a candidate Body or Organ node for Four-Force routing."""

    name: str
    coords: Coord
    affinity: str
    potential: float
    entropy: float
    gravitational_mass: float


def gravitational_mass(queue_len: int, entropy: float, bound_mass: float = 0.0) -> float:
    """Effective gravitational mass created by queued work, thermal entropy, and structural mass."""
    return round(1.0 + (queue_len * 0.6) + (entropy * 0.4) + (bound_mass * 0.05), 4)


def time_dilation(mass: float) -> float:
    """Spacetime dilation factor (>= 1.0) slowing cadence under heavy local mass."""
    return round(1.0 + 0.15 * max(0.0, mass - 1.0), 4)


def em_force(charge: ChargeVector, target: ForceTarget, origin: Coord) -> float:
    """Electromagnetic force: affinity attraction attenuated by distance^2; mismatch repels."""
    if charge.affinity != "*" and target.affinity != "*" and target.affinity != charge.affinity:
        return -1.0  # EM repulsion: incompatible flavor
    dist = max(1.0, origin.distance_to(target.coords))
    fuel_factor = max(0.0, target.potential / 100.0)
    return round((charge.valence * fuel_factor) / (dist ** 2), 6)


def effective_action_cost(charge: ChargeVector, target: ForceTarget, origin: Coord) -> float:
    """Lagrangian action cost combining EM attraction, Gravitational well, and Risk drag."""
    em = em_force(charge, target, origin)
    if em < 0:
        return float("inf")
    grav_barrier = target.gravitational_mass * 0.5
    risk_drag = charge.risk * (1.0 + target.entropy * 0.5)
    return round(grav_barrier + risk_drag - em, 6)


def select_target_by_forces(
    charge: ChargeVector,
    targets: list[ForceTarget],
    origin: Coord = Coord(0.0, 0.0, 2.0),
) -> ForceTarget | None:
    """Bossless Four-Force routing: select the least-action compatible target in spacetime."""
    viable = [(effective_action_cost(charge, t, origin), t.name, t) for t in targets]
    viable = [item for item in viable if math.isfinite(item[0])]
    if not viable:
        return None
    viable.sort(key=lambda item: (item[0], item[1]))
    return viable[0][2]
