import json

import pytest

from bigbang.cli import main
from bigbang.runtime import Runner, replay, request_halt, revive, status


def write_issues(directory, issues):
    directory.mkdir(parents=True, exist_ok=True)
    for issue in issues:
        (directory / f"{issue['id']:04d}.json").write_text(json.dumps(issue))


ISSUES = [
    {"id": 1, "title": "[bug] crash", "body": ""},
    {"id": 2, "title": "How do I run it?", "body": "close 1"},
    {"id": 3, "title": "Please add support for X", "body": ""},
]


def test_run_persists_state_and_trace(tmp_path):
    state, issues = tmp_path / "state", tmp_path / "issues"
    write_issues(issues, ISSUES)
    rep = Runner(state, issues_dir=issues).run(10)
    assert rep["issues_labelled"] == 3
    for name in ("config.json", "snapshot.json", "host.json", "ledger.json", "trace.jsonl"):
        assert (state / name).exists()
    assert status(state)["tick"] == 10


def test_refuses_to_overwrite_and_resumes(tmp_path):
    state, issues = tmp_path / "state", tmp_path / "issues"
    write_issues(issues, ISSUES[:1])
    Runner(state, issues_dir=issues).run(5)
    with pytest.raises(FileExistsError):
        Runner(state, issues_dir=issues)
    write_issues(issues, ISSUES[1:])
    rep = Runner(state, issues_dir=issues, resume=True).run(10)
    assert rep["tick"] == 15
    assert rep["issues_labelled"] == 3
    assert rep["issues_seen"] == 3  # earlier issue not re-ingested


def test_owner_commands_file(tmp_path):
    state, cmds = tmp_path / "state", tmp_path / "commands.txt"
    cmds.write_text("close 9\n")
    Runner(state, commands_file=cmds).run(5)
    ledger = json.loads((state / "ledger.json").read_text())
    assert ledger["issues"]["9"]["closed"] is True


def test_halt_file_stops_the_organism(tmp_path):
    state = tmp_path / "state"
    runner = Runner(state)
    runner.run(3)
    request_halt(state, "maintenance")
    rep = runner.run(None)  # would run forever without the kill switch
    assert rep["halted"] and rep["tick"] == 3
    assert status(state)["halted"] is True


def test_replay_matches_single_session(tmp_path):
    state, issues, cmds = tmp_path / "state", tmp_path / "issues", tmp_path / "c.txt"
    write_issues(issues, ISSUES)
    cmds.write_text("close 2\n")
    Runner(state, issues_dir=issues, commands_file=cmds).run(12)
    ok, detail = replay(state)
    assert ok, detail


def test_replay_refuses_multi_session(tmp_path):
    state = tmp_path / "state"
    Runner(state).run(2)
    Runner(state, resume=True).run(2)
    ok, detail = replay(state)
    assert not ok and "several sessions" in detail


def test_revive_clears_halt(tmp_path):
    state = tmp_path / "state"
    runner = Runner(state)
    runner.run(1)
    request_halt(state)
    runner.run(1)
    revive(state, "reasoner", refuel=10, clear_halt=True)
    rep = Runner(state, resume=True).run(2)
    assert not rep["halted"] and rep["tick"] == 3


def test_cli_end_to_end(tmp_path, capsys):
    state, issues = tmp_path / "state", tmp_path / "issues"
    write_issues(issues, ISSUES)
    assert main(["run", "--state", str(state), "--issues", str(issues), "--ticks", "8"]) == 0
    assert main(["status", "--state", str(state)]) == 0
    assert main(["trace", "--state", str(state), "--event", "declassify"]) == 0
    assert main(["replay", "--state", str(state)]) == 0
    assert main(["halt", "--state", str(state)]) == 0
    assert main(["run", "--state", str(state)]) == 2  # refuses to overwrite
    out = capsys.readouterr().out
    assert "declassify" in out and "OK: identical" in out


def test_cli_model_list(capsys):
    assert main(["model", "list"]) == 0
    out = capsys.readouterr().out
    assert "qwen2.5-1.5b" in out and "Qwen/Qwen2.5-1.5B-Instruct-GGUF" in out


def test_skipped_scenarios_render_as_skipped():
    from bigbang.evaluation import _skipped, to_markdown

    md = to_markdown({"passed": True, "scenarios": [_skipped("x", "claim", "no model")]})
    assert "| x | claim | skipped |" in md


def test_cli_eval(tmp_path, capsys):
    out_file = tmp_path / "eval.md"
    assert main(["eval", "--out", str(out_file)]) == 0
    assert "PASS" in out_file.read_text()
