"""Chemistry: stoichiometric bonding, reaction kinetics, catalysis, and equilibrium."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .matter import Molecule
from .signal import Trust


@dataclass(frozen=True)
class Reaction:
    """A stoichiometric transformation from reactant signals into a bonded Molecule."""

    name: str
    reactants: dict[str, int]            # reactant_type -> required count
    product: str                         # output compound name
    activation_energy: float = 2.0       # E_a barrier required to initiate reaction
    enthalpy: float = 0.0                # + endothermic cost, - exothermic saving
    max_product_concentration: int = 20  # Le Chatelier saturation limit


@dataclass(frozen=True)
class Catalyst:
    """Zero-consumption accelerator that lowers a reaction's activation energy E_a."""

    name: str
    reaction_name: str
    ea_reduction: float = 0.25  # multiplies E_a (e.g. 0.25 = 75% lower barrier)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Catalyst:
        return cls(
            name=str(data["name"]),
            reaction_name=str(data["reaction_name"]),
            ea_reduction=float(data.get("ea_reduction", 0.25)),
        )


def toxicity_ph(dropped: int, accepted: int) -> float:
    """Compartment buffer ratio [0.0 clean .. 1.0 toxic] from noisy/malformed drops."""
    total = dropped + accepted
    return round(dropped / total, 4) if total > 0 else 0.0


class ReactionChamber:
    """JSON-serializable chemical workspace holding reagents, catalysts, and kinetics."""

    def __init__(self, *, max_reagents_per_kind: int = 128) -> None:
        self.max_reagents_per_kind = max_reagents_per_kind
        self.reagents: dict[str, list[dict[str, Any]]] = {}
        self.catalysts: dict[str, Catalyst] = {}
        self.reactions_completed: int = 0

    def add_catalyst(self, catalyst: Catalyst) -> None:
        self.catalysts[catalyst.name] = catalyst

    def add_reagent(
        self,
        kind: str,
        payload: Any,
        *,
        trust: Trust,
        risk: float,
        tick: int,
        ttl: int = 20,
    ) -> None:
        bucket = self.reagents.setdefault(kind, [])
        bucket.append({
            "kind": kind,
            "payload": payload,
            "trust": trust.name,
            "risk": float(risk),
            "born": int(tick),
            "ttl": int(ttl),
        })
        while len(bucket) > self.max_reagents_per_kind:
            bucket.pop(0)

    def decay(self, tick: int) -> int:
        """Expire stale unbonded reagents."""
        expired_count = 0
        for kind in list(self.reagents):
            kept = [r for r in self.reagents[kind] if (tick - r["born"]) <= r["ttl"]]
            expired_count += len(self.reagents[kind]) - len(kept)
            if kept:
                self.reagents[kind] = kept
            else:
                del self.reagents[kind]
        return expired_count

    def effective_ea(self, reaction: Reaction, *, product_concentration: int = 0) -> float:
        """Compute activation energy after Catalysis and Le Chatelier backpressure."""
        if product_concentration >= reaction.max_product_concentration:
            return float("inf")  # Saturated: Le Chatelier shifts equilibrium back
        ea = reaction.activation_energy
        for cat in self.catalysts.values():
            if cat.reaction_name == reaction.name:
                ea = min(ea, reaction.activation_energy * cat.ea_reduction)
        # Mild concentration pressure as products approach saturation
        if reaction.max_product_concentration > 0 and product_concentration > 0:
            pressure = 1.0 + (product_concentration / reaction.max_product_concentration)
            ea *= pressure
        return round(ea, 4)

    def step_reaction(
        self,
        reaction: Reaction,
        *,
        tick: int,
        available_energy: float,
        product_concentration: int = 0,
    ) -> tuple[list[Molecule], float]:
        """Attempt to react stoichiometric reactants into bonded Molecules.

        Returns ``(synthesized_molecules, energy_spent)``. Conserves Trust (min)
        and Risk (max) across all consumed reactants. Catalysts are never consumed.
        """
        self.decay(tick)
        molecules: list[Molecule] = []
        total_spent = 0.0

        while True:
            # 1. Check stoichiometry
            if not all(len(self.reagents.get(r, [])) >= cnt for r, cnt in reaction.reactants.items()):
                break
            # 2. Check activation energy & Le Chatelier equilibrium
            ea = self.effective_ea(reaction, product_concentration=product_concentration + len(molecules))
            cost = max(0.0, ea + max(0.0, reaction.enthalpy))
            if cost > (available_energy - total_spent) or ea == float("inf"):
                break

            # 3. Consume reactants & conserve charges (min Trust, max Risk)
            consumed: list[dict[str, Any]] = []
            for r_kind, cnt in sorted(reaction.reactants.items()):
                bucket = self.reagents[r_kind]
                for _ in range(cnt):
                    consumed.append(bucket.pop(0))
                if not bucket:
                    del self.reagents[r_kind]

            bonded_trust = min(Trust[r["trust"]] for r in consumed)
            bonded_risk = max(float(r["risk"]) for r in consumed)
            compound_payload = {
                "reaction": reaction.name,
                "product": reaction.product,
                "bonds": [{r["kind"]: r["payload"]} for r in consumed],
                "risk": bonded_risk,
            }
            mol = Molecule(
                key=f"{reaction.product}:{tick}:{self.reactions_completed + 1}",
                value=compound_payload,
                trust=bonded_trust,
                born=tick,
                ttl=None,
            )
            molecules.append(mol)
            self.reactions_completed += 1
            total_spent += cost

        return molecules, round(total_spent, 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reagents": self.reagents,
            "catalysts": {k: c.to_dict() for k, c in self.catalysts.items()},
            "reactions_completed": self.reactions_completed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, max_reagents_per_kind: int = 128) -> ReactionChamber:
        chamber = cls(max_reagents_per_kind=max_reagents_per_kind)
        chamber.reagents = {k: list(v) for k, v in data.get("reagents", {}).items()}
        chamber.catalysts = {
            k: Catalyst.from_dict(v) for k, v in data.get("catalysts", {}).items()
        }
        chamber.reactions_completed = int(data.get("reactions_completed", 0))
        return chamber
