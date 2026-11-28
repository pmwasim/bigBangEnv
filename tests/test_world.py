"""Tests for ADR-0018: SharedWorld topology, Locality, finite resources, and HTTP daemon."""

import threading

from bigbang.apps.caretaker import Host, Ledger
from bigbang.body import Genome, build_body
from bigbang.runtime import Runner
from bigbang.world import SharedWorld, WorldClient, make_world_server


def test_shared_world_locality_movement_and_persistence(tmp_path):
    state_file = tmp_path / "world.json"
    w = SharedWorld(state_path=state_file)
    w.enter("body-a", role="sentinel", zone="alpha-sector")
    w.enter("body-b", role="executor", zone="beta-sector")
    ent = w.spawn_entity("beta-sector", title="[feature] world artifact", body="needs sync")

    # Body A in alpha-sector cannot teleport directly to beta-sector (not adjacent)
    assert w.move("body-a", "beta-sector")["moved"] is False
    # Body A cannot sense beta-sector entities from alpha-sector
    assert w.sense("body-a")["objects"] == []
    assert len(w.sense("body-b")["objects"]) == 1

    # Moving via topological path alpha-sector -> hub -> beta-sector reveals both peer & entity
    assert w.move("body-a", "hub")["moved"] is True
    assert w.move("body-a", "beta-sector")["moved"] is True
    sensed = w.sense("body-a")
    assert len(sensed["objects"]) == 1
    assert sensed["peers"][0]["body_id"] == "body-b"

    # Persistence round-trip preserves entities, locations, and tick
    w.step(3)
    w2 = SharedWorld(state_path=state_file)
    assert w2.tick == 3
    assert w2.bodies["body-a"]["zone"] == "beta-sector"
    assert ent.entity_id in w2.entities


def test_shared_world_finite_energy_entropy_and_locality_guard():
    w = SharedWorld()
    w.enter("body-a", role="sentinel", zone="frontier")
    ent_alpha = w.spawn_entity("alpha-sector", title="[bug] remote")
    ent_front = w.spawn_entity("frontier", title="[bug] local anomaly", ttl=10)

    # Cannot act on entity outside current Zone
    bad = w.act("body-a", ent_alpha.issue_id, verb="label", label="bug")
    assert bad["ok"] is False
    assert bad["reason"] == "locality_violation"

    # Harvest draws finite energy; cannot harvest more than zone reserve
    taken = w.harvest("body-a", 500.0)
    assert taken == 500.0
    assert w.zones["frontier"].energy_reserve == 100.0
    more = w.harvest("body-a", 500.0)
    assert more == 100.0
    assert w.zones["frontier"].energy_reserve == 0.0

    # Acting mutates shared WorldEntity and emits ambient entropy
    res = w.act("body-a", ent_front.issue_id, verb="label", label="bug")
    assert res["ok"] is True
    assert w.zones["frontier"].ambient_entropy == 0.25
    w.step(1)
    assert w.zones["frontier"].energy_reserve == w.zones["frontier"].regen_rate


def test_http_world_server_connects_runner_organisms(tmp_path):
    world = SharedWorld(state_path=tmp_path / "world.json")
    srv = make_world_server(world, host="127.0.0.1", port=0)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    url = f"http://127.0.0.1:{port}"
    try:
        client = WorldClient(url)
        spawned = client.spawn_entity("alpha-sector", kind="incident", title="[bug] live world alert", body="disk")
        runner = Runner(
            tmp_path / "body_state",
            config={"organism": "body", "role": "sentinel"},
            world_url=url,
            world_zone="alpha-sector",
        )
        rep = runner.run(8)
        assert rep["issues_labelled"] == 1
        snap = client.summary()
        assert "body-sentinel" in snap["bodies"]
        assert snap["bodies"]["body-sentinel"]["actions_completed"] == 1
        ent = world.entities[spawned["entity_id"]]
        assert ent.state == "labelled"
        assert ent.labels == ["bug"]
    finally:
        srv.shutdown()
        srv.server_close()


def test_shared_world_doors_competitions_rewards_and_punishments(tmp_path):
    w = SharedWorld(state_path=tmp_path / "world3d.json")
    w.enter("bb-gamma-scout", role="scout", zone="frontier")
    w.enter("bb-gamma-arbiter", role="arbiter", zone="playground")
    assert "playground" in w.zones
    assert w.zones["hub"].x == 0.0 and w.zones["playground"].y > 0.0

    # Moving across adjacent playground <-> hub doorway tracks door crossings
    mv = w.move("bb-gamma-scout", "playground")
    assert mv["moved"] is True
    assert mv["door"] == "door:frontier:playground"
    assert w.doors["door:frontier:playground"]["crossings"] == 1

    # Competition, reward, and punishment
    comp = w.start_competition("Harmony Trial", kind="harmony_trial", duration=4)
    assert comp["status"] == "active"
    rew = w.award_reward("bb-gamma-scout", honor=2, reason="swift pathfinding")
    assert rew["ok"] is True
    assert w.bodies["bb-gamma-scout"]["honor"] == 2

    pun = w.apply_punishment("bb-gamma-scout", penalty=3, reason="rushed past a quiet gate", guard_door=True)
    assert pun["ok"] is True
    assert w.bodies["bb-gamma-scout"]["honor"] == -1
    assert w.bodies["bb-gamma-scout"]["penance_ticks"] >= 4
    blocked = w.move("bb-gamma-scout", "hub")
    assert blocked["moved"] is False

    # Advancing steps settles penance & completes the trial
    w.step(5)
    assert w.bodies["bb-gamma-scout"]["penance_ticks"] == 0
    assert w.competition is not None and w.competition["status"] == "completed"
    assert w.competition["winner"] is not None

    # Persistence round-trip preserves 3D doors, competition, and rewards_log
    w2 = SharedWorld(state_path=tmp_path / "world3d.json")
    assert w2.competition is not None and w2.competition["status"] == "completed"
    assert len(w2.rewards_log) >= 2


def test_shared_world_choreograph_and_door_toggle():
    w = SharedWorld()
    w.enter("bb-gamma-scout", role="scout", zone="frontier")
    w.enter("bb-gamma-weaver", role="weaver", zone="hub")
    w.enter("bb-beta-planner", role="planner", zone="beta-sector")

    # Toggle door open <-> guarded
    t1 = w.toggle_door("door:hub:playground")
    assert t1["ok"] is True and t1["door"]["state"] == "guarded"
    t2 = w.toggle_door("door:hub:playground")
    assert t2["ok"] is True and t2["door"]["state"] == "open"

    # Run choreograph across several ticks and confirm autonomous trial & movement
    seen_actions: list[str] = []
    for _ in range(12):
        w.step(1)
        res = w.choreograph()
        seen_actions.extend(res["actions"])

    assert w.competition is not None
    assert any(a.startswith("move:") for a in seen_actions)
    assert any(d["crossings"] > 0 for d in w.doors.values())
