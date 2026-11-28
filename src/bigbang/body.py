"""The Unified Body: immutable Genome, five vital organs, bloodstream, and M2 myelination."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .apps.caretaker import LABELS, LABEL_SCHEMA, Commander, Ledger, drain
from .brains import Brain, BrainUnavailable, RuleBrain, make_brain
from .cell import Cell, Context
from .kernel import MAX_INT, Kernel
from .lineages import Defense, Motor
from .matter import MatterStore
from .organ import Organ
from .signal import Trust

MAX_TITLE, MAX_BODY = 300, 20_000
PROMOTE_SCHEMA = {"sig_id": int, "label": frozenset(LABELS), "shadow": bool}
DEMOTE_SCHEMA = {"sig_id": int}


def stable_sig_id(sig: str) -> int:
    digest = hashlib.blake2b(sig.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big") % MAX_INT


@dataclass(frozen=True)
class Genome:
    """Immutable operational core defining organism identity and hard boundaries."""

    identity: str
    role: str = "general"
    allowed_labels: tuple[str, ...] = LABELS
    forbidden_verbs: tuple[str, ...] = ("delete",)
    myelin_min_support: int = 5
    myelin_min_span: int = 5
    myelin_shadow_needed: int = 3


# ===================================================================== Organ 1: Perception
class SensoryIngest(Cell):
    """Perception receptor: validates inputs, stores transient molecules, emits internally."""

    lineage = "sensory"
    subscriptions = ("world.issue", "peer.signal")

    def __init__(self, name: str = "perception.ingest", *, max_seen: int = 10_000, **kw: Any):
        kw.setdefault("emits", ["_organ.perception.parsed"])
        super().__init__(name, **kw)
        self.max_seen = max_seen
        self._seen_set: set[int] = set()
        self.memory.update(seen=[], seen_total=0, dropped=0, backlog=[], max_backlog=0, molecules=[])

    def step(self, ctx: Context) -> None:
        seen_list = self.memory["seen"]
        if len(self._seen_set) != len(seen_list):
            self._seen_set = set(seen_list)
        if "seen_total" not in self.memory:
            self.memory["seen_total"] = len(seen_list)

        store = MatterStore.from_list(self.memory.get("molecules", []), max_molecules=256)
        store.decay(ctx.tick)

        fresh = []
        for signal in ctx.inbox:
            issue = signal.payload
            ok = (
                isinstance(issue, dict)
                and isinstance(issue.get("id"), int)
                and not isinstance(issue.get("id"), bool)
                and 0 <= issue["id"] < MAX_INT
                and isinstance(issue.get("title"), str)
                and isinstance(issue.get("body", ""), str)
                and issue["title"].strip()
            )
            if not ok or issue["id"] in self._seen_set:
                self.memory["dropped"] += 1
                ctx.emit_gradient("friction", 0.2)
                continue
            self._seen_set.add(issue["id"])
            seen_list.append(issue["id"])
            self.memory["seen_total"] += 1
            if len(seen_list) > self.max_seen:
                self._seen_set.discard(seen_list.pop(0))

            clean = {
                "id": issue["id"],
                "title": issue["title"][:MAX_TITLE],
                "body": issue.get("body", "")[:MAX_BODY],
                "source_topic": signal.topic,
            }
            store.put(f"issue:{clean['id']}", clean["title"], trust=signal.trust, tick=ctx.tick, ttl=30)
            fresh.append(clean)

        self.memory["molecules"] = store.to_list()
        drain(self, ctx, fresh, lambda item: ctx.emit("_organ.perception.parsed", item) is not None)


class FastSpineReflex(Cell):
    """Fast spinal reflex inside Perception: static + myelinated sig_id classification."""

    lineage = "reflex"
    subscriptions = ("_organ.perception.parsed", "myelin.promote", "myelin.demote")
    TAGS = {"[bug]": "bug", "[feature]": "feature", "[docs]": "docs", "[question]": "question"}
    SPAM = ("free money", "click here", "buy now", "casino")

    def __init__(self, name: str = "perception.reflex", *, enabled: bool = True, **kw: Any):
        kw.setdefault("emits", ["action.label", "issue.novel", "myelin.shadow"])
        kw.setdefault("declassify", True)
        super().__init__(name, **kw)
        self.enabled = enabled
        self.memory.update(
            hits=0, compiled_hits=0, escalated=0, backlog=[], max_backlog=0,
            candidates={}, compiled={},
        )

    @staticmethod
    def extract_signature(title: str) -> str:
        words = [w.strip(".,!?:;()[]{}\"'") for w in title.lower().split()]
        words = [w for w in words if len(w) >= 3][:2]
        return " ".join(words) if len(words) == 2 else ""

    def _static_classify(self, title: str, body: str) -> str | None:
        lowered = title.lower().strip()
        for tag, label in self.TAGS.items():
            if lowered.startswith(tag):
                return label
        text = f"{lowered}\n{body.lower()}"
        if any(phrase in text for phrase in self.SPAM):
            return "spam"
        return None

    def _handle(self, ctx: Context, issue: dict[str, Any]) -> bool:
        if self.enabled:
            static = self._static_classify(issue["title"], issue["body"])
            if static is not None:
                if ctx.emit_declassified(
                    "action.label", {"issue": issue["id"], "label": static, "source": "auto"}, LABEL_SCHEMA
                ) is None:
                    return False
                self.memory["hits"] += 1
                return True

            sig = self.extract_signature(issue["title"])
            sig_id = stable_sig_id(sig) if sig else None
            sid = str(sig_id) if sig_id is not None else None
            rule = self.memory["compiled"].get(sid) if sid else None

            if rule and not rule["shadow"] and rule["sig"] == sig:
                if ctx.emit_declassified(
                    "action.label", {"issue": issue["id"], "label": rule["label"], "source": "auto"}, LABEL_SCHEMA
                ) is None:
                    return False
                rule["hits"] += 1
                self.memory["compiled_hits"] += 1
                return True

            if sig_id is not None:
                # Keep candidates bounded
                if len(self.memory["candidates"]) >= 256:
                    oldest = next(iter(self.memory["candidates"]))
                    del self.memory["candidates"][oldest]
                self.memory["candidates"][sid] = sig
            if rule and rule["shadow"]:
                ctx.emit("myelin.shadow", {"issue": issue["id"], "sig_id": sig_id, "predicted": rule["label"]})
            payload = {**issue, "sig_id": sig_id}
        else:
            payload = issue

        if ctx.emit("issue.novel", payload) is None:
            return False
        self.memory["escalated"] += 1
        return True

    def step(self, ctx: Context) -> None:
        fresh = []
        for s in ctx.inbox:
            if s.topic == "myelin.promote" and s.trust >= Trust.OPERATOR:
                sid = str(s.payload["sig_id"])
                sig_text = self.memory["candidates"].get(sid)
                if sig_text:
                    self.memory["compiled"][sid] = {
                        "sig": sig_text,
                        "label": s.payload["label"],
                        "shadow": s.payload["shadow"],
                        "hits": 0,
                    }
            elif s.topic == "myelin.demote" and s.trust >= Trust.OPERATOR:
                self.memory["compiled"].pop(str(s.payload["sig_id"]), None)
            elif s.topic == "_organ.perception.parsed":
                fresh.append(s.payload)
        drain(self, ctx, fresh, lambda issue: self._handle(ctx, issue))


# ===================================================================== Organ 2: Deliberation
class CortexReasoner(Cell):
    """Slow prefrontal cortex inside DeliberationOrgan: dormant during SLEEP_REM."""

    lineage = "reasoning"
    subscriptions = ("issue.novel",)

    def __init__(self, name: str = "deliberation.cortex", *, brain: Brain, reserve: float = 10.0, **kw: Any):
        kw.setdefault("emits", ["action.label"])
        kw.setdefault("declassify", True)
        super().__init__(name, **kw)
        self.brain = brain
        self.reserve = reserve
        self.memory.update(thoughts=0, outages=0, deferred_low_fuel=0, energy=0.0, backlog=[], max_backlog=0)

    def _decide(self, ctx: Context, issue: dict[str, Any]) -> str:
        if ctx.fuel < self.reserve or ctx.mode == "DORMANT":
            self.memory["deferred_low_fuel"] += 1
            return "needs-human"
        try:
            thought = self.brain.classify(issue["title"], issue["body"], LABELS)
        except BrainUnavailable:
            self.memory["outages"] += 1
            ctx.emit_gradient("friction", 0.4)
            return "needs-human"
        if not ctx.spend(thought.cost, f"brain:{self.brain.name}"):
            self.memory["deferred_low_fuel"] += 1
            return "needs-human"
        self.memory["thoughts"] += 1
        self.memory["energy"] += thought.cost
        return thought.label

    def step(self, ctx: Context) -> None:
        work = self.memory["backlog"] + [[s.payload, None] for s in ctx.inbox]
        if ctx.mode == "SLEEP_REM" and not ctx.inbox:
            self.memory["backlog"] = work
            return
        backlog = []
        for issue, label in work:
            if ctx.fuel < Kernel.EMIT_COST:
                backlog.append([issue, label])
                continue
            label = label or self._decide(ctx, issue)
            sent = ctx.emit_declassified(
                "action.label", {"issue": issue["id"], "label": label, "source": "auto"}, LABEL_SCHEMA
            )
            if sent is None:
                backlog.append([issue, label])
        self.memory["backlog"] = backlog
        self.memory["max_backlog"] = max(self.memory["max_backlog"], len(backlog))


# ===================================================================== Organ 3: Memory (Consolidation + M2)
class MemoryConsolidator(Cell):
    """Hippocampus housekeeping cell: condenses outcomes into Molecules, runs REM decay."""

    lineage = "housekeeping"
    subscriptions = ("outcome.*",)

    def __init__(self, name: str = "memory.consolidator", **kw: Any):
        kw.setdefault("emits", [])
        super().__init__(name, **kw)
        self.memory.update(outcomes={}, molecules=[], consolidations=0)

    def step(self, ctx: Context) -> None:
        store = MatterStore.from_list(self.memory.get("molecules", []), max_molecules=256)
        pruned = store.decay(ctx.tick)

        for signal in ctx.inbox:
            verb = signal.topic.split(".", 1)[1]
            status = signal.payload.get("status")
            key = f"{verb}:{status}"
            self.memory["outcomes"][key] = self.memory["outcomes"].get(key, 0) + 1
            store.put(
                f"outcome:{signal.id}",
                {"verb": verb, "status": status},
                trust=signal.trust,
                tick=ctx.tick,
                ttl=50 if status == "done" else 200,
            )

        if ctx.mode == "SLEEP_REM":
            for mol in store.items():
                if mol.hits >= 2 and mol.ttl is not None:
                    store.consolidate(mol.key)
                    ctx.condense(0.5)
                    self.memory["consolidations"] += 1
        if pruned:
            self.memory["consolidations"] += pruned
        self.memory["molecules"] = store.to_list()


class MyelinCompiler(Cell):
    """M2 Myelination inside MemoryOrgan: compiles repeated patterns safely."""

    lineage = "housekeeping"
    subscriptions = ("issue.novel", "action.label", "myelin.shadow")

    def __init__(
        self,
        name: str = "memory.myelin",
        *,
        min_support: int = 5,
        min_tick_span: int = 5,
        shadow_needed: int = 3,
        **kw: Any,
    ):
        kw.setdefault("emits", ["myelin.promote", "myelin.demote"])
        kw.setdefault("declassify", True)
        super().__init__(name, **kw)
        self.min_support = min_support
        self.min_tick_span = min_tick_span
        self.shadow_needed = shadow_needed
        self.memory.update(
            issue_meta={}, sig_ticks={}, stats={}, shadow={},
            promoted=[], demoted=[], shadow_preds={},
        )

    def step(self, ctx: Context) -> None:
        for s in ctx.inbox:
            if s.topic == "issue.novel":
                iid = str(s.payload["id"])
                sig_id = s.payload.get("sig_id")
                if sig_id is not None:
                    body_sig = hash(s.payload.get("body", "")[:100]) % 10_000_000
                    if len(self.memory["issue_meta"]) >= 512:
                        oldest = next(iter(self.memory["issue_meta"]))
                        del self.memory["issue_meta"][oldest]
                    self.memory["issue_meta"][iid] = (str(sig_id), ctx.tick, body_sig)
            elif s.topic == "myelin.shadow":
                iid = str(s.payload["issue"])
                self.memory["shadow_preds"][iid] = (s.payload["sig_id"], s.payload["predicted"])
            elif s.topic == "action.label":
                iid = str(s.payload["issue"])
                lbl = s.payload["label"]
                meta = self.memory["issue_meta"].get(iid)
                if s.sender == "commander":
                    # Owner override immediately demotes compiled reflex if one exists
                    if meta and meta[0] in self.memory["promoted"]:
                        ctx.emit_declassified("myelin.demote", {"sig_id": int(meta[0])}, DEMOTE_SCHEMA)
                        self.memory["demoted"].append(meta[0])
                        self.memory["promoted"].remove(meta[0])
                    continue

                if lbl == "needs-human" or not meta:
                    self.memory["issue_meta"].pop(iid, None)
                    self.memory["shadow_preds"].pop(iid, None)
                    continue

                sid, tick, body_sig = meta
                self.memory["issue_meta"].pop(iid, None)
                tinfo = self.memory["sig_ticks"].setdefault(sid, {"first": tick, "last": tick, "bodies": []})
                tinfo["last"] = tick
                if body_sig not in tinfo["bodies"] and len(tinfo["bodies"]) < 20:
                    tinfo["bodies"].append(body_sig)

                if iid in self.memory["shadow_preds"]:
                    sh_sid_int, sh_pred = self.memory["shadow_preds"].pop(iid)
                    sh_sid = str(sh_sid_int)
                    sh = self.memory["shadow"].get(sh_sid)
                    if sh:
                        if sh_pred == lbl:
                            sh["agree"] += 1
                            if sh["agree"] >= self.shadow_needed and sh_sid not in self.memory["promoted"]:
                                ctx.emit_declassified(
                                    "myelin.promote",
                                    {"sig_id": sh_sid_int, "label": lbl, "shadow": False},
                                    PROMOTE_SCHEMA,
                                )
                                ctx.condense(1.5)
                                self.memory["promoted"].append(sh_sid)
                        else:
                            sh["disagree"] += 1
                            ctx.emit_declassified("myelin.demote", {"sig_id": sh_sid_int}, DEMOTE_SCHEMA)
                            self.memory["demoted"].append(sh_sid)
                            self.memory["shadow"].pop(sh_sid, None)
                    continue

                counts = self.memory["stats"].setdefault(sid, {})
                counts[lbl] = counts.get(lbl, 0) + 1
                total = sum(counts.values())
                span_ok = (tinfo["last"] - tinfo["first"]) >= self.min_tick_span
                diversity_ok = len(tinfo["bodies"]) >= 3
                if (
                    total >= self.min_support
                    and len(counts) == 1
                    and span_ok
                    and diversity_ok
                    and sid not in self.memory["shadow"]
                    and sid not in self.memory["promoted"]
                ):
                    self.memory["shadow"][sid] = {"label": lbl, "agree": 0, "disagree": 0}
                    ctx.emit_declassified(
                        "myelin.promote",
                        {"sig_id": int(sid), "label": lbl, "shadow": True},
                        PROMOTE_SCHEMA,
                    )


# ===================================================================== Organ 4: Action (with Outcome Sensor)
class OutcomeSensor(Cell):
    """Sensory feedback loop inside ActionOrgan: emits friction gradients on failed actions."""

    lineage = "sensory"
    subscriptions = ("outcome.*",)

    def __init__(self, name: str = "action.verifier", **kw: Any):
        kw.setdefault("emits", [])
        super().__init__(name, **kw)
        self.memory.update(verified=0, failures=0)

    def step(self, ctx: Context) -> None:
        for s in ctx.inbox:
            status = s.payload.get("status")
            if status == "done":
                self.memory["verified"] += 1
            elif status in ("failed", "expired"):
                self.memory["failures"] += 1
                ctx.emit_gradient("friction", 0.5)


# ===================================================================== Organ 5: Bloodstream Coordinator
class Bloodstream(Cell):
    """Dynamic energy bloodstream adjusting organ regeneration by circadian posture."""

    lineage = "housekeeping"
    subscriptions = ()

    def __init__(self, name: str = "defense.bloodstream", organs: dict[str, Organ] | None = None, **kw: Any):
        kw.setdefault("emits", [])
        super().__init__(name, **kw)
        self._organs = organs or {}
        self.memory.update(last_mode="ALERT", shifts=0)

    def step(self, ctx: Context) -> None:
        mode = ctx.mode
        if mode == self.memory["last_mode"]:
            return
        self.memory["last_mode"] = mode
        self.memory["shifts"] += 1
        weights = {
            "ALERT": {"perception": 1.0, "action": 1.0, "memory": 1.0, "defense": 1.0, "deliberation": 1.0},
            "DEEP_FOCUS": {"perception": 1.25, "action": 1.25, "memory": 0.5, "defense": 1.0, "deliberation": 1.5},
            "LOCKDOWN": {"perception": 0.75, "action": 0.5, "memory": 0.5, "defense": 1.75, "deliberation": 0.5},
            "SLEEP_REM": {"perception": 0.5, "action": 0.5, "memory": 2.0, "defense": 1.0, "deliberation": 0.5},
            "DORMANT": {"perception": 0.5, "action": 0.25, "memory": 0.5, "defense": 1.0, "deliberation": 0.25},
        }.get(mode, {})
        for name, factor in weights.items():
            if name in self._organs:
                self._organs[name].scale_regen(ctx._kernel, factor)


# ===================================================================== Body Builder
def build_body(
    config: dict[str, Any] | None = None,
    *,
    genome: Genome | None = None,
    ledger: Ledger | None = None,
    brain: Brain | None = None,
) -> tuple[Kernel, Ledger, Genome, dict[str, Organ]]:
    """Boot a unified 5-organ living Body coupled to an authoritative Kernel."""
    cfg = {
        "brain": "rule",
        "brain_options": {},
        "reflex": True,
        "role": "general",
        "fuel": 1000.0,
        "regen": 4.0,
        "reasoner_fuel": 500.0,
        "reasoner_regen": 2.0,
        "reasoner_reserve": 10.0,
        "defense": {"max_actions": 20, "window": 5, "max_repeats": 2, "lockdown_ttl": 10},
        **(config or {}),
    }
    genome = genome or Genome(identity=f"body-{cfg['role']}", role=cfg["role"])
    ledger = ledger or Ledger()
    brain = brain or (make_brain(cfg["brain"], **cfg["brain_options"]) if cfg["brain"] else RuleBrain())

    kernel = Kernel()
    for topic in ("action.label", "action.close", "action.reopen", "myelin.promote", "myelin.demote"):
        kernel.require(topic, Trust.OPERATOR)

    fuel, regen = cfg["fuel"], cfg["regen"]
    pace = max(0.1, cfg["defense"]["max_actions"] / cfg["defense"]["window"])

    perception_organ = Organ(
        name="perception",
        in_ports=("world.issue", "peer.signal", "myelin.promote", "myelin.demote"),
        out_ports=("action.label", "issue.novel", "myelin.shadow"),
        energy_pool=fuel * 2.0,
        base_regen=regen * 2.0,
    )
    perception_organ.add_cell(SensoryIngest(), share=1.0)
    perception_organ.add_cell(FastSpineReflex(enabled=cfg["reflex"]), share=1.0)

    deliberation_organ = Organ(
        name="deliberation",
        in_ports=("issue.novel",),
        out_ports=("action.label",),
        energy_pool=cfg["reasoner_fuel"],
        base_regen=cfg["reasoner_regen"],
    )
    deliberation_organ.add_cell(CortexReasoner(brain=brain, reserve=cfg["reasoner_reserve"]), share=1.0)

    memory_organ = Organ(
        name="memory",
        in_ports=("outcome.*", "issue.novel", "action.label", "myelin.shadow"),
        out_ports=("myelin.promote", "myelin.demote"),
        energy_pool=fuel * 2.0,
        base_regen=regen * 2.0,
    )
    memory_organ.add_cell(MemoryConsolidator(), share=1.0)
    memory_organ.add_cell(
        MyelinCompiler(
            min_support=genome.myelin_min_support,
            min_tick_span=genome.myelin_min_span,
            shadow_needed=genome.myelin_shadow_needed,
        ),
        share=1.0,
    )

    action_organ = Organ(
        name="action",
        in_ports=("action.*", "owner.command"),
        out_ports=("action.close", "action.reopen", "action.label", "outcome.*"),
        energy_pool=fuel * 3.0,
        base_regen=regen * 3.0,
    )
    action_organ.add_cell(Commander(), share=1.0)
    action_organ.add_cell(Motor("action.motor", ledger.effectors(), resume_per_tick=pace), share=1.0)
    action_organ.add_cell(OutcomeSensor(), share=1.0)

    organs: dict[str, Organ] = {
        "perception": perception_organ,
        "deliberation": deliberation_organ,
        "memory": memory_organ,
        "action": action_organ,
    }

    defense_organ = Organ(
        name="defense",
        in_ports=("action.*",),
        out_ports=("action.*",),
        energy_pool=fuel * 2.0,
        base_regen=regen * 2.0,
    )
    defense_organ.add_cell(
        Defense("defense.guardian", forbidden=genome.forbidden_verbs, guards=("action.*",), **cfg["defense"]),
        share=1.0,
    )
    defense_organ.add_cell(Bloodstream(organs=organs), share=1.0)
    organs["defense"] = defense_organ

    for organ in organs.values():
        organ.mount(kernel)

    return kernel, ledger, genome, organs


def body_report(kernel: Kernel, ledger: Ledger, genome: Genome, organs: dict[str, Organ]) -> dict[str, Any]:
    """Operational & physiological summary of one unified Body."""
    events = dict(kernel.stats["events"])
    work_energy = float(kernel.stats["work_energy"])
    labelled = sum(1 for i in ledger.data["issues"].values() if i["labels"])
    ingest = kernel.cells["perception.ingest"].memory
    reflex = kernel.cells["perception.reflex"].memory
    cortex = kernel.cells["deliberation.cortex"].memory
    motor = kernel.cells["action.motor"].memory
    guardian = kernel.cells["defense.guardian"].memory
    myelin = kernel.cells["memory.myelin"].memory
    return {
        "identity": genome.identity,
        "role": genome.role,
        "tick": kernel.tick,
        "halted": kernel.halted,
        "operating_mode": kernel.operating_mode,
        "hormones": dict(kernel.hormones),
        "issues_seen": ingest.get("seen_total", len(ingest["seen"])),
        "issues_dropped": ingest["dropped"],
        "issues_labelled": labelled,
        "issues_closed": sum(1 for i in ledger.data["issues"].values() if i["closed"]),
        "reflex_hits": reflex["hits"],
        "compiled_reflex_hits": reflex["compiled_hits"],
        "compiled_rules": len(reflex["compiled"]),
        "cortex": {k: cortex[k] for k in ("thoughts", "outages", "deferred_low_fuel", "energy", "max_backlog")},
        "myelin": {"promoted": len(myelin["promoted"]), "demoted": len(myelin["demoted"])},
        "motor": {k: motor.get(k, 0) for k in ("executed", "vetoed", "failed", "expired")},
        "defense": {k: guardian[k] for k in ("mode", "vetoes", "lockdowns")},
        "organs": {name: organ.summary(kernel) for name, organ in organs.items()},
        "physics": kernel.physics_summary(),
        "work_energy": round(work_energy, 3),
        "dormant": sorted(kernel.dormant),
        "quarantined": sorted(kernel.quarantined),
        "events": dict(sorted(events.items())),
    }
