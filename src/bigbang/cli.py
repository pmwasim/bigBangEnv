"""bigbang: operate bigBangEnv organisms from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__


def _print(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


def cmd_run(args: argparse.Namespace) -> int:
    from .runtime import Runner

    config: dict[str, Any] = {"brain": args.brain}
    if args.model:
        config["brain_options"] = {"model": args.model}
    if args.no_reflex:
        config["reflex"] = False
    runner = Runner(
        args.state, config=config, issues_dir=args.issues, commands_file=args.commands, resume=args.resume
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


def cmd_eval(args: argparse.Namespace) -> int:
    from .evaluation import run_suite, to_markdown

    suite = run_suite()
    if args.json:
        _print(suite)
    else:
        print(to_markdown(suite))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(to_markdown(suite))
    return 0 if suite["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bigbang", description=__doc__)
    parser.add_argument("--version", action="version", version=f"bigbang {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="boot or resume a caretaker organism")
    run.add_argument("--state", required=True, help="state directory")
    run.add_argument("--issues", help="directory of issue *.json files (WORLD trust)")
    run.add_argument("--commands", help="owner command file, one per line (OWNER trust)")
    run.add_argument("--brain", default="rule", choices=["rule", "offline", "claude"])
    run.add_argument("--model", help="model for --brain claude (default claude-opus-5-5)")
    run.add_argument("--no-reflex", action="store_true", help="disable the fast spine")
    run.add_argument("--ticks", type=int, default=50)
    run.add_argument("--forever", action="store_true", help="run until a HALT file appears")
    run.add_argument("--interval", type=float, default=0.0, help="seconds to sleep between ticks")
    run.add_argument("--resume", action="store_true", help="continue an existing organism")
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

    ev = sub.add_parser("eval", help="run the M1 evaluation suite")
    ev.add_argument("--json", action="store_true")
    ev.add_argument("--out", help="also write the markdown report here")
    ev.set_defaults(func=cmd_eval)
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
