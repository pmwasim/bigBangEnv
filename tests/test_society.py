"""Tests for ADR-0016: Society Skin attestation, reputation, territory mutex, and backpressure."""

from bigbang.apps.caretaker import Host
from bigbang.body import Genome, body_report, build_body
from bigbang.cell import Cell
from bigbang.signal import Trust
from bigbang.society import ReputationLedger, Skin, TerritoryTable, WorldSociety, should_backpressure


def test_skin_seal_and_tamper_rejection():
    skin = Skin("body-a", "secret-a")
    env = skin.seal({"id": 1, "title": "hi"}, seq=1)
    assert Skin.verify(env, {"body-a": "secret-a"}) == (True, "ok")

    tampered = {**env, "payload": {"id": 1, "title": "evil"}}
    ok, _ = Skin.verify(tampered, {"body-a": "secret-a"})
    assert ok is False
    assert Skin.verify(env, {"body-b": "secret-b"}) == (False, "unknown sender")


def test_reputation_and_territory_mutex():
    rep = ReputationLedger(default_score=0.6, min_trusted=0.4)
    assert rep.is_trusted("p1")
    rep.penalize("p1", 0.3)
    assert not rep.is_trusted("p1")
    rep.reward("p1", 0.2)
    assert rep.is_trusted("p1")

    table = TerritoryTable()
    assert table.claim("vm:300", "body-a", tick=10, ttl=5) is True
    assert table.claim("vm:300", "body-b", tick=12, ttl=5) is False
    # Expires after ttl (10 + 5 == 15 -> expired at tick 16)
    assert table.claim("vm:300", "body-b", tick=16, ttl=5) is True
    assert table.release("vm:300", "body-a") is False
    assert table.release("vm:300", "body-b") is True


def test_backpressure_hysteresis_prevents_oscillation():
    assert should_backpressure({"operating_mode": "ALERT", "hormones": {"fuel": 0.5, "stress": 0.1}}, False) is False
    assert should_backpressure({"operating_mode": "LOCKDOWN", "hormones": {"fuel": 0.9, "stress": 0.7}}, False) is True
    # Hysteresis keeps pause active until fuel >= 0.60 and stress <= 0.35
    assert should_backpressure({"operating_mode": "ALERT", "hormones": {"fuel": 0.5, "stress": 0.2}}, True) is True
    assert should_backpressure({"operating_mode": "ALERT", "hormones": {"fuel": 0.65, "stress": 0.30}}, True) is False


def test_world_society_routes_attested_holds_lockdown_and_drops_spoof():
    soc = WorldSociety()
    k1, l1, g1, o1 = build_body({"role": "alpha"}, genome=Genome(identity="body-alpha", role="alpha"))
    k2, l2, g2, o2 = build_body({"role": "beta"}, genome=Genome(identity="body-beta", role="beta"))
    soc.register(k1, l1, g1, o1, secret="k-alpha")
    soc.register(k2, l2, g2, o2, secret="k-beta")

    # Induce LOCKDOWN on target via friction gradient
    class Spiker(Cell):
        def step(self, ctx):
            ctx.emit_gradient("friction", 4.0)

    k2.spawn(Spiker("spiker", organ="defense"), fuel=50.0)
    soc.step_all(12)
    assert k2.operating_mode == "LOCKDOWN"

    # Relay during LOCKDOWN is held (not lost!)
    held = soc.relay("body-alpha", "body-beta", {"id": 42, "title": "[bug] held incident", "body": "wait"})
    assert held["status"] == "held_backpressure"
    assert held["queued"] == 1

    # Remove spiker and let stress decay below 0.35 -> queued relay flushes cleanly
    k2.quarantined.add("spiker")
    soc.step_all(40)
    assert k2.operating_mode != "LOCKDOWN"
    assert "42" in l2.data["issues"]
    assert l2.data["issues"]["42"]["labels"] == ["bug"]
    rep2 = body_report(k2, l2, g2, o2)
    assert rep2["society"]["peer_accepted"] == 1


def test_host_routes_reagent_and_signed_peer_envelope():
    k, l, g, o = build_body({"role": "host-test"})
    skin = Skin("peer-x", "shared-secret")
    env = skin.seal({"id": 77, "title": "[feature] synced", "body": ""}, seq=1)

    host = Host(
        issues=[
            {"topic": "world.reagent", "payload": {"kind": "symptom", "id": 88, "title": "[bug] chem", "body": "a"}, "risk": 0.2},
            {"topic": "world.reagent", "payload": {"kind": "context", "title": "b", "body": "c"}, "risk": 0.5},
            {"topic": "peer.signal", "envelope": env},
        ],
        peer_secrets={"peer-x": "shared-secret"},
    )
    for _ in range(8):
        host.poll(k)
        k.step()

    assert l.data["issues"]["77"]["labels"] == ["feature"]
    assert l.data["issues"]["88"]["labels"] == ["bug"]
