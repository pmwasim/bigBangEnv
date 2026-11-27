"""Tests for ADR-0011: fail-closed guardians and bounded infinite-run metabolism."""

from __future__ import annotations

import json
import signal

from bigbang import Cell, Kernel, Trust, big_bang
from bigbang.apps.caretaker import Host, Ledger, Perception, build, report
from bigbang.lineages import Defense, Motor
from bigbang.runtime import Runner


def test_dormant_guardian_holds_actions_fail_closed():
    executed = []
    k = Kernel()
    k.require("action.delete", Trust.OPERATOR)
    k.spawn(Defense("defense", forbidden=("delete",), guards=("action.*",)), fuel=10.0, regen=0.4)
    k.budgets["defense"].spent = 9.5  # after regen=0.4: remaining=0.9 (<1.0) on tick 1 -> dormant; wakes on tick 2 (remaining=1.3)
    k.spawn(Motor("motor", {"delete": lambda p: (executed.append(p), {"ok": True})[1]}, hold=1), fuel=100.0, regen=1.0)

    k.inject("action.delete", {"target": "prod"}, trust=Trust.OWNER)
    k.step()  # tick 1: defense sleeps, action held rather than delivered to motor
    assert "defense" in k.dormant
    assert executed == []
    assert any(e["event"] == "hold" and e["topic"] == "action.delete" for e in k.trace)

    k.step()  # tick 2: defense wakes, receives held action, and vetoes it
    k.step()  # tick 3: motor sees no unvetoed action
    assert executed == []
    assert k.cells["defense"].memory["vetoes"] >= 1


def test_quarantined_guardian_pauses_pending_motor_actions():
    executed = []

    class CrashDefense(Cell):
        subscriptions = ("action.*",)

        def __init__(self, name: str, **kw):
            super().__init__(name, guards=("action.*",), **kw)

        def step(self, ctx):
            if ctx.inbox:
                raise RuntimeError("guardian bug")

    k = big_bang(
        CrashDefense("a_guard"),
        Motor("z_motor", {"close": lambda p: (executed.append(p), {"ok": True})[1]}, hold=1),
        fuel=100.0,
    )
    k.inject("action.close", {"issue": 1}, trust=Trust.OPERATOR)
    k.run(4)  # a_guard crashes on tick 1; z_motor must stay paused instead of executing unchecked
    assert "a_guard" in k.quarantined
    assert executed == []
    assert k.is_inhibited("action.close")

    k.revive("a_guard", refuel=10.0)
    # Replace behavior so guardian survives next tick
    k.cells["a_guard"].step = lambda ctx: None
    k.run(2)
    assert len(executed) == 1


def test_kernel_stats_and_drain_trace_preserve_report():
    k, ledger = build()
    host = Host(issues=[{"id": 1, "title": "[bug] crash", "body": ""}])
    for _ in range(10):
        host.poll(k)
        k.step()

    full_rep = report(k, ledger)
    drained = k.drain_trace()
    assert len(drained) > 0
    assert k.trace == []

    drained_rep = report(k, ledger)
    assert drained_rep == full_rep

    # Snapshot + restore preserves cumulative stats
    k2, _ = build()
    k2.restore(k.snapshot())
    assert k2.stats["work_energy"] == k.stats["work_energy"]
    assert k2.stats["events"]["emit"] == k.stats["events"]["emit"]


def test_runner_drains_in_memory_trace_and_flushes_ledger(tmp_path):
    state, issues = tmp_path / "state", tmp_path / "issues"
    issues.mkdir()
    for i in range(1, 25):
        (issues / f"{i:03d}.json").write_text(json.dumps({"id": i, "title": f"[bug] item {i}", "body": ""}))

    runner = Runner(state, issues_dir=issues)
    rep = runner.run(30, save_every=10)
    assert rep["issues_labelled"] == 24
    assert runner.kernel.trace == []  # drained cleanly to trace.jsonl
    assert (state / "trace.jsonl").read_text().count("\n") > 50
    ledger_disk = json.loads((state / "ledger.json").read_text())
    assert len(ledger_disk["issues"]) == 24


def test_perception_bounded_seen_and_total_count():
    p = Perception(max_seen=5)
    k = big_bang(p, fuel=100.0, regen=10.0)
    for i in range(1, 9):
        k.inject("world.issue", {"id": i, "title": f"issue {i}", "body": ""})
        k.step()
    k.step()
    assert len(p.memory["seen"]) == 5
    assert p.memory["seen"] == [4, 5, 6, 7, 8]
    assert p.memory["seen_total"] == 8

    # Duplicate of older evicted id still runs cleanly; recent id 8 is dropped
    k.inject("world.issue", {"id": 8, "title": "dup", "body": ""})
    k.run(2)
    assert p.memory["dropped"] == 1
    assert p.memory["seen_total"] == 8


def test_sigterm_triggers_orderly_halt_and_save(tmp_path):
    state = tmp_path / "state"
    runner = Runner(state)
    # Trigger SIGTERM on tick 2 by sending signal to self inside step
    orig_step = runner.kernel.step

    def step_then_sigterm():
        orig_step()
        if runner.kernel.tick == 2:
            signal.raise_signal(signal.SIGTERM)

    runner.kernel.step = step_then_sigterm  # type: ignore[method-assign]
    rep = runner.run(10)
    assert rep["halted"] is True
    assert rep["tick"] == 2
    assert json.loads((state / "snapshot.json").read_text())["halted"] is True
