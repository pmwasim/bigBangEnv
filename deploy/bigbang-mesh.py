#!/usr/bin/env python3
"""bigbang-mesh: Multi-tier collective Body orchestrator for bigBangEnv on Incus."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def run_cmd(cmd: list[str], check: bool = True, capture: bool = True) -> str:
    res = subprocess.run(cmd, stdin=subprocess.DEVNULL, text=True, capture_output=capture, check=check)
    return res.stdout.strip() if capture else ""


def get_incus_containers() -> list[dict[str, Any]]:
    out = run_cmd(["incus", "list", "--format", "json"])
    return json.loads(out) if out else []


def cmd_list(args: argparse.Namespace) -> int:
    containers = get_incus_containers()
    bb_containers = [c for c in containers if c["name"].startswith("bb-")]

    if not bb_containers:
        print("No active bigBangEnv organism environments found.")
        return 0

    print(f"{'TIER':<8} {'BODY':<14} {'STATE':<8} {'IPV4':<14} {'TICKS':<6} {'MODE':<10} {'MASS':<6} {'HEAT':<6} {'HALTED'}")
    print("-" * 86)

    for c in bb_containers:
        name = c["name"]
        parts = name.split("-", 2)
        tier = parts[1] if len(parts) > 1 else "unknown"
        role = parts[2] if len(parts) > 2 else name

        state = c["status"]
        ipv4 = "-"
        if c.get("state") and c["state"].get("network"):
            for net_name, net in c["state"]["network"].items():
                if net_name != "lo" and net.get("addresses"):
                    for addr in net["addresses"]:
                        if addr.get("family") == "inet":
                            ipv4 = addr.get("address", "-")
                            break

        ticks = mode = mass = heat = halted = "-"
        if state == "Running":
            try:
                res = run_cmd([
                    "incus", "exec", name, "--",
                    "/opt/bigbang/venv/bin/python", "-m", "bigbang", "status", "--state", "/var/lib/bigbang/state"
                ])
                stat = json.loads(res)
                ticks = str(stat.get("tick", 0))
                mode = str(stat.get("operating_mode", "ALERT"))
                phys = stat.get("physics", {})
                mass = str(round(phys.get("gravitational_mass", 1.0), 2))
                heat = str(round(phys.get("entropy", 0.0), 2))
                halted = str(stat.get("halted", False))
            except Exception:
                ticks = mode = mass = heat = halted = "init"

        print(f"{tier:<8} {role:<14} {state:<8} {ipv4:<14} {ticks:<6} {mode:<10} {mass:<6} {heat:<6} {halted}")

    return 0


def cmd_spawn_tier(args: argparse.Namespace) -> int:
    tier = args.tier_name
    net_name = f"bb-net-{tier}"
    subnet = args.subnet

    print(f"[*] Spawning Tier '{tier}' (Subnet: {subnet})...")

    try:
        run_cmd(["incus", "network", "show", net_name])
    except subprocess.CalledProcessError:
        print(f"[+] Creating isolated synaptic bridge: {net_name}...")
        run_cmd([
            "incus", "network", "create", net_name,
            f"ipv4.address={subnet}", "ipv4.nat=true", "ipv6.address=none"
        ])

    members = [m.strip() for m in args.members.split(",") if m.strip()]
    for role in members:
        c_name = f"bb-{tier}-{role}"
        print(f"[+] Provisioning 5-organ Body environment: {c_name} (Role: {role})...")

        exists = any(c["name"] == c_name for c in get_incus_containers())
        if not exists:
            run_cmd([
                "incus", "launch", "debian12-base", c_name,
                "--profile", "bigbang-organism",
                "--network", net_name
            ])
            print(f"[+] Waiting for network on {c_name}...")
            run_cmd(["sleep", "3"])

            print(f"[+] Bootstrapping 5-organ Body kernel inside {c_name}...")
            branch = getattr(args, "branch", "main")
            setup_script = f"""
set -euo pipefail
apt-get update -y >/dev/null 2>&1
apt-get install -y --no-install-recommends git python3 python3-venv logrotate >/dev/null 2>&1

useradd --system --shell /usr/sbin/nologin --home-dir /var/lib/bigbang --create-home bigbang || true
mkdir -p /opt/bigbang /var/lib/bigbang/state /var/lib/bigbang/issues /var/log/bigbang /etc/bigbang
touch /var/lib/bigbang/commands.txt
chown -R bigbang:bigbang /var/lib/bigbang /var/log/bigbang

git clone --branch {branch} https://github.com/pmwasim/bigBangEnv.git /opt/bigbang/repo >/dev/null 2>&1
python3 -m venv /opt/bigbang/venv
/opt/bigbang/venv/bin/pip install -q --upgrade pip
/opt/bigbang/venv/bin/pip install -q -e "/opt/bigbang/repo[dev]"

cp /opt/bigbang/repo/deploy/bigbang.conf /etc/bigbang/bigbang.conf
sed -i 's/^BIGBANG_ROLE=.*/BIGBANG_ROLE={role}/' /etc/bigbang/bigbang.conf
cp /opt/bigbang/repo/deploy/bigbang-prestart.sh /usr/local/bin/bigbang-prestart.sh
chmod +x /usr/local/bin/bigbang-prestart.sh
cp /opt/bigbang/repo/deploy/bigbang-logrotate.conf /etc/logrotate.d/bigbang
cp /opt/bigbang/repo/deploy/bigbang.service /etc/systemd/system/bigbang.service

systemctl daemon-reload
systemctl enable --now bigbang.service
"""
            run_cmd(["incus", "exec", c_name, "--", "bash", "-c", setup_script])
            print(f"[✓] {c_name} (Body role={role}) is active and ticking.")
        else:
            print(f"[i] {c_name} already exists. Skipping.")

    print(f"\n[✓] Tier '{tier}' instantiated across {len(members)} living Body environments.")
    return 0


def cmd_relay_loop(args: argparse.Namespace) -> int:
    """Continuous synaptic relay forwarding verified Motor outcomes from source -> target."""
    source_c, target_c = args.source, args.target
    cursor_file = Path(f"/tmp/bigbang_relay_{source_c}_to_{target_c}.cursor")
    cursor = int(cursor_file.read_text()) if cursor_file.exists() else 0

    print(f"[*] Synaptic relay live: {source_c} (cursor={cursor}) -> {target_c}")
    while True:
        try:
            raw = run_cmd([
                "incus", "exec", source_c, "--",
                "cat", "/var/lib/bigbang/state/ledger.json"
            ], check=False)
            if raw:
                data = json.loads(raw)
                history = data.get("history", [])
                while cursor < len(history):
                    entry = history[cursor]
                    cursor += 1
                    cursor_file.write_text(str(cursor))
                    # Forward non-trivial actions into target Body's sensory ingress
                    relay_id = 100_000 + cursor
                    label = entry.get("label", entry.get("verb", "event"))
                    payload = {
                        "id": relay_id,
                        "title": f"[{label}] peer relay from {source_c} (issue #{entry.get('issue')})",
                        "body": f"Verified {entry.get('verb')} from {source_c}: {json.dumps(entry)}",
                    }
                    fname = f"synapse_{source_c}_{relay_id:06d}.json"
                    encoded = json.dumps(payload).replace("'", "'\\''")
                    run_cmd([
                        "incus", "exec", target_c, "--", "bash", "-c",
                        f"echo '{encoded}' > /var/lib/bigbang/issues/{fname} && chown bigbang:bigbang /var/lib/bigbang/issues/{fname}"
                    ])
                    print(f"[→] Relayed event #{cursor} ({label}) from {source_c} -> {target_c}")
        except Exception as exc:
            print(f"[!] Relay cycle warning: {exc}", file=sys.stderr)
        time.sleep(args.interval)


def cmd_bridge(args: argparse.Namespace) -> int:
    source_c, target_c = args.source, args.target
    unit_name = f"bigbang-synapse-{source_c}-to-{target_c}"
    print(f"[*] Starting persistent Synaptic Conduit service: {unit_name} ({source_c} -> {target_c})...")
    run_cmd(["sudo", "systemctl", "stop", unit_name], check=False)
    run_cmd([
        "sudo", "systemd-run", "--unit", unit_name,
        "--description", f"bigBangEnv Synaptic Conduit {source_c} -> {target_c}",
        sys.executable, str(Path(__file__).resolve()),
        "relay-loop", source_c, target_c, "--interval", "2.0"
    ])
    print(f"[✓] Synaptic Conduit active! Motor outcomes from {source_c} now flow directly into {target_c}.")
    return 0


def cmd_halt_tier(args: argparse.Namespace) -> int:
    tier = args.tier_name
    containers = [c["name"] for c in get_incus_containers() if c["name"].startswith(f"bb-{tier}-")]
    for c in containers:
        print(f"[*] Requesting halt for {c}...")
        try:
            run_cmd([
                "incus", "exec", c, "--",
                "/opt/bigbang/venv/bin/python", "-m", "bigbang", "halt",
                "--state", "/var/lib/bigbang/state", "--reason", "operator halt"
            ])
        except Exception as e:
            print(f"Could not halt {c}: {e}")
    print(f"[✓] All organisms in Tier '{tier}' halted.")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    """Route an incoming impulse to a Body in the tier using EM affinity + Gravitational curvature."""
    import math

    tier = args.tier_name
    containers = [
        c for c in get_incus_containers()
        if c["name"].startswith(f"bb-{tier}-") and c["status"] == "Running"
    ]
    if not containers:
        print(f"No running Bodies in tier '{tier}'.", file=sys.stderr)
        return 1

    best_name, best_action = None, float("inf")
    for idx, c in enumerate(sorted(containers, key=lambda x: x["name"]), start=1):
        name = c["name"]
        role = name.split("-", 2)[2]
        if args.affinity != "*" and role != args.affinity:
            continue  # EM repulsion
        raw = run_cmd([
            "incus", "exec", name, "--",
            "/opt/bigbang/venv/bin/python", "-m", "bigbang", "status", "--state", "/var/lib/bigbang/state"
        ], check=False)
        stat = json.loads(raw) if raw else {}
        phys = stat.get("physics", {})
        mass = float(phys.get("gravitational_mass", 1.0))
        heat = float(phys.get("entropy", 0.0))
        pot = float(phys.get("potential", 100.0))
        em = (pot / 100.0) / (float(idx) ** 2)
        action = (mass * 0.5) + (args.risk * (1.0 + heat * 0.5)) - em
        print(f"  candidate={name:<20} mass={mass:.2f} heat={heat:.2f} em={em:.3f} action={action:.3f}")
        if action < best_action:
            best_action = action
            best_name = name

    if best_name is None:
        print(f"EM repulsion: no Body matched affinity '{args.affinity}'.", file=sys.stderr)
        return 1

    issue_id = int(time.time() * 1000) % 1_000_000_000
    payload = {"id": issue_id, "title": args.title, "body": args.body}
    encoded = json.dumps(payload).replace("'", "'\\''")
    fname = f"routed_{issue_id}.json"
    run_cmd([
        "incus", "exec", best_name, "--", "bash", "-c",
        f"echo '{encoded}' > /var/lib/bigbang/issues/{fname} && chown bigbang:bigbang /var/lib/bigbang/issues/{fname}"
    ])
    print(f"[✓] Least-action routing chose {best_name} (action={best_action:.3f}) -> injected {fname}")
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    c_name = args.container
    tail = args.tail
    cmd = [
        "incus", "exec", c_name, "--",
        "/opt/bigbang/venv/bin/python", "-m", "bigbang", "trace",
        "--state", "/var/lib/bigbang/state", "--tail", str(tail)
    ]
    subprocess.run(cmd)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="bigbang-mesh: Multi-tier collective Body manager")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all active Body tiers and organisms")

    spawn = sub.add_parser("spawn-tier", help="Spawn an isolated tier of 5-organ Body environments")
    spawn.add_argument("tier_name", help="Name of the system tier (e.g. alpha, beta)")
    spawn.add_argument("--subnet", default="10.99.1.1/24", help="Private CIDR for this tier's virtual bridge")
    spawn.add_argument("--members", default="sentinel,triage,auditor,executor", help="Comma-separated Body roles")
    spawn.add_argument("--branch", default="main", help="Git branch of bigBangEnv to deploy")

    bridge = sub.add_parser("bridge", help="Establish a live Synaptic Conduit from source Body to target Body")
    bridge.add_argument("source", help="Source container name (e.g. bb-alpha-sentinel)")
    bridge.add_argument("target", help="Target container name (e.g. bb-alpha-triage)")

    relay = sub.add_parser("relay-loop", help="Internal foreground synaptic relay loop")
    relay.add_argument("source")
    relay.add_argument("target")
    relay.add_argument("--interval", type=float, default=2.0)

    halt = sub.add_parser("halt-tier", help="Halt all Bodies in a tier")
    halt.add_argument("tier_name", help="Name of the tier to halt")

    trace = sub.add_parser("trace", help="View live trace of a Body")
    trace.add_argument("container", help="Container name (e.g. bb-alpha-sentinel)")
    trace.add_argument("--tail", type=int, default=15, help="Number of records to show")

    route = sub.add_parser("route", help="Route an impulse across a tier using EM + Gravitational curvature")
    route.add_argument("tier_name", help="Target tier name (e.g. alpha)")
    route.add_argument("--title", required=True)
    route.add_argument("--body", default="")
    route.add_argument("--affinity", default="*", help="Required Body role affinity (or * for any)")
    route.add_argument("--risk", type=float, default=0.1, help="Signal risk charge [0.0..1.0]")

    args = parser.parse_args()
    if args.command == "list":
        return cmd_list(args)
    elif args.command == "spawn-tier":
        return cmd_spawn_tier(args)
    elif args.command == "bridge":
        return cmd_bridge(args)
    elif args.command == "relay-loop":
        return cmd_relay_loop(args)
    elif args.command == "halt-tier":
        return cmd_halt_tier(args)
    elif args.command == "trace":
        return cmd_trace(args)
    elif args.command == "route":
        return cmd_route(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
