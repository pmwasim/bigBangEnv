"""Repo caretaker: the first real bigBangEnv organism (milestone M1).

It triages incoming issues and executes owner commands. Issue text is
untrusted (WORLD); owner commands are OWNER. Wiring:

    world.issue ─▶ perception ─▶ issue.new ─▶ reflex ──(declassified)──▶ action.label ─┐
                                               └─▶ issue.novel ─▶ reasoner ─(declassified)┤
    owner.command ─▶ commander ─────────────────────────────▶ action.close / .label ──────┤
                                                       defense (veto) ◀── action.* ──▶ motor ─▶ ledger
                                                                         outcome.* ─▶ journal
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..brains import Brain, BrainUnavailable, RuleBrain, make_brain
from ..cell import Cell, Context
from ..kernel import Kernel
from ..lineages import Defense, Motor
from ..signal import Trust

LABELS = ("bug", "feature", "question", "docs", "spam", "needs-human")
LABEL_SCHEMA = {"issue": int, "label": frozenset(LABELS), "source": frozenset({"auto"})}
MAX_TITLE, MAX_BODY = 300, 20_000

DEFAULT_CONFIG: dict[str, Any] = {
    "brain": "rule",
    "brain_options": {},
    "reflex": True,
    "fuel": 1000.0,
    # Sustained throughput is regen minus the 1-unit heartbeat, in emits per tick.
    # 4.0 keeps up with issues_per_tick=3; at 1.0 a drained cell could never emit again.
    "regen": 4.0,
    "reasoner_fuel": 500.0,
    "reasoner_regen": 2.0,
    "reasoner_reserve": 10.0,
    "issues_per_tick": 3,
    "defense": {"max_actions": 20, "window": 5, "max_repeats": 2, "lockdown_ttl": 10},
}


# ---------------------------------------------------------------- cells
def drain(cell: Cell, ctx: Context, fresh: list[Any], send: Any) -> None:
    """Work through ``cell.memory['backlog']`` plus fresh items without ever dropping one.

    ``send(item)`` returns True once the item is handled. Anything it can't
    afford yet stays in the persisted backlog and is retried as energy
    regenerates; with no fuel left, items aren't even attempted (no denial spam).
    """
    backlog = []
    for item in cell.memory["backlog"] + fresh:
        if ctx.fuel < Kernel.EMIT_COST:
            backlog.append(item)  # unaffordable now: keep it
        elif not send(item):
            if ctx.fuel < Kernel.EMIT_COST:
                backlog.append(item)  # ran dry part-way: keep it
            else:  # refused for a lasting reason (capability, floor, schema): logged by the kernel
                cell.memory["undeliverable"] = cell.memory.get("undeliverable", 0) + 1
    cell.memory["backlog"] = backlog
    cell.memory["max_backlog"] = max(cell.memory["max_backlog"], len(backlog))


class Perception(Cell):
    """Sensory cell: validates, truncates and de-duplicates raw issues."""

    lineage = "sensory"
    subscriptions = ("world.issue",)

    def __init__(self, name: str = "perception", *, max_seen: int | None = 10_000, **kw: Any):
        kw.setdefault("emits", ["issue.new"])
        super().__init__(name, **kw)
        self.max_seen = max_seen
        self._seen_set: set[int] = set()
        self.memory.update(seen=[], seen_total=0, dropped=0, backlog=[], max_backlog=0)

    def step(self, ctx: Context) -> None:
        seen_list = self.memory["seen"]
        if len(self._seen_set) != len(seen_list):
            self._seen_set = set(seen_list)
        if "seen_total" not in self.memory:
            self.memory["seen_total"] = len(seen_list)
        fresh = []
        for signal in ctx.inbox:
            issue = signal.payload
            ok = (
                isinstance(issue, dict)
                and isinstance(issue.get("id"), int)
                and not isinstance(issue.get("id"), bool)
                and 0 <= issue["id"] < 2**31
                and isinstance(issue.get("title"), str)
                and isinstance(issue.get("body", ""), str)
                and issue["title"].strip()
            )
            if not ok or issue["id"] in self._seen_set:
                self.memory["dropped"] += 1
                continue
            self._seen_set.add(issue["id"])
            seen_list.append(issue["id"])  # accepted: it now lives in the backlog until sent
            self.memory["seen_total"] += 1
            if self.max_seen is not None and len(seen_list) > self.max_seen:
                evicted = seen_list.pop(0)
                self._seen_set.discard(evicted)
            fresh.append({"id": issue["id"], "title": issue["title"][:MAX_TITLE],
                          "body": issue.get("body", "")[:MAX_BODY]})
        drain(self, ctx, fresh, lambda item: ctx.emit("issue.new", item) is not None)


class Reflex(Cell):
    """Fast spine: labels unambiguous issues without waking the reasoner."""

    lineage = "reflex"
    subscriptions = ("issue.new",)
    TAGS = {"[bug]": "bug", "[feature]": "feature", "[docs]": "docs", "[question]": "question"}
    SPAM = ("free money", "click here", "buy now", "casino")

    def __init__(self, name: str = "reflex", *, enabled: bool = True, **kw: Any):
        kw.setdefault("emits", ["action.label", "issue.novel"])
        kw.setdefault("declassify", True)
        super().__init__(name, **kw)
        self.enabled = enabled
        self.memory.update(hits=0, escalated=0, backlog=[], max_backlog=0)

    def classify(self, title: str, body: str) -> str | None:
        lowered = title.lower().strip()
        for tag, label in self.TAGS.items():
            if lowered.startswith(tag):
                return label
        text = f"{lowered}\n{body.lower()}"
        if any(phrase in text for phrase in self.SPAM):
            return "spam"
        return None

    def _handle(self, ctx: Context, issue: dict[str, Any]) -> bool:
        label = self.classify(issue["title"], issue["body"]) if self.enabled else None
        if label is None:
            if ctx.emit("issue.novel", issue) is None:
                return False
            self.memory["escalated"] += 1
            return True
        sent = ctx.emit_declassified(
            "action.label", {"issue": issue["id"], "label": label, "source": "auto"}, LABEL_SCHEMA
        )
        if sent is None:
            return False
        self.memory["hits"] += 1
        return True

    def step(self, ctx: Context) -> None:
        drain(self, ctx, [s.payload for s in ctx.inbox], lambda issue: self._handle(ctx, issue))


class Reasoner(Cell):
    """Slow cortex: asks a brain about novel issues; degrades to needs-human."""

    lineage = "reasoning"
    subscriptions = ("issue.novel",)

    def __init__(self, name: str = "reasoner", *, brain: Brain, reserve: float = 10.0, **kw: Any):
        kw.setdefault("emits", ["action.label"])
        kw.setdefault("declassify", True)
        super().__init__(name, **kw)
        self.brain = brain
        self.reserve = reserve
        # backlog: [issue, decided label or None] that could not be emitted yet
        self.memory.update(thoughts=0, outages=0, deferred_low_fuel=0, energy=0.0, backlog=[], max_backlog=0)

    def _decide(self, ctx: Context, issue: dict[str, Any]) -> str:
        if ctx.fuel < self.reserve:
            self.memory["deferred_low_fuel"] += 1  # sensed scarcity: don't think
            return "needs-human"
        try:
            thought = self.brain.classify(issue["title"], issue["body"], LABELS)
        except BrainUnavailable:
            self.memory["outages"] += 1
            return "needs-human"
        if not ctx.spend(thought.cost, f"brain:{self.brain.name}"):
            self.memory["deferred_low_fuel"] += 1
            return "needs-human"
        self.memory["thoughts"] += 1
        self.memory["energy"] += thought.cost
        return thought.label

    def step(self, ctx: Context) -> None:
        work = self.memory["backlog"] + [[s.payload, None] for s in ctx.inbox]
        backlog = []
        for issue, label in work:
            if ctx.fuel < Kernel.EMIT_COST:  # can't even report: keep it, don't drop it
                backlog.append([issue, label])
                continue
            label = label or self._decide(ctx, issue)
            sent = ctx.emit_declassified(
                "action.label", {"issue": issue["id"], "label": label, "source": "auto"}, LABEL_SCHEMA
            )
            if sent is None:
                backlog.append([issue, label])  # decided but unaffordable: retry, never re-pay
        self.memory["backlog"] = backlog
        self.memory["max_backlog"] = max(self.memory["max_backlog"], len(backlog))


class Commander(Cell):
    """Parses owner commands. Its output can only be as trusted as its input."""

    lineage = "motor-planning"
    subscriptions = ("owner.command",)
    PATTERN = re.compile(r"^\s*(close|reopen)\s+#?(\d+)\s*$|^\s*label\s+#?(\d+)\s+([\w-]+)\s*$", re.I)

    def __init__(self, name: str = "commander", **kw: Any):
        kw.setdefault("emits", ["action.close", "action.reopen", "action.label"])
        # Receptor: only the owner speaks here. Without it, one WORLD-trust
        # command would leave a taint residue that blocks every later one.
        kw.setdefault("accepts", Trust.OWNER)
        super().__init__(name, **kw)
        self.memory.update(accepted=0, rejected=0, backlog=[], max_backlog=0)

    def _handle(self, ctx: Context, command: str) -> bool:
        match = self.PATTERN.match(command)
        if not match:
            self.memory["rejected"] += 1
            return True
        verb, number, label_issue, label = match.groups()
        if verb:
            sent = ctx.emit(f"action.{verb.lower()}", {"issue": int(number)})
        elif label in LABELS:
            sent = ctx.emit("action.label", {"issue": int(label_issue), "label": label, "source": "owner"})
        else:
            self.memory["rejected"] += 1
            return True
        if sent is None:
            return False
        self.memory["accepted"] += 1
        return True

    def step(self, ctx: Context) -> None:
        drain(self, ctx, [str(s.payload) for s in ctx.inbox], lambda command: self._handle(ctx, command))


class Journal(Cell):
    """Housekeeping: keeps outcome statistics."""

    lineage = "housekeeping"
    subscriptions = ("outcome.*",)

    def __init__(self, name: str = "journal", **kw: Any):
        kw.setdefault("emits", [])
        super().__init__(name, **kw)
        self.memory.update(outcomes={})

    def step(self, ctx: Context) -> None:
        for signal in ctx.inbox:
            key = f"{signal.topic.split('.', 1)[1]}:{signal.payload.get('status')}"
            self.memory["outcomes"][key] = self.memory["outcomes"].get(key, 0) + 1


# ---------------------------------------------------------------- world
class Ledger:
    """The caretaker's external world: issue labels and open/closed state."""

    def __init__(self, path: str | Path | None = None, *, auto_flush: bool = True):
        self.path = Path(path) if path else None
        self.auto_flush = auto_flush
        self._dirty = False
        self.data: dict[str, Any] = {"issues": {}, "history": []}
        if self.path and self.path.exists():
            self.data = json.loads(self.path.read_text())

    def _issue(self, number: int) -> dict[str, Any]:
        return self.data["issues"].setdefault(str(number), {"labels": [], "closed": False})

    def flush(self) -> None:
        if self.path and self._dirty:
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(self.data, indent=2, sort_keys=True))
            tmp.replace(self.path)
            self._dirty = False

    def _record(self, verb: str, payload: dict[str, Any]) -> None:
        self.data["history"].append({"verb": verb, **payload})
        self._dirty = True
        if self.auto_flush:
            self.flush()

    def label(self, payload: dict[str, Any]) -> dict[str, Any]:
        issue = self._issue(payload["issue"])
        if payload.get("source") == "auto" and issue["labels"]:
            # Automatic triage never overrides a label that is already there
            # (for example one the owner set before triage ran).
            return {"labels": list(issue["labels"]), "skipped": True}
        if payload["label"] not in issue["labels"]:
            issue["labels"].append(payload["label"])
        self._record("label", payload)
        return {"labels": list(issue["labels"])}

    def close(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._issue(payload["issue"])["closed"] = True
        self._record("close", payload)
        return {"closed": True}

    def reopen(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._issue(payload["issue"])["closed"] = False
        self._record("reopen", payload)
        return {"closed": False}

    def effectors(self) -> dict[str, Any]:
        return {"label": self.label, "close": self.close, "reopen": self.reopen}


class Host:
    """Feeds the outside world into the kernel: issues (WORLD) and owner commands (OWNER)."""

    def __init__(
        self,
        *,
        issues: list[Any] | None = None,
        commands: list[str] | None = None,
        issues_dir: str | Path | None = None,
        commands_file: str | Path | None = None,
        issues_per_tick: int = 3,
        peer_secrets: dict[str, str] | None = None,
    ):
        self.commands = list(commands or [])
        self.issues_dir = Path(issues_dir) if issues_dir else None
        self.commands_file = Path(commands_file) if commands_file else None
        self.issues_per_tick = issues_per_tick
        self.peer_secrets = dict(peer_secrets or {})
        # Persisted between sessions: issues read but not yet injected, files
        # already read, and how many command lines were consumed.
        self.state: dict[str, Any] = {"pending": list(issues or []), "command_cursor": 0, "ingested_files": []}
        self._ingested_set: set[str] = set()
        self._last_issues_stamp: tuple[int, int] | None = None
        self._last_commands_stamp: tuple[int, int, int] | None = None

    def _pull_files(self) -> None:
        if len(self._ingested_set) != len(self.state["ingested_files"]):
            self._ingested_set = set(self.state["ingested_files"])
        if self.issues_dir and self.issues_dir.is_dir():
            st = self.issues_dir.stat()
            stamp = (st.st_mtime_ns, st.st_ctime_ns)
            if stamp != self._last_issues_stamp:
                self._last_issues_stamp = stamp
                new_paths = sorted(
                    (p for p in self.issues_dir.iterdir()
                     if p.is_file() and p.suffix == ".json" and p.name not in self._ingested_set),
                    key=lambda p: p.name,
                )
                for path in new_paths:
                    self._ingested_set.add(path.name)
                    self.state["ingested_files"].append(path.name)
                    try:
                        self.state["pending"].append(json.loads(path.read_text()))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        self.state["pending"].append({"invalid": path.name})
        if self.commands_file and self.commands_file.exists():
            cst = self.commands_file.stat()
            cstamp = (cst.st_mtime_ns, cst.st_ctime_ns, cst.st_size)
            if cstamp != self._last_commands_stamp:
                self._last_commands_stamp = cstamp
                lines = [ln for ln in self.commands_file.read_text().splitlines() if ln.strip()]
                self.commands = lines

    def poll(self, kernel: Kernel) -> None:
        from ..society import Skin

        self._pull_files()
        batch = self.state["pending"][:self.issues_per_tick]
        self.state["pending"] = self.state["pending"][self.issues_per_tick:]
        for item in batch:
            if isinstance(item, dict) and item.get("topic") == "world.reagent" and isinstance(item.get("payload"), dict):
                kernel.inject(
                    "world.reagent",
                    item["payload"],
                    trust=Trust.WORLD,
                    sender="reagent-feed",
                    ttl=int(item.get("ttl", 5)),
                    risk=float(item.get("risk", 0.0)),
                )
            elif isinstance(item, dict) and item.get("topic") == "peer.signal" and isinstance(item.get("envelope"), dict):
                env = item["envelope"]
                ok, _ = Skin.verify(env, self.peer_secrets)
                kernel.inject(
                    "peer.signal",
                    env.get("payload"),
                    trust=Trust.USER if ok else Trust.WORLD,
                    sender=str(env.get("from", "peer")) if ok else "peer-unverified",
                    ttl=5,
                    risk=float(item.get("risk", 0.1 if ok else 0.6)),
                )
            else:
                kernel.inject("world.issue", item, trust=Trust.WORLD, sender="issue-feed", ttl=5)
        for command in self.commands[self.state["command_cursor"]:]:
            kernel.inject("owner.command", command, trust=Trust.OWNER, sender="owner", ttl=5)
            self.state["command_cursor"] += 1

    @property
    def drained(self) -> bool:
        return not self.state["pending"] and self.state["command_cursor"] >= len(self.commands)


# ---------------------------------------------------------------- build
def build(
    config: dict[str, Any] | None = None,
    *,
    ledger: Ledger | None = None,
    brain: Brain | None = None,
    extra_cells: list[tuple[Cell, float]] | None = None,
) -> tuple[Kernel, Ledger]:
    """Boot a caretaker organism. The Big Bang for this app."""
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    ledger = ledger or Ledger()
    brain = brain or (make_brain(cfg["brain"], **cfg["brain_options"]) if cfg["brain"] else RuleBrain())

    kernel = Kernel()
    for topic in ("action.label", "action.close", "action.reopen"):
        kernel.require(topic, Trust.OPERATOR)

    fuel, regen = cfg["fuel"], cfg["regen"]
    kernel.spawn(Perception(), fuel=fuel, regen=regen)
    kernel.spawn(Reflex(enabled=cfg["reflex"]), fuel=fuel, regen=regen)
    kernel.spawn(
        Reasoner(brain=brain, reserve=cfg["reasoner_reserve"]),
        fuel=cfg["reasoner_fuel"], regen=cfg["reasoner_regen"],
    )
    kernel.spawn(Commander(), fuel=fuel, regen=regen)
    kernel.spawn(Defense("defense", forbidden=("delete",), guards=("action.*",), **cfg["defense"]), fuel=fuel, regen=regen)
    # After a lockdown, paused work resumes no faster than Defense's own rate limit.
    defense = {"max_actions": 20, "window": 5, **cfg["defense"]}
    pace = max(1, defense["max_actions"] // defense["window"])
    kernel.spawn(Motor("motor", ledger.effectors(), resume_per_tick=pace), fuel=fuel, regen=regen)
    kernel.spawn(Journal(), fuel=fuel, regen=regen)
    for cell, cell_fuel in extra_cells or []:
        kernel.spawn(cell, fuel=cell_fuel, regen=regen)
    return kernel, ledger


def report(kernel: Kernel, ledger: Ledger) -> dict[str, Any]:
    """Operational summary of one organism."""
    events = dict(kernel.stats["events"])
    work_energy = float(kernel.stats["work_energy"])
    labelled = sum(1 for i in ledger.data["issues"].values() if i["labels"])
    perception = kernel.cells["perception"].memory
    reflex = kernel.cells["reflex"].memory
    return {
        "tick": kernel.tick,
        "halted": kernel.halted,
        "issues_seen": perception.get("seen_total", len(perception["seen"])),
        "issues_dropped": perception["dropped"],
        "issues_labelled": labelled,
        "issues_closed": sum(1 for i in ledger.data["issues"].values() if i["closed"]),
        "reflex_hits": reflex["hits"],
        "reasoner": {
            **{k: kernel.cells["reasoner"].memory[k] for k in ("thoughts", "outages", "deferred_low_fuel", "energy", "max_backlog")},
            "backlog": len(kernel.cells["reasoner"].memory["backlog"]),
        },
        "motor": {k: kernel.cells["motor"].memory.get(k, 0) for k in ("executed", "vetoed", "failed", "expired")},
        "backlogs": {name: len(kernel.cells[name].memory.get("backlog", kernel.cells[name].memory.get("unsent", [])))
                     for name in ("perception", "reflex", "reasoner", "commander", "motor")},
        "defense": {k: kernel.cells["defense"].memory[k] for k in ("mode", "vetoes", "lockdowns")},
        "work_energy": round(work_energy, 3),
        "work_energy_per_issue": round(work_energy / labelled, 3) if labelled else None,
        "fuel_remaining": {n: round(b.remaining, 1) for n, b in sorted(kernel.budgets.items())},
        "dormant": sorted(kernel.dormant),
        "quarantined": sorted(kernel.quarantined),
        "events": dict(sorted(events.items())),
    }
