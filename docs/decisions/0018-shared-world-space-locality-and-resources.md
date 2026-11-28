# ADR-0018: Shared World Space, Locality, Ambient Resources, and World Kernel

- **Status:** Accepted
- **Date:** 2026-11-28

## Context

Prior milestones built the internal microkernel (`Kernel`), Physics (`physics.py`), Chemistry (`chemistry.py`), 5-organ Bodies (`body.py`), Homeostasis (`ADR-0015`), and Society attestation/backpressure (`society.py`). However, organisms still operated primarily on private `Ledger` files and JSON file drops rather than inhabiting a single shared **World** (`Space` + ambient `Energy` + persistent `WorldEntity` objects + topological `Locality` as specified in Genesis §1, §3.4, and `VISION.md`).

## Decision

1. **Shared World Runtime (`src/bigbang/world.py`)**:
   - **Topology & Spatial Locality (`Zone`)**: The World consists of named Zones (`hub`, `alpha-sector`, `beta-sector`, `frontier`) with explicit adjacency edges (`neighbors`). Bodies inhabit one Zone at a time (`enter`, `move`), move only along adjacent edges, and perceive only objects, ambient conditions, and peer Bodies in their current Zone (`sense`).
   - **Shared Objects & Territory Safety (`WorldEntity`)**: External incidents, reagents, and artifacts live inside Zones as shared `WorldEntity` records. Mutations (`act`) require Locality (same Zone) and `TerritoryTable` mutual exclusion so cooperating Bodies observe each other's changes directly in the World rather than maintaining siloed state.
   - **Ambient Thermodynamics**: Zones hold finite `energy_reserve` (harvested via `harvest`), accumulate `ambient_entropy` when Bodies act, and regenerate/cool deterministically on `world.step()`.
   - **Networked Live World Daemon (`serve_world`, `WorldClient`)**: Pure-stdlib `ThreadingHTTPServer` + `urllib.request` client so distributed Incus Bodies (`bigbang run --world http://...`) inhabit one shared authoritative World daemon (`bigbang world serve`).
2. **Host, Ledger, Society & CLI Binding (`apps/caretaker.py`, `runtime.py`, `cli.py`, `society.py`)**:
   - `Host.poll` senses open local-Zone entities & hazards from an attached `SharedWorld` or `WorldClient`; `Ledger` pushes committed Motor actions (`label`, `close`, `reopen`) back to `world.act()`.
   - `WorldSociety` embeds a `SharedWorld` (`soc.world`), advancing physical World ticks alongside resident Bodies.

## Consequences

- Agents cease operating in isolated vacuums: multiple Bodies across Incus networks share one causal space, perceive each other's mutations locally, harvest finite zone energy, and leave persistent marks in the World.
