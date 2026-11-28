"""The Shared World: spatial Zones, Locality, shared Entities, ambient energy, and HTTP daemon."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .society import TerritoryTable
from .soul import BeliefSystem, Character


@dataclass(frozen=True)
class RelativeWorld:
    """Subjective local reference frame (Umwelt) of an entity at any emergent scale."""

    observer_id: str
    scale: str  # "molecule" | "cell" | "organ" | "body" | "society"
    frame_origin: str
    horizon: tuple[str, ...]
    ambient: dict[str, Any]
    observables: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "observer_id": self.observer_id,
            "scale": self.scale,
            "frame_origin": self.frame_origin,
            "horizon": list(self.horizon),
            "ambient": dict(self.ambient),
            "observables": list(self.observables),
        }


def molecule_world(chamber: Any, reaction: Any, *, product_concentration: int = 0) -> RelativeWorld:
    """The Chemical relative world surrounding reacting molecules inside a ReactionChamber."""
    available_reagents = {k: len(v) for k, v in sorted(chamber.reagents.items())}
    catalysts = [c.name for c in chamber.catalysts.values() if c.reaction_name == reaction.name]
    ea = chamber.effective_ea(reaction, product_concentration=product_concentration)
    return RelativeWorld(
        observer_id=reaction.name,
        scale="molecule",
        frame_origin="reaction_chamber",
        horizon=tuple(sorted(reaction.reactants.keys())),
        ambient={"effective_ea": ea, "catalysts": catalysts, "product_concentration": product_concentration},
        observables=[{"reactant": k, "count": cnt, "required": reaction.reactants.get(k, 0)} for k, cnt in available_reagents.items()],
    )


def cell_world(kernel: Any, cell: Any) -> RelativeWorld:
    """The Cellular relative world: compartment gradients, receptor-filtered signals, and budget."""
    compartment = cell.organ or "body"
    peers = tuple(
        sorted(name for name, peer in kernel.cells.items() if name != cell.name and (peer.organ or "body") == compartment)
    )
    visible = [
        {"id": s.id, "topic": s.topic, "trust": s.trust.name, "risk": s.risk}
        for s in kernel.queue
        if s.trust >= cell.accepts and (not s.topic.startswith("_organ.") or s.topic.startswith(f"_organ.{compartment}."))
    ]
    budget = kernel.budgets.get(cell.name)
    return RelativeWorld(
        observer_id=cell.name,
        scale="cell",
        frame_origin=compartment,
        horizon=peers,
        ambient={
            "gradients": dict(kernel.gradients.get(compartment, {})),
            "fuel": round(budget.remaining, 2) if budget else 0.0,
            "cooldown": kernel._cooldowns.get(cell.name, 0),
            "accepts": cell.accepts.name,
        },
        observables=visible,
    )


def organ_world(kernel: Any, organ: Any) -> RelativeWorld:
    """The Organ relative world: internal tissue pool, typed ports, and whole-body hormones."""
    summary = organ.summary(kernel)
    return RelativeWorld(
        observer_id=organ.name,
        scale="organ",
        frame_origin="body",
        horizon=tuple(organ.in_ports) + tuple(organ.out_ports),
        ambient={
            "hormones": dict(kernel.hormones),
            "operating_mode": kernel.operating_mode,
            "fuel_remaining": summary["fuel_remaining"],
            "gradients": summary["gradients"],
        },
        observables=[{"cell": c.name, "lineage": c.lineage} for c, _ in organ.cells],
    )


def body_world(
    shared_world: SharedWorld,
    body_id: str,
    *,
    character: Character | None = None,
    beliefs: BeliefSystem | None = None,
) -> RelativeWorld:
    """Subjective Body Umwelt: local SharedWorld Zone filtered through Character & Beliefs."""
    raw = shared_world.sense(body_id)
    char = character or Character()
    bs = beliefs or BeliefSystem()
    obs = []
    for obj in raw["objects"]:
        prop = f"zone:{obj['zone']}:{obj['kind']}"
        salience = bs.salience(prop, base_risk=float(obj.get("risk", 0.1)), caution=char.caution)
        obs.append({
            **obj,
            "subjective_salience": salience,
            "cautious_flag": salience >= char.max_salient_risk,
        })
    obs.sort(key=lambda item: (-item["subjective_salience"], item["issue_id"]))
    return RelativeWorld(
        observer_id=body_id,
        scale="body",
        frame_origin=raw["zone"]["name"],
        horizon=tuple(p["body_id"] for p in raw["peers"]) + tuple(raw["zone"]["neighbors"]),
        ambient={
            "zone": raw["zone"],
            "curiosity": char.curiosity,
            "caution": char.caution,
            "world_tick": raw["world_tick"],
        },
        observables=obs,
    )


@dataclass
class Zone:
    """A spatial neighborhood in the World with finite ambient energy and entropy."""

    name: str
    neighbors: tuple[str, ...] = ()
    energy_reserve: float = 1000.0
    max_energy: float = 1000.0
    regen_rate: float = 5.0
    ambient_entropy: float = 0.0
    hazard: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "neighbors": list(self.neighbors),
            "energy_reserve": round(self.energy_reserve, 3),
            "max_energy": self.max_energy,
            "regen_rate": self.regen_rate,
            "ambient_entropy": round(self.ambient_entropy, 4),
            "hazard": round(self.hazard, 4),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Zone:
        return cls(
            name=str(data["name"]),
            neighbors=tuple(data.get("neighbors", ())),
            energy_reserve=float(data.get("energy_reserve", 1000.0)),
            max_energy=float(data.get("max_energy", 1000.0)),
            regen_rate=float(data.get("regen_rate", 5.0)),
            ambient_entropy=float(data.get("ambient_entropy", 0.0)),
            hazard=float(data.get("hazard", 0.0)),
        )


@dataclass
class WorldEntity:
    """A persistent object living in a World Zone (shared across resident Bodies)."""

    entity_id: str
    issue_id: int
    zone: str
    kind: str
    title: str
    body: str = ""
    state: str = "open"  # open | labelled | resolved | decayed
    labels: list[str] = field(default_factory=list)
    owner: str | None = None
    born_tick: int = 0
    ttl: int | None = None
    risk: float = 0.1
    resolved_by: str | None = None

    def expired(self, tick: int) -> bool:
        return self.ttl is not None and (tick - self.born_tick) > self.ttl

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorldEntity:
        return cls(
            entity_id=str(data["entity_id"]),
            issue_id=int(data["issue_id"]),
            zone=str(data["zone"]),
            kind=str(data.get("kind", "incident")),
            title=str(data["title"]),
            body=str(data.get("body", "")),
            state=str(data.get("state", "open")),
            labels=list(data.get("labels", [])),
            owner=data.get("owner"),
            born_tick=int(data.get("born_tick", 0)),
            ttl=data.get("ttl"),
            risk=float(data.get("risk", 0.1)),
            resolved_by=data.get("resolved_by"),
        )


def default_zones() -> dict[str, Zone]:
    """Genesis spatial topology connecting Hub, Alpha/Beta Sectors, and Frontier."""
    return {
        "hub": Zone("hub", neighbors=("alpha-sector", "beta-sector"), energy_reserve=2000.0, max_energy=2000.0, regen_rate=10.0),
        "alpha-sector": Zone("alpha-sector", neighbors=("hub", "frontier"), energy_reserve=1000.0, max_energy=1000.0, regen_rate=5.0),
        "beta-sector": Zone("beta-sector", neighbors=("hub", "frontier"), energy_reserve=1000.0, max_energy=1000.0, regen_rate=5.0),
        "frontier": Zone("frontier", neighbors=("alpha-sector", "beta-sector"), energy_reserve=600.0, max_energy=800.0, regen_rate=3.0, hazard=0.15),
    }


class SharedWorld:
    """Authoritative outer World inhabited by sovereign Bodies (Space, Locality, Resources)."""

    def __init__(
        self,
        *,
        zones: dict[str, Zone] | None = None,
        state_path: str | Path | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self.state_path = Path(state_path) if state_path else None
        self.tick: int = 0
        self.zones: dict[str, Zone] = zones if zones is not None else default_zones()
        self.bodies: dict[str, dict[str, Any]] = {}
        self.entities: dict[str, WorldEntity] = {}
        self._issue_index: dict[int, str] = {}
        self.territory = TerritoryTable()
        self.events: list[dict[str, Any]] = []
        self._next_seq: int = 1
        if self.state_path and self.state_path.exists():
            self._load_unlocked(json.loads(self.state_path.read_text(encoding="utf-8")))

    def _log(self, event: str, **data: Any) -> None:
        self.events.append({"tick": self.tick, "event": event, **data})
        if len(self.events) > 256:
            del self.events[:-256]

    def save(self) -> None:
        with self._lock:
            if not self.state_path:
                return
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
            tmp.replace(self.state_path)

    def _load_unlocked(self, data: dict[str, Any]) -> None:
        self.tick = int(data.get("tick", 0))
        self._next_seq = int(data.get("next_seq", 1))
        if data.get("zones"):
            self.zones = {k: Zone.from_dict(v) for k, v in data["zones"].items()}
        self.bodies = {k: dict(v) for k, v in data.get("bodies", {}).items()}
        self.entities = {k: WorldEntity.from_dict(v) for k, v in data.get("entities", {}).items()}
        self._issue_index = {e.issue_id: e.entity_id for e in self.entities.values()}
        self.events = list(data.get("events", []))[-256:]

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "tick": self.tick,
                "next_seq": self._next_seq,
                "zones": {k: z.to_dict() for k, z in sorted(self.zones.items())},
                "bodies": {k: dict(v) for k, v in sorted(self.bodies.items())},
                "entities": {k: e.to_dict() for k, e in sorted(self.entities.items())},
                "territory": {res: [h, exp] for res, (h, exp) in sorted(self.territory.claims.items())},
                "events": list(self.events[-50:]),
            }

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, state_path: str | Path | None = None) -> SharedWorld:
        w = cls(state_path=None)
        w.state_path = Path(state_path) if state_path else None
        w._load_unlocked(data)
        for res, pair in data.get("territory", {}).items():
            w.territory.claims[str(res)] = (str(pair[0]), int(pair[1]))
        return w

    # ----------------------------------------------------------- presence & locality
    def enter(self, body_id: str, *, role: str = "general", zone: str = "hub") -> dict[str, Any]:
        with self._lock:
            if zone not in self.zones:
                raise KeyError(f"unknown zone {zone!r}")
            existing = self.bodies.get(body_id, {})
            rec = {
                "body_id": body_id,
                "role": role,
                "zone": existing.get("zone", zone),
                "entered_tick": existing.get("entered_tick", self.tick),
                "last_seen_tick": self.tick,
                "energy_harvested": float(existing.get("energy_harvested", 0.0)),
                "actions_completed": int(existing.get("actions_completed", 0)),
            }
            self.bodies[body_id] = rec
            self._log("enter", body=body_id, zone=rec["zone"], role=role)
            self.save()
            return dict(rec)

    def move(self, body_id: str, target_zone: str) -> dict[str, Any]:
        """Enforce topological Locality: Bodies move step-by-step between neighboring Zones."""
        with self._lock:
            if body_id not in self.bodies:
                return {"moved": False, "reason": "unknown_body"}
            if target_zone not in self.zones:
                return {"moved": False, "reason": "unknown_zone"}
            cur = self.bodies[body_id]["zone"]
            if cur == target_zone:
                return {"moved": True, "zone": target_zone}
            if target_zone not in self.zones[cur].neighbors:
                return {"moved": False, "reason": "not_adjacent", "from": cur, "to": target_zone}
            self.bodies[body_id]["zone"] = target_zone
            self.bodies[body_id]["last_seen_tick"] = self.tick
            self._log("move", body=body_id, from_zone=cur, to_zone=target_zone)
            self.save()
            return {"moved": True, "zone": target_zone}

    def spawn_entity(
        self,
        zone: str,
        *,
        kind: str = "incident",
        title: str,
        body: str = "",
        risk: float = 0.1,
        ttl: int | None = None,
        issue_id: int | None = None,
    ) -> WorldEntity:
        with self._lock:
            if zone not in self.zones:
                raise KeyError(f"unknown zone {zone!r}")
            seq = self._next_seq
            self._next_seq += 1
            eid = f"ent:{seq}"
            iid = int(issue_id) if issue_id is not None else (700_000 + seq)
            ent = WorldEntity(
                entity_id=eid,
                issue_id=iid,
                zone=zone,
                kind=kind,
                title=str(title),
                body=str(body),
                born_tick=self.tick,
                ttl=ttl,
                risk=float(risk),
            )
            self.entities[eid] = ent
            self._issue_index[iid] = eid
            self._log("spawn_entity", entity=eid, issue_id=iid, zone=zone, kind=kind)
            self.save()
            return ent

    def sense(self, body_id: str) -> dict[str, Any]:
        """Return strictly local perceptions for ``body_id`` (peers, open entities, zone physics)."""
        with self._lock:
            if body_id not in self.bodies:
                raise KeyError(f"body {body_id!r} has not entered the world")
            info = self.bodies[body_id]
            info["last_seen_tick"] = self.tick
            zone_name = info["zone"]
            zone = self.zones[zone_name]
            peers = [
                {"body_id": b_id, "role": b["role"], "actions_completed": b["actions_completed"]}
                for b_id, b in sorted(self.bodies.items())
                if b_id != body_id and b["zone"] == zone_name
            ]
            objects = [
                e.to_dict()
                for e in sorted(self.entities.values(), key=lambda x: x.issue_id)
                if e.zone == zone_name and e.state in ("open", "labelled")
                and (e.owner is None or e.owner == body_id)
            ]
            return {"world_tick": self.tick, "zone": zone.to_dict(), "peers": peers, "objects": objects}

    def harvest(self, body_id: str, amount: float) -> float:
        """Harvest finite ambient energy from the Body's current Zone."""
        with self._lock:
            if body_id not in self.bodies or amount <= 0.0:
                return 0.0
            zone = self.zones[self.bodies[body_id]["zone"]]
            taken = round(min(float(amount), max(0.0, zone.energy_reserve)), 3)
            if taken <= 0.0:
                return 0.0
            zone.energy_reserve = round(zone.energy_reserve - taken, 3)
            self.bodies[body_id]["energy_harvested"] = round(self.bodies[body_id]["energy_harvested"] + taken, 3)
            self._log("harvest", body=body_id, zone=zone.name, amount=taken)
            self.save()
            return taken

    def act(
        self,
        body_id: str,
        issue_id: int,
        *,
        verb: str,
        label: str | None = None,
        entropy_cost: float = 0.25,
    ) -> dict[str, Any]:
        """Apply a Body's verified Motor outcome onto a shared WorldEntity in its Zone."""
        with self._lock:
            if body_id not in self.bodies:
                return {"ok": False, "reason": "unknown_body"}
            eid = self._issue_index.get(int(issue_id))
            if eid is None or eid not in self.entities:
                return {"ok": False, "reason": "unknown_entity"}
            ent = self.entities[eid]
            body_zone = self.bodies[body_id]["zone"]
            if ent.zone != body_zone:
                return {"ok": False, "reason": "locality_violation", "body_zone": body_zone, "entity_zone": ent.zone}

            if not self.territory.claim(eid, body_id, tick=self.tick, ttl=5):
                return {"ok": False, "reason": "territory_claimed", "holder": self.territory.holder(eid, self.tick)}

            if verb == "label" and label:
                if label not in ent.labels:
                    ent.labels.append(label)
                if ent.state == "open":
                    ent.state = "labelled"
            elif verb == "close":
                ent.state = "resolved"
                ent.resolved_by = body_id
                self.territory.release(eid, body_id)
            elif verb == "reopen":
                ent.state = "open"
                ent.resolved_by = None

            zone = self.zones[body_zone]
            zone.ambient_entropy = round(zone.ambient_entropy + max(0.0, entropy_cost), 4)
            self.bodies[body_id]["actions_completed"] += 1
            self.bodies[body_id]["last_seen_tick"] = self.tick
            self._log("world_act", body=body_id, zone=body_zone, entity=eid, verb=verb, label=label, state=ent.state)
            self.save()
            return {"ok": True, "entity": ent.to_dict()}

    def step(self, ticks: int = 1) -> int:
        """Advance planetary physics: regenerate Zone reserves, cool entropy, expire entities."""
        with self._lock:
            for _ in range(max(1, int(ticks))):
                self.tick += 1
                self.territory.prune(self.tick)
                for zone in self.zones.values():
                    zone.energy_reserve = round(min(zone.max_energy, zone.energy_reserve + zone.regen_rate), 3)
                    zone.ambient_entropy = round(zone.ambient_entropy * 0.9, 4)
                    if zone.ambient_entropy < 0.01:
                        zone.ambient_entropy = 0.0
                    zone.hazard = round(max(0.0, zone.hazard * 0.85), 4)
                for ent in self.entities.values():
                    if ent.state in ("open", "labelled") and ent.expired(self.tick):
                        ent.state = "decayed"
                        self._log("entity_decay", entity=ent.entity_id, zone=ent.zone)
            self.save()
            return self.tick

    def summary(self) -> dict[str, Any]:
        with self._lock:
            counts: dict[str, int] = {}
            for ent in self.entities.values():
                counts[ent.state] = counts.get(ent.state, 0) + 1
            return {
                "tick": self.tick,
                "zones": {k: z.to_dict() for k, z in sorted(self.zones.items())},
                "bodies": {k: dict(v) for k, v in sorted(self.bodies.items())},
                "entities_total": len(self.entities),
                "entity_states": counts,
                "recent_events": list(self.events[-15:]),
            }


# ----------------------------------------------------------- HTTP daemon & client
class WorldClient:
    """Zero-dependency HTTP JSON client connecting distributed Bodies to SharedWorld."""

    def __init__(self, base_url: str, *, timeout: float = 2.5) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)

    def _req(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def summary(self) -> dict[str, Any]:
        return self._req("GET", "/world")

    def enter(self, body_id: str, *, role: str = "general", zone: str = "hub") -> dict[str, Any]:
        return self._req("POST", "/enter", {"body_id": body_id, "role": role, "zone": zone})

    def move(self, body_id: str, target_zone: str) -> dict[str, Any]:
        return self._req("POST", "/move", {"body_id": body_id, "target_zone": target_zone})

    def sense(self, body_id: str) -> dict[str, Any]:
        q = urllib.parse.urlencode({"body_id": body_id})
        return self._req("GET", f"/sense?{q}")

    def spawn_entity(
        self,
        zone: str,
        *,
        kind: str = "incident",
        title: str,
        body: str = "",
        risk: float = 0.1,
        ttl: int | None = None,
    ) -> dict[str, Any]:
        return self._req("POST", "/spawn", {
            "zone": zone, "kind": kind, "title": title, "body": body, "risk": risk, "ttl": ttl,
        })

    def harvest(self, body_id: str, amount: float) -> float:
        res = self._req("POST", "/harvest", {"body_id": body_id, "amount": amount})
        return float(res.get("harvested", 0.0))

    def act(self, body_id: str, issue_id: int, *, verb: str, label: str | None = None) -> dict[str, Any]:
        return self._req("POST", "/act", {"body_id": body_id, "issue_id": issue_id, "verb": verb, "label": label})

    def step(self, ticks: int = 1) -> dict[str, Any]:
        return self._req("POST", "/step", {"ticks": ticks})


def make_world_server(
    world: SharedWorld,
    *,
    host: str = "127.0.0.1",
    port: int = 8787,
) -> ThreadingHTTPServer:
    """Create a multi-threaded stdlib HTTP JSON server around ``SharedWorld``."""

    class _Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, payload: dict[str, Any]) -> None:
            raw = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _json_body(self) -> dict[str, Any]:
            n = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(n).decode("utf-8")) if n > 0 else {}

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return  # keep daemon stdout clean

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            try:
                if parsed.path == "/world":
                    self._send(200, world.summary())
                elif parsed.path == "/sense":
                    qs = urllib.parse.parse_qs(parsed.query)
                    bid = qs.get("body_id", [""])[0]
                    self._send(200, world.sense(bid))
                else:
                    self._send(404, {"error": "not found"})
            except KeyError as exc:
                self._send(404, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            try:
                data = self._json_body()
                if self.path == "/enter":
                    self._send(200, world.enter(data["body_id"], role=data.get("role", "general"), zone=data.get("zone", "hub")))
                elif self.path == "/move":
                    self._send(200, world.move(data["body_id"], data["target_zone"]))
                elif self.path == "/spawn":
                    ent = world.spawn_entity(
                        data["zone"],
                        kind=data.get("kind", "incident"),
                        title=data["title"],
                        body=data.get("body", ""),
                        risk=float(data.get("risk", 0.1)),
                        ttl=data.get("ttl"),
                    )
                    self._send(200, ent.to_dict())
                elif self.path == "/harvest":
                    amt = world.harvest(data["body_id"], float(data["amount"]))
                    self._send(200, {"harvested": amt})
                elif self.path == "/act":
                    self._send(200, world.act(
                        data["body_id"], int(data["issue_id"]), verb=data["verb"], label=data.get("label")
                    ))
                elif self.path == "/step":
                    tick = world.step(int(data.get("ticks", 1)))
                    self._send(200, {"tick": tick})
                else:
                    self._send(404, {"error": "not found"})
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                self._send(400, {"error": str(exc)})

    return ThreadingHTTPServer((host, port), _Handler)
