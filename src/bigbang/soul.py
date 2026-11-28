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
