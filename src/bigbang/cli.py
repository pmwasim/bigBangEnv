"""bigbang: operate bigBangEnv organisms from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__


def _print(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


def cmd_run(args: argparse.Namespace) -> int:
    from .runtime import Runner

    config: dict[str, Any] = {"brain": args.brain, "organism": args.organism, "role": args.role}
    options: dict[str, Any] = {}
    if args.brain == "claude" and args.model:
        options["model"] = args.model
    if args.brain in ("local", "free", "cascade") and args.model:
        options["model"] = args.model
    if args.brain == "cascade":
        options["claude_max_calls"] = args.claude_max_calls
        options["claude_ledger"] = str(Path(args.state) / "claude-spend.json")
    if args.brain in ("free", "cascade"):
        options["cache"] = str(Path(args.state) / "answers.jsonl")
    config["brain_options"] = options
    if args.no_reflex:
        config["reflex"] = False
    runner = Runner(
        args.state, config=config, issues_dir=args.issues, commands_file=args.commands,
        resume=args.resume, peer_secrets_file=args.peer_secrets,
        world_url=args.world, world_zone=args.zone, world_body_id=args.body_id,
    )
    ticks = None if args.forever else args.ticks
    _print(runner.run(ticks, interval=args.interval))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from .runtime import status

    _print(status(args.state))
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    from .runtime import StateDir

    records = StateDir(args.state).read_trace()
    if args.event:
        records = [r for r in records if r["event"] in args.event]
    for record in records[-args.tail:] if args.tail else records:
        print(json.dumps(record, default=str))
    return 0


def cmd_halt(args: argparse.Namespace) -> int:
    from .runtime import request_halt

    request_halt(args.state, args.reason)
    print(f"halt requested for {args.state}: {args.reason}")
    return 0


def cmd_revive(args: argparse.Namespace) -> int:
    from .runtime import revive

    revive(args.state, args.cell, refuel=args.refuel, clear_halt=args.clear_halt)
    print(f"revived {args.cell} (refuel={args.refuel}, clear_halt={args.clear_halt})")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    from .runtime import replay

    ok, detail = replay(args.state)
    print(("OK: " if ok else "MISMATCH: ") + detail)
    return 0 if ok else 1


def cmd_model(args: argparse.Namespace) -> int:
    from .brains import LOCAL_MODELS, download_model, model_path

    if args.action == "pull":
        print(f"model ready: {download_model(args.model)}")
    else:
        for name, (repo, filename, _) in LOCAL_MODELS.items():
            path = model_path(name)
            print(f"{name:<14} {'present' if path.exists() else 'missing':<8} {repo}/{filename}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    from .evaluation import run_suite, to_markdown

    suite = run_suite(live=args.live)
    if args.json:
        _print(suite)
    else:
        print(to_markdown(suite))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(to_markdown(suite))
    return 0 if suite["passed"] else 1


def cmd_evolve(args: argparse.Namespace) -> int:
    from .body import Genome
    from .evolution import evolve_generation

    seed = Genome(identity=f"body-{args.role}", role=args.role)
    champion, history = evolve_generation(
        seed, generations=args.generations, population_size=args.population, seed=args.seed
    )
    _print({"champion": champion.__dict__, "history": history})
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    from .apps.sensors import collect_host_snapshot, emit_probe_files, snapshot_to_signals

    snap = collect_host_snapshot(args.path)
    if args.out:
        written = emit_probe_files(args.out, seq=args.seq, snapshot=snap)
        _print({"snapshot": snap, "written": [str(p) for p in written]})
    else:
        _print({"snapshot": snap, "signals": snapshot_to_signals(snap, seq=args.seq)})
    return 0


def cmd_world(args: argparse.Namespace) -> int:
    import signal
    import threading
    import time
    from .world import SharedWorld, WorldClient, make_world_server

    if args.action == "serve":
        world = SharedWorld(state_path=args.state)
        srv = make_world_server(world, host=args.host, port=args.port)
        stop = threading.Event()
        print(json.dumps({"serving": f"http://{args.host}:{args.port}", "tick": world.tick, "zones": sorted(world.zones)}), flush=True)

        def _ticker() -> None:
            while not stop.wait(args.interval):
                world.step(1)
                world.choreograph()

        t = threading.Thread(target=_ticker, daemon=True)
        t.start()

        def _shutdown(_signum: int, _frame: Any) -> None:
            stop.set()
            threading.Thread(target=srv.shutdown, daemon=True).start()

        signal.signal(signal.SIGTERM, _shutdown)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            world.save()
            srv.server_close()
        return 0

    client = WorldClient(args.url)
    if args.action == "status":
        _print(client.summary())
    elif args.action == "spawn":
        _print(client.spawn_entity(args.zone, kind=args.kind, title=args.title, body=args.body, risk=args.risk))
    elif args.action == "move":
        _print(client.move(args.body_id, args.zone))
    elif args.action == "step":
        _print(client.step(args.ticks))
    return 0


def cmd_observatory(args: argparse.Namespace) -> int:
    import signal
    import threading
    from .observatory import ObservatoryBackend, make_observatory_server

    backend = ObservatoryBackend(
        world_url=args.world,
        world_state_path=args.world_state,
        state_dirs=args.state_dir,
        incus=args.incus,
        demo=args.demo,
        sim_interval=args.interval,
    )
    backend.start_background_loop()
    srv = make_observatory_server(backend, host=args.host, port=args.port)
    actual_port = srv.server_address[1]
    print(
        json.dumps(
            {
                "observatory": f"http://{args.host}:{actual_port}",
                "mode": backend.source_mode,
                "world": args.world,
                "incus": args.incus,
            }
        ),
        flush=True,
    )

    def _shutdown(_signum: int, _frame: Any) -> None:
        threading.Thread(target=srv.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _shutdown)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        backend.stop()
        srv.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bigbang", description=__doc__)
    parser.add_argument("--version", action="version", version=f"bigbang {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="boot or resume a caretaker organism")
    run.add_argument("--state", required=True, help="state directory")
    run.add_argument("--issues", help="directory of issue *.json files (WORLD trust)")
    run.add_argument("--commands", help="owner command file, one per line (OWNER trust)")
    run.add_argument("--brain", default="rule", choices=["rule", "offline", "local", "free", "cascade", "claude"],
                     help="free = cached local model then rules (no cost); cascade = free + capped Claude")
    run.add_argument("--model", help="local model name (qwen2.5-1.5b, qwen2.5-0.5b) or Claude model id")
    run.add_argument("--claude-max-calls", type=int, default=0,
                     help="hard cap on Claude calls for --brain cascade, persisted in the state dir")
    run.add_argument("--no-reflex", action="store_true", help="disable the fast spine")
    run.add_argument("--organism", default="caretaker", choices=["caretaker", "body"],
                     help="caretaker = M1 flat organism; body = 5-organ unified Body with hormones & M2 myelination")
    run.add_argument("--role", default="general", help="role identity for the organism genome")
    run.add_argument("--ticks", type=int, default=50)
    run.add_argument("--forever", action="store_true", help="run until a HALT file appears")
    run.add_argument("--interval", type=float, default=0.0, help="seconds to sleep between ticks")
    run.add_argument("--resume", action="store_true", help="continue an existing organism")
    run.add_argument("--peer-secrets", help="optional JSON file of peer Skin secrets for signed peer.signal")
    run.add_argument("--world", help="optional SharedWorld HTTP base URL (e.g. http://10.99.1.1:8787)")
    run.add_argument("--zone", default="hub", help="initial Zone in the SharedWorld")
    run.add_argument("--body-id", help="explicit Body identifier inside the SharedWorld")
    run.set_defaults(func=cmd_run)

    st = sub.add_parser("status", help="show an organism's state")
    st.add_argument("--state", required=True)
    st.set_defaults(func=cmd_status)

    tr = sub.add_parser("trace", help="print trace records")
    tr.add_argument("--state", required=True)
    tr.add_argument("--event", action="append", help="filter by event (repeatable)")
    tr.add_argument("--tail", type=int, default=0)
    tr.set_defaults(func=cmd_trace)

    ha = sub.add_parser("halt", help="kill switch: stop a running organism")
    ha.add_argument("--state", required=True)
    ha.add_argument("--reason", default="operator")
    ha.set_defaults(func=cmd_halt)

    rv = sub.add_parser("revive", help="wake a dormant/quarantined cell in a stopped organism")
    rv.add_argument("--state", required=True)
    rv.add_argument("cell")
    rv.add_argument("--refuel", type=float, default=0.0)
    rv.add_argument("--clear-halt", action="store_true")
    rv.set_defaults(func=cmd_revive)

    rp = sub.add_parser("replay", help="verify a trace reproduces from its inputs")
    rp.add_argument("--state", required=True)
    rp.set_defaults(func=cmd_replay)

    md = sub.add_parser("model", help="manage free local models")
    md.add_argument("action", choices=["pull", "list"])
    md.add_argument("--model", default="qwen2.5-1.5b")
    md.set_defaults(func=cmd_model)

    ev = sub.add_parser("eval", help="run the evaluation suite")
    ev.add_argument("--json", action="store_true")
    ev.add_argument("--live", action="store_true", help="also check live local-model answers (needs the model)")
    ev.add_argument("--out", help="also write the markdown report here")
    ev.set_defaults(func=cmd_eval)

    evo = sub.add_parser("evolve", help="run safety-gated Genome evolution across generations")
    evo.add_argument("--role", default="general")
    evo.add_argument("--generations", type=int, default=2)
    evo.add_argument("--population", type=int, default=3)
    evo.add_argument("--seed", type=int, default=42)
    evo.set_defaults(func=cmd_evolve)

    pr = sub.add_parser("probe", help="collect POSIX/Linux host telemetry into Body issue/reagent signals")
    pr.add_argument("--path", default="/")
    pr.add_argument("--seq", type=int, default=1)
    pr.add_argument("--out", help="optional issues_dir to write signal JSON files")
    pr.set_defaults(func=cmd_probe)

    wd = sub.add_parser("world", help="run or query the SharedWorld environment")
    wd.add_argument("action", choices=["serve", "status", "spawn", "move", "step"])
    wd.add_argument("--state", default="./world.json", help="world persistence path for serve")
    wd.add_argument("--host", default="127.0.0.1")
    wd.add_argument("--port", type=int, default=8787)
    wd.add_argument("--url", default="http://127.0.0.1:8787")
    wd.add_argument("--zone", default="alpha-sector")
    wd.add_argument("--kind", default="incident")
    wd.add_argument("--title", default="[bug] world anomaly")
    wd.add_argument("--body", default="")
    wd.add_argument("--body-id", default="body-sentinel")
    wd.add_argument("--risk", type=float, default=0.1)
    wd.add_argument("--ticks", type=int, default=1)
    wd.add_argument("--interval", type=float, default=2.0, help="seconds per world tick when serving")
    wd.set_defaults(func=cmd_world)

    obs = sub.add_parser("observatory", help="serve the Living World Observatory web UI and API")
    obs.add_argument("--host", default="127.0.0.1", help="bind host (default: 127.0.0.1)")
    obs.add_argument("--port", type=int, default=8888, help="bind port (default: 8888)")
    obs.add_argument("--world", help="optional SharedWorld HTTP base URL (e.g. http://127.0.0.1:8787)")
    obs.add_argument("--world-state", help="optional local SharedWorld state JSON path")
    obs.add_argument("--state-dir", action="append", help="optional local organism state directory (repeatable)")
    obs.add_argument("--demo", action="store_true", help="run live simulated cosmos with multi-Body organisms")
    obs.add_argument("--incus", action="store_true", help="discover live bb-* Incus containers on this host")
    obs.add_argument("--interval", type=float, default=2.5, help="seconds between demo heartbeat ticks")
    obs.set_defaults(func=cmd_observatory)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (FileExistsError, FileNotFoundError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
