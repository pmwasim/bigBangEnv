"""Live Domain Sensors: convert real POSIX/Linux host & container metrics into Body impulses."""

from __future__ import annotations

import json
import os
import shutil
import socket
from pathlib import Path
from typing import Any


def _read_linux_mem_pct() -> float | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    vals: dict[str, int] = {}
    for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split(":", 1)
        if len(parts) != 2:
            continue
        num = parts[1].strip().split()[0]
        if num.isdigit():
            vals[parts[0].strip()] = int(num)
    total = vals.get("MemTotal", 0)
    avail = vals.get("MemAvailable", vals.get("MemFree", 0))
    if total <= 0:
        return None
    return round(100.0 * max(0, total - avail) / total, 2)


def _read_linux_uptime() -> float | None:
    uptime = Path("/proc/uptime")
    if not uptime.exists():
        return None
    first = uptime.read_text(encoding="utf-8", errors="ignore").strip().split()[0]
    try:
        return round(float(first), 1)
    except ValueError:
        return None


def collect_host_snapshot(path: str | Path = "/") -> dict[str, Any]:
    """Collect live infrastructure health metrics using pure Python stdlib."""
    du = shutil.disk_usage(path)
    disk_pct = round(100.0 * du.used / max(1, du.total), 2)
    try:
        load_1m = round(os.getloadavg()[0], 3)
    except (AttributeError, OSError):
        load_1m = 0.0
    cpu_count = os.cpu_count() or 1
    mem_pct = _read_linux_mem_pct()
    uptime_s = _read_linux_uptime()
    return {
        "host": socket.gethostname(),
        "cpu_count": cpu_count,
        "load_1m": load_1m,
        "load_ratio": round(load_1m / cpu_count, 3),
        "disk_used_pct": disk_pct,
        "mem_used_pct": mem_pct,
        "uptime_s": uptime_s,
    }


def snapshot_to_signals(
    snap: dict[str, Any],
    *,
    seq: int = 1,
    disk_warn_pct: float = 85.0,
    mem_warn_pct: float = 85.0,
    load_ratio_warn: float = 1.5,
) -> list[dict[str, Any]]:
    """Translate a host snapshot into typed world.reagent / world.issue envelopes."""
    signals: list[dict[str, Any]] = []
    base_id = 500_000 + (seq * 10)
    host = snap.get("host", "node")

    if float(snap.get("disk_used_pct", 0.0)) >= disk_warn_pct:
        signals.append({
            "topic": "world.reagent",
            "payload": {"kind": "symptom", "id": base_id + 1, "title": f"[bug] high disk usage on {host}", "body": f"disk={snap['disk_used_pct']}%"},
            "risk": 0.4,
        })
        signals.append({
            "topic": "world.reagent",
            "payload": {"kind": "context", "title": f"filesystem telemetry {host}", "body": json.dumps(snap, sort_keys=True)},
            "risk": 0.2,
        })

    mem_pct = snap.get("mem_used_pct")
    if mem_pct is not None and float(mem_pct) >= mem_warn_pct:
        signals.append({
            "topic": "world.reagent",
            "payload": {"kind": "symptom", "id": base_id + 2, "title": f"[bug] high memory pressure on {host}", "body": f"mem={mem_pct}%"},
            "risk": 0.5,
        })
        signals.append({
            "topic": "world.reagent",
            "payload": {"kind": "context", "title": f"memory telemetry {host}", "body": json.dumps(snap, sort_keys=True)},
            "risk": 0.3,
        })

    if float(snap.get("load_ratio", 0.0)) >= load_ratio_warn:
        signals.append({
            "topic": "world.issue",
            "id": base_id + 3,
            "title": f"[bug] high CPU load on {host} ({snap['load_1m']})",
            "body": json.dumps(snap, sort_keys=True),
        })

    if not signals:
        signals.append({
            "topic": "world.issue",
            "id": base_id,
            "title": f"[question] host health heartbeat {host}",
            "body": json.dumps(snap, sort_keys=True),
        })
    return signals


def emit_probe_files(
    issues_dir: str | Path,
    *,
    seq: int = 1,
    snapshot: dict[str, Any] | None = None,
) -> list[Path]:
    """Write live telemetry signal JSON files into an organism's issues_dir."""
    target = Path(issues_dir)
    target.mkdir(parents=True, exist_ok=True)
    snap = snapshot or collect_host_snapshot()
    signals = snapshot_to_signals(snap, seq=seq)
    written: list[Path] = []
    for idx, sig in enumerate(signals, start=1):
        out = target / f"probe_{seq:06d}_{idx:02d}.json"
        out.write_text(json.dumps(sig, indent=2, sort_keys=True), encoding="utf-8")
        written.append(out)
    return written
