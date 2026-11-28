# ADR-0020: Autonomous World Choreography, Embodied Morphology, and Non-Blocking Observatory v2

- **Status:** Accepted
- **Date:** 2026-11-28

## Context

`ADR-0018` and `ADR-0019` established a spatial `SharedWorld` and ontological organism identity (`Soul`, `Character`, `BeliefSystem`). Running the 10-organism collective (`alpha`, `beta`, `gamma` tiers) on VM 300 revealed three operational gaps:
1. Synchronous sequential `incus exec` polling inside `GET /api/universe` caused multi-second request latency and unnecessary host CPU load.
2. Live `SharedWorld` daemons only stepped ambient energy and entropy without autonomous world choreography—leaving inhabitants stationary unless manually nudged.
3. Embodied morphology (`Anatomy` with `eyes`, `ears`, `tongue`, `hands`, `legs`), interactive `Doors`, `Homes`, `Playground` competitions, and non-blocking `evolve` insights needed unified representation across `soul.py`, `world.py`, `observatory.py`, and permanent `systemd` services.

## Decision

1. **Non-Blocking Parallel Incus Poller (`src/bigbang/observatory.py`)**:
   - `ObservatoryBackend` runs a dedicated `_incus_poller` daemon thread (4s interval) using `concurrent.futures.ThreadPoolExecutor(max_workers=5)` to inspect running `bb-*` containers in parallel and publish results atomically under `_cache_lock`.
   - `GET /api/universe` reads directly from the atomic cache and cached host vitality, serving requests in tens of milliseconds without blocking on container subprocesses.
2. **Autonomous World Choreography (`src/bigbang/world.py`, `src/bigbang/cli.py`)**:
   - `SharedWorld.step()` remains 100% deterministic for offline tests and evaluation scenarios.
   - `SharedWorld.choreograph()` is invoked by live daemon loops (`bigbang world serve` and Observatory `--demo`), periodically launching friendly Playground competitions, updating standings from real actions/energy/honor, guiding inhabitants across luminous `Doors` and `Paths`, settling residents into `Homes`, and issuing gentle corrections under high zone turbulence.
   - `SharedWorld.toggle_door(door_id)` allows interactive `open` <-> `guarded` doorway transitions exposed via `POST /door` and `POST /api/pulse` (`kind="door"`).
3. **Embodied Morphology & Evolution Pulse (`src/bigbang/soul.py`, `body.py`, `observatory.py`)**:
   - `Anatomy.for_role(role)` models `eyes`, `ears`, `tongue`, `hands`, and `legs` with bounded strengths and natural-language descriptions without relaxing Kernel trust/DIFC invariants.
   - `POST /api/pulse` supports `kind="evolve"` to run a fast bounded `evolve_generation` trial and record safety-verified trait insights in the Observatory chronicle.
4. **Permanent Systemd Units (`deploy/bigbang-world.service`, `deploy/bigbang-observatory.service`)**:
   - Both host daemons run under `/usr/bin/python3` with `PYTHONPATH=/opt/bigbang-world/src` and `WorkingDirectory=/opt/bigbang-world` for reboot-safe operation.

## Consequences

- `GET /api/universe` latency drops from ~3s sequential `incus exec` scans to sub-50ms cache reads while keeping container telemetry fresh.
- Live 10-Body worlds continuously breathe, journey across Doors, compete in `Starlight Playground`, and adapt traits safely while all deterministic unit and `bigbang eval` tests remain unchanged.
