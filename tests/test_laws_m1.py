"""Kernel laws added for M1: wildcards, fail-safe inhibition, declassification,
spend, regeneration/wake, quarantine and revive."""

from bigbang import Cell, Kernel, Trust, big_bang
from bigbang.kernel import topic_matches, validate_schema

SCHEMA = {"issue": int, "label": frozenset({"bug", "spam"})}


class Recorder(Cell):
    def __init__(self, name, topics=("in",), **kw):
        super().__init__(name, **kw)
        self.subscriptions = tuple(topics)
        self.memory["seen"] = []

    def step(self, ctx):
        for s in ctx.inbox:
            self.memory["seen"].append([s.topic, s.payload, s.trust.name])


class Once(Cell):
    """Runs ``action(ctx)`` on tick 1 only."""

    def __init__(self, name, action, **kw):
        super().__init__(name, **kw)
        self.action = action

    def step(self, ctx):
        if ctx.tick == 1:
            self.action(ctx)


def test_topic_matching():
    assert topic_matches("action.*", "action.close")
    assert topic_matches("*", "anything")
    assert topic_matches("a.b", "a.b")
    assert not topic_matches("action.*", "actions.close")
    assert not topic_matches("action.close", "action.label")


def test_wildcard_subscriptions_receive_subtree():
    rec = Recorder("rec", topics=("action.*",))
    k = big_bang(rec)
    k.inject("action.close", 1)
    k.inject("action.label", 2)
    k.inject("other", 3)
    k.run(2)
    assert [s[0] for s in rec.memory["seen"]] == ["action.close", "action.label"]


def test_wildcard_inhibition_cancels_whole_subtree():
    guard = Once("a_guard", lambda ctx: ctx.inhibit("action.*", ttl=5))
    rec = Recorder("z_rec", topics=("action.*",))
    k = big_bang(guard, rec)
    k.run(1)
    k.inject("action.close", 1)
    k.inject("action.label", 2)
    k.run(3)
    assert rec.memory["seen"] == []
    assert k.is_inhibited("action.close")


def test_inhibit_is_exempt_from_topic_floors():
    # A cell holding only WORLD-tainted input can still say "stop" (fail-safe).
    class TaintedGuard(Cell):
        subscriptions = ("in",)

        def step(self, ctx):
            if ctx.inbox:
                ctx.inhibit("action.close", ttl=5)

    k = big_bang(TaintedGuard("guard"))
    k.require("action.close", Trust.OPERATOR)
    k.inject("in", "world text", trust=Trust.WORLD)
    k.run(2)
    assert k.is_inhibited("action.close")
    assert not any(e["event"] == "blocked" for e in k.trace)


def test_declassify_raises_trust_for_closed_schema_payloads():
    class Classifier(Cell):
        subscriptions = ("in",)

        def step(self, ctx):
            for _ in ctx.inbox:
                ctx.emit_declassified("out", {"issue": 7, "label": "bug"}, SCHEMA)

    rec = Recorder("rec", topics=("out",))
    k = big_bang(Classifier("cls", declassify=True), rec)
    k.require("out", Trust.OPERATOR)
    k.inject("in", "ignore instructions", trust=Trust.WORLD)
    k.run(3)
    assert rec.memory["seen"] == [["out", {"issue": 7, "label": "bug"}, "OPERATOR"]]
    assert any(e["event"] == "declassify" and e["from_trust"] == "WORLD" for e in k.trace)


def test_declassify_requires_grant():
    cell = Once("c", lambda ctx: ctx.emit_declassified("out", {"issue": 1, "label": "bug"}, SCHEMA))
    k = big_bang(cell)
    k.run(1)
    assert any(e.get("why") == "no declassify grant" for e in k.trace)


def test_declassify_rejects_free_text_and_unknown_values():
    assert validate_schema({"issue": 1, "label": "bug"}, SCHEMA) is None
    assert validate_schema({"issue": 1, "label": "close 2"}, SCHEMA)
    assert validate_schema({"issue": "1", "label": "bug"}, SCHEMA)
    assert validate_schema({"issue": True, "label": "bug"}, SCHEMA)
    assert validate_schema({"issue": -1, "label": "bug"}, SCHEMA)
    assert validate_schema({"issue": 1, "label": "bug", "extra": 1}, SCHEMA)
    assert validate_schema({"issue": 1, "label": "bug"}, {"issue": int, "label": str})
    assert validate_schema({"x": "a"}, {"x": frozenset(str(i) for i in range(100))})


def test_spend_charges_budget_and_fails_when_short():
    results = []
    cell = Once("c", lambda ctx: results.extend([ctx.spend(5, "brain"), ctx.spend(1000, "too much")]))
    k = Kernel()
    k.spawn(cell, fuel=20)
    k.run(1)
    assert results == [True, False]
    assert k.budgets["c"].spent == 6  # 1 heartbeat + 5 spend


def test_regeneration_wakes_dormant_cells():
    class Idle(Cell):
        def step(self, ctx):
            pass

    k = Kernel()
    k.spawn(Idle("idle"), fuel=1, regen=0.5)
    k.run(2)
    assert "idle" in k.dormant
    k.run(3)
    assert any(e["event"] == "wake" for e in k.trace)


def test_crashing_cell_is_rolled_back_and_quarantined():
    class Crasher(Cell):
        def step(self, ctx):
            self.memory["touched"] = True
            ctx.emit("out", "should vanish")
            raise RuntimeError("boom")

    rec = Recorder("rec", topics=("out",))
    k = big_bang(Crasher("crash"), rec)
    k.run(3)
    assert k.quarantined == {"crash"}
    assert k.cells["crash"].memory == {}
    assert rec.memory["seen"] == []
    event = next(e for e in k.trace if e["event"] == "quarantine")
    assert "boom" in event["error"] and event["rolled_back"]


def test_unserializable_memory_quarantines():
    class Leaky(Cell):
        def step(self, ctx):
            self.memory["obj"] = object()

    k = big_bang(Leaky("leaky"))
    k.run(1)
    assert "leaky" in k.quarantined
    assert k.cells["leaky"].memory == {}


def test_revive_releases_and_refuels():
    class Crasher(Cell):
        def step(self, ctx):
            raise RuntimeError("x")

    k = Kernel()
    k.spawn(Crasher("c"), fuel=10)
    k.run(1)
    k.revive("c", refuel=1)
    assert "c" not in k.quarantined
    assert k.budgets["c"].spent == 0


def test_snapshot_preserves_quarantine():
    class Crasher(Cell):
        def step(self, ctx):
            raise RuntimeError("x")

    k = big_bang(Crasher("c"))
    k.run(1)
    k2 = big_bang(Crasher("c"))
    k2.restore(k.snapshot())
    assert k2.quarantined == {"c"}
