#!/usr/bin/env python3
"""bigbang-mesh: Multi-tier collective environment orchestrator for bigBangEnv on Incus."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_cmd(cmd: list[str], check: bool = True, capture: bool = True) -> str:
    res = subprocess.run(cmd, text=True, capture_output=capture, check=check)
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

    print(f"{'TIER':<15} {'ORGANISM':<24} {'STATE':<10} {'IPV4':<16} {'TICKS':<8} {'HALTED'}")
    print("-" * 75)

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

        # Query organism kernel status if running
        ticks = "-"
        halted = "-"
        if state == "Running":
            try:
                res = run_cmd([
                    "incus", "exec", name, "--",
                    "/opt/bigbang/venv/bin/python", "-m", "bigbang", "status", "--state", "/var/lib/bigbang/state"
                ])
                stat = json.loads(res)
                ticks = str(stat.get("tick", 0))
                halted = str(stat.get("halted", False))
            except Exception:
                ticks = "init"
                halted = "init"

        print(f"{tier:<15} {role:<24} {state:<10} {ipv4:<16} {ticks:<8} {halted}")

    return 0


def cmd_spawn_tier(args: argparse.Namespace) -> int:
    tier = args.tier_name
    net_name = f"bb-net-{tier}"
    subnet = args.subnet

    print(f"[*] Spawning Tier '{tier}' (Subnet: {subnet})...")

    # 1. Ensure dedicated synaptic bridge network
    try:
        run_cmd(["incus", "network", "show", net_name])
    except subprocess.CalledProcessError:
        print(f"[+] Creating isolated synaptic bridge: {net_name}...")
        run_cmd([
            "incus", "network", "create", net_name,
            f"ipv4.address={subnet}", "ipv4.nat=true", "ipv6.address=none"
        ])

    # 2. Spawn member organisms
    members = [m.strip() for m in args.members.split(",") if m.strip()]
    for role in members:
        c_name = f"bb-{tier}-{role}"
        print(f"[+] Provisioning organism environment: {c_name} (Role: {role})...")

        # Check if already exists
        exists = any(c["name"] == c_name for c in get_incus_containers())
        if not exists:
            run_cmd([
                "incus", "launch", "debian12-base", c_name,
                "--profile", "bigbang-organism",
                "--network", net_name
            ])
            print(f"[+] Waiting for network on {c_name}...")
            run_cmd(["sleep", "3"])

            # Install bigBangEnv inside container
            print(f"[+] Bootstrapping bigBangEnv kernel inside {c_name}...")
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
cp /opt/bigbang/repo/deploy/bigbang-prestart.sh /usr/local/bin/bigbang-prestart.sh
chmod +x /usr/local/bin/bigbang-prestart.sh
cp /opt/bigbang/repo/deploy/bigbang-logrotate.conf /etc/logrotate.d/bigbang
cp /opt/bigbang/repo/deploy/bigbang.service /etc/systemd/system/bigbang.service

systemctl daemon-reload
systemctl enable --now bigbang.service
"""
            run_cmd(["incus", "exec", c_name, "--", "bash", "-c", setup_script])
            print(f"[✓] {c_name} is active and ticking.")
        else:
            print(f"[i] {c_name} already exists. Skipping.")

    print(f"\n[✓] Tier '{tier}' fully instantiated across {len(members)} collective environments.")
    return 0


def cmd_bridge(args: argparse.Namespace) -> int:
    source_c, target_c = args.source, args.target
    link_name = f"{source_c}_to_{target_c}"
    synapse_dir = Path("/var/lib/bigbang-mesh/synapses") / link_name
    synapse_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Establishing Synaptic Bridge: {source_c} -> {target_c}...")
    try:
        # Unprivileged Incus containers require shift=true for shared host mounts.
        # Mount source outbox and target inbox separately to avoid colliding on issues/.
        run_cmd([
            "incus", "config", "device", "add", source_c, f"outbox_{target_c}",
            "disk", f"source={synapse_dir}", f"path=/var/lib/bigbang/outbox/{target_c}", "shift=true"
        ])
        run_cmd([
            "incus", "config", "device", "add", target_c, f"synapse_{source_c}",
            "disk", f"source={synapse_dir}", "path=/var/lib/bigbang/issues", "shift=true"
        ])
        print(f"[✓] Synaptic bridge active ({synapse_dir}, shift=true).")
        print(f"    Note: {source_c} writes JSON impulses to /var/lib/bigbang/outbox/{target_c}/")
        print(f"    which appear directly in {target_c}'s /var/lib/bigbang/issues/ at WORLD trust.")
    except Exception as e:
        print(f"Notice or error: {e}")
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
    parser = argparse.ArgumentParser(description="bigbang-mesh: Multi-tier collective environment manager")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all active organism tiers and environments")

    spawn = sub.add_parser("spawn-tier", help="Spawn an isolated tier of organism environments")
    spawn.add_argument("tier_name", help="Name of the system tier (e.g. alpha, beta, triage)")
    spawn.add_argument("--subnet", default="10.99.1.1/24", help="Private CIDR for this tier's virtual bridge")
    spawn.add_argument("--members", default="sensor,reasoner,defense,motor", help="Comma-separated organism roles")
    spawn.add_argument("--branch", default="main", help="Git branch of bigBangEnv to deploy")

    bridge = sub.add_parser("bridge", help="Connect Motor output of source to Sensor input of target")
    bridge.add_argument("source", help="Source container name (e.g. bb-alpha-motor)")
    bridge.add_argument("target", help="Target container name (e.g. bb-beta-sensor)")

    halt = sub.add_parser("halt-tier", help="Halt all organisms in a tier")
    halt.add_argument("tier_name", help="Name of the tier to halt")

    trace = sub.add_parser("trace", help="View live trace of an organism")
    trace.add_argument("container", help="Container name (e.g. bb-alpha-reasoner)")
    trace.add_argument("--tail", type=int, default=15, help="Number of records to show")

    args = parser.parse_args()
    if args.command == "list":
        return cmd_list(args)
    elif args.command == "spawn-tier":
        return cmd_spawn_tier(args)
    elif args.command == "bridge":
        return cmd_bridge(args)
    elif args.command == "halt-tier":
        return cmd_halt_tier(args)
    elif args.command == "trace":
        return cmd_trace(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
