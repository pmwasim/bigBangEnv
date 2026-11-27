"""Operations: run an organism against a state directory, resume, halt, replay.

State directory layout::

    config.json     organism configuration (written on first run)
    snapshot.json   last kernel snapshot (matter, budgets, queue)
    host.json       host cursors (which issues/commands were ingested)
    ledger.json     the external world the motor changes
    trace.jsonl     append-only event trace (all sessions)
    HALT            create this file to stop a running organism (kill switch)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .apps.caretaker import DEFAULT_CONFIG, Host, Ledger, build, report
from .kernel import Kernel


class StateDir:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def file(self, name: str) -> Path:
        return self.path / name

    def read_json(self, name: str, default: Any = None) -> Any:
        f = self.file(name)
        return json.loads(f.read_text()) if f.exists() else default

    def write_json(self, name: str, data: Any) -> None:
        tmp = self.file(name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True, default=str))
        tmp.replace(self.file(name))

    def read_trace(self) -> list[dict[str, Any]]:
        f = self.file("trace.jsonl")
        if not f.exists():
            return []
        return [json.loads(line) for line in f.read_text().splitlines() if line.strip()]


class Runner:
    """Drives one caretaker organism persisted in a state directory."""

    def __init__(
        self,
        state_dir: str | Path,
        *,
        config: dict[str, Any] | None = None,
        issues_dir: str | Path | None = None,
        commands_file: str | Path | None = None,
        resume: bool = False,
        brain: Any = None,
    ):
        self.state = StateDir(state_dir)
        self.state.path.mkdir(parents=True, exist_ok=True)
        has_snapshot = self.state.file("snapshot.json").exists()
        if has_snapshot and not resume:
            raise FileExistsError(f"{self.state.path} already holds an organism; use --resume")
        if resume and not has_snapshot:
            raise FileNotFoundError(f"nothing to resume in {self.state.path}")

        saved = self.state.read_json("config.json")
        self.config = saved if resume and saved else {**DEFAULT_CONFIG, **(config or {})}
        self.kernel, self.ledger = build(self.config, ledger=Ledger(self.state.file("ledger.json")), brain=brain)
        self.host = Host(
            issues_dir=issues_dir, commands_file=commands_file,
            issues_per_tick=self.config["issues_per_tick"],
        )
        if resume:
            self.kernel.restore(self.state.read_json("snapshot.json"))
            self.host.state = self.state.read_json("host.json", self.host.state)
        else:
            self.state.write_json("config.json", self.config)
            self.state.file("trace.jsonl").write_text("")
        self._flushed = 0

    def save(self) -> None:
        self.state.write_json("snapshot.json", self.kernel.snapshot())
        self.state.write_json("host.json", self.host.state)
        with open(self.state.file("trace.jsonl"), "a", encoding="utf-8") as fh:
            for record in self.kernel.trace[self._flushed:]:
                fh.write(json.dumps(record, default=str) + "\n")
        self._flushed = len(self.kernel.trace)

    def check_halt(self) -> bool:
        halt = self.state.file("HALT")
        if halt.exists() and not self.kernel.halted:
            self.kernel.halt(halt.read_text().strip() or "HALT file")
        return self.kernel.halted

    def run(self, ticks: int | None = None, *, interval: float = 0.0, save_every: int = 10) -> dict[str, Any]:
        """Run ``ticks`` ticks, or forever when ``ticks`` is None (until HALT)."""
        done = 0
        try:
            while ticks is None or done < ticks:
                if self.check_halt():
                    break
                self.host.poll(self.kernel)
                self.kernel.step()
                done += 1
                if done % save_every == 0:
                    self.save()
                if interval:
                    time.sleep(interval)
        finally:
            self.save()
        return report(self.kernel, self.ledger)


def status(state_dir: str | Path) -> dict[str, Any]:
    state = StateDir(state_dir)
    snap = state.read_json("snapshot.json")
    if snap is None:
        raise FileNotFoundError(f"no organism in {state_dir}")
    trace = state.read_trace()
    counts: dict[str, int] = {}
    for record in trace:
        counts[record["event"]] = counts.get(record["event"], 0) + 1
    ledger = state.read_json("ledger.json", {"issues": {}})
    return {
        "tick": snap["tick"],
        "halted": snap["halted"],
        "halt_requested": state.file("HALT").exists(),
        "queue": len(snap["queue"]),
        "cells": {
            name: {
                "spent": round(c["spent"], 1),
                "dormant": c["dormant"],
                "quarantined": c.get("quarantined", False),
            }
            for name, c in sorted(snap["cells"].items())
        },
        "issues": len(ledger["issues"]),
        "closed": sum(1 for i in ledger["issues"].values() if i["closed"]),
        "events": dict(sorted(counts.items())),
    }


def request_halt(state_dir: str | Path, reason: str = "operator") -> None:
    StateDir(state_dir).file("HALT").write_text(reason)


def revive(state_dir: str | Path, cell: str, *, refuel: float = 0.0, clear_halt: bool = False) -> None:
    """Offline operator action on a stopped organism's snapshot."""
    state = StateDir(state_dir)
    snap = state.read_json("snapshot.json")
    if snap is None or cell not in snap["cells"]:
        raise KeyError(f"no cell {cell!r} in {state_dir}")
    entry = snap["cells"][cell]
    entry["spent"] = max(0.0, entry["spent"] - refuel)
    entry["dormant"] = False
    entry["quarantined"] = False
    if clear_halt:
        snap["halted"] = False
        state.file("HALT").unlink(missing_ok=True)
    state.write_json("snapshot.json", snap)
    with open(state.file("trace.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"tick": snap["tick"], "event": "revive", "cell": cell, "refuel": refuel}) + "\n")


def _normalise(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return json.loads(json.dumps(records, default=str))


def replay_trace(trace: list[dict[str, Any]], config: dict[str, Any]) -> tuple[bool, str]:
    """Re-run an organism from its recorded inputs and compare traces.

    Works for single-session traces (no restore/revive) with a deterministic brain.
    Side effects go to a fresh in-memory ledger.
    """
    if not trace or trace[0]["event"] != "genesis":
        return False, "trace does not start at genesis"
    if any(r["event"] in ("restore", "revive") for r in trace):
        return False, "trace spans several sessions; replay needs a single session"
    if config.get("brain") not in ("rule", "offline"):
        return False, f"brain {config.get('brain')!r} is not deterministic"

    kernel, _ = build(config, ledger=Ledger())
    injects: dict[int, list[dict[str, Any]]] = {}
    halt: dict[str, Any] | None = None
    for record in trace:
        # Outside input refused by a topic floor is logged only as `blocked` (with a
        # sender, no cell). Re-offer it so the kernel refuses it again in the same place.
        refused = record["event"] == "blocked" and "sender" in record and "cell" not in record
        if record["event"] == "inject" or refused:
            injects.setdefault(record["tick"], []).append(record)
        elif record["event"] == "halt":
            halt = record
    final_tick = trace[-1]["tick"]
    for tick in range(final_tick + 1):
        if halt and halt["tick"] == tick:  # the runner checks HALT before polling inputs
            kernel.halt(halt["reason"])
            break
        for r in injects.get(tick, []):
            # A refused attempt never recorded its payload; the kernel refuses it before reading one.
            kernel.inject(r["topic"], r.get("payload"), trust=_trust(r["trust"]), sender=r["sender"],
                          ttl=r.get("ttl", 3))
        if tick < final_tick:
            kernel.step()
    return diff_traces(_normalise(trace), _normalise(kernel.trace))


def _trust(name: str):
    from .signal import Trust

    return Trust[name]


def diff_traces(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> tuple[bool, str]:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return False, f"diverged at record {i}: {x} != {y}"
    if len(a) != len(b):
        return False, f"length differs: {len(a)} vs {len(b)}"
    return True, f"identical ({len(a)} records)"


def replay(state_dir: str | Path) -> tuple[bool, str]:
    state = StateDir(state_dir)
    return replay_trace(state.read_trace(), state.read_json("config.json", {}))


__all__ = ["Runner", "StateDir", "diff_traces", "replay", "replay_trace", "request_halt", "revive", "status", "Kernel"]
