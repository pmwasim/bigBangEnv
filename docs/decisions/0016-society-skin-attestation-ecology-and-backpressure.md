# ADR-0016: Society, Cryptographic Skin, Reputation, Territory Ecology, and Peer Backpressure

- **Status:** Accepted
- **Date:** 2026-11-28

## Context

Level 6 unified living `Body` organisms (`body.py`) operate inside bounded Physics (`physics.py`), Chemistry (`chemistry.py`), and cellular Homeostasis (`ADR-0015`). However, coordinating multiple sovereign Bodies (`deploy/bigbang-mesh.py` or `WorldSociety`) lacked:
1. A cryptographic outer **Skin** verifying `peer.signal` provenance without elevating peers to `OPERATOR` or `OWNER`.
2. **Reputation** scoring to reward reliable collaborators and isolate spoofed/noisy peers.
3. **Mutual-exclusion Territory claims** so Bodies do not act on the same external target concurrently.
4. **Schmitt-trigger upstream backpressure** across Bodies so a saturated or `LOCKDOWN` downstream organism suppresses upstream flood relays without oscillation or message loss.

## Decision

1. **`Skin` & Signed Envelopes (`src/bigbang/society.py`)**:
   - `Skin(identity, secret)` seals outbound peer payloads with canonical HMAC-SHA256 signatures.
   - `verify_envelope(envelope, peer_secrets)` verifies authenticity in constant time.
   - Verified `peer.signal` inputs from trusted peers enter `SensoryIngest` at `Trust.USER` (strictly below `OPERATOR`/`OWNER`); unverified or low-reputation `peer.signal` payloads are rejected with `friction` gradient emission.
2. **Reputation & Shared Ecology (`ReputationLedger`, `TerritoryTable`)**:
   - `ReputationLedger` tracks peer trustworthiness (`[0.0 .. 1.0]`, threshold `0.4`).
   - `TerritoryTable` manages deterministic TTL-bounded resource locks across Bodies.
3. **Cross-Body Schmitt-Trigger Backpressure (`should_backpressure`, `WorldSociety`, `deploy/bigbang-mesh.py`)**:
   - Asserts backpressure when target `operating_mode in ("LOCKDOWN", "DORMANT")`, `halted` is `True`, `fuel <= 0.35`, or `stress >= 0.55`.
   - Releases only once `fuel >= 0.60` and `stress <= 0.35` (zero hysteresis oscillation).
   - `bigbang-mesh` `relay-loop` and `route` respect downstream backpressure before forwarding signals.

## Consequences

- Cross-body communication preserves compartment isolation and DIFC provenance while preventing cascading overload across multi-tier Incus meshes.
