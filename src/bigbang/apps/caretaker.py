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
    "regen": 1.0,
    "reasoner_fuel": 500.0,
    "reasoner_regen": 2.0,
    "reasoner_reserve": 10.0,
    "issues_per_tick": 3,
    "defense": {"max_actions": 20, "window": 5, "max_repeats": 2, "lockdown_ttl": 10},
}


# ---------------------------------------------------------------- cells
class Perception(Cell):
    """Sensory cell: validates, truncates and de-duplicates raw issues."""

    lineage = "sensory"
    subscriptions = ("world.issue",)

    def __init__(self, name: str = "perception", **kw: Any):
        kw.setdefault("emits", ["issue.new"])
        super().__init__(name, **kw)
        self.memory.update(seen=[], dropped=0)

    def step(self, ctx: Context) -> None:
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
            if not ok or issue["id"] in self.memory["seen"]:
                self.memory["dropped"] += 1
                continue
            self.memory["seen"].append(issue["id"])
            ctx.emit("issue.new", {
                "id": issue["id"],
                "title": issue["title"][:MAX_TITLE],
                "body": issue.get("body", "")[:MAX_BODY],
            })


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
        self.memory.update(hits=0, escalated=0)

    def classify(self, title: str, body: str) -> str | None:
        lowered = title.lower().strip()
        for tag, label in self.TAGS.items():
            if lowered.startswith(tag):
                return label
        text = f"{lowered}\n{body.lower()}"
        if any(phrase in text for phrase in self.SPAM):
            return "spam"
        return None

    def step(self, ctx: Context) -> None:
        for signal in ctx.inbox:
            issue = signal.payload
            label = self.classify(issue["title"], issue["body"]) if self.enabled else None
            if label is None:
                self.memory["escalated"] += 1
                ctx.emit("issue.novel", issue)
            else:
                self.memory["hits"] += 1
                ctx.emit_declassified(
                    "action.label", {"issue": issue["id"], "label": label, "source": "auto"}, LABEL_SCHEMA
                )


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
        self.memory.update(thoughts=0, outages=0, deferred_low_fuel=0, energy=0.0)

    def step(self, ctx: Context) -> None:
        for signal in ctx.inbox:
            issue = signal.payload
            label = "needs-human"
            if ctx.fuel < self.reserve:
                self.memory["deferred_low_fuel"] += 1  # sensed scarcity: don't think
            else:
                try:
                    thought = self.brain.classify(issue["title"], issue["body"], LABELS)
                except BrainUnavailable:
                    self.memory["outages"] += 1
                else:
                    if ctx.spend(thought.cost, f"brain:{self.brain.name}"):
                        label = thought.label
                        self.memory["thoughts"] += 1
                        self.memory["energy"] += thought.cost
                    else:
                        self.memory["deferred_low_fuel"] += 1
            ctx.emit_declassified(
                "action.label", {"issue": issue["id"], "label": label, "source": "auto"}, LABEL_SCHEMA
            )


class Commander(Cell):
    """Parses owner commands. Its output can only be as trusted as its input."""

    lineage = "motor-planning"
    subscriptions = ("owner.command",)
    PATTERN = re.compile(r"^\s*(close|reopen)\s+#?(\d+)\s*$|^\s*label\s+#?(\d+)\s+([\w-]+)\s*$", re.I)

    def __init__(self, name: str = "commander", **kw: Any):
        kw.setdefault("emits", ["action.close", "action.reopen", "action.label"])
        super().__init__(name, **kw)
        self.memory.update(accepted=0, rejected=0)

    def step(self, ctx: Context) -> None:
        for signal in ctx.inbox:
            match = self.PATTERN.match(str(signal.payload))
            if not match:
                self.memory["rejected"] += 1
                continue
            verb, number, label_issue, label = match.groups()
            if verb:
                ctx.emit(f"action.{verb.lower()}", {"issue": int(number)})
            elif label in LABELS:
                ctx.emit("action.label", {"issue": int(label_issue), "label": label, "source": "owner"})
            else:
                self.memory["rejected"] += 1
                continue
            self.memory["accepted"] += 1


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

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.data: dict[str, Any] = {"issues": {}, "history": []}
        if self.path and self.path.exists():
            self.data = json.loads(self.path.read_text())

    def _issue(self, number: int) -> dict[str, Any]:
        return self.data["issues"].setdefault(str(number), {"labels": [], "closed": False})

    def _record(self, verb: str, payload: dict[str, Any]) -> None:
        self.data["history"].append({"verb": verb, **payload})
        if self.path:
            self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True))

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
    ):
        self.commands = list(commands or [])
        self.issues_dir = Path(issues_dir) if issues_dir else None
        self.commands_file = Path(commands_file) if commands_file else None
        self.issues_per_tick = issues_per_tick
        # Persisted between sessions: issues read but not yet injected, files
        # already read, and how many command lines were consumed.
        self.state: dict[str, Any] = {"pending": list(issues or []), "command_cursor": 0, "ingested_files": []}

    def _pull_files(self) -> None:
        if self.issues_dir and self.issues_dir.is_dir():
            for path in sorted(self.issues_dir.glob("*.json")):
                if path.name in self.state["ingested_files"]:
                    continue
                self.state["ingested_files"].append(path.name)
                try:
                    self.state["pending"].append(json.loads(path.read_text()))
                except json.JSONDecodeError:
                    self.state["pending"].append({"invalid": path.name})
        if self.commands_file and self.commands_file.exists():
            lines = [ln for ln in self.commands_file.read_text().splitlines() if ln.strip()]
            self.commands = lines

    def poll(self, kernel: Kernel) -> None:
        self._pull_files()
        batch = self.state["pending"][:self.issues_per_tick]
        self.state["pending"] = self.state["pending"][self.issues_per_tick:]
        for issue in batch:
            kernel.inject("world.issue", issue, trust=Trust.WORLD, sender="issue-feed", ttl=5)
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
    kernel.spawn(Defense("defense", forbidden=("delete",), **cfg["defense"]), fuel=fuel, regen=regen)
    kernel.spawn(Motor("motor", ledger.effectors()), fuel=fuel, regen=regen)
    kernel.spawn(Journal(), fuel=fuel, regen=regen)
    for cell, cell_fuel in extra_cells or []:
        kernel.spawn(cell, fuel=cell_fuel, regen=regen)
    return kernel, ledger


def report(kernel: Kernel, ledger: Ledger) -> dict[str, Any]:
    """Operational summary of one organism."""
    events: dict[str, int] = {}
    work_energy = 0.0
    for record in kernel.trace:
        events[record["event"]] = events.get(record["event"], 0) + 1
        if record["event"] == "emit":
            work_energy += Kernel.EMIT_COST
        elif record["event"] == "spend":
            work_energy += record["units"]
    labelled = sum(1 for i in ledger.data["issues"].values() if i["labels"])
    reflex = kernel.cells["reflex"].memory
    return {
        "tick": kernel.tick,
        "halted": kernel.halted,
        "issues_seen": len(kernel.cells["perception"].memory["seen"]),
        "issues_dropped": kernel.cells["perception"].memory["dropped"],
        "issues_labelled": labelled,
        "issues_closed": sum(1 for i in ledger.data["issues"].values() if i["closed"]),
        "reflex_hits": reflex["hits"],
        "reasoner": {k: kernel.cells["reasoner"].memory[k] for k in ("thoughts", "outages", "deferred_low_fuel", "energy")},
        "motor": {k: kernel.cells["motor"].memory[k] for k in ("executed", "vetoed", "failed")},
        "defense": {k: kernel.cells["defense"].memory[k] for k in ("mode", "vetoes", "lockdowns")},
        "work_energy": round(work_energy, 3),
        "work_energy_per_issue": round(work_energy / labelled, 3) if labelled else None,
        "fuel_remaining": {n: round(b.remaining, 1) for n, b in sorted(kernel.budgets.items())},
        "dormant": sorted(kernel.dormant),
        "quarantined": sorted(kernel.quarantined),
        "events": dict(sorted(events.items())),
    }
