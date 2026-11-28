"""Tests for ADR-0013: conserved charges, energy tensor, entropy, and the four forces."""

from __future__ import annotations

from bigbang import Cell, Kernel, Trust, big_bang
from bigbang.body import body_report, build_body
from bigbang.physics import ChargeVector, Coord, ForceTarget, gravitational_mass, select_target_by_forces


def test_risk_charge_conservation_and_max_risk_gate():
    seen = []

    class Relay(Cell):
        subscriptions = ("in",)

        def step(self, ctx):
            for s in ctx.inbox:
                # Tries to emit with risk=0.1, but incoming signal had risk=0.8 -> conserved!
                ctx.emit("out", s.payload, risk=0.1)

    class Receiver(Cell):
        subscriptions = ("out",)

        def step(self, ctx):
            seen.extend((s.payload, s.risk) for s in ctx.inbox)

    k = Kernel()
    k.require_max_risk("out", 0.5)
    k.spawn(Relay("a_relay"), fuel=100.0)
    k.spawn(Receiver("b_recv"), fuel=100.0)

    # Low-risk signal passes on its own tick
    k.inject("in", "safe", risk=0.2)
    k.run(2)
    # High-risk signal on a subsequent tick cannot be laundered down to 0.1 and is blocked at out
    k.inject("in", "dangerous", risk=0.8)
    k.run(2)

    assert seen == [("safe", 0.2)]
    assert any(e["event"] == "blocked" and e.get("topic") == "out" and e.get("risk") == 0.8 for e in k.trace)


def test_energy_tensor_entropy_and_condensation():
    class Worker(Cell):
        subscriptions = ("in",)

        def step(self, ctx):
            for _ in ctx.inbox:
                ctx.emit("forbidden", "x")  # denied -> raises entropy
                ctx.condense(2.0)

    k = Kernel()
    k.spawn(Worker("w", emits=["allowed"]), fuel=100.0, regen=2.0)
    k.inject("in", "go")
    k.run(1)

    phys = k.physics_summary()
    assert phys["kinetic"] > 0.0
    assert phys["entropy"] > 0.0
    assert phys["bound_mass"] == 2.0
    assert phys["gravitational_mass"] > 1.0

    # Snapshot + restore preserves kinetic, entropy, and bound_mass
    k2 = Kernel()
    k2.spawn(Worker("w", emits=["allowed"]), fuel=100.0, regen=2.0)
    k2.restore(k.snapshot())
    assert k2.physics_summary()["bound_mass"] == 2.0
    assert k2.physics_summary()["kinetic"] == phys["kinetic"]

    # Cooling over calm ticks dissipates entropy
    k.run(25)
    assert k.physics_summary()["entropy"] < phys["entropy"]


def test_four_force_em_repulsion_and_gravitational_routing():
    origin = Coord(0.0, 0.0, 2.0)
    wrong_flavor = ForceTarget("motor-near", Coord(0.5, 0.0, 2.0), "executor", 100.0, 0.0, 1.0)
    heavy_near = ForceTarget(
        "triage-near", Coord(1.0, 0.0, 2.0), "triage", 90.0, 3.0, gravitational_mass(8, 3.0)
    )
    light_mid = ForceTarget(
        "triage-mid", Coord(2.0, 0.0, 2.0), "triage", 100.0, 0.0, gravitational_mass(0, 0.0)
    )

    charge = ChargeVector(authority=Trust.WORLD, valence=1.0, risk=0.3, affinity="triage")
    chosen = select_target_by_forces(charge, [wrong_flavor, heavy_near, light_mid], origin=origin)
    # Wrong flavor is repelled by EM; heavy_near bends spacetime so light_mid wins
    assert chosen is not None
    assert chosen.name == "triage-mid"


def test_body_condenses_mass_on_consolidation_and_myelination():
    kernel, ledger, genome, organs = build_body({
        "role": "triage",
        "fuel": 5000.0,
        "regen": 20.0,
        "reasoner_fuel": 5000.0,
        "reasoner_regen": 20.0,
    })

    for i in range(1, 15):
        kernel.inject(
            "world.issue",
            {"id": i, "title": f"Database timeout on shard {i}", "body": f"crash error {i * 11}"},
            trust=Trust.WORLD,
        )
        kernel.step()
    kernel.run(15)

    rep = body_report(kernel, ledger, genome, organs)
    assert rep["physics"]["bound_mass"] >= 1.5
    assert rep["physics"]["kinetic"] > 0.0
