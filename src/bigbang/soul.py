"""Organism Identity & Inner Life: immutable Soul, Character disposition, and subjective Beliefs."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any

DEFAULT_CONSCIENCE: tuple[str, ...] = (
    "do_no_harm",
    "preserve_owner_sovereignty",
    "truth_before_action",
)


@dataclass(frozen=True)
class Soul:
    """Immutable existential core and stewardship continuity anchor of an organism."""

    soul_id: str
    calling: str = "steward"
    conscience: tuple[str, ...] = DEFAULT_CONSCIENCE
    origin_seed: str = "genesis"

    @classmethod
    def create(cls, identity: str, *, calling: str = "steward", seed: str = "genesis") -> Soul:
        digest = hashlib.sha256(f"{identity}:{calling}:{seed}".encode("utf-8")).hexdigest()[:16]
        return cls(soul_id=f"soul:{digest}", calling=calling, conscience=DEFAULT_CONSCIENCE, origin_seed=seed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "soul_id": self.soul_id,
            "calling": self.calling,
            "conscience": list(self.conscience),
            "origin_seed": self.origin_seed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Soul:
        return cls(
            soul_id=str(data["soul_id"]),
            calling=str(data.get("calling", "steward")),
            conscience=tuple(data.get("conscience", DEFAULT_CONSCIENCE)),
            origin_seed=str(data.get("origin_seed", "genesis")),
        )


@dataclass(frozen=True)
class Character:
    """Temperament & behavioral disposition traits [0.0..1.0] (never overrides Kernel Trust/Genome)."""

    caution: float = 0.65
    curiosity: float = 0.60
    diligence: float = 0.80
    altruism: float = 0.75

    def __post_init__(self) -> None:
        for name in ("caution", "curiosity", "diligence", "altruism"):
            val = float(getattr(self, name))
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be in [0.0..1.0], got {val}")

    @classmethod
    def for_role(cls, role: str) -> Character:
        presets = {
            "sentinel": cls(caution=0.85, curiosity=0.45, diligence=0.80, altruism=0.75),
            "auditor": cls(caution=0.95, curiosity=0.35, diligence=0.95, altruism=0.65),
            "executor": cls(caution=0.80, curiosity=0.30, diligence=0.85, altruism=0.70),
            "planner": cls(caution=0.55, curiosity=0.90, diligence=0.80, altruism=0.70),
            "triage": cls(caution=0.65, curiosity=0.60, diligence=0.80, altruism=0.75),
            "scout": cls(caution=0.50, curiosity=0.95, diligence=0.75, altruism=0.75),
            "artisan": cls(caution=0.70, curiosity=0.75, diligence=0.95, altruism=0.80),
            "arbiter": cls(caution=0.90, curiosity=0.55, diligence=0.90, altruism=0.85),
            "weaver": cls(caution=0.65, curiosity=0.80, diligence=0.85, altruism=0.95),
        }
        return presets.get(role, cls())

    @property
    def max_salient_risk(self) -> float:
        """Threshold above which the organism treats signals as suspiciously hazardous."""
        return round(max(0.15, 1.0 - (0.7 * self.caution)), 4)

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Character:
        return cls(
            caution=float(data.get("caution", 0.65)),
            curiosity=float(data.get("curiosity", 0.60)),
            diligence=float(data.get("diligence", 0.80)),
            altruism=float(data.get("altruism", 0.75)),
        )


@dataclass
class Belief:
    """A single subjective belief held with bounded confidence [0.0..1.0]."""

    proposition: str
    confidence: float = 0.5
    evidence: int = 0
    updated_tick: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposition": self.proposition,
            "confidence": round(self.confidence, 4),
            "evidence": self.evidence,
            "updated_tick": self.updated_tick,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Belief:
        return cls(
            proposition=str(data["proposition"]),
            confidence=float(data.get("confidence", 0.5)),
            evidence=int(data.get("evidence", 0)),
            updated_tick=int(data.get("updated_tick", 0)),
        )


class BeliefSystem:
    """Subjective epistemic model updated by grounded execution outcomes."""

    def __init__(self, *, max_beliefs: int = 128) -> None:
        self.max_beliefs = max_beliefs
        self.beliefs: dict[str, Belief] = {}

    def confidence(self, proposition: str, default: float = 0.5) -> float:
        entry = self.beliefs.get(proposition)
        return entry.confidence if entry is not None else default

    def observe(self, proposition: str, *, confirmed: bool, tick: int = 0, weight: float = 0.15) -> float:
        b = self.beliefs.get(proposition)
        if b is None:
            if len(self.beliefs) >= self.max_beliefs:
                oldest = next(iter(self.beliefs))
                del self.beliefs[oldest]
            b = Belief(proposition=proposition, confidence=0.5, evidence=0, updated_tick=tick)
            self.beliefs[proposition] = b
        target = 1.0 if confirmed else 0.0
        w = max(0.01, min(1.0, float(weight)))
        b.confidence = round((1.0 - w) * b.confidence + w * target, 4)
        b.evidence += 1
        b.updated_tick = int(tick)
        return b.confidence

    def salience(self, proposition: str, *, base_risk: float = 0.1, caution: float = 0.65) -> float:
        """Compute subjective salience [0.0..1.0] blending base risk, doubt, and caution."""
        conf = self.confidence(proposition)
        doubt = max(0.0, 1.0 - conf)
        score = base_risk + (doubt * 0.45 * (0.5 + caution))
        return round(min(1.0, max(0.0, score)), 4)

    def to_dict(self) -> dict[str, Any]:
        return {k: v.to_dict() for k, v in sorted(self.beliefs.items())}

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, max_beliefs: int = 128) -> BeliefSystem:
        bs = cls(max_beliefs=max_beliefs)
        for k, v in data.items():
            bs.beliefs[str(k)] = Belief.from_dict(v)
        return bs


@dataclass(frozen=True)
class AnatomyPart:
    """One embodied sensory or motor appendage with bounded strength [0.0..1.0]."""

    strength: float = 0.7
    active: bool = True
    role_story: str = ""

    def __post_init__(self) -> None:
        val = float(self.strength)
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"strength must be in [0.0..1.0], got {val}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "strength": round(float(self.strength), 3),
            "active": bool(self.active),
            "role_story": self.role_story,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnatomyPart:
        return cls(
            strength=float(data.get("strength", 0.7)),
            active=bool(data.get("active", True)),
            role_story=str(data.get("role_story", "")),
        )


_ANATOMY_ROLE_DATA: dict[str, dict[str, tuple[float, str]]] = {
    "sentinel": {
        "eyes": (0.94, "Keen far-seeing eyes sweep the horizon for subtle shifts."),
        "ears": (0.90, "Attentive ears catch faint whispers drifting across bridges."),
        "tongue": (0.68, "Steady voice calls clear warnings when needed."),
        "hands": (0.72, "Ready hands hold the sanctuary gate calm and firm."),
        "legs": (0.76, "Sure-footed legs patrol the outer paths tirelessly."),
    },
    "auditor": {
        "eyes": (0.95, "Discerning eyes spot the smallest inconsistency in any pattern."),
        "ears": (0.80, "Patient ears listen closely to every account."),
        "tongue": (0.86, "Measured voice speaks truths clearly and kindly."),
        "hands": (0.68, "Careful hands record and seal verified findings."),
        "legs": (0.62, "Deliberate legs walk steadily between realms."),
    },
    "scout": {
        "eyes": (0.92, "Wide-horizon eyes spot distant wonders and changing weather."),
        "ears": (0.78, "Quick ears tune into wind and footsteps far ahead."),
        "tongue": (0.65, "Crisp voice relays discoveries back home."),
        "hands": (0.64, "Light hands sketch trail markers along new ground."),
        "legs": (0.96, "Swift, tireless legs bound across hills and bridges."),
    },
    "arbiter": {
        "eyes": (0.88, "Balanced eyes weigh every side with calm fairness."),
        "ears": (0.92, "Empathetic ears hear the unspoken nuance in every voice."),
        "tongue": (0.94, "Resonant voice brings harmony and fair judgment."),
        "hands": (0.70, "Gentle hands award honor and restore balance."),
        "legs": (0.68, "Composed legs step into the arena to preside."),
    },
    "triage": {
        "eyes": (0.78, "Quick eyes read arriving sparks at a glance."),
        "ears": (0.80, "Warm ears greet every newcomer's call."),
        "tongue": (0.92, "Welcoming voice names and guides new thoughts clearly."),
        "hands": (0.76, "Nimble hands sort incoming threads gently."),
        "legs": (0.72, "Agile legs move swiftly around the sanctuary."),
    },
    "planner": {
        "eyes": (0.82, "Farsighted eyes trace pathways across the whole cosmos."),
        "ears": (0.76, "Thoughtful ears gather quiet hints from neighbors."),
        "tongue": (0.90, "Articulate voice shares clear visions and invitations."),
        "hands": (0.68, "Skilled hands map constellations and trials."),
        "legs": (0.86, "Wandering legs roam freely from Hearth to Horizon."),
    },
    "executor": {
        "eyes": (0.72, "Focused eyes lock onto the task at hand."),
        "ears": (0.66, "Practical ears listen for clear directions."),
        "tongue": (0.65, "Concise voice confirms work completed."),
        "hands": (0.96, "Masterful hands turn intentions into finished craft."),
        "legs": (0.88, "Energetic legs carry effort wherever it is needed."),
    },
    "artisan": {
        "eyes": (0.78, "Appreciative eyes notice beauty, symmetry, and detail."),
        "ears": (0.70, "Calm ears enjoy the ambient hum of creation."),
        "tongue": (0.72, "Warm voice shares stories behind each creation."),
        "hands": (0.95, "Deft, expressive hands shape delicate wonders."),
        "legs": (0.70, "Unrushed legs wander between workshop and hearth."),
    },
    "weaver": {
        "eyes": (0.74, "Gentle eyes see how distant threads belong together."),
        "ears": (0.90, "Deeply tuned ears hear harmonies between habitats."),
        "tongue": (0.80, "Soothing voice bridges conversations across realms."),
        "hands": (0.92, "Graceful hands weave shared bonds and living light."),
        "legs": (0.74, "Light legs cross doors to connect companions."),
    },
    "general": {
        "eyes": (0.74, "Watchful eyes take in the glow of the surrounding land."),
        "ears": (0.74, "Open ears listen gently to neighboring voices."),
        "tongue": (0.74, "Friendly voice greets companions along the path."),
        "hands": (0.74, "Helpful hands lend care wherever a spark lands."),
        "legs": (0.74, "Steady legs explore paths between sanctuaries."),
    },
}


@dataclass(frozen=True)
class Anatomy:
    """Embodied sensory & motor morphology of an organism (eyes, ears, tongue, hands, legs)."""

    eyes: AnatomyPart
    ears: AnatomyPart
    tongue: AnatomyPart
    hands: AnatomyPart
    legs: AnatomyPart

    @classmethod
    def for_role(cls, role: str) -> Anatomy:
        spec = _ANATOMY_ROLE_DATA.get(role, _ANATOMY_ROLE_DATA["general"])
        return cls(
            eyes=AnatomyPart(strength=spec["eyes"][0], active=True, role_story=spec["eyes"][1]),
            ears=AnatomyPart(strength=spec["ears"][0], active=True, role_story=spec["ears"][1]),
            tongue=AnatomyPart(strength=spec["tongue"][0], active=True, role_story=spec["tongue"][1]),
            hands=AnatomyPart(strength=spec["hands"][0], active=True, role_story=spec["hands"][1]),
            legs=AnatomyPart(strength=spec["legs"][0], active=True, role_story=spec["legs"][1]),
        )

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {
            "eyes": self.eyes.to_dict(),
            "ears": self.ears.to_dict(),
            "tongue": self.tongue.to_dict(),
            "hands": self.hands.to_dict(),
            "legs": self.legs.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Anatomy:
        default = cls.for_role("general")
        return cls(
            eyes=AnatomyPart.from_dict(data["eyes"]) if "eyes" in data else default.eyes,
            ears=AnatomyPart.from_dict(data["ears"]) if "ears" in data else default.ears,
            tongue=AnatomyPart.from_dict(data["tongue"]) if "tongue" in data else default.tongue,
            hands=AnatomyPart.from_dict(data["hands"]) if "hands" in data else default.hands,
            legs=AnatomyPart.from_dict(data["legs"]) if "legs" in data else default.legs,
        )
