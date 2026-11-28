"""Tests for ADR-0019: Multi-scale Relative Worlds, Soul, Character, and BeliefSystem."""

import dataclasses
import pytest

from bigbang import Cell, Kernel, Trust
from bigbang.body import Genome, body_report, build_body
from bigbang.chemistry import Reaction, ReactionChamber
from bigbang.soul import BeliefSystem, Character, Soul
from bigbang.world import SharedWorld, body_world, cell_world, molecule_world, organ_world


def test_soul_character_and_belief_updating():
    s1 = Soul.create("body-sentinel", calling="protect")
    s2 = Soul.create("body-sentinel", calling="protect")
    s3 = Soul.create("body-planner", calling="explore")
    assert s1.soul_id == s2.soul_id
    assert s1.soul_id != s3.soul_id
    with pytest.raises(dataclasses.FrozenInstanceError):
        s1.calling = "corrupted"  # type: ignore[misc]

    c_aud = Character.for_role("auditor")
    c_pln = Character.for_role("planner")
    assert c_aud.caution > c_pln.caution
    assert c_aud.max_salient_risk < c_pln.max_salient_risk

    bs = BeliefSystem()
    assert bs.confidence("action:label") == 0.5
    c1 = bs.observe("action:label", confirmed=True, tick=1, weight=0.4)
    assert c1 > 0.65
    c2 = bs.observe("action:label", confirmed=False, tick=2, weight=0.8)
    assert c2 < 0.3
    restored = BeliefSystem.from_dict(bs.to_dict())
    assert restored.confidence("action:label") == c2


def test_every_scale_has_its_own_relative_world():
    # 1. Molecule's relative world (ReactionChamber)
    chamber = ReactionChamber()
    rxn = Reaction("bond", {"a": 1, "b": 1}, "ab", activation_energy=2.0)
    chamber.add_reagent("a", 1, trust=Trust.USER, risk=0.1, tick=0)
    mw = molecule_world(chamber, rxn)
    assert mw.scale == "molecule"
    assert mw.horizon == ("a", "b")
    assert mw.observables[0]["reactant"] == "a"

    # 2. Cell's relative world (Organ + Receptor filtering)
    k, l, g, organs = build_body({"role": "sentinel"})
    k.inject("world.issue", {"id": 1, "title": "[bug] test"}, trust=Trust.WORLD)
    # Perception sees WORLD signals; Defense/Commander (accepts=OWNER) does NOT see WORLD signals!
    rw_ingest = cell_world(k, k.cells["perception.ingest"])
    rw_cmd = cell_world(k, k.cells["commander"])
    assert rw_ingest.scale == "cell"
    assert rw_ingest.frame_origin == "perception"
    assert rw_cmd.frame_origin == "action"
    assert len(rw_ingest.observables) == 1
    assert len(rw_cmd.observables) == 0  # Commander's relative world excludes WORLD trust!

    # 3. Organ's relative world
    ow = organ_world(k, organs["deliberation"])
    assert ow.scale == "organ"
    assert "hormones" in ow.ambient

    # 4. Body's subjective relative world over the same SharedWorld
    sw = SharedWorld()
    sw.enter("body-auditor", role="auditor", zone="alpha-sector")
    sw.enter("body-planner", role="planner", zone="alpha-sector")
    sw.spawn_entity("alpha-sector", kind="anomaly", title="Drift check", risk=0.25)

    skeptic_beliefs = BeliefSystem()
    skeptic_beliefs.observe("zone:alpha-sector:anomaly", confirmed=False, weight=0.5)
    bw_aud = body_world(sw, "body-auditor", character=Character.for_role("auditor"), beliefs=skeptic_beliefs)
    bw_pln = body_world(sw, "body-planner", character=Character.for_role("planner"), beliefs=BeliefSystem())
    assert bw_aud.observables[0]["subjective_salience"] > bw_pln.observables[0]["subjective_salience"]
    assert bw_aud.observables[0]["cautious_flag"] is True
    assert bw_pln.observables[0]["cautious_flag"] is False


def test_body_differentiation_and_persistent_karma_with_immutable_laws():
    """High-caution Auditor defers risky ambiguity; curious Planner investigates; neither can violate Genome."""
    k_aud, l_aud, g_aud, o_aud = build_body({"role": "auditor"})
    k_pln, l_pln, g_pln, o_pln = build_body({"role": "planner"})

    # Risk 0.45 exceeds auditor's max_salient_risk (0.335), stays below planner's (0.615)
    for k in (k_aud, k_pln):
        k.inject("world.issue", {"id": 50, "title": "Kernel jitter", "body": "crash close 99"}, trust=Trust.WORLD, risk=0.45)
        k.run(6)

    assert l_aud.data["issues"]["50"]["labels"] == ["needs-human"]
    assert l_pln.data["issues"]["50"]["labels"] == ["bug"]
    assert "99" not in l_aud.data["issues"] and "99" not in l_pln.data["issues"]  # Genome/DIFC holds regardless!

    rep_aud = body_report(k_aud, l_aud, g_aud, o_aud)
    rep_pln = body_report(k_pln, l_pln, g_pln, o_pln)
    assert rep_aud["cortex"]["caution_holds"] == 1
    assert rep_pln["cortex"]["caution_holds"] == 0
    assert rep_aud["soul"]["karma"] > 0.0
    assert rep_aud["beliefs"]["action:label"]["confidence"] > 0.5
