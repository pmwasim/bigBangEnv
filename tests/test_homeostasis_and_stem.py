"""Tests for ADR-0015: Stem cell mitosis, programmed apoptosis, catabolism, and homeostasis."""

import dataclasses
from bigbang import Cell, Kernel, Trust, big_bang
from bigbang.body import BurstWorker, DeliberationStem, body_report, build_body
from bigbang.matter import MatterStore
from bigbang.runtime import replay, Runner


def test_stem_mitosis_and_apoptosis_conserve_fuel_and_trust():
    """Stem division debits parent fuel, caps trust/declassify, and returns unused fuel on apoptosis."""

    class OneShotWorker(Cell):
        lineage = "housekeeping"
        subscriptions = ("work",)
        step_cost = 0.5

        def step(self, ctx):
            if ctx.inbox:
                ctx.emit("_organ.lab.done", "ok")
            else:
                ctx.apoptosis("done")

    class LabStem(Cell):
        lineage = "stem"
        step_cost = 0.5

        def step(self, ctx):
            if ctx.tick == 1:
                w = OneShotWorker("w1", trust=Trust.OWNER, declassify=True, emits=["_organ.lab.done"])
                assert ctx.spawn_worker(w, fuel=10.0, reason="unit_test")
                # Non-ephemeral parent cannot apoptosis
                assert ctx.apoptosis() is False

    kernel = Kernel()
    stem = LabStem("stem", trust=Trust.USER, organ="lab")
    kernel.spawn(stem, fuel=50.0, regen=0.0)

    # Normal cells cannot spawn workers
    class Normal(Cell):
        lineage = "generic"

        def step(self, ctx):
            assert ctx.spawn_worker(OneShotWorker("illegal"), fuel=5.0) is False

    kernel.spawn(Normal("normal", organ="lab"), fuel=20.0)
    kernel.inject("work", 1, trust=Trust.USER)
    kernel.run(3)

    assert "w1" not in kernel.cells
    assert "w1" not in kernel.ephemeral
    # Parent started at 50, spent 0.5*3=1.5 step cost, donated 10 -> w1 spent 0.5*2 + 1 emit = 2 -> 8 reclaimed!
    events = [e for e in kernel.trace if e["event"] in ("mitosis", "apoptosis")]
    assert [e["event"] for e in events] == ["mitosis", "apoptosis"]
    assert events[1]["reclaimed"] == 8.0
    assert kernel.budgets["stem"].remaining > 45.0


def test_catabolism_recovers_fuel_in_sleep_rem_bounded_by_capacity():
    """Decaying molecules during SLEEP_REM trigger exothermic catabolism without exceeding budget cap."""
    kernel, ledger, genome, organs = build_body({"role": "catabolic"})
    con = kernel.cells["memory.consolidator"]
    # Seed expired WORLD molecules directly into MemoryConsolidator and record mild spend
    store = MatterStore()
    for i in range(4):
        store.put(f"noise:{i}", {"i": i}, trust=Trust.WORLD, tick=0, ttl=2)
    con.memory["molecules"] = store.to_list()
    kernel.budgets["memory.consolidator"].spent = 10.0

    # 12 ticks idle puts organism into SLEEP_REM -> consolidator prunes expired molecules & recovers fuel
    kernel.run(14)
    assert kernel.operating_mode == "SLEEP_REM"
    rep = body_report(kernel, ledger, genome, organs)
    assert rep["homeostasis"]["catabolized_fuel"] > 0.0
    assert kernel.budgets["memory.consolidator"].remaining <= kernel.budgets["memory.consolidator"].capacity


def test_body_burst_stem_spawns_and_reclaims_cleanly(tmp_path):
    """Urgency burst triggers DeliberationStem mitosis; runner persistence & replay remain identical."""
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir()
    for i in range(1, 25):
        (issues_dir / f"{i:03d}.json").write_text(
            f'{{"id": {i}, "title": "Shard timeout {i}?", "body": "exception trace {i}"}}'
        )

    runner = Runner(
        tmp_path / "state",
        config={
            "organism": "body",
            "role": "burst",
            "fuel": 5000.0,
            "regen": 20.0,
            "reasoner_fuel": 5000.0,
            "reasoner_regen": 20.0,
        },
        issues_dir=issues_dir,
    )
    rep = runner.run(30)
    assert rep["issues_labelled"] == 24
    assert rep["homeostasis"]["mitoses"] >= 1
    assert rep["homeostasis"]["apoptoses"] >= 1
    assert rep["homeostasis"]["active_ephemeral"] == 0

    ok, detail = replay(tmp_path / "state")
    assert ok, detail
