"""Tests for ADR-0014: Chemical bonding, activation energy, catalysis, equilibrium, and pH."""

from bigbang.body import CORRELATE_REACTION, body_report, build_body
from bigbang.chemistry import Catalyst, Reaction, ReactionChamber, toxicity_ph
from bigbang.signal import Trust


def test_stoichiometric_bonding_and_conservation():
    """Partial reagents wait in the chamber until balanced stoichiometry is satisfied."""
    chamber = ReactionChamber()
    chamber.add_reagent("symptom", {"id": 1, "title": "[bug] crash"}, trust=Trust.USER, risk=0.2, tick=0, ttl=10)

    # Unbalanced: only symptom present, context missing
    products, spent = chamber.step_reaction(CORRELATE_REACTION, tick=0, available_energy=10.0)
    assert products == []
    assert spent == 0.0
    assert len(chamber.reagents["symptom"]) == 1

    # Add missing context with lower trust and higher risk
    chamber.add_reagent("context", {"title": "stack trace"}, trust=Trust.WORLD, risk=0.7, tick=1, ttl=10)
    products, spent = chamber.step_reaction(CORRELATE_REACTION, tick=1, available_energy=10.0)
    assert len(products) == 1
    assert spent == CORRELATE_REACTION.activation_energy
    # Trust degrades to min(USER, WORLD) == WORLD; Risk preserves max == 0.7; reagents consumed
    assert products[0].trust == Trust.WORLD
    assert products[0].value["risk"] == 0.7
    assert products[0].value["product"] == "correlated_issue"
    assert len(chamber.reagents.get("symptom", [])) == 0
    assert len(chamber.reagents.get("context", [])) == 0


def test_reagent_ttl_decay_prevents_stale_bonding():
    """Expired reagents decay out of the chamber before a late partner arrives."""
    chamber = ReactionChamber()
    chamber.add_reagent("symptom", {"id": 2, "title": "old"}, trust=Trust.WORLD, risk=0.1, tick=0, ttl=2)
    chamber.add_reagent("context", {"title": "late"}, trust=Trust.WORLD, risk=0.1, tick=3, ttl=5)

    products, spent = chamber.step_reaction(CORRELATE_REACTION, tick=3, available_energy=10.0)
    assert products == []
    assert spent == 0.0
    assert chamber.reagents.get("symptom", []) == []


def test_activation_energy_barrier_and_zero_consumption_catalysis():
    """Insufficient energy blocks reaction until a catalyst lowers Ea without being consumed."""
    chamber = ReactionChamber()
    rxn = Reaction("tight", {"a": 1, "b": 1}, "ab", activation_energy=4.0)
    chamber.add_reagent("a", 1, trust=Trust.USER, risk=0.0, tick=0)
    chamber.add_reagent("b", 2, trust=Trust.USER, risk=0.0, tick=0)

    # Energy 3.0 < Ea 4.0 -> reaction stalls
    products, spent = chamber.step_reaction(rxn, tick=0, available_energy=3.0)
    assert products == []
    assert spent == 0.0

    # Add catalyst reducing Ea by 50% (to 2.0) -> succeeds with 3.0 energy
    chamber.add_catalyst(Catalyst("enzyme_x", "tight", ea_reduction=0.5))
    products, spent = chamber.step_reaction(rxn, tick=1, available_energy=3.0)
    assert len(products) == 1
    assert spent == 2.0
    # Catalyst remains unconsumed and can catalyze again
    assert "enzyme_x" in chamber.catalysts


def test_le_chatelier_saturation_backpressure():
    """High product concentration halts further forward reactions and increases pressure below cap."""
    chamber = ReactionChamber()
    rxn = Reaction("saturate", {"x": 1}, "p", activation_energy=1.0, max_product_concentration=2)
    chamber.add_reagent("x", 1, trust=Trust.OPERATOR, risk=0.0, tick=0)

    products, spent = chamber.step_reaction(rxn, tick=0, available_energy=10.0, product_concentration=2)
    assert products == []
    assert spent == 0.0
    assert len(chamber.reagents["x"]) == 1

    # Below capacity (1/2 full), reaction proceeds with Le Chatelier backpressure (1.0 * 1.5)
    products, spent = chamber.step_reaction(rxn, tick=1, available_energy=10.0, product_concentration=1)
    assert len(products) == 1
    assert spent == 1.5


def test_toxicity_ph_scales_from_clean_to_toxic():
    assert toxicity_ph(0, 10) == 0.0
    assert toxicity_ph(5, 5) == 0.5
    assert toxicity_ph(10, 0) == 1.0


def test_body_synthesis_cell_bonds_reagents_and_registers_catalysts():
    """End-to-end: world.reagent (symptom + context) -> SynthesisCell -> Reflex -> Motor -> Ledger."""
    kernel, ledger, genome, organs = build_body({"role": "chemist"})

    # Operator/Myelin catalysis registers a persistent zero-consumption catalyst
    kernel.inject("chemistry.catalyze", {"sig_id": 77}, trust=Trust.OPERATOR)
    kernel.run(1)

    # Partial symptom reagent enters perception.synthesis without triggering action
    kernel.inject(
        "world.reagent",
        {"kind": "symptom", "id": 101, "title": "[bug] kernel panic", "body": "OOM"},
        trust=Trust.WORLD,
        risk=0.4,
    )
    kernel.run(2)
    assert not ledger.data["issues"]

    # Matching context reagent completes stoichiometry at catalyzed Ea (0.5) -> labelled "bug"
    kernel.inject(
        "world.reagent",
        {"kind": "context", "title": "backtrace", "body": "oom_kill+0x12"},
        trust=Trust.WORLD,
        risk=0.6,
    )
    kernel.run(5)
    assert ledger.data["issues"]["101"]["labels"] == ["bug"]
    rep = body_report(kernel, ledger, genome, organs)
    assert rep["chemistry"]["synthesized"] == 1
    assert rep["chemistry"]["catalysts"] == 1
    assert rep["chemistry"]["enthalpy"] == 0.5
    assert rep["chemistry"]["toxicity_ph"] == 0.0
