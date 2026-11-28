"""Tests for the Living World Observatory backend, APIs, storytelling, and CLI."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from bigbang.cli import build_parser
from bigbang.observatory import (
    ObservatoryBackend,
    collect_machine_stats,
    make_observatory_server,
)
from bigbang.runtime import Runner
from bigbang.soul import Anatomy, Character
from bigbang.world import SharedWorld, make_world_server


def _http_json(url: str, *, method: str = "GET", body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _http_text(url: str) -> tuple[int, str, str]:
    try:
        with urllib.request.urlopen(url, timeout=3.0) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read().decode("utf-8")


def test_observatory_demo_universe_beings_world_and_pulse(tmp_path: Path):
    web_dir = tmp_path / "web"
    web_dir.mkdir()
    (web_dir / "index.html").write_text("<html><body>Sanctuary</body></html>", encoding="utf-8")
    (web_dir / "app.js").write_text("console.log('alive');", encoding="utf-8")
    (web_dir / "styles.css").write_text("body { color: #fff; }", encoding="utf-8")

    backend = ObservatoryBackend(demo=True)
    srv = make_observatory_server(backend, host="127.0.0.1", port=0, web_dir=web_dir)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{port}"
    try:
        # Static serving & traversal guard
        code, ctype, html = _http_text(f"{base}/")
        assert code == 200
        assert "text/html" in ctype
        assert "Sanctuary" in html

        code, ctype, js = _http_text(f"{base}/app.js")
        assert code == 200 and "javascript" in ctype and "alive" in js

        code, _, _ = _http_text(f"{base}/../secret.txt")
        assert code == 404

        # GET /api/universe
        code, uni = _http_json(f"{base}/api/universe")
        assert code == 200
        assert uni["source_mode"] == "demo"
        assert set(uni["narrative"]) >= {"headline", "story", "spoken_bulletin", "bulletin_id"}
        assert "Sanctuary" in uni["narrative"]["headline"] or "Cosmos" in uni["narrative"]["headline"] or "Biosphere" in uni["narrative"]["headline"] or "Minds" in uni["narrative"]["headline"]

        machine = uni["machine"]
        assert machine["host"]
        assert machine["cpu_count"] >= 1
        assert machine["disk_free_gb"] >= 0.0
        assert machine["vitality_phrase"]

        world = uni["world"]
        assert world["tick"] > 0
        assert {z["name"] for z in world["zones"]} == {"hub", "alpha-sector", "beta-sector", "playground", "frontier"}
        for z in world["zones"]:
            assert z["story"]
            assert z["mood"] in {"serene", "lively", "thirsty", "stirring"}
            assert 0.0 <= z["energy_pct"] <= 100.0
            assert 0.0 <= z["calmness"] <= 1.0
            assert "x" in z and "y" in z and "z" in z

        assert len(world["lands"]) == 5
        assert len(world["homes"]) == 5
        assert len(world["playgrounds"]) >= 1
        assert len(world["paths"]) >= 5
        assert len(world["doors"]) >= 5
        assert world["competition"] is not None
        assert "ticks_remaining" in world["competition"]
        assert "podium" in world["competition"]
        assert 0.0 <= world["daylight"] <= 1.0
        assert "api_ms" in uni["perf"]
        assert len(uni["rewards_log"]) >= 1

        beings = uni["beings"]
        assert len(beings) == 10
        assert any(b["mode"] == "SLEEP_REM" for b in beings)
        for b in beings:
            assert len(b["organs"]) == 5
            assert {o["name"] for o in b["organs"]} == {"perception", "deliberation", "memory", "action", "defense"}
            assert set(b["soul"]) >= {"soul_id", "calling", "conscience", "karma"}
            assert set(b["character"]) == {"caution", "curiosity", "diligence", "altruism"}
            assert set(b["anatomy"]) == {"eyes", "ears", "tongue", "hands", "legs"}
            assert set(b["location"]) == {"zone", "x", "y", "z", "walk_state"}
            assert b["home"]["id"] and b["action_story"]
            assert "honor" in b and "rewards" in b and "punishments" in b

        chronicle = uni["chronicle"]
        expected_chapters = [
            "Genesis & Physics",
            "Chemistry & Bonding",
            "Cells, Organs & Living Body",
            "Homeostasis & Stem Renewal",
            "Society & Skin",
            "Evolution & Senses",
            "Shared & Relative Worlds",
            "Soul, Character & Beliefs",
        ]
        assert [c["title"] for c in chronicle["chapters"]] == expected_chapters
        assert len(chronicle["events"]) >= 1
        for ev in chronicle["events"]:
            assert set(ev) >= {"id", "tick", "who", "where", "sentence", "tone"}

        # GET /api/beings/<id>/world
        first_id = beings[0]["id"]
        code, bw = _http_json(f"{base}/api/beings/{first_id}/world")
        assert code == 200
        assert bw["body_world"]["observer_id"] == first_id
        assert bw["body_world"]["scale"] == "body"
        assert bw["voice_intro"].startswith("I am ")
        assert len(bw["soul"]["conscience_phrases"]) == 3

        code, missing = _http_json(f"{base}/api/beings/nonexistent-being/world")
        assert code == 404
        assert missing["ok"] is False

        # POST /api/pulse (curiosity, competition, reward, move)
        code, pulse = _http_json(
            f"{base}/api/pulse",
            method="POST",
            body={"zone": "alpha-sector", "spark": "Lantern shimmer in the east", "kind": "curiosity"},
        )
        assert code == 200
        assert pulse["ok"] is True
        assert "Alpha Sanctuary" in pulse["acknowledgment"]
        assert pulse["entity"]["title"] == "Lantern shimmer in the east"

        code, comp_res = _http_json(
            f"{base}/api/pulse",
            method="POST",
            body={"zone": "playground", "spark": "Twilight Rhythm Trial", "kind": "competition"},
        )
        assert code == 200 and comp_res["ok"] is True
        assert comp_res["competition"]["title"] == "Twilight Rhythm Trial"

        code, rew_res = _http_json(
            f"{base}/api/pulse",
            method="POST",
            body={"zone": "alpha-sector", "body_id": "bb-alpha-sentinel", "spark": "vigilant care", "kind": "reward"},
        )
        assert code == 200 and rew_res["ok"] is True

        code, mv_res = _http_json(
            f"{base}/api/pulse",
            method="POST",
            body={"zone": "hub", "body_id": "bb-gamma-scout", "target_zone": "hub", "kind": "move"},
        )
        assert code == 200 and mv_res["ok"] is True and mv_res["moved_to"] is not None

        code, door_res = _http_json(
            f"{base}/api/pulse",
            method="POST",
            body={"door_id": "door:hub:playground", "kind": "door"},
        )
        assert code == 200 and door_res["ok"] is True and door_res["door"]["state"] == "guarded"

        code, evo_res = _http_json(
            f"{base}/api/pulse",
            method="POST",
            body={"body_id": "bb-alpha-sentinel", "kind": "evolve"},
        )
        assert code == 200 and evo_res["ok"] is True
        assert evo_res["champion"]["identity"].startswith("body-sentinel")
        assert evo_res["insight"]

        # Invalid pulse rejected
        code, bad_pulse = _http_json(f"{base}/api/pulse", method="POST", body={"zone": "alpha-sector", "spark": "   "})
        assert code == 400
        assert bad_pulse["ok"] is False

        code, bad_zone = _http_json(f"{base}/api/pulse", method="POST", body={"zone": "void", "spark": "Hello"})
        assert code == 400
        assert bad_zone["ok"] is False
    finally:
        backend.stop()
        srv.shutdown()
        srv.server_close()


def test_observatory_local_state_dirs_and_external_world(tmp_path: Path):
    world = SharedWorld(state_path=tmp_path / "world.json")
    wsrv = make_world_server(world, host="127.0.0.1", port=0)
    wport = wsrv.server_address[1]
    wth = threading.Thread(target=wsrv.serve_forever, daemon=True)
    wth.start()
    wurl = f"http://127.0.0.1:{wport}"

    state_dir = tmp_path / "triage_state"
    try:
        world.spawn_entity("beta-sector", kind="incident", title="[bug] warm coil near beta bridge")
        runner = Runner(
            state_dir,
            config={"organism": "body", "role": "triage"},
            world_url=wurl,
            world_zone="beta-sector",
            world_body_id="bb-beta-triage",
        )
        runner.run(6)

        backend = ObservatoryBackend(world_url=wurl, state_dirs=[state_dir])
        assert backend.source_mode == "local"
        uni = backend.get_universe()
        assert len(uni["beings"]) == 1
        being = uni["beings"][0]
        assert being["id"] == "bb-beta-triage"
        assert being["zone"] == "beta-sector"
        assert being["soul"]["karma"] >= 0.1
        assert len(being["beliefs"]) >= 1

        bw = backend.get_being_world("bb-beta-triage")
        assert bw is not None
        assert bw["body_world"]["frame_origin"] == "beta-sector"

        pulse = backend.pulse(zone="beta-sector", spark="Starlight ripple over Beta", kind="incident")
        assert pulse["ok"] is True
        assert len(world.entities) == 2
    finally:
        wsrv.shutdown()
        wsrv.server_close()


def test_observatory_incus_discovery_and_host_stats(monkeypatch, tmp_path: Path):
    fake_snap = {
        "tick": 42,
        "hormones": {"fuel": 0.91, "stress": 0.05, "urgency": 0.1, "idle": 3.0},
        "operating_mode": "ALERT",
        "cells": {
            "action.verifier": {
                "memory": {
                    "karma": 1.2,
                    "soul": {"soul_id": "soul:abc", "calling": "sentinel", "conscience": ["do_no_harm"]},
                    "character": {"caution": 0.85, "curiosity": 0.45, "diligence": 0.8, "altruism": 0.75},
                    "beliefs": {"action:label": {"confidence": 0.88, "evidence": 7, "updated_tick": 40}},
                }
            }
        },
    }
    fake_cfg = {"role": "sentinel", "world_body_id": "bb-alpha-sentinel", "world_zone": "alpha-sector"}
    fake_containers = [
        {
            "name": "bb-alpha-sentinel",
            "status": "Running",
            "state": {"memory": {"usage": 64 * 1024 * 1024}},
        }
    ]

    class _FakeProc:
        def __init__(self, returncode: int, stdout: str) -> None:
            self.returncode = returncode
            self.stdout = stdout

    def _fake_run(cmd, **_kwargs):
        if cmd[:2] == ["incus", "list"]:
            return _FakeProc(0, json.dumps(fake_containers))
        if cmd[:2] == ["incus", "exec"]:
            payload = f"{json.dumps(fake_cfg)}\n---SPLIT---\n{json.dumps(fake_snap)}\n---SPLIT---\n"
            return _FakeProc(0, payload)
        return _FakeProc(1, "")

    monkeypatch.setattr("bigbang.observatory.subprocess.run", _fake_run)
    backend = ObservatoryBackend(world_state_path=tmp_path / "missing_world.json", incus=True)
    uni = backend.get_universe()
    assert uni["source_mode"] == "incus"
    assert len(uni["beings"]) == 1
    b = uni["beings"][0]
    assert b["id"] == "bb-alpha-sentinel"
    assert b["memory_mb"] == 64.0
    assert b["ticks"] == 42
    assert b["soul"]["karma"] == 1.2

    # Host stats work on both macOS and Linux paths without raising
    stats = collect_machine_stats("/")
    assert stats["cpu_count"] >= 1
    assert 0.0 <= stats["disk_used_pct"] <= 100.0
    assert stats["vitality_phrase"]


def test_cli_observatory_parser():
    args = build_parser().parse_args([
        "observatory", "--host", "0.0.0.0", "--port", "9090",
        "--world", "http://127.0.0.1:8787", "--demo", "--incus",
    ])
    assert args.command == "observatory"
    assert args.host == "0.0.0.0"
    assert args.port == 9090
    assert args.world == "http://127.0.0.1:8787"
    assert args.demo is True
    assert args.incus is True


def test_embodied_anatomy_and_role_presets():
    for role in ("sentinel", "auditor", "scout", "arbiter", "triage", "planner", "executor", "artisan", "weaver"):
        anat = Anatomy.for_role(role).to_dict()
        assert set(anat) == {"eyes", "ears", "tongue", "hands", "legs"}
        for part in anat.values():
            assert 0.0 <= part["strength"] <= 1.0
            assert part["role_story"]
        ch = Character.for_role(role)
        assert 0.0 <= ch.caution <= 1.0 and 0.0 <= ch.curiosity <= 1.0


def test_observatory_parallel_incus_poller_cache(monkeypatch, tmp_path: Path):
    import time

    calls = {"list": 0, "exec": 0}
    fake_containers = [
        {"name": f"bb-alpha-{role}", "status": "Running", "state": {"memory": {"usage": 32 * 1024 * 1024}}}
        for role in ("sentinel", "triage", "auditor", "executor")
    ]

    class _FakeProc:
        def __init__(self, returncode: int, stdout: str) -> None:
            self.returncode = returncode
            self.stdout = stdout

    def _fake_run(cmd, **_kwargs):
        if cmd[:2] == ["incus", "list"]:
            calls["list"] += 1
            return _FakeProc(0, json.dumps(fake_containers))
        if cmd[:2] == ["incus", "exec"]:
            calls["exec"] += 1
            time.sleep(0.05)
            return _FakeProc(0, '{"role":"sentinel"}\n---SPLIT---\n{"tick":12,"cells":{},"hormones":{},"operating_mode":"ALERT"}\n---SPLIT---\n')
        return _FakeProc(1, "")

    monkeypatch.setattr("bigbang.observatory.subprocess.run", _fake_run)
    backend = ObservatoryBackend(world_state_path=tmp_path / "missing_world.json", incus=True, incus_interval=1.0)
    backend.poll_incus_once()
    assert calls["list"] == 1 and calls["exec"] == 4

    # Subsequent get_universe calls serve from atomic cache with zero extra incus subprocess calls
    t0 = time.perf_counter()
    uni = backend.get_universe()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert len(uni["beings"]) == 4
    assert calls["list"] == 1 and calls["exec"] == 4
    assert elapsed_ms < 250.0
