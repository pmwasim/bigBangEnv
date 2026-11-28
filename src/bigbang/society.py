"""Society & Civilization (Level 7): outer Skin, peer attestation, reputation, territory locks, backpressure."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from .body import body_report
from .signal import Trust


def canonical_bytes(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


class Skin:
    """Cryptographic outer boundary sealing and verifying cross-Body peer envelopes."""

    def __init__(self, identity: str, secret: str) -> None:
        if not identity or not secret:
            raise ValueError("Skin requires non-empty identity and secret")
        self.identity = identity
        self._key = secret.encode("utf-8")

    def seal(self, payload: dict[str, Any], *, seq: int, affinity: str = "*") -> dict[str, Any]:
        body = {
            "from": self.identity,
            "seq": int(seq),
            "affinity": str(affinity),
            "payload": payload,
        }
        sig = hmac.new(self._key, canonical_bytes(body), hashlib.sha256).hexdigest()
        return {**body, "sig": sig}

    @staticmethod
    def verify(envelope: Any, peer_secrets: dict[str, str]) -> tuple[bool, str]:
        if not isinstance(envelope, dict):
            return False, "not a dict"
        sender = envelope.get("from")
        sig = envelope.get("sig")
        if not isinstance(sender, str) or not isinstance(sig, str) or sender not in peer_secrets:
            return False, "unknown sender"
        body = {
            "from": sender,
            "seq": envelope.get("seq"),
            "affinity": envelope.get("affinity", "*"),
            "payload": envelope.get("payload"),
        }
        expected = hmac.new(peer_secrets[sender].encode("utf-8"), canonical_bytes(body), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False, "bad signature"
        return True, "ok"


class ReputationLedger:
    """Tracks peer Body trustworthiness in [0.0..1.0]."""

    def __init__(self, *, default_score: float = 0.75, min_trusted: float = 0.4) -> None:
        self.default_score = float(default_score)
        self.min_trusted = float(min_trusted)
        self.scores: dict[str, float] = {}

    def score(self, peer: str) -> float:
        return self.scores.get(peer, self.default_score)

    def is_trusted(self, peer: str) -> bool:
        return self.score(peer) >= self.min_trusted

    def reward(self, peer: str, delta: float = 0.05) -> float:
        updated = round(min(1.0, self.score(peer) + max(0.0, delta)), 4)
        self.scores[peer] = updated
        return updated

    def penalize(self, peer: str, delta: float = 0.25) -> float:
        updated = round(max(0.0, self.score(peer) - max(0.0, delta)), 4)
        self.scores[peer] = updated
        return updated

    def to_dict(self) -> dict[str, Any]:
        return {"default_score": self.default_score, "min_trusted": self.min_trusted, "scores": dict(self.scores)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReputationLedger:
        rep = cls(default_score=data.get("default_score", 0.75), min_trusted=data.get("min_trusted", 0.4))
        rep.scores = {k: float(v) for k, v in data.get("scores", {}).items()}
        return rep


class TerritoryTable:
    """Deterministic TTL-bounded mutual exclusion claims for shared external targets."""

    def __init__(self) -> None:
        self.claims: dict[str, tuple[str, int]] = {}  # resource -> (holder, expires_at_tick)

    def prune(self, tick: int) -> None:
        expired = [res for res, (_, exp) in self.claims.items() if tick > exp]
        for res in expired:
            del self.claims[res]

    def holder(self, resource: str, tick: int) -> str | None:
        self.prune(tick)
        entry = self.claims.get(resource)
        return entry[0] if entry else None

    def claim(self, resource: str, holder: str, *, tick: int, ttl: int = 10) -> bool:
        self.prune(tick)
        current = self.claims.get(resource)
        if current is not None and current[0] != holder:
            return False
        self.claims[resource] = (holder, tick + max(1, int(ttl)))
        return True

    def release(self, resource: str, holder: str) -> bool:
        current = self.claims.get(resource)
        if current is None or current[0] != holder:
            return False
        del self.claims[resource]
        return True


def should_backpressure(target_status: dict[str, Any], paused: bool) -> bool:
    """Schmitt-trigger hysteresis deciding whether upstream peer relay must throttle."""
    if target_status.get("halted"):
        return True
    mode = target_status.get("operating_mode", "ALERT")
    if mode in ("LOCKDOWN", "DORMANT"):
        return True
    hormones = target_status.get("hormones", {})
    fuel = float(hormones.get("fuel", 1.0))
    stress = float(hormones.get("stress", 0.0))
    if paused:
        return not (fuel >= 0.60 and stress <= 0.35)
    return fuel <= 0.35 or stress >= 0.55


class WorldSociety:
    """Multi-Body coordinator enforcing Skin verification, reputation, territory mutex, and backpressure."""

    def __init__(self, *, world: Any = None) -> None:
        from .world import SharedWorld

        self.world: SharedWorld = world if world is not None else SharedWorld()
        self.bodies: dict[str, dict[str, Any]] = {}
        self.skins: dict[str, Skin] = {}
        self.secrets: dict[str, str] = {}
        self.reputation = ReputationLedger()
        self.territory = TerritoryTable()
        self.backpressure: dict[tuple[str, str], bool] = {}
        self._outboxes: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._seq: int = 0

    def register(
        self,
        kernel: Any,
        ledger: Any,
        genome: Any,
        organs: dict[str, Any],
        *,
        secret: str,
        zone: str = "hub",
    ) -> Skin:
        ident = genome.identity
        skin = Skin(ident, secret)
        self.bodies[ident] = {"kernel": kernel, "ledger": ledger, "genome": genome, "organs": organs}
        self.skins[ident] = skin
        self.secrets[ident] = secret
        self.world.enter(ident, role=genome.role, zone=zone)
        return skin

    def relay(
        self,
        source: str,
        target: str,
        payload: dict[str, Any],
        *,
        envelope: dict[str, Any] | None = None,
        risk: float = 0.1,
    ) -> dict[str, Any]:
        """Queue or deliver an inter-Body impulse, honoring Skin attestation and target backpressure."""
        if target not in self.bodies:
            return {"status": "unknown_target"}
        self._seq += 1
        env = envelope if envelope is not None else self.skins[source].seal(payload, seq=self._seq)
        ok, why = Skin.verify(env, self.secrets)
        sender = str(env.get("from", source)) if isinstance(env, dict) else source
        if not ok or not self.reputation.is_trusted(sender):
            self.reputation.penalize(sender)
            # Deliver forged/untrusted signals strictly at WORLD trust so SensoryIngest quarantines/drops them
            self.bodies[target]["kernel"].inject(
                "peer.signal", env.get("payload") if isinstance(env, dict) else payload,
                trust=Trust.WORLD, sender=sender, risk=max(0.5, float(risk)),
            )
            return {"status": "rejected", "reason": why if not ok else "low_reputation"}

        buf = self._outboxes.setdefault((source, target), [])
        buf.append({"sender": sender, "payload": env["payload"], "risk": float(risk)})
        return self.flush_link(source, target)

    def flush_link(self, source: str, target: str) -> dict[str, Any]:
        link = (source, target)
        t_info = self.bodies[target]
        t_rep = body_report(t_info["kernel"], t_info["ledger"], t_info["genome"], t_info["organs"])
        paused = should_backpressure(t_rep, self.backpressure.get(link, False))
        self.backpressure[link] = paused
        if paused:
            return {"status": "held_backpressure", "queued": len(self._outboxes.get(link, []))}

        sent = 0
        queue = self._outboxes.get(link, [])
        while queue:
            item = queue.pop(0)
            injected = t_info["kernel"].inject(
                "peer.signal",
                item["payload"],
                trust=Trust.USER,
                sender=item["sender"],
                risk=item["risk"],
            )
            if injected is not None:
                self.reputation.reward(item["sender"], 0.02)
                sent += 1
        return {"status": "delivered", "sent": sent, "queued": len(queue)}

    def step_all(self, ticks: int = 1) -> None:
        for _ in range(ticks):
            self.world.step(1)
            for (source, target) in list(self._outboxes):
                if self._outboxes[(source, target)]:
                    self.flush_link(source, target)
            for info in self.bodies.values():
                info["kernel"].step()
