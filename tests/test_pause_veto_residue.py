"""Laws from the PR #1 review: inhibition pauses, vetoes are targeted, taint lives in matter."""

from bigbang import Cell, Trust, big_bang
from bigbang.apps.caretaker import Host, Ledger, build
from bigbang.lineages import Defense, Motor


class Recorder(Cell):
    def __init__(self, name, topics=("in",), **kw):
        super().__init__(name, **kw)
        self.subscriptions = tuple(topics)
        self.memory["seen"] = []

    def step(self, ctx):
        for s in ctx.inbox:
            self.memory["seen"].append([ctx.tick, s.topic, s.payload, s.trust.name])


class OnTick(Cell):
    """Runs ``action(ctx)`` on one tick only."""

    def __init__(self, name, tick, action, **kw):
        super().__init__(name, **kw)
        self.at, self.action = tick, action

    def step(self, ctx):
        if self.at is None or ctx.tick == self.at:
            self.action(ctx)


def run(kernel, host, ticks):
    for _ in range(ticks):
        host.poll(kernel)
        kernel.step()


# ------------------------------------------------------- inhibition pauses
def test_inhibition_holds_pending_signals_until_it_lifts():
    guard = OnTick("a_guard", 1, lambda ctx: ctx.inhibit("in", ttl=5, reason="pause"))
    rec = Recorder("z_rec")
    k = big_bang(guard, rec)
    k.run(1)  # inhibition is live from tick 2 to tick 6
    k.inject("in", "later", ttl=2)  # would expire long before the pause ends if held time counted
    k.run(3)
    assert rec.memory["seen"] == []
    assert any(e["event"] == "hold" for e in k.trace)
    assert not any(e["event"] in ("cancel", "expire") for e in k.trace)
    k.run(6)
    assert [s[2] for s in rec.memory["seen"]] == ["later"]
    assert rec.memory["seen"][0][0] == 7  # first tick after the inhibition expired


def test_veto_cancels_only_the_named_signal():
    ids = {}
    script = {
        1: lambda ctx: ctx.inhibit("in", ttl=3, reason="pause"),  # live ticks 2-4
        2: lambda ctx: ctx.veto("in", [ids["bad"]], reason="no"),  # live from tick 3
    }
    guard = OnTick("a_guard", None, lambda ctx: script.get(ctx.tick, lambda c: None)(ctx))
    rec = Recorder("z_rec")
    k = big_bang(guard, rec)
    k.run(1)
    ids["bad"] = k.inject("in", "bad").id
    k.inject("in", "good")
    k.run(2)
    assert k.is_vetoed(ids["bad"], "in")
    k.run(4)
    assert not k.is_inhibited("in")  # a veto never quiets the whole topic
    assert [s[2] for s in rec.memory["seen"]] == ["good"]
    assert [e["id"] for e in k.trace if e["event"] == "cancel"] == [ids["bad"]]


# ---------------------------------------------------- taint lives in matter
class Hoarder(Cell):
    """Stores whatever it hears and emits it on a later, empty-inbox tick."""

    subscriptions = ("in",)

    def __init__(self, name, **kw):
        kw.setdefault("emits", ["out"])
        super().__init__(name, **kw)
        self.memory["kept"] = []
        self.memory["trust_seen"] = []

    def step(self, ctx):
        self.memory["trust_seen"].append(ctx.trust.name)
        self.memory["kept"] += [s.payload for s in ctx.inbox]
        if not ctx.inbox and self.memory["kept"]:
            ctx.emit("out", self.memory["kept"].pop())


def test_stored_world_input_keeps_its_taint_on_a_later_tick():
    hoarder, rec = Hoarder("hoarder"), Recorder("rec", topics=("out",))
    k = big_bang(hoarder, rec)
    k.require("out", Trust.OPERATOR)
    k.inject("in", {"issue": 1}, trust=Trust.WORLD)
    k.run(4)
    assert rec.memory["seen"] == []  # laundering through memory used to emit this at OPERATOR
    assert hoarder.memory["trust_seen"][1:] == ["WORLD"] * 3
    assert any(e["event"] == "blocked" and e["topic"] == "out" for e in k.trace)


def test_taint_residue_survives_snapshot_and_restore():
    def boot():
        hoarder, rec = Hoarder("hoarder"), Recorder("rec", topics=("out",))
        k = big_bang(hoarder, rec)
        k.require("out", Trust.OPERATOR)
        return k

    k = boot()
    k.inject("in", "world text", trust=Trust.WORLD)
    k.run(1)
    snap = k.snapshot()
    k2 = boot()
    k2.restore(snap)
    k2.run(3)
    assert k2.cells["rec"].memory["seen"] == []


def test_taint_is_not_kept_when_the_step_is_rolled_back():
    class Crasher(Cell):
        subscriptions = ("in",)

        def step(self, ctx):
            raise RuntimeError("boom")

    k = big_bang(Crasher("crasher"))
    k.inject("in", "world text", trust=Trust.WORLD)
    k.run(2)
    assert k.taint.get("crasher", Trust.OPERATOR) == Trust.OPERATOR


def test_caretaker_never_re_emits_issue_text_above_world():
    # Starve reflex so issues wait in its backlog and leave on later ticks.
    kernel, _ = build()
    kernel.budgets["reflex"].capacity, kernel.budgets["reflex"].regen = 6.0, 2.0
    issues = [{"id": i, "title": f"plain issue {i}", "body": ""} for i in range(1, 30)]
    run(kernel, Host(issues=issues), 60)
    reflex_novel = [e for e in kernel.trace if e["event"] == "emit" and e["sender"] == "reflex"]
    assert len(reflex_novel) == 29 and kernel.cells["reflex"].memory["max_backlog"] > 0
    emits = [e for e in kernel.trace if e["event"] == "emit" and e["topic"] in ("issue.new", "issue.novel")]
    assert emits and {e["trust"] for e in emits} == {"WORLD"}


def test_owner_commands_still_work_after_world_input_on_the_command_topic():
    # Without a receptor, the WORLD command would leave a residue that blocks every later one.
    kernel, ledger = build()
    kernel.inject("owner.command", "close 1", trust=Trust.WORLD)
    kernel.run(3)
    kernel.inject("owner.command", "close 2", trust=Trust.OWNER, sender="owner")
    kernel.run(5)
    assert ledger.data["issues"]["2"]["closed"] is True
    assert "1" not in ledger.data["issues"]
    assert "commander" not in kernel.taint
    assert any(e["event"] == "blocked" and e.get("why") == "receptor" for e in kernel.trace)


# --------------------------------------------- lockdown pauses, never destroys
def test_lockdown_pauses_owner_commands_and_triage_instead_of_destroying_them():
    kernel, ledger = build()
    host = Host(
        commands=[f"close {n}" for n in range(1, 26)],
        issues=[{"id": 100 + n, "title": f"[bug] crash {n}", "body": ""} for n in range(1, 4)],
    )
    run(kernel, host, 80)
    issues = ledger.data["issues"]
    assert kernel.cells["defense"].memory["lockdowns"] >= 1
    assert sum(1 for n in range(1, 26) if issues[str(n)]["closed"]) == 25
    assert all(issues[str(100 + n)]["labels"] == ["bug"] for n in range(1, 4))
    assert kernel.cells["motor"].memory["vetoed"] == 0
    assert not any(e["event"] == "cancel" for e in kernel.trace)


def test_paused_actions_resume_at_a_graded_pace():
    ledger = Ledger()
    guard = OnTick("a_guard", 1, lambda ctx: ctx.inhibit("action.*", ttl=4, reason="lockdown"))
    motor = Motor("motor", ledger.effectors(), resume_per_tick=2)
    k = big_bang(guard, motor)
    for n in range(6):
        k.inject("action.close", {"issue": n}, trust=Trust.OPERATOR)
    k.run(1)  # motor receives all six at tick 1; the lockdown starts at tick 2
    per_tick = []
    for _ in range(12):
        before = motor.memory["executed"]
        k.step()
        per_tick.append(motor.memory["executed"] - before)
    assert sum(per_tick) == 6
    assert max(per_tick) <= 2


def test_paused_actions_resume_no_faster_than_a_sub_one_per_tick_rate():
    # PR #3 review (Codex): a rate below one per tick was rounded up to one per tick.
    ledger = Ledger()
    guard = OnTick("a_guard", 1, lambda ctx: ctx.inhibit("action.*", ttl=4, reason="lockdown"))
    motor = Motor("motor", ledger.effectors(), resume_per_tick=0.2)  # one per five ticks
    k = big_bang(guard, motor)
    for n in range(4):
        k.inject("action.close", {"issue": n}, trust=Trust.OPERATOR)
    k.run(1)
    per_tick = []
    for _ in range(30):
        before = motor.memory["executed"]
        k.step()
        per_tick.append(motor.memory["executed"] - before)
    assert sum(per_tick) == 4
    assert all(sum(per_tick[i:i + 5]) <= 1 for i in range(len(per_tick)))


def test_caretaker_resume_rate_follows_a_slow_defense_limit():
    kernel, _ = build({"defense": {"max_actions": 1, "window": 5, "max_repeats": 2, "lockdown_ttl": 10}})
    assert kernel.cells["motor"].resume_per_tick == 0.2


def test_motor_gives_up_on_a_pause_after_its_patience_and_says_so():
    ledger = Ledger()
    guard = OnTick("a_guard", 1, lambda ctx: ctx.inhibit("action.*", ttl=50, reason="lockdown"))
    motor = Motor("motor", ledger.effectors(), patience=5)
    k = big_bang(guard, motor)
    k.inject("action.close", {"issue": 1}, trust=Trust.OPERATOR)
    k.run(12)
    assert ledger.data["history"] == []
    assert motor.memory["expired"] == 1
    assert any(e["event"] == "emit" and e["payload"].get("status") == "expired"
               for e in k.trace if e.get("topic") == "outcome.close")


def test_forbidden_verbs_never_run_even_after_a_lockdown_lifts():
    calls = []
    defense = Defense("defense", forbidden=("delete",), max_actions=1, window=5, lockdown_ttl=3)
    motor = Motor("motor", {"delete": lambda p: calls.append(p) or {}, "close": lambda p: {}})
    k = big_bang(defense, motor)
    k.inject("action.close", {"issue": 1}, trust=Trust.OPERATOR)
    k.inject("action.delete", {"issue": 2}, trust=Trust.OPERATOR)  # 2 > max_actions: lockdown too
    k.run(20)
    assert calls == []
    assert motor.memory["vetoed"] == 1
    assert motor.memory["executed"] == 1  # the close resumes after the lockdown


def test_snapshots_from_before_adr_0010_still_resume():
    # PR #3 review (Codex): restored Defense/Motor memory lacked the new fields, so
    # their first step raised and the kernel quarantined them.
    kernel, ledger = build()
    snap = kernel.snapshot()
    defense = snap["cells"]["defense"]["memory"]
    motor = snap["cells"]["motor"]["memory"]
    defense.pop("vetoed_ids")
    defense["recent"] = [[0, "action.close", '{"issue": 1}']]  # old 3-field entry
    for key in ("expired", "resumed"):
        motor.pop(key)
    motor["pending"] = [[1, "action.close", {"issue": 7}]]  # old 3-field entry
    fresh, ledger = build()
    fresh.restore(snap)
    run(fresh, Host(commands=["label 3 bug"] * 3), 10)
    assert fresh.quarantined == set()
    assert ledger.data["issues"]["7"]["closed"] is True
    assert ledger.data["issues"]["3"]["labels"] == ["bug"]


def test_a_veto_stays_final_for_a_motor_that_slept_through_it():
    # PR #3 review (Codex): a dormant Motor missed the timed veto and ran the action on waking.
    calls = []
    defense = Defense("defense", forbidden=("delete",), window=3)
    motor = Motor("motor", {"delete": lambda p: calls.append(p) or {}})
    k = big_bang(defense, motor)
    k.inject("action.delete", {"issue": 2}, trust=Trust.OPERATOR)
    k.run(1)  # both receive it at tick 1; Defense vetoes it
    k.dormant.add("motor")  # Motor sleeps through the veto's whole life
    k.budgets["motor"].spent = k.budgets["motor"].capacity
    k.run(10)
    k.revive("motor", refuel=100.0)
    k.run(5)
    assert calls == []
    assert motor.memory["vetoed"] == 1


def test_veto_record_survives_snapshot_and_restore():
    def boot():
        return big_bang(Defense("defense", forbidden=("delete",), window=3),
                        Motor("motor", {"delete": lambda p: {}}))

    k = boot()
    sig = k.inject("action.delete", {"issue": 2}, trust=Trust.OPERATOR)
    k.run(8)  # the veto signal has long expired
    k2 = boot()
    k2.restore(k.snapshot())
    assert k2.is_vetoed(sig.id, "action.delete")


def test_legacy_recent_entries_count_toward_the_repeat_limit():
    defense = Defense("defense", max_repeats=2, window=5)
    k = big_bang(defense)
    body = '{"issue": 1, "label": "bug"}'
    defense.memory["recent"] = [[0, "action.label", body], [0, "action.label", body]]  # pre-ADR-0010
    sig = k.inject("action.label", {"issue": 1, "label": "bug"}, trust=Trust.OPERATOR)
    k.run(2)
    assert k.is_vetoed(sig.id, "action.label")


# ------------------------------------------ the loop breaker is scoped
def test_loop_breaker_stops_only_the_repeated_action():
    kernel, ledger = build()
    host = Host(commands=["label 9 bug"] * 3)
    host.poll(kernel)
    kernel.step()
    kernel.step()
    host.state["pending"].append({"id": 10, "title": "[docs] typo", "body": ""})
    run(kernel, host, 30)
    issues = ledger.data["issues"]
    assert issues["9"]["labels"] == ["bug"]
    assert issues["10"]["labels"] == ["docs"]
    assert kernel.cells["defense"].memory["vetoes"] >= 1  # the third repeat was still stopped
    assert kernel.cells["motor"].memory["vetoed"] == 1


def test_a_runaway_loop_is_still_broken():
    calls = []
    defense = Defense("defense", max_repeats=2, window=5)
    motor = Motor("motor", {"label": lambda p: calls.append(p) or {}})

    class Loop(Cell):
        def __init__(self, name, **kw):
            kw.setdefault("emits", ["action.label"])
            super().__init__(name, **kw)

        def step(self, ctx):
            ctx.emit("action.label", {"issue": 1, "label": "bug"})

    k = big_bang(defense, Loop("loop"), motor, fuel=1000.0)
    k.run(20)
    assert len(calls) < 10  # far fewer than the ~19 it asked for
    assert motor.memory["vetoed"] >= 5
