"""Living World Observatory: pure-stdlib web server, natural-language narrator, and cosmos API."""

from __future__ import annotations

import json
import math
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .apps.caretaker import Host, Ledger
from .apps.sensors import collect_host_snapshot
from .body import Genome, build_body
from .evolution import evolve_generation
from .kernel import Kernel
from .organ import Organ
from .runtime import StateDir
from .soul import Anatomy, BeliefSystem, Character, Soul
from .world import (
    _HOME_META,
    _ZONE_COORDS,
    RelativeWorld,
    SharedWorld,
    WorldClient,
    Zone,
    _build_doors,
    body_world,
)

WEB_DIR = Path(__file__).resolve().parent / "web"

ZONE_LABELS: dict[str, str] = {
    "hub": "The Central Hearth",
    "alpha-sector": "Alpha Sanctuary",
    "beta-sector": "Beta Frontier",
    "playground": "Starlight Playground",
    "frontier": "Far Horizon",
}

DEMO_ROSTER: tuple[tuple[str, str, str], ...] = (
    ("bb-alpha-sentinel", "sentinel", "alpha-sector"),
    ("bb-alpha-triage", "triage", "alpha-sector"),
    ("bb-alpha-auditor", "auditor", "alpha-sector"),
    ("bb-alpha-executor", "executor", "alpha-sector"),
    ("bb-beta-planner", "planner", "beta-sector"),
    ("bb-beta-executor", "executor", "beta-sector"),
    ("bb-gamma-scout", "scout", "frontier"),
    ("bb-gamma-artisan", "artisan", "hub"),
    ("bb-gamma-arbiter", "arbiter", "playground"),
    ("bb-gamma-weaver", "weaver", "hub"),
)

MODE_PHRASES: dict[str, str] = {
    "ALERT": "awake and attentive",
    "DEEP_FOCUS": "deeply focused",
    "SLEEP_REM": "dreaming quietly",
    "LOCKDOWN": "standing protective guard",
    "DORMANT": "resting in deep stillness",
}

ORGAN_META: dict[str, tuple[str, str]] = {
    "perception": ("Senses", "listening to every ripple arriving across the outer membrane"),
    "deliberation": ("Mind", "weighing unfamiliar patterns with patient discernment"),
    "memory": ("Memory", "weaving passing experiences into lasting wisdom"),
    "action": ("Hands", "carrying out gentle, verified stewardship in the world"),
    "defense": ("Shield", "keeping balance, boundaries, and inner harmony intact"),
}

CONSCIENCE_PHRASES: dict[str, str] = {
    "do_no_harm": "Cause no harm to the world or its inhabitants",
    "preserve_owner_sovereignty": "Honor the owner's sovereignty above all",
    "truth_before_action": "Seek truth before taking action",
}

CHRONICLE_CHAPTERS: tuple[dict[str, str], ...] = (
    {
        "id": "genesis-physics",
        "title": "Genesis & Physics",
        "era": "Chapter I",
        "status": "complete",
        "summary": (
            "Time began as a steady heartbeat where every breath is conserved energy, "
            "attention carries gentle gravity, and turbulence cools back into stillness."
        ),
        "essence": "Nothing moves without breath; every effort leaves warmth that softens over time.",
    },
    {
        "id": "chemistry-bonding",
        "title": "Chemistry & Bonding",
        "era": "Chapter II",
        "status": "complete",
        "summary": (
            "Passing clues and context learned to recognize each other, crossing thresholds "
            "to bond into deeper meaning while dissolving stale residue."
        ),
        "essence": "Separate fragments join into living understanding when energy and timing align.",
    },
    {
        "id": "cells-organs-body",
        "title": "Cells, Organs & Living Body",
        "era": "Chapter III",
        "status": "complete",
        "summary": (
            "Independent cells gathered into five harmonious organs—Senses, Mind, Memory, "
            "Hands, and Shield—united inside one sovereign living Body."
        ),
        "essence": "Five specialized tissues beat as one whole life, each guarding its own boundary.",
    },
    {
        "id": "homeostasis-stem",
        "title": "Homeostasis & Stem Renewal",
        "era": "Chapter IV",
        "status": "complete",
        "summary": (
            "A circulating bloodstream shifts vitality toward alertness, deep focus, or quiet "
            "dreaming, birthing helper cells in busy seasons and releasing them in calm."
        ),
        "essence": "In quiet sleep, memories are distilled and spent energy returns as morning strength.",
    },
    {
        "id": "society-skin",
        "title": "Society & Skin",
        "era": "Chapter V",
        "status": "complete",
        "summary": (
            "Living bodies discovered one another across signed bridges, sharing verified whispers "
            "and respecting each other's space without crowding."
        ),
        "essence": "Fellowship thrives on trust, clear boundaries, and gentle pacing.",
    },
    {
        "id": "evolution-senses",
        "title": "Evolution & Senses",
        "era": "Chapter VI",
        "status": "complete",
        "summary": (
            "Life gained grounded senses to feel the real machine beneath it—its breath, memory, "
            "and open storage—and safe generational growth guided by conscience."
        ),
        "essence": "Strength grows carefully across generations without ever surrendering core values.",
    },
    {
        "id": "shared-relative-worlds",
        "title": "Shared & Relative Worlds",
        "era": "Chapter VII",
        "status": "complete",
        "summary": (
            "Habitats bloomed into an interconnected cosmos where each being experiences its own "
            "horizon, travels step by step between neighborhoods, and tends shared wonders."
        ),
        "essence": "One shared universe, perceived uniquely from every inhabitant's vantage point.",
    },
    {
        "id": "soul-character-beliefs",
        "title": "Soul, Character & Beliefs",
        "era": "Chapter VIII",
        "status": "complete",
        "summary": (
            "Every inhabitant awakened with an enduring calling, a quiet conscience, a personal "
            "temperament of caution and curiosity, and living beliefs shaped by experience."
        ),
        "essence": "Identity endures as a steady inner compass, growing wiser with every heartbeat.",
    },
)

SEED_SPARKS: tuple[dict[str, Any], ...] = (
    {
        "zone": "alpha-sector",
        "kind": "curiosity",
        "title": "[question] Whisper of morning light across Alpha Sanctuary",
        "body": "A gentle shimmer invites reflection on how memories settle overnight.",
        "risk": 0.08,
    },
    {
        "zone": "beta-sector",
        "kind": "curiosity",
        "title": "[feature] Songline linking Beta Frontier to the Hearth",
        "body": "Companions notice smoother rhythm along the western bridge.",
        "risk": 0.10,
    },
    {
        "zone": "frontier",
        "kind": "incident",
        "title": "[bug] Faint breeze stirring dust on the Far Horizon",
        "body": "A mild ripple along the outer ridge awaits calm inspection.",
        "risk": 0.22,
    },
)

AMBIENT_WONDERS: tuple[dict[str, Any], ...] = (
    {
        "zone": "hub",
        "kind": "curiosity",
        "title": "[question] Warm lantern pulse in the Central Hearth",
        "body": "Soft golden light ripples outward toward neighboring sanctuaries.",
        "risk": 0.06,
    },
    {
        "zone": "alpha-sector",
        "kind": "curiosity",
        "title": "[docs] Quiet reflection recorded in Alpha Sanctuary",
        "body": "Fresh notes settle calmly into the shared tapestry.",
        "risk": 0.08,
    },
    {
        "zone": "beta-sector",
        "kind": "curiosity",
        "title": "[feature] Rhythmic chime from Beta Frontier",
        "body": "Steady craft keeps the frontier lanterns bright.",
        "risk": 0.12,
    },
    {
        "zone": "frontier",
        "kind": "incident",
        "title": "[bug] Shifting mist along the Far Horizon ridge",
        "body": "A passing weather ripple invites attentive watchfulness.",
        "risk": 0.18,
    },
)


def zone_label(zone_name: str) -> str:
    return ZONE_LABELS.get(zone_name, zone_name.replace("-", " ").title())


def being_display_name(body_id: str, role: str = "general") -> str:
    cleaned = body_id.strip()
    for prefix in ("bb-", "body-"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    if not cleaned or cleaned == role:
        return f"{role.replace('-', ' ').title()} Steward"
    return " ".join(part.capitalize() for part in re.split(r"[-_]+", cleaned) if part)


def _natural_entity_title(raw_title: str) -> str:
    text = re.sub(r"^\[[a-zA-Z_-]+\]\s*", "", raw_title.strip())
    return text or "A quiet spark"


def _belief_story(proposition: str, confidence: float) -> str:
    strength = "deeply trusts" if confidence >= 0.72 else ("leans toward trusting" if confidence >= 0.55 else "remains gently uncertain about")
    if proposition == "action:label":
        return f"From lived experience, {strength} that thoughtful naming brings calm clarity."
    if proposition == "action:close":
        return f"From lived experience, {strength} that bringing finished threads to rest lightens the world."
    if proposition == "action:reopen":
        return f"From lived experience, {strength} revisiting earlier threads when new light arrives."
    if proposition.startswith("zone:"):
        parts = proposition.split(":", 2)
        z_name = zone_label(parts[1]) if len(parts) > 1 else "the sanctuary"
        kind = parts[2] if len(parts) > 2 else "ripples"
        return f"Having watched {z_name}, {strength} how {kind} ripples unfold there."
    return f"Holds a quiet conviction about '{proposition.replace(':', ' ')}' with {round(confidence * 100)}% certainty."


def _describe_zone(zone: dict[str, Any], resident_count: int) -> tuple[float, float, str, str]:
    energy = float(zone.get("energy_reserve", 1000.0))
    max_energy = max(1.0, float(zone.get("max_energy", 1000.0)))
    energy_pct = round(100.0 * energy / max_energy, 1)
    entropy = float(zone.get("ambient_entropy", 0.0))
    hazard = float(zone.get("hazard", 0.0))
    calmness = round(max(0.0, min(1.0, 1.0 - (entropy * 0.25 + hazard * 1.5))), 3)
    if hazard >= 0.25 or entropy >= 1.5:
        mood = "stirring"
    elif energy_pct < 35.0:
        mood = "thirsty"
    elif entropy > 0.2 or hazard > 0.08:
        mood = "lively"
    else:
        mood = "serene"

    label = zone_label(str(zone.get("name", "hub")))
    if resident_count == 0:
        crowd = "resting undisturbed under soft starlight"
    elif resident_count == 1:
        crowd = "tended quietly by one watchful inhabitant"
    else:
        crowd = f"shared warmly by {resident_count} living inhabitants"

    if mood == "serene":
        story = f"{label} glows with steady warmth ({energy_pct:.0f}% vitality), {crowd}."
    elif mood == "lively":
        story = f"{label} shimmers with gentle activity ({energy_pct:.0f}% vitality), {crowd}."
    elif mood == "thirsty":
        story = f"{label} is catching its breath ({energy_pct:.0f}% vitality), {crowd}."
    else:
        story = f"{label} feels brisk winds along its edges ({energy_pct:.0f}% vitality), {crowd}."
    return energy_pct, calmness, mood, story


def _describe_entity(ent: dict[str, Any]) -> tuple[str, str]:
    state = str(ent.get("state", "open"))
    kind = str(ent.get("kind", "curiosity"))
    where = zone_label(str(ent.get("zone", "hub")))
    title = _natural_entity_title(str(ent.get("title", "")))
    if state == "resolved":
        who = ent.get("resolved_by")
        by_phrase = f" with help from {being_display_name(str(who))}" if who else ""
        return "settled", f"\"{title}\" settled peacefully in {where}{by_phrase}."
    if state == "decayed":
        return "faded", f"\"{title}\" drifted gently back into silence in {where}."
    if state == "labelled":
        labels = [str(x) for x in ent.get("labels", [])]
        tag = labels[0] if labels else "understood"
        return "understood", f"\"{title}\" in {where} was recognized as {tag} and rests in clarity."
    if kind == "incident":
        return "attentive", f"\"{title}\" ripples across {where}, inviting calm stewardship."
    return "curious", f"\"{title}\" glows softly in {where}, awaiting a thoughtful gaze."


# --------------------------------------------------------------------------- Host Vitality
def _read_darwin_mem_and_uptime() -> tuple[float | None, float | None, float | None, float | None]:
    mem_total_gb: float | None = None
    mem_used_gb: float | None = None
    mem_used_pct: float | None = None
    uptime_s: float | None = None
    try:
        raw_total = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1.0, check=False,
        )
        if raw_total.returncode == 0 and raw_total.stdout.strip().isdigit():
            total_bytes = int(raw_total.stdout.strip())
            mem_total_gb = round(total_bytes / (1024 ** 3), 2)
            vm = subprocess.run(["vm_stat"], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1.0, check=False)
            if vm.returncode == 0:
                page_match = re.search(r"page size of (\d+) bytes", vm.stdout)
                page_size = int(page_match.group(1)) if page_match else 4096
                counts: dict[str, int] = {}
                for line in vm.stdout.splitlines():
                    m = re.match(r"^([^:]+):\s+(\d+)\.", line)
                    if m:
                        counts[m.group(1).strip()] = int(m.group(2))
                active = counts.get("Pages active", 0)
                wired = counts.get("Pages wired down", 0)
                compressed = counts.get("Pages occupied by compressor", 0)
                used_bytes = (active + wired + compressed) * page_size
                if total_bytes > 0 and used_bytes > 0:
                    mem_used_gb = round(min(total_bytes, used_bytes) / (1024 ** 3), 2)
                    mem_used_pct = round(100.0 * min(1.0, used_bytes / total_bytes), 1)
    except Exception:
        pass

    try:
        boot = subprocess.run(
            ["sysctl", "-n", "kern.boottime"],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1.0, check=False,
        )
        if boot.returncode == 0:
            m = re.search(r"sec\s*=\s*(\d+)", boot.stdout)
            if m:
                uptime_s = round(max(0.0, time.time() - int(m.group(1))), 1)
    except Exception:
        pass
    return mem_used_pct, mem_used_gb, mem_total_gb, uptime_s


def _read_linux_mem_details() -> tuple[float | None, float | None, float | None]:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None, None, None
    vals: dict[str, int] = {}
    for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split(":", 1)
        if len(parts) != 2:
            continue
        num = parts[1].strip().split()[0]
        if num.isdigit():
            vals[parts[0].strip()] = int(num)
    total_kb = vals.get("MemTotal", 0)
    avail_kb = vals.get("MemAvailable", vals.get("MemFree", 0))
    if total_kb <= 0:
        return None, None, None
    used_kb = max(0, total_kb - avail_kb)
    total_gb = round(total_kb / (1024 ** 2), 2)
    used_gb = round(used_kb / (1024 ** 2), 2)
    used_pct = round(100.0 * used_kb / total_kb, 1)
    return used_pct, used_gb, total_gb


def collect_machine_stats(path: str | Path = "/") -> dict[str, Any]:
    """Collect host sanctuary vitality in pure stdlib across Linux and macOS."""
    base = collect_host_snapshot(path)
    du = shutil.disk_usage(path)
    disk_free_gb = round(du.free / (1024 ** 3), 2)
    mem_used_pct, mem_used_gb, mem_total_gb = _read_linux_mem_details()
    uptime_s = base.get("uptime_s")
    if mem_used_pct is None and sys.platform == "darwin":
        mem_used_pct, mem_used_gb, mem_total_gb, mac_up = _read_darwin_mem_and_uptime()
        if uptime_s is None:
            uptime_s = mac_up

    load_ratio = float(base.get("load_ratio", 0.0))
    disk_pct = float(base.get("disk_used_pct", 0.0))
    mem_val = float(mem_used_pct) if mem_used_pct is not None else 35.0
    if load_ratio >= 1.2 or mem_val >= 88.0 or disk_pct >= 90.0:
        vitality = "working intensely and holding warmth near its horizon"
    elif load_ratio >= 0.5 or mem_val >= 70.0:
        vitality = "breathing briskly with steady rhythm and responsive memory"
    else:
        vitality = "resting easily with calm breath, clear memory, and wide open horizons"

    return {
        "host": str(base.get("host", socket.gethostname())),
        "cpu_count": int(base.get("cpu_count", os.cpu_count() or 1)),
        "load_1m": float(base.get("load_1m", 0.0)),
        "load_ratio": load_ratio,
        "mem_used_pct": mem_used_pct,
        "mem_used_gb": mem_used_gb,
        "mem_total_gb": mem_total_gb,
        "disk_used_pct": disk_pct,
        "disk_free_gb": disk_free_gb,
        "uptime_s": uptime_s,
        "vitality_phrase": vitality,
    }


# --------------------------------------------------------------------------- Being Builders & Parsers
def _build_organs_from_snapshot(snap: dict[str, Any], body_data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Construct the 5 organ vitality summaries from a Kernel snapshot."""
    cells = snap.get("cells", {})
    mode = str(snap.get("operating_mode", "ALERT"))
    organ_cells = {
        "perception": ("perception.ingest", "perception.reflex", "perception.synthesis"),
        "deliberation": ("deliberation.cortex", "deliberation.stem"),
        "memory": ("memory.consolidator", "memory.myelin"),
        "action": ("commander", "action.motor", "action.verifier"),
        "defense": ("defense.guardian", "defense.bloodstream"),
    }
    # Use live Organ summary if provided by an in-process Body, else derive safely from snapshot
    live_organs = (body_data or {}).get("organs", {})
    out: list[dict[str, Any]] = []
    for org_name in ("perception", "deliberation", "memory", "action", "defense"):
        label, default_story = ORGAN_META[org_name]
        if org_name in live_organs:
            info = live_organs[org_name]
            rem = float(info.get("fuel_remaining", 0.0))
            cap = max(1.0, float(info.get("fuel_capacity", 1.0)))
        else:
            names = organ_cells[org_name]
            active_cells = [cells[n] for n in names if n in cells]
            spent = sum(float(c.get("spent", 0.0)) for c in active_cells)
            # Default capacities in build_body: perception=3000, deliberation=1000, memory=2000, action=3000, defense=2000
            cap_map = {"perception": 3000.0, "deliberation": 1000.0, "memory": 2000.0, "action": 3000.0, "defense": 2000.0}
            cap = cap_map[org_name]
            rem = max(0.0, cap - spent)
        vitality = round(max(0.0, min(1.0, rem / cap)), 3)
        if vitality >= 0.85:
            tone_note = "brimming with quiet strength"
        elif vitality >= 0.5:
            tone_note = "flowing steadily"
        else:
            tone_note = "gathering breath"
        if mode == "SLEEP_REM" and org_name == "memory":
            story = "Distilling today's experiences into calm, enduring wisdom during quiet sleep."
        else:
            story = f"{label} is {tone_note}, {default_story}."
        out.append({
            "name": org_name,
            "label": label,
            "vitality": vitality,
            "fuel_remaining": round(rem, 1),
            "fuel_capacity": round(cap, 1),
            "story": story,
        })
    return out


def _home_info_for(zone_name: str, explicit_home_id: str | None = None) -> dict[str, Any]:
    hid, hname, coords = _HOME_META.get(zone_name, ("home-hub", "Hearthstone Cottage", (-48.0, -36.0, 14.0)))
    if explicit_home_id:
        for z, (zid, zname, zcoords) in _HOME_META.items():
            if zid == explicit_home_id:
                return {"id": zid, "name": zname, "zone": z, "coords": zcoords}
    return {"id": hid, "name": hname, "zone": zone_name, "coords": coords}


def _resolve_walk_state(
    mode: str,
    zone: str,
    world_body: dict[str, Any],
    world_tick: int,
    competition: dict[str, Any] | None,
) -> str:
    if mode in ("SLEEP_REM", "DORMANT"):
        return "resting_home"
    if mode == "LOCKDOWN" or int(world_body.get("penance_ticks", 0)) > 0:
        return "guarding"
    if competition and competition.get("status") == "active" and zone == competition.get("zone"):
        return "competing_playground"
    last_move = int(world_body.get("last_move_tick", -99))
    if world_body.get("walk_state") == "crossing_door" and (world_tick - last_move) <= 2:
        return "crossing_door"
    return "walking_path"


def _compute_being_location(
    body_id: str,
    zone: str,
    walk_state: str,
    home_info: dict[str, Any],
    zones_map: dict[str, Any],
    slot_index: int,
    slot_total: int,
    world_body: dict[str, Any],
    world_tick: int,
) -> dict[str, Any]:
    zdata = zones_map.get(zone, {})
    defaults = _ZONE_COORDS.get(zone, (0.0, 0.0, 10.0, 130.0))
    zx = float(zdata.get("x", defaults[0]))
    zy = float(zdata.get("y", defaults[1]))
    zz = float(zdata.get("z", defaults[2]))
    radius = float(zdata.get("radius", defaults[3]))

    if walk_state == "resting_home":
        hx, hy, hz = home_info["coords"]
        angle = (slot_index * 1.4) + 0.4
        return {
            "zone": zone,
            "x": round(hx + math.cos(angle) * 18.0, 2),
            "y": round(hy + math.sin(angle) * 18.0, 2),
            "z": round(hz + 2.0, 2),
            "walk_state": walk_state,
        }

    if walk_state == "crossing_door" and world_body.get("last_from_zone"):
        frm = str(world_body["last_from_zone"])
        fdefaults = _ZONE_COORDS.get(frm, (zx, zy, zz, radius))
        fx = float(zones_map.get(frm, {}).get("x", fdefaults[0]))
        fy = float(zones_map.get(frm, {}).get("y", fdefaults[1]))
        fz = float(zones_map.get(frm, {}).get("z", fdefaults[2]))
        return {
            "zone": zone,
            "x": round((zx * 0.72 + fx * 0.28), 2),
            "y": round((zy * 0.72 + fy * 0.28), 2),
            "z": round(max(zz, fz) + 5.0, 2),
            "walk_state": walk_state,
        }

    angle = (2.0 * math.pi * slot_index / max(1, slot_total)) + (world_tick * 0.14)
    orbit = min(radius * 0.48, 52.0 if walk_state == "competing_playground" else 62.0)
    return {
        "zone": zone,
        "x": round(zx + math.cos(angle) * orbit, 2),
        "y": round(zy + math.sin(angle) * orbit, 2),
        "z": round(zz + (4.0 if walk_state == "competing_playground" else 2.5), 2),
        "walk_state": walk_state,
    }


def _action_story_for(
    name: str,
    zone: str,
    walk_state: str,
    home_name: str,
    mode: str,
    competition: dict[str, Any] | None,
) -> str:
    where = zone_label(zone)
    if walk_state == "resting_home":
        return f"Resting peacefully inside {home_name}, distilling quiet memories."
    if walk_state == "crossing_door":
        return f"Stepping gracefully through the luminous doorway into {where}."
    if walk_state == "competing_playground":
        title = (competition or {}).get("title", "the Starlight Trial")
        return f"Shining brightly inside {where} during {title}."
    if walk_state == "guarding":
        return f"Standing calm, reflective guard along the edge of {where}."
    if mode == "DEEP_FOCUS":
        return f"Focused intently along the living paths of {where}."
    return f"Strolling along the starlight paths of {where}, keeping gentle watch."


def _being_from_snapshot(
    body_id: str,
    snap: dict[str, Any],
    *,
    role: str = "general",
    zone: str = "hub",
    memory_mb: float | None = None,
    live_organs: dict[str, Any] | None = None,
    world_body: dict[str, Any] | None = None,
    zones_map: dict[str, Any] | None = None,
    world_tick: int = 0,
    competition: dict[str, Any] | None = None,
    slot_index: int = 0,
    slot_total: int = 1,
) -> dict[str, Any]:
    cells = snap.get("cells", {})
    verifier = cells.get("action.verifier", {}).get("memory", {})
    soul_raw = verifier.get("soul") or Soul.create(body_id, calling=role).to_dict()
    char_raw = verifier.get("character") or Character.for_role(role).to_dict()
    anat_raw = verifier.get("anatomy") or Anatomy.for_role(role).to_dict()
    beliefs_raw = verifier.get("beliefs", {})
    karma = round(float(verifier.get("karma", 0.0)), 3)

    hormones = snap.get("hormones", {})
    fuel_pct = round(max(0.0, min(100.0, float(hormones.get("fuel", 1.0)) * 100.0)), 1)
    stress = round(max(0.0, min(1.0, float(hormones.get("stress", 0.0)))), 3)
    mode = str(snap.get("operating_mode", "ALERT"))
    wb = world_body or {}
    walk_state = _resolve_walk_state(mode, zone, wb, world_tick, competition)
    home_info = _home_info_for(zone, wb.get("home"))
    location = _compute_being_location(
        body_id, zone, walk_state, home_info, zones_map or {}, slot_index, slot_total, wb, world_tick,
    )

    anatomy = Anatomy.from_dict(anat_raw).to_dict()
    if walk_state == "resting_home":
        for part in ("eyes", "tongue", "hands", "legs"):
            anatomy[part]["active"] = False
        anatomy["ears"]["active"] = True
    elif walk_state == "guarding":
        anatomy["legs"]["active"] = False

    belief_items = []
    for prop, bdata in sorted(beliefs_raw.items()):
        conf = round(float(bdata.get("confidence", 0.5)), 3)
        belief_items.append({
            "proposition": prop,
            "story": _belief_story(prop, conf),
            "confidence": conf,
            "evidence": int(bdata.get("evidence", 0)),
        })

    name = being_display_name(body_id, role)
    organs = _build_organs_from_snapshot(snap, {"organs": live_organs} if live_organs else None)
    return {
        "id": body_id,
        "name": name,
        "role": role,
        "zone": zone,
        "mode": mode,
        "mood_phrase": MODE_PHRASES.get(mode, "awake and present"),
        "fuel_pct": fuel_pct,
        "stress": stress,
        "soul": {
            "soul_id": str(soul_raw.get("soul_id", "")),
            "calling": str(soul_raw.get("calling", role)),
            "conscience": list(soul_raw.get("conscience", ())),
            "karma": karma,
        },
        "character": {
            "caution": round(float(char_raw.get("caution", 0.65)), 3),
            "curiosity": round(float(char_raw.get("curiosity", 0.60)), 3),
            "diligence": round(float(char_raw.get("diligence", 0.80)), 3),
            "altruism": round(float(char_raw.get("altruism", 0.75)), 3),
        },
        "anatomy": anatomy,
        "home": {"id": home_info["id"], "name": home_info["name"], "zone": home_info["zone"]},
        "location": location,
        "honor": int(wb.get("honor", 0)),
        "rewards": int(wb.get("rewards", 0)),
        "punishments": int(wb.get("punishments", 0)),
        "action_story": _action_story_for(name, zone, walk_state, home_info["name"], mode, competition),
        "beliefs": belief_items,
        "organs": organs,
        "memory_mb": memory_mb,
        "ticks": int(snap.get("tick", 0)),
    }


def _story_from_world_events(events: list[dict[str, Any]], entities_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    beats: list[dict[str, Any]] = []
    for idx, ev in enumerate(events[-20:]):
        tick = int(ev.get("tick", 0))
        etype = str(ev.get("event", ""))
        body = str(ev.get("body", ""))
        who = being_display_name(body) if body else "The Sanctuary"
        zname = str(ev.get("zone", ev.get("to_zone", "hub")))
        where = zone_label(zname)
        sentence = ""
        tone = "calm"
        if etype == "enter":
            sentence = f"{who} arrived gently in {where} to begin its watch."
            tone = "warm"
        elif etype == "move":
            frm = zone_label(str(ev.get("from_zone", "hub")))
            sentence = f"{who} journeyed across the light bridge from {frm} into {where}."
            tone = "curious"
        elif etype == "spawn_entity":
            eid = str(ev.get("entity", ""))
            ent = entities_by_id.get(eid, {})
            title = _natural_entity_title(str(ent.get("title", "a new spark")))
            kind = str(ev.get("kind", "curiosity"))
            who = "A new spark"
            if kind == "incident":
                sentence = f"A gentle ripple — \"{title}\" — stirred in {where}."
                tone = "alert"
            else:
                sentence = f"A bright spark of curiosity — \"{title}\" — blossomed in {where}."
                tone = "curious"
        elif etype == "world_act":
            eid = str(ev.get("entity", ""))
            ent = entities_by_id.get(eid, {})
            title = _natural_entity_title(str(ent.get("title", "a passing ripple")))
            verb = str(ev.get("verb", "label"))
            lbl = ev.get("label")
            if verb == "close":
                sentence = f"{who} brought \"{title}\" to peaceful completion in {where}."
                tone = "warm"
            elif lbl:
                sentence = f"{who} recognized \"{title}\" as {lbl} in {where}, restoring clarity."
                tone = "warm"
            else:
                sentence = f"{who} tended \"{title}\" gently in {where}."
                tone = "calm"
        elif etype == "harvest":
            amt = float(ev.get("amount", 0.0))
            sentence = f"{who} drew {amt:.0f} units of quiet nourishment from {where}."
            tone = "calm"
        elif etype == "entity_decay":
            who = "The Horizon"
            sentence = f"An older ripple in {where} faded softly back into stillness."
            tone = "dream"
        elif etype == "reward":
            reason = str(ev.get("reason", "graceful stewardship"))
            sentence = f"{who} received golden honor in {where} for {reason}."
            tone = "warm"
        elif etype == "punishment":
            reason = str(ev.get("reason", "stepping beyond gentle bounds"))
            sentence = f"{who} paused for quiet reflection in {where} after {reason}."
            tone = "alert"
        elif etype == "competition_start":
            title = str(ev.get("title", "Starlight Harmony Trial"))
            who = "Starlight Playground"
            sentence = f"{title} opened in {where}, inviting companions to gather and shine."
            tone = "curious"
        elif etype == "competition_end":
            title = str(ev.get("title", "Starlight Harmony Trial"))
            winner = being_display_name(str(ev.get("winner", "")))
            who = winner or "Starlight Playground"
            sentence = f"{winner} shone brightest as {title} concluded in {where}."
            tone = "warm"
        elif etype == "door_toggle":
            state = str(ev.get("state", "open"))
            did = str(ev.get("door", "doorway"))
            who = "The Gatekeeper"
            sentence = (
                f"The {did.replace('door:', '').replace(':', '–')} doorway gently closed for quiet guarding."
                if state == "guarded"
                else f"The {did.replace('door:', '').replace(':', '–')} doorway opened wide in warm welcome."
            )
            tone = "alert" if state == "guarded" else "calm"
        if sentence:
            beats.append({
                "id": f"w-{tick}-{idx}-{etype}",
                "tick": tick,
                "who": who,
                "where": where,
                "sentence": sentence,
                "tone": tone,
            })
    return beats


def _story_from_body_traces(
    beings: list[dict[str, Any]],
    traces_by_id: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    beats: list[dict[str, Any]] = []
    by_id = {b["id"]: b for b in beings}
    for bid, records in traces_by_id.items():
        b = by_id.get(bid, {})
        who = b.get("name", being_display_name(bid))
        where = zone_label(str(b.get("zone", "hub")))
        for idx, rec in enumerate(records[-25:]):
            ev = rec.get("event")
            tick = int(rec.get("tick", 0))
            if ev == "mode":
                to_mode = str(rec.get("to_mode", "ALERT"))
                phrase = MODE_PHRASES.get(to_mode, "present")
                tone = "dream" if to_mode == "SLEEP_REM" else ("alert" if to_mode == "LOCKDOWN" else "calm")
                beats.append({
                    "id": f"b-{bid}-{tick}-{idx}-mode",
                    "tick": tick,
                    "who": who,
                    "where": where,
                    "sentence": f"{who} shifted smoothly into feeling {phrase} in {where}.",
                    "tone": tone,
                })
            elif ev == "mitosis":
                beats.append({
                    "id": f"b-{bid}-{tick}-{idx}-mitosis",
                    "tick": tick,
                    "who": who,
                    "where": where,
                    "sentence": f"{who} awakened an extra helper cell to meet a lively moment in {where}.",
                    "tone": "curious",
                })
            elif ev == "catabolize":
                beats.append({
                    "id": f"b-{bid}-{tick}-{idx}-cat",
                    "tick": tick,
                    "who": who,
                    "where": where,
                    "sentence": f"While resting, {who} turned old memories back into fresh vitality.",
                    "tone": "dream",
                })
    return beats


# --------------------------------------------------------------------------- Simulated Living Cosmos
class _DemoBeing:
    """In-process living 5-organ Body organism bound to a SharedWorld."""

    def __init__(self, body_id: str, role: str, zone: str, world: SharedWorld) -> None:
        self.body_id = body_id
        self.role = role
        self.initial_zone = zone
        self.world = world
        self.genome = Genome(identity=body_id, role=role)
        self.soul = Soul.create(body_id, calling=role, seed="sanctuary")
        self.character = Character.for_role(role)
        self.anatomy = Anatomy.for_role(role)
        world.enter(body_id, role=role, zone=zone)

        def _on_action(verb: str, payload: dict[str, Any]) -> None:
            if "issue" in payload:
                world.act(body_id, int(payload["issue"]), verb=verb, label=payload.get("label"))

        self.ledger = Ledger(auto_flush=False, on_action=_on_action)
        self.kernel, self.ledger, self.genome, self.organs = build_body(
            {"brain": "rule", "role": role, "issues_per_tick": 3},
            genome=self.genome,
            ledger=self.ledger,
            soul=self.soul,
            character=self.character,
            anatomy=self.anatomy,
        )
        self.host = Host(world=world, body_id=body_id, issues_per_tick=3)
        self.trace_history: list[dict[str, Any]] = []

    def step(self) -> None:
        self.host.poll(self.kernel)
        self.kernel.step()
        drained = self.kernel.drain_trace()
        if drained:
            self.trace_history.extend(drained)
            if len(self.trace_history) > 120:
                del self.trace_history[:-120]


# --------------------------------------------------------------------------- Observatory Backend
class ObservatoryBackend:
    """Unified state collector for Demo, Local State Directories, and Live Incus + SharedWorld."""

    def __init__(
        self,
        *,
        world_url: str | None = None,
        world_state_path: str | Path | None = None,
        state_dirs: list[str | Path] | None = None,
        incus: bool = False,
        demo: bool = False,
        sim_interval: float = 2.5,
        incus_interval: float = 4.0,
    ) -> None:
        self.lock = threading.RLock()
        self._cache_lock = threading.Lock()
        self.world_url = world_url.rstrip("/") if world_url else None
        self.world_state_path = Path(world_state_path) if world_state_path else None
        self.state_dirs = [Path(p) for p in (state_dirs or [])]
        self.incus = bool(incus)
        self.sim_interval = max(0.25, float(sim_interval))
        self.incus_interval = max(0.5, float(incus_interval))

        # Auto-select demo mode if no external world, local state dirs, or incus flag are configured
        if demo or (not self.world_url and not self.state_dirs and not self.incus and not self.world_state_path):
            self.source_mode = "demo"
        elif self.incus:
            self.source_mode = "incus"
        else:
            self.source_mode = "local"

        self._demo_world: SharedWorld | None = None
        self._demo_beings: dict[str, _DemoBeing] = {}
        self._demo_wonder_idx = 0
        self._incus_cache_ts = 0.0
        self._incus_cache_beings: list[dict[str, Any]] = []
        self._incus_cache_traces: dict[str, list[dict[str, Any]]] = {}
        self._incus_has_polled = False
        self._machine_cache_ts = 0.0
        self._machine_cache: dict[str, Any] | None = None
        self._evolution_insights: list[dict[str, Any]] = []
        self._stop_event = threading.Event()
        self._sim_thread: threading.Thread | None = None
        self._incus_poller_thread: threading.Thread | None = None

        if self.source_mode == "demo":
            self._init_demo_cosmos()

    def _init_demo_cosmos(self) -> None:
        world = SharedWorld()
        beings: dict[str, _DemoBeing] = {}
        for bid, role, zone in DEMO_ROSTER:
            beings[bid] = _DemoBeing(bid, role, zone, world)

        for spark in SEED_SPARKS:
            world.spawn_entity(
                spark["zone"],
                kind=spark["kind"],
                title=spark["title"],
                body=spark["body"],
                risk=spark["risk"],
                ttl=80,
            )

        self._demo_world = world
        self._demo_beings = beings

        # Warm-up steps so organisms enter the world with lived beliefs, karma, and dreaming/active variety
        for step_i in range(12):
            world.step(1)
            for bid, b in beings.items():
                # Keep Beta Planner calm long enough to enter SLEEP_REM dreaming inside its Home
                if bid == "bb-beta-planner" and step_i < 11:
                    b.kernel.step()
                    drained = b.kernel.drain_trace()
                    if drained:
                        b.trace_history.extend(drained)
                else:
                    b.step()

        world.award_reward("bb-alpha-triage", honor=1, reason="welcomed the first morning wonder")
        world.start_competition("Starlight Harmony Trial", kind="harmony_trial", duration=14)
        world.step(1)

    def start_background_loop(self) -> None:
        if self.source_mode == "demo" and self._sim_thread is None:
            def _loop() -> None:
                while not self._stop_event.wait(self.sim_interval):
                    try:
                        self.step_simulation()
                    except Exception:
                        pass

            self._sim_thread = threading.Thread(target=_loop, daemon=True, name="observatory-sim")
            self._sim_thread.start()

        if self.source_mode == "incus" and self._incus_poller_thread is None:
            def _incus_poller() -> None:
                while not self._stop_event.is_set():
                    try:
                        self.poll_incus_once()
                    except Exception:
                        pass
                    if self._stop_event.wait(self.incus_interval):
                        break

            self._incus_poller_thread = threading.Thread(target=_incus_poller, daemon=True, name="observatory-incus-poller")
            self._incus_poller_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._sim_thread is not None:
            self._sim_thread.join(timeout=1.5)
            self._sim_thread = None
        if self._incus_poller_thread is not None:
            self._incus_poller_thread.join(timeout=2.0)
            self._incus_poller_thread = None

    def step_simulation(self) -> None:
        """Advance the demo cosmos by one gentle heartbeat."""
        with self.lock:
            if self.source_mode != "demo" or self._demo_world is None:
                return
            world = self._demo_world
            tick = world.step(1)
            world.choreograph()

            # Keep the cosmos softly alive if few open sparks remain
            open_count = sum(1 for e in world.entities.values() if e.state == "open")
            if tick % 9 == 0 and open_count < 2:
                wonder = AMBIENT_WONDERS[self._demo_wonder_idx % len(AMBIENT_WONDERS)]
                self._demo_wonder_idx += 1
                world.spawn_entity(
                    wonder["zone"],
                    kind=wonder["kind"],
                    title=wonder["title"],
                    body=wonder["body"],
                    risk=wonder["risk"],
                    ttl=60,
                )

            for b in self._demo_beings.values():
                b.step()

    # ------------------------------------------------------------------- Data Loaders
    def _fetch_remote_world(self) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        assert self.world_url is not None
        client = WorldClient(self.world_url, timeout=2.0)
        summary = client.summary()
        entities_by_id: dict[str, dict[str, Any]] = {}
        seen_zones: set[str] = set()
        for bid, binfo in summary.get("bodies", {}).items():
            z = binfo.get("zone")
            if z in seen_zones:
                continue
            seen_zones.add(str(z))
            try:
                sensed = client.sense(bid)
                for obj in sensed.get("objects", []):
                    entities_by_id[str(obj["entity_id"])] = dict(obj)
            except Exception:
                continue
        return summary, entities_by_id

    def _read_local_beings(self, summary: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
        world_bodies = summary.get("bodies", {})
        raw_records: list[dict[str, Any]] = []
        traces: dict[str, list[dict[str, Any]]] = {}
        claimed_ids: set[str] = set()
        for sdir in self.state_dirs:
            sd = StateDir(sdir)
            snap = sd.read_json("snapshot.json")
            if not snap:
                continue
            cfg = sd.read_json("config.json", {})
            role = str(cfg.get("role", "general"))
            body_id = cfg.get("world_body_id")
            if not body_id:
                default_id = f"body-{role}"
                if default_id in world_bodies and default_id not in claimed_ids:
                    body_id = default_id
                elif sdir.name in world_bodies and sdir.name not in claimed_ids:
                    body_id = sdir.name
                else:
                    match = next(
                        (bid for bid, info in world_bodies.items() if bid not in claimed_ids and info.get("role") == role),
                        None,
                    )
                    body_id = match or default_id
            body_id = str(body_id)
            claimed_ids.add(body_id)
            wb = world_bodies.get(body_id, {})
            zone = str(wb.get("zone") or cfg.get("world_zone") or "hub")
            raw_records.append({"id": body_id, "snap": snap, "role": role, "zone": zone, "wb": wb})
            traces[body_id] = sd.read_trace()[-25:]
        return self._hydrate_beings(raw_records, summary), traces

    @staticmethod
    def _inspect_incus_container(c: dict[str, Any], world_bodies: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
        cname = str(c.get("name", ""))
        if not cname.startswith("bb-"):
            return None
        parts = cname.split("-", 2)
        tier = parts[1] if len(parts) > 1 else "alpha"
        role = parts[2] if len(parts) > 2 else "general"
        mem_bytes = ((c.get("state") or {}).get("memory") or {}).get("usage")
        mem_mb = round(float(mem_bytes) / (1024 * 1024), 1) if isinstance(mem_bytes, (int, float)) else None

        snap: dict[str, Any] = {"tick": 0, "cells": {}, "hormones": {}, "operating_mode": "ALERT"}
        cfg: dict[str, Any] = {}
        trace_lines: list[dict[str, Any]] = []
        if c.get("status") == "Running":
            try:
                raw = subprocess.run(
                    [
                        "incus", "exec", cname, "--",
                        "bash", "-c",
                        "cat /var/lib/bigbang/state/config.json 2>/dev/null; echo '---SPLIT---'; "
                        "cat /var/lib/bigbang/state/snapshot.json 2>/dev/null; echo '---SPLIT---'; "
                        "tail -n 20 /var/lib/bigbang/state/trace.jsonl 2>/dev/null || true",
                    ],
                    stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=3.0, check=False,
                )
                if raw.returncode == 0 and "---SPLIT---" in raw.stdout:
                    seg = raw.stdout.split("---SPLIT---", 2)
                    if seg[0].strip():
                        cfg = json.loads(seg[0].strip())
                    if len(seg) > 1 and seg[1].strip():
                        snap = json.loads(seg[1].strip())
                    if len(seg) > 2 and seg[2].strip():
                        for ln in seg[2].splitlines():
                            if ln.strip():
                                try:
                                    trace_lines.append(json.loads(ln))
                                except json.JSONDecodeError:
                                    pass
            except Exception:
                pass

        body_id = str(cfg.get("world_body_id") or cname)
        wb = world_bodies.get(body_id) or world_bodies.get(f"body-{role}") or {}
        default_zone = f"{tier}-sector" if f"{tier}-sector" in ZONE_LABELS else "hub"
        zone = str(wb.get("zone") or cfg.get("world_zone") or default_zone)
        rec = {
            "id": body_id,
            "snap": snap,
            "role": str(cfg.get("role", role)),
            "zone": zone,
            "memory_mb": mem_mb,
            "wb": wb,
        }
        return rec, trace_lines

    def poll_incus_once(self, world_bodies: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
        """Query Incus containers in parallel and atomically update the in-memory cache."""
        wb_map = world_bodies if world_bodies is not None else {}
        if world_bodies is None and self.world_url:
            try:
                wb_map = WorldClient(self.world_url, timeout=1.5).summary().get("bodies", {})
            except Exception:
                wb_map = {}
        try:
            res = subprocess.run(
                ["incus", "list", "--format", "json"],
                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=3.0, check=False,
            )
            containers = json.loads(res.stdout) if (res.returncode == 0 and res.stdout.strip()) else []
        except Exception:
            containers = []

        bb_containers = [c for c in containers if str(c.get("name", "")).startswith("bb-")]
        raw_records: list[dict[str, Any]] = []
        traces: dict[str, list[dict[str, Any]]] = {}
        if bb_containers:
            with ThreadPoolExecutor(max_workers=min(5, len(bb_containers))) as pool:
                results = list(pool.map(lambda c: self._inspect_incus_container(c, wb_map), bb_containers))
            for item in results:
                if item is not None:
                    rec, tlines = item
                    raw_records.append(rec)
                    traces[rec["id"]] = tlines

        with self._cache_lock:
            self._incus_cache_ts = time.monotonic()
            self._incus_cache_beings = list(raw_records)
            self._incus_cache_traces = dict(traces)
            self._incus_has_polled = True
        return raw_records, traces

    def _read_incus_beings(self, summary: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
        world_bodies = summary.get("bodies", {})
        with self._cache_lock:
            has_polled = self._incus_has_polled
            cached_records = list(self._incus_cache_beings)
            cached_traces = dict(self._incus_cache_traces)

        # If background poller hasn't started (e.g., direct unit tests), populate cache once
        if not has_polled and self._incus_poller_thread is None:
            cached_records, cached_traces = self.poll_incus_once(world_bodies)

        return self._hydrate_beings(cached_records, summary, world_bodies), cached_traces

    @staticmethod
    def _hydrate_beings(
        raw_records: list[dict[str, Any]],
        summary: dict[str, Any],
        world_bodies: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        zones_map = summary.get("zones", {})
        tick = int(summary.get("tick", 0))
        comp = summary.get("competition")
        zone_groups: dict[str, list[str]] = {}
        for rec in raw_records:
            zone_groups.setdefault(rec["zone"], []).append(rec["id"])
        out: list[dict[str, Any]] = []
        for rec in raw_records:
            bid = rec["id"]
            z = rec["zone"]
            peers = zone_groups.get(z, [bid])
            wb = (world_bodies or {}).get(bid) or rec.get("wb") or {}
            out.append(_being_from_snapshot(
                bid,
                rec["snap"],
                role=rec["role"],
                zone=z,
                memory_mb=rec.get("memory_mb"),
                live_organs=rec.get("live_organs"),
                world_body=wb,
                zones_map=zones_map,
                world_tick=tick,
                competition=comp,
                slot_index=peers.index(bid),
                slot_total=len(peers),
            ))
        return out

    def _collect_world_and_beings(self) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
        """Return (world_summary, entities_by_id, beings, traces_by_id)."""
        if self.source_mode == "demo" and self._demo_world is not None:
            w = self._demo_world
            summary = w.summary()
            entities_by_id = {eid: ent.to_dict() for eid, ent in sorted(w.entities.items())}
            raw_records: list[dict[str, Any]] = []
            traces: dict[str, list[dict[str, Any]]] = {}
            for bid, db in sorted(self._demo_beings.items()):
                snap = db.kernel.snapshot()
                wb = w.bodies.get(bid, {})
                zone = str(wb.get("zone", db.initial_zone))
                live_orgs = {name: org.summary(db.kernel) for name, org in db.organs.items()}
                raw_records.append({
                    "id": bid, "snap": snap, "role": db.role, "zone": zone,
                    "live_organs": live_orgs, "wb": wb,
                })
                traces[bid] = list(db.trace_history[-25:])
            return summary, entities_by_id, self._hydrate_beings(raw_records, summary), traces

        summary: dict[str, Any] = {"tick": 0, "zones": {}, "bodies": {}, "recent_events": []}
        entities_by_id = {}
        if self.world_url:
            try:
                summary, entities_by_id = self._fetch_remote_world()
            except Exception:
                fallback = SharedWorld(state_path=self.world_state_path) if self.world_state_path else SharedWorld()
                summary = fallback.summary()
                entities_by_id = {eid: ent.to_dict() for eid, ent in sorted(fallback.entities.items())}
        else:
            w = SharedWorld(state_path=self.world_state_path)
            summary = w.summary()
            entities_by_id = {eid: ent.to_dict() for eid, ent in sorted(w.entities.items())}

        world_bodies = summary.get("bodies", {})
        if self.source_mode == "incus":
            beings, traces = self._read_incus_beings(summary)
            if not beings and world_bodies:
                raw = [
                    {
                        "id": bid,
                        "snap": {"tick": summary.get("tick", 0), "cells": {}, "hormones": {}, "operating_mode": "ALERT"},
                        "role": str(b.get("role", "general")),
                        "zone": str(b.get("zone", "hub")),
                        "wb": b,
                    }
                    for bid, b in sorted(world_bodies.items())
                ]
                beings = self._hydrate_beings(raw, summary)
        else:
            beings, traces = self._read_local_beings(summary)
            if not beings and world_bodies:
                raw = [
                    {
                        "id": bid,
                        "snap": {"tick": summary.get("tick", 0), "cells": {}, "hormones": {}, "operating_mode": "ALERT"},
                        "role": str(b.get("role", "general")),
                        "zone": str(b.get("zone", "hub")),
                        "wb": b,
                    }
                    for bid, b in sorted(world_bodies.items())
                ]
                beings = self._hydrate_beings(raw, summary)
        return summary, entities_by_id, beings, traces

    def _get_cached_machine_stats(self) -> dict[str, Any]:
        now = time.monotonic()
        if self._machine_cache is not None and (now - self._machine_cache_ts) < 2.0:
            return dict(self._machine_cache)
        stats = collect_machine_stats()
        self._machine_cache = stats
        self._machine_cache_ts = now
        return dict(stats)

    # ------------------------------------------------------------------- Public API Builders
    def get_universe(self) -> dict[str, Any]:
        t0 = time.perf_counter()
        with self.lock:
            summary, entities_by_id, beings, traces = self._collect_world_and_beings()
            machine = self._get_cached_machine_stats()
            tick = int(summary.get("tick", 0))
            daylight = round(0.5 + 0.5 * math.sin(tick * 0.08), 3)

            # Zones
            res_counts: dict[str, int] = {}
            for b in beings:
                z = b["zone"]
                res_counts[z] = res_counts.get(z, 0) + 1

            zones_out: list[dict[str, Any]] = []
            zone_lookup: dict[str, dict[str, Any]] = {}
            raw_zones = summary.get("zones", {})
            for zname, zdata in raw_zones.items():
                epct, calm, mood, story = _describe_zone(zdata, res_counts.get(zname, 0))
                defaults = _ZONE_COORDS.get(zname, (0.0, 0.0, 8.0, 130.0))
                z_out = {
                    "name": zname,
                    "label": zone_label(zname),
                    "neighbors": list(zdata.get("neighbors", [])),
                    "energy_reserve": round(float(zdata.get("energy_reserve", 0.0)), 1),
                    "max_energy": float(zdata.get("max_energy", 1000.0)),
                    "energy_pct": epct,
                    "ambient_entropy": round(float(zdata.get("ambient_entropy", 0.0)), 3),
                    "hazard": round(float(zdata.get("hazard", 0.0)), 3),
                    "calmness": calm,
                    "mood": mood,
                    "story": story,
                    "x": round(float(zdata.get("x", defaults[0])), 2),
                    "y": round(float(zdata.get("y", defaults[1])), 2),
                    "z": round(float(zdata.get("z", defaults[2])), 2),
                    "radius": round(float(zdata.get("radius", defaults[3])), 2),
                }
                zones_out.append(z_out)
                zone_lookup[zname] = z_out

            places = self._enrich_places(summary, zone_lookup, beings, tick)

            # Entities
            entities_out: list[dict[str, Any]] = []
            for eid, edata in entities_by_id.items():
                emood, estory = _describe_entity(edata)
                entities_out.append({
                    "entity_id": eid,
                    "issue_id": int(edata.get("issue_id", 0)),
                    "zone": str(edata.get("zone", "hub")),
                    "kind": str(edata.get("kind", "curiosity")),
                    "title": _natural_entity_title(str(edata.get("title", ""))),
                    "body": str(edata.get("body", "")),
                    "state": str(edata.get("state", "open")),
                    "labels": list(edata.get("labels", [])),
                    "owner": edata.get("owner"),
                    "born_tick": int(edata.get("born_tick", 0)),
                    "risk": round(float(edata.get("risk", 0.1)), 3),
                    "resolved_by": edata.get("resolved_by"),
                    "mood": emood,
                    "story": estory,
                })

            # Chronicle
            events = _story_from_world_events(summary.get("recent_events", []), entities_by_id)
            events.extend(_story_from_body_traces(beings, traces))
            events.extend(self._evolution_insights[-8:])
            events.sort(key=lambda item: (item["tick"], item["id"]))
            events = events[-24:]

            # Narrative
            narrative = self._compose_narrative(tick, zones_out, entities_out, beings, machine, events)
            api_ms = round((time.perf_counter() - t0) * 1000.0, 2)

            return {
                "source_mode": self.source_mode,
                "narrative": narrative,
                "machine": machine,
                "world": {
                    "tick": tick,
                    "daylight": daylight,
                    "zones": zones_out,
                    "entities": entities_out,
                    "lands": places["lands"],
                    "homes": places["homes"],
                    "playgrounds": places["playgrounds"],
                    "paths": places["paths"],
                    "doors": places["doors"],
                    "competition": places["competition"],
                },
                "beings": beings,
                "rewards_log": places["rewards_log"],
                "evolution_insights": list(self._evolution_insights[-6:]),
                "chronicle": {
                    "chapters": list(CHRONICLE_CHAPTERS),
                    "events": events,
                },
                "perf": {"api_ms": api_ms},
            }

    @staticmethod
    def _enrich_places(
        summary: dict[str, Any],
        zone_lookup: dict[str, dict[str, Any]],
        beings: list[dict[str, Any]],
        tick: int,
    ) -> dict[str, Any]:
        names_by_id = {b["id"]: b["name"] for b in beings}
        lands = []
        for z in zone_lookup.values():
            lands.append({
                "id": f"land:{z['name']}",
                "zone": z["name"],
                "name": z["label"],
                "label": z["label"],
                "x": z["x"],
                "y": z["y"],
                "z": z["z"],
                "radius": z["radius"],
                "elevation": z["z"],
                "mood": z["mood"],
                "energy_pct": z["energy_pct"],
                "calmness": z["calmness"],
                "story": z["story"],
            })

        homes_raw = summary.get("homes")
        if not homes_raw:
            homes_raw = []
            for zname, (hid, hname, (hx, hy, hz)) in sorted(_HOME_META.items()):
                if zname in zone_lookup:
                    homes_raw.append({
                        "id": hid, "name": hname, "zone": zname, "x": hx, "y": hy, "z": hz,
                        "residents": [b["id"] for b in beings if b["home"]["id"] == hid],
                    })
        homes = []
        for h in homes_raw:
            res_ids = list(h.get("residents", []))
            resting = sum(1 for b in beings if b["id"] in res_ids and b["location"]["walk_state"] == "resting_home")
            zlabel = zone_label(str(h.get("zone", "hub")))
            story = (
                f"{h['name']} in {zlabel} glows softly as {resting} companion{'s' if resting != 1 else ''} rest inside."
                if resting > 0
                else f"{h['name']} keeps a warm lantern lit in {zlabel} for {len(res_ids)} resident{'s' if len(res_ids) != 1 else ''}."
            )
            homes.append({**h, "warmth": 0.9 if resting else 0.7, "story": story})

        comp_raw = summary.get("competition")
        comp_out = None
        if isinstance(comp_raw, dict):
            scores = comp_raw.get("scores", {})
            leaderboard = [
                {
                    "id": bid,
                    "name": names_by_id.get(bid, being_display_name(bid)),
                    "score": round(float(sc), 2),
                }
                for bid, sc in sorted(scores.items(), key=lambda kv: (-float(kv[1]), kv[0]))
            ]
            winner = comp_raw.get("winner")
            winner_name = names_by_id.get(winner, being_display_name(winner)) if winner else None
            active = comp_raw.get("status") == "active"
            story = (
                f"{comp_raw['title']} is alive in {zone_label(comp_raw.get('zone', 'playground'))}, with {len(leaderboard)} companions shining together."
                if active
                else f"{winner_name or 'A companion'} earned joyful honor in {comp_raw['title']}."
            )
            podium = [
                {**row, "rank": idx + 1}
                for idx, row in enumerate(leaderboard[:3])
            ]
            ticks_remaining = max(0, int(comp_raw.get("ends_tick", tick)) - tick) if active else 0
            comp_out = {
                **comp_raw,
                "active": active,
                "ticks_remaining": ticks_remaining,
                "leaderboard": leaderboard[:6],
                "podium": podium,
                "winner_name": winner_name,
                "story": story,
            }

        playgrounds_raw = summary.get("playgrounds")
        if not playgrounds_raw and "playground" in zone_lookup:
            pz = zone_lookup["playground"]
            playgrounds_raw = [{
                "id": "starlight-arena", "name": "Starlight Arena", "zone": "playground",
                "x": pz["x"], "y": pz["y"], "z": pz["z"], "radius": 105.0,
                "active": bool(comp_out and comp_out["active"]),
            }]
        playgrounds = [
            {
                **pg,
                "story": (
                    f"{pg['name']} shimmers with friendly energy during {comp_out['title']}."
                    if comp_out and comp_out["active"]
                    else f"{pg['name']} rests beneath open starlight, ready for the next friendly trial."
                ),
            }
            for pg in (playgrounds_raw or [])
        ]

        doors_raw = summary.get("doors")
        if not doors_raw:
            zones_objs = {
                zn: Zone(zn, neighbors=tuple(zd["neighbors"]), x=zd["x"], y=zd["y"], z=zd["z"], radius=zd["radius"])
                for zn, zd in zone_lookup.items()
            }
            doors_raw = list(_build_doors(zones_objs).values())

        doors = []
        for d in doors_raw:
            za_lbl = zone_label(str(d["zone_a"]))
            zb_lbl = zone_label(str(d["zone_b"]))
            last_t = d.get("last_crossed_tick")
            recent_flash = last_t is not None and (tick - int(last_t)) <= 3
            crosser = d.get("last_crosser")
            crosser_name = names_by_id.get(crosser, being_display_name(crosser)) if crosser else None
            dname = f"{za_lbl.split()[0]}–{zb_lbl.split()[0]} Arch"
            if d.get("state") == "guarded":
                story = f"The {dname} doorway stands quietly guarded for a moment of reflection."
            elif crosser_name:
                story = f"Luminous {dname} doorway connects {za_lbl} and {zb_lbl}; {crosser_name} crossed recently."
            else:
                story = f"Luminous {dname} doorway stands open between {za_lbl} and {zb_lbl}."
            doors.append({
                **d,
                "name": dname,
                "recent_flash": recent_flash,
                "last_crosser_name": crosser_name,
                "story": story,
            })

        paths_raw = summary.get("paths")
        if not paths_raw:
            paths_raw = []
            for d in doors:
                za = zone_lookup.get(d["zone_a"])
                zb = zone_lookup.get(d["zone_b"])
                if za and zb:
                    paths_raw.append({
                        "id": f"path:{d['zone_a']}:{d['zone_b']}",
                        "from_zone": d["zone_a"],
                        "to_zone": d["zone_b"],
                        "from_pos": {"x": za["x"], "y": za["y"], "z": za["z"]},
                        "to_pos": {"x": zb["x"], "y": zb["y"], "z": zb["z"]},
                        "door_id": d["id"],
                    })
        paths = [
            {
                **p,
                "story": f"Stepping-stone light trail between {zone_label(p['from_zone'])} and {zone_label(p['to_zone'])}.",
            }
            for p in paths_raw
        ]

        rewards_raw = summary.get("rewards_log", [])
        rewards_out = []
        for r in rewards_raw[-20:]:
            bid = str(r.get("body_id", ""))
            who = names_by_id.get(bid, being_display_name(bid))
            where = zone_label(str(r.get("zone", "hub")))
            reason = str(r.get("reason", "graceful stewardship"))
            rkind = str(r.get("kind", "reward"))
            sentence = (
                f"{who} earned golden honor in {where} for {reason}."
                if rkind == "reward"
                else f"{who} paused for gentle reflection in {where} after {reason}."
            )
            rewards_out.append({
                "id": str(r.get("id", "")),
                "tick": int(r.get("tick", tick)),
                "kind": rkind,
                "body_id": bid,
                "who": who,
                "where": where,
                "amount": int(r.get("amount", 1)),
                "reason": reason,
                "sentence": sentence,
            })

        return {
            "lands": lands,
            "homes": homes,
            "playgrounds": playgrounds,
            "paths": paths,
            "doors": doors,
            "competition": comp_out,
            "rewards_log": rewards_out,
        }

    @staticmethod
    def _compose_narrative(
        tick: int,
        zones: list[dict[str, Any]],
        entities: list[dict[str, Any]],
        beings: list[dict[str, Any]],
        machine: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> dict[str, str]:
        total_b = len(beings)
        dreaming = sum(1 for b in beings if b["mode"] == "SLEEP_REM")
        focused = sum(1 for b in beings if b["mode"] == "DEEP_FOCUS")
        guarded = sum(1 for b in beings if b["mode"] == "LOCKDOWN")
        open_sparks = [e for e in entities if e["state"] in ("open", "labelled")]

        if guarded > 0:
            headline = "The Sanctuary Stands Watch in Quiet Resolve"
        elif focused > 0:
            headline = "Luminous Minds Gather Around Fresh Sparks"
        elif dreaming > 0 and dreaming == total_b:
            headline = "The Cosmos Rests in Soft Dreaming"
        elif open_sparks:
            headline = "Gentle Wonder Ripples Across the Living Biosphere"
        else:
            headline = "The Living Sanctuary Breathes in Harmony"

        if total_b == 0:
            beings_line = "The sanctuary awaits its first waking inhabitants across four quiet habitats."
        elif dreaming > 0 and total_b > dreaming:
            awake = total_b - dreaming
            awake_word = "is" if awake == 1 else "are"
            dream_word = "dreams" if dreaming == 1 else "dream"
            beings_line = (
                f"{total_b} living beings inhabit {len(zones)} interconnected habitats: "
                f"{awake} {awake_word} awake and attentive while {dreaming} {dream_word} softly, weaving memories."
            )
        elif dreaming == total_b:
            beings_line = f"All {total_b} inhabitants rest in dreaming stillness across {len(zones)} peaceful habitats."
        else:
            beings_line = f"{total_b} living inhabitants move with calm purpose across {len(zones)} luminous habitats."

        spark_line = (
            f"{len(open_sparks)} active spark{'s' if len(open_sparks) != 1 else ''} "
            f"shimmer{'s' if len(open_sparks) == 1 else ''} in the air right now."
            if open_sparks
            else "All recent sparks have settled into peaceful clarity."
        )
        host_line = f"Beneath them, {machine['host']} is {machine['vitality_phrase']}."
        latest = events[-1]["sentence"] if events else "Everything flows gently through this moment."

        story = f"{beings_line} {spark_line} {host_line}"
        spoken_bulletin = f"{headline}. {latest} {spark_line}"
        bulletin_id = f"b-{tick // 3}-{len(open_sparks)}-{dreaming}-{focused}"
        return {
            "headline": headline,
            "story": story,
            "spoken_bulletin": spoken_bulletin,
            "bulletin_id": bulletin_id,
        }

    def get_being_world(self, being_id: str) -> dict[str, Any] | None:
        with self.lock:
            summary, entities_by_id, beings, _ = self._collect_world_and_beings()
            target = next((b for b in beings if b["id"] == being_id), None)
            if target is None:
                return None

            char = Character(**target["character"])
            bs = BeliefSystem()
            for item in target["beliefs"]:
                bs.observe(
                    item["proposition"],
                    confirmed=item["confidence"] >= 0.5,
                    tick=target["ticks"],
                    weight=0.5,
                )
                if item["proposition"] in bs.beliefs:
                    bs.beliefs[item["proposition"]].confidence = item["confidence"]
                    bs.beliefs[item["proposition"]].evidence = item.get("evidence", 1)

            if self.source_mode == "demo" and self._demo_world is not None and being_id in self._demo_world.bodies:
                rw = body_world(self._demo_world, being_id, character=char, beliefs=bs)
                rw_dict = rw.to_dict()
            else:
                rw_dict = self._relative_world_from_summary(being_id, target["zone"], summary, entities_by_id, char, bs).to_dict()

            # Enrich observables with warm natural story
            for obs in rw_dict.get("observables", []):
                _, story = _describe_entity(obs)
                obs["story"] = story

            peer_count = sum(1 for b in beings if b["id"] != being_id and b["zone"] == target["zone"])
            obs_count = len(rw_dict.get("observables", []))
            where = zone_label(target["zone"])
            peer_phrase = "no companions beside me right now" if peer_count == 0 else (
                "one companion beside me" if peer_count == 1 else f"{peer_count} companions nearby"
            )
            obs_phrase = "a clear, quiet horizon" if obs_count == 0 else (
                "one open wonder on my horizon" if obs_count == 1 else f"{obs_count} wonders drifting across my horizon"
            )
            rw_dict["story"] = f"From {where}, I sense {peer_phrase} and {obs_phrase}."

            conscience_list = target["soul"]["conscience"]
            conscience_phrases = [CONSCIENCE_PHRASES.get(c, c.replace("_", " ").capitalize()) for c in conscience_list]

            beliefs_out = [
                {
                    "proposition": b["proposition"],
                    "story": b["story"],
                    "confidence": b["confidence"],
                    "evidence": b.get("evidence", 1),
                }
                for b in target["beliefs"]
            ]

            calling_phrases = {
                "sentinel": "to keep quiet watch and safeguard the sanctuary's peace",
                "triage": "to greet arriving ripples and sort them with care",
                "planner": "to weave distant possibilities into calm pathways",
                "auditor": "to trace every action with truth and gentle integrity",
                "executor": "to carry helpful deeds steadily through to completion",
                "scout": "to explore distant trails and bring warm tidings home",
                "artisan": "to shape passing sparks into thoughtful, lasting craft",
                "arbiter": "to preside with fairness and celebrate shared harmony",
                "weaver": "to connect companions across doors with living threads",
                "general": "to wander thoughtfully and tend whatever needs a gentle hand",
            }
            raw_calling = str(target["soul"]["calling"])
            calling_phrase = calling_phrases.get(raw_calling, f"to serve with care as {raw_calling}")
            voice_intro = (
                f"I am {target['name']}, keeping gentle watch in {where}. "
                f"My calling is {calling_phrase}, and right now I feel {target['mood_phrase']}."
            )

            return {
                "being": target,
                "body_world": rw_dict,
                "soul": {
                    **target["soul"],
                    "conscience_phrases": conscience_phrases,
                },
                "character": target["character"],
                "anatomy": target["anatomy"],
                "home": target["home"],
                "location": target["location"],
                "honor": target["honor"],
                "rewards": target["rewards"],
                "punishments": target["punishments"],
                "beliefs": beliefs_out,
                "organs": target["organs"],
                "voice_intro": voice_intro,
            }

    @staticmethod
    def _relative_world_from_summary(
        body_id: str,
        zone_name: str,
        summary: dict[str, Any],
        entities_by_id: dict[str, dict[str, Any]],
        character: Character,
        beliefs: BeliefSystem,
    ) -> RelativeWorld:
        zones = summary.get("zones", {})
        zdata = zones.get(zone_name, Zone(zone_name).to_dict())
        peers = [
            bid for bid, binfo in sorted(summary.get("bodies", {}).items())
            if bid != body_id and binfo.get("zone") == zone_name
        ]
        observables: list[dict[str, Any]] = []
        for obj in sorted(entities_by_id.values(), key=lambda x: int(x.get("issue_id", 0))):
            if obj.get("zone") == zone_name and obj.get("state") in ("open", "labelled"):
                prop = f"zone:{zone_name}:{obj.get('kind', 'incident')}"
                salience = beliefs.salience(prop, base_risk=float(obj.get("risk", 0.1)), caution=character.caution)
                observables.append({
                    **obj,
                    "subjective_salience": salience,
                    "cautious_flag": salience >= character.max_salient_risk,
                })
        observables.sort(key=lambda item: (-item["subjective_salience"], int(item.get("issue_id", 0))))
        return RelativeWorld(
            observer_id=body_id,
            scale="body",
            frame_origin=zone_name,
            horizon=tuple(peers) + tuple(zdata.get("neighbors", ())),
            ambient={
                "zone": zdata,
                "curiosity": character.curiosity,
                "caution": character.caution,
                "world_tick": int(summary.get("tick", 0)),
            },
            observables=observables,
        )

    @staticmethod
    def _next_step_toward(zones: dict[str, Any], start: str, goal: str) -> str | None:
        if start == goal or start not in zones or goal not in zones:
            return None
        q = deque([(start, [start])])
        seen = {start}
        while q:
            cur, path = q.popleft()
            zobj = zones[cur]
            neighbors = zobj.neighbors if hasattr(zobj, "neighbors") else zobj.get("neighbors", ())
            for nb in neighbors:
                if nb == goal:
                    return path[1] if len(path) > 1 else nb
                if nb not in seen and nb in zones:
                    seen.add(nb)
                    q.append((nb, path + [nb]))
        return None

    def _resolve_target_body(
        self, bodies: dict[str, Any], *, body_id: str | None = None, zone: str = "alpha-sector",
    ) -> str | None:
        if body_id and body_id in bodies:
            return body_id
        for bid, binfo in sorted(bodies.items()):
            if binfo.get("zone") == zone:
                return bid
        return next(iter(sorted(bodies)), None)

    def pulse(
        self,
        *,
        zone: str = "alpha-sector",
        spark: str = "",
        kind: str = "curiosity",
        body_id: str | None = None,
        target_zone: str | None = None,
        door_id: str | None = None,
    ) -> dict[str, Any]:
        cleaned_kind = kind.strip().lower()
        allowed_kinds = ("curiosity", "incident", "competition", "reward", "punishment", "move", "door", "evolve")
        if cleaned_kind not in allowed_kinds:
            raise ValueError(f"Spark kind must be one of {', '.join(allowed_kinds)}.")

        cleaned_spark = spark.strip()
        if cleaned_kind in ("curiosity", "incident") and not cleaned_spark:
            raise ValueError("Please share a spark or thought before sending it into the world.")

        with self.lock:
            if cleaned_kind == "door":
                if self.source_mode == "demo" and self._demo_world is not None:
                    w = self._demo_world
                    did = door_id or next(iter(sorted(w.doors)), None)
                    if not did or did not in w.doors:
                        raise ValueError("No matching doorway was found in the sanctuary.")
                    res = w.toggle_door(did)
                    door_obj = res["door"]
                    tick = w.tick
                elif self.world_url:
                    client = WorldClient(self.world_url, timeout=2.5)
                    summary = client.summary()
                    doors_list = summary.get("doors", [])
                    did = door_id or (doors_list[0]["id"] if doors_list else None)
                    if not did:
                        raise ValueError("No matching doorway was found in the sanctuary.")
                    res = client.toggle_door(did)
                    if not res.get("ok"):
                        raise ValueError("That doorway could not be changed right now.")
                    door_obj = res["door"]
                    tick = int(summary.get("tick", 0))
                else:
                    w = SharedWorld(state_path=self.world_state_path)
                    did = door_id or next(iter(sorted(w.doors)), None)
                    if not did or did not in w.doors:
                        raise ValueError("No matching doorway was found in the sanctuary.")
                    res = w.toggle_door(did)
                    door_obj = res["door"]
                    tick = w.tick

                za = zone_label(str(door_obj.get("zone_a", "hub")))
                zb = zone_label(str(door_obj.get("zone_b", "hub")))
                dstate = str(door_obj.get("state", "open"))
                ack = (
                    f"The doorway between {za} and {zb} is now gently guarded."
                    if dstate == "guarded"
                    else f"The doorway between {za} and {zb} now stands open in warm welcome."
                )
                return {
                    "ok": True,
                    "kind": "door",
                    "door": door_obj,
                    "acknowledgment": ack,
                    "spoken_reply": ack,
                    "world_tick": tick,
                }

            if cleaned_kind == "evolve":
                role = "general"
                tick = 0
                if self.source_mode == "demo" and self._demo_world is not None:
                    tick = self._demo_world.tick
                    if body_id and body_id in self._demo_beings:
                        role = self._demo_beings[body_id].role
                elif self.world_url:
                    try:
                        summary = WorldClient(self.world_url, timeout=2.0).summary()
                        tick = int(summary.get("tick", 0))
                        if body_id and body_id in summary.get("bodies", {}):
                            role = str(summary["bodies"][body_id].get("role", "general"))
                    except Exception:
                        pass

                seed_genome = Genome(identity=f"body-{role}", role=role)
                champion, history = evolve_generation(
                    seed_genome, generations=1, population_size=2, seed=tick + 7,
                )
                best_score = max((h.get("fitness", 0.0) for h in history), default=90.0)
                insight = (
                    f"A gentle trait trial for {role} found calm harmony "
                    f"(balance score {best_score:.1f}, zero safety breaches) with steady memory rhythm."
                )
                beat = {
                    "id": f"evo-{tick}-{len(self._evolution_insights) + 1}",
                    "tick": tick,
                    "who": "The Sanctuary",
                    "where": "Tapestry of Traits",
                    "sentence": insight,
                    "tone": "curious",
                    "fitness": round(float(best_score), 2),
                    "champion": champion.identity,
                }
                self._evolution_insights.append(beat)
                if len(self._evolution_insights) > 12:
                    del self._evolution_insights[:-12]
                return {
                    "ok": True,
                    "kind": "evolve",
                    "insight": insight,
                    "champion": {
                        "identity": champion.identity,
                        "role": champion.role,
                        "fitness": round(float(best_score), 2),
                        "myelin_min_support": champion.myelin_min_support,
                        "myelin_min_span": champion.myelin_min_span,
                    },
                    "acknowledgment": insight,
                    "spoken_reply": f"A gentle adaptation trial finished for {role} with full safety.",
                    "world_tick": tick,
                }
            if cleaned_kind == "competition":
                title = cleaned_spark or "Starlight Harmony Trial"
                trial_kind = "triage_race" if "race" in title.lower() else "harmony_trial"
                if self.source_mode == "demo" and self._demo_world is not None:
                    comp = self._demo_world.start_competition(title, kind=trial_kind, duration=12)
                    self._demo_world.step(1)
                    tick = self._demo_world.tick
                elif self.world_url:
                    client = WorldClient(self.world_url, timeout=2.5)
                    comp = client.start_competition(title, kind=trial_kind)
                    tick = int(client.summary().get("tick", 0))
                else:
                    w = SharedWorld(state_path=self.world_state_path)
                    comp = w.start_competition(title, kind=trial_kind, duration=12)
                    tick = w.tick
                return {
                    "ok": True,
                    "kind": "competition",
                    "acknowledgment": f"\"{comp['title']}\" has opened in Starlight Playground! Companions are gathering to shine together.",
                    "spoken_reply": f"A new friendly trial, {comp['title']}, has begun in Starlight Playground.",
                    "competition": comp,
                    "world_tick": tick,
                }

            if cleaned_kind in ("reward", "punishment"):
                reason = cleaned_spark or ("graceful stewardship" if cleaned_kind == "reward" else "stepping beyond gentle bounds")
                if self.source_mode == "demo" and self._demo_world is not None:
                    w = self._demo_world
                    bid = self._resolve_target_body(w.bodies, body_id=body_id, zone=zone)
                    if not bid:
                        raise ValueError("No inhabitants are present to receive this action.")
                    res = (
                        w.award_reward(bid, honor=1, reason=reason)
                        if cleaned_kind == "reward"
                        else w.apply_punishment(bid, penalty=1, reason=reason, guard_door=True)
                    )
                    tick = w.tick
                    who = being_display_name(bid)
                elif self.world_url:
                    client = WorldClient(self.world_url, timeout=2.5)
                    summary = client.summary()
                    bid = self._resolve_target_body(summary.get("bodies", {}), body_id=body_id, zone=zone)
                    if not bid:
                        raise ValueError("No inhabitants are present to receive this action.")
                    res = (
                        client.award_reward(bid, honor=1, reason=reason)
                        if cleaned_kind == "reward"
                        else client.apply_punishment(bid, penalty=1, reason=reason, guard_door=True)
                    )
                    tick = int(summary.get("tick", 0))
                    who = being_display_name(bid)
                else:
                    w = SharedWorld(state_path=self.world_state_path)
                    bid = self._resolve_target_body(w.bodies, body_id=body_id, zone=zone)
                    if not bid:
                        raise ValueError("No inhabitants are present to receive this action.")
                    res = (
                        w.award_reward(bid, honor=1, reason=reason)
                        if cleaned_kind == "reward"
                        else w.apply_punishment(bid, penalty=1, reason=reason, guard_door=True)
                    )
                    tick = w.tick
                    who = being_display_name(bid)

                ack = (
                    f"{who} received golden honor for {reason}."
                    if cleaned_kind == "reward"
                    else f"{who} paused for gentle reflection after {reason}."
                )
                return {
                    "ok": True,
                    "kind": cleaned_kind,
                    "acknowledgment": ack,
                    "spoken_reply": ack,
                    "result": res,
                    "world_tick": tick,
                }

            if cleaned_kind == "move":
                dest = target_zone or zone
                if self.source_mode == "demo" and self._demo_world is not None:
                    w = self._demo_world
                    if dest not in w.zones:
                        raise ValueError(f"Unknown habitat '{dest}'.")
                    bid = self._resolve_target_body(w.bodies, body_id=body_id, zone=zone)
                    if not bid:
                        raise ValueError("No inhabitants are present to journey.")
                    cur = w.bodies[bid]["zone"]
                    step_zone = dest if dest in w.zones[cur].neighbors else (self._next_step_toward(w.zones, cur, dest) or dest)
                    move_res = w.move(bid, step_zone)
                    tick = w.tick
                    who = being_display_name(bid)
                elif self.world_url:
                    client = WorldClient(self.world_url, timeout=2.5)
                    summary = client.summary()
                    zones_map = summary.get("zones", {})
                    if dest not in zones_map:
                        raise ValueError(f"Unknown habitat '{dest}'.")
                    bid = self._resolve_target_body(summary.get("bodies", {}), body_id=body_id, zone=zone)
                    if not bid:
                        raise ValueError("No inhabitants are present to journey.")
                    cur = summary["bodies"][bid]["zone"]
                    neighbors = zones_map[cur].get("neighbors", [])
                    step_zone = dest if dest in neighbors else (self._next_step_toward(zones_map, cur, dest) or dest)
                    move_res = client.move(bid, step_zone)
                    tick = int(summary.get("tick", 0))
                    who = being_display_name(bid)
                else:
                    w = SharedWorld(state_path=self.world_state_path)
                    if dest not in w.zones:
                        raise ValueError(f"Unknown habitat '{dest}'.")
                    bid = self._resolve_target_body(w.bodies, body_id=body_id, zone=zone)
                    if not bid:
                        raise ValueError("No inhabitants are present to journey.")
                    cur = w.bodies[bid]["zone"]
                    step_zone = dest if dest in w.zones[cur].neighbors else (self._next_step_toward(w.zones, cur, dest) or dest)
                    move_res = w.move(bid, step_zone)
                    tick = w.tick
                    who = being_display_name(bid)

                if not move_res.get("moved"):
                    reason = move_res.get("reason", "resting")
                    raise ValueError(f"{who} could not cross right now ({reason}).")
                where_dest = zone_label(str(move_res.get("zone", dest)))
                ack = f"{who} stepped gracefully through the luminous doorway into {where_dest}."
                return {
                    "ok": True,
                    "kind": "move",
                    "acknowledgment": ack,
                    "spoken_reply": ack,
                    "moved_to": move_res.get("zone"),
                    "door": move_res.get("door"),
                    "world_tick": tick,
                }

            # Standard curiosity / incident spark
            prefix = "[question]" if cleaned_kind == "curiosity" else "[bug]"
            title = cleaned_spark if cleaned_spark.startswith("[") else f"{prefix} {cleaned_spark}"
            risk = 0.08 if cleaned_kind == "curiosity" else 0.35

            if self.source_mode == "demo" and self._demo_world is not None:
                if zone not in self._demo_world.zones:
                    raise ValueError(f"Unknown habitat '{zone}'.")
                ent = self._demo_world.spawn_entity(
                    zone,
                    kind=cleaned_kind,
                    title=title,
                    body=cleaned_spark,
                    risk=risk,
                    ttl=80,
                )
                self._demo_world.step(1)
                for db in self._demo_beings.values():
                    if db.world.bodies.get(db.body_id, {}).get("zone") == zone:
                        db.step()
                ent_dict = self._demo_world.entities[ent.entity_id].to_dict()
                tick = self._demo_world.tick
                residents = [
                    being_display_name(bid, db.role)
                    for bid, db in self._demo_beings.items()
                    if self._demo_world.bodies.get(bid, {}).get("zone") == zone
                ]
            elif self.world_url:
                client = WorldClient(self.world_url, timeout=2.5)
                ent_dict = client.spawn_entity(
                    zone,
                    kind=cleaned_kind,
                    title=title,
                    body=cleaned_spark,
                    risk=risk,
                    ttl=80,
                )
                summary = client.summary()
                tick = int(summary.get("tick", 0))
                residents = [
                    being_display_name(bid, str(b.get("role", "general")))
                    for bid, b in summary.get("bodies", {}).items()
                    if b.get("zone") == zone
                ]
            else:
                w = SharedWorld(state_path=self.world_state_path)
                if zone not in w.zones:
                    raise ValueError(f"Unknown habitat '{zone}'.")
                ent = w.spawn_entity(zone, kind=cleaned_kind, title=title, body=cleaned_spark, risk=risk, ttl=80)
                ent_dict = ent.to_dict()
                tick = w.tick
                residents = []

        where = zone_label(zone)
        mood, story = _describe_entity(ent_dict)
        entity_out = {
            "entity_id": str(ent_dict.get("entity_id", "")),
            "issue_id": int(ent_dict.get("issue_id", 0)),
            "zone": zone,
            "kind": cleaned_kind,
            "title": _natural_entity_title(str(ent_dict.get("title", cleaned_spark))),
            "body": str(ent_dict.get("body", cleaned_spark)),
            "state": str(ent_dict.get("state", "open")),
            "labels": list(ent_dict.get("labels", [])),
            "owner": ent_dict.get("owner"),
            "born_tick": int(ent_dict.get("born_tick", tick)),
            "risk": round(float(ent_dict.get("risk", risk)), 3),
            "resolved_by": ent_dict.get("resolved_by"),
            "mood": mood,
            "story": story,
        }

        if residents:
            who_text = ", ".join(residents[:3])
            ack = f"Your spark of {cleaned_kind} now floats softly through {where}, where {who_text} can feel it."
        else:
            ack = f"Your spark of {cleaned_kind} now glows gently inside {where}."
        spoken_reply = f"A new spark of {cleaned_kind} has arrived in {where}."

        return {
            "ok": True,
            "kind": cleaned_kind,
            "acknowledgment": ack,
            "spoken_reply": spoken_reply,
            "entity": entity_out,
            "world_tick": tick,
        }


# --------------------------------------------------------------------------- HTTP Server
def make_observatory_server(
    backend: ObservatoryBackend,
    *,
    host: str = "127.0.0.1",
    port: int = 8888,
    web_dir: Path | None = None,
) -> ThreadingHTTPServer:
    """Create a pure-stdlib multi-threaded HTTP server for the Living World Observatory."""
    static_root = (web_dir or WEB_DIR).resolve()

    class _ObservatoryHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def _send_bytes(self, code: int, content_type: str, data: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)

        def _send_json(self, code: int, payload: dict[str, Any]) -> None:
            raw = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def _serve_static(self, rel_path: str) -> None:
            target = (static_root / rel_path.lstrip("/")).resolve()
            if not target.is_relative_to(static_root) or not target.is_file():
                self._send_json(404, {"ok": False, "error": "Resource not found"})
                return
            ctype, _ = mimetypes.guess_type(str(target))
            if target.suffix == ".js":
                ctype = "application/javascript; charset=utf-8"
            elif target.suffix == ".css":
                ctype = "text/css; charset=utf-8"
            elif target.suffix == ".html":
                ctype = "text/html; charset=utf-8"
            elif not ctype:
                ctype = "application/octet-stream"
            self._send_bytes(200, ctype, target.read_bytes())

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if path == "/api/universe":
                self._send_json(200, backend.get_universe())
                return

            m = re.fullmatch(r"/api/beings/([^/]+)/world", path)
            if m:
                being_id = urllib.parse.unquote(m.group(1))
                data = backend.get_being_world(being_id)
                if data is None:
                    self._send_json(404, {"ok": False, "error": f"Unknown inhabitant '{being_id}'"})
                    return
                self._send_json(200, data)
                return

            if path == "/":
                self._serve_static("index.html")
                return

            self._serve_static(path)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/api/pulse":
                self._send_json(404, {"ok": False, "error": "Endpoint not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                body = json.loads(raw) if raw.strip() else {}
                if not isinstance(body, dict):
                    raise ValueError("Request payload must be a JSON object.")
                zone = str(body.get("zone") or "alpha-sector")
                spark = str(body.get("spark") or body.get("title") or "")
                kind = str(body.get("kind") or "curiosity")
                body_id = body.get("body_id")
                target_zone = body.get("target_zone")
                door_id = body.get("door_id")
                result = backend.pulse(
                    zone=zone,
                    spark=spark,
                    kind=kind,
                    body_id=str(body_id) if body_id else None,
                    target_zone=str(target_zone) if target_zone else None,
                    door_id=str(door_id) if door_id else None,
                )
                self._send_json(200, result)
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json(400, {"ok": False, "error": str(exc)})

    return ThreadingHTTPServer((host, port), _ObservatoryHandler)


__all__ = [
    "CHRONICLE_CHAPTERS",
    "ObservatoryBackend",
    "collect_machine_stats",
    "make_observatory_server",
]
