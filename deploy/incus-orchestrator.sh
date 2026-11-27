#!/usr/bin/env bash
# incus-orchestrator.sh
# Demonstrates multi-tier collective environment orchestration for bigBangEnv.
# Run this inside the Incubator VM (running Incus / system containers).
#
# Tier Architecture:
# - Level 1: Individual Organism Environments (e.g. env-sensor, env-reasoner, env-motor, env-defense)
# - Level 2: Interconnected Systems (e.g. system-triage = sensor + reasoner + defense)
# - Level 3: Collective Meta-System (e.g. system-triage <--> system-execution)

set -euo pipefail

ACTION="${1:-spawn}"
SYSTEM_NAME="${2:-system-alpha}"

spawn_tier() {
  echo "=========================================================="
  echo " Spawning Collective Environment Tier: $SYSTEM_NAME"
  echo "=========================================================="

  # 1. Create dedicated software-defined virtual network for this system tier
  NET_NAME="bb-${SYSTEM_NAME}"
  if ! incus network show "$NET_NAME" >/dev/null 2>&1; then
    echo "[+] Creating isolated synaptic bridge: $NET_NAME..."
    incus network create "$NET_NAME" ipv4.address=10.99.1.1/24 ipv4.nat=true ipv6.address=none
  fi

  # 2. Spawn Member Environments (Level 1 Organisms)
  MEMBERS=("sensor" "reasoner" "defense" "motor")
  for role in "${MEMBERS[@]}"; do
    CONTAINER_NAME="bb-${SYSTEM_NAME}-${role}"
    if ! incus info "$CONTAINER_NAME" >/dev/null 2>&1; then
      echo "[+] Launching isolated environment: $CONTAINER_NAME..."
      incus launch images:debian/12 "$CONTAINER_NAME" --network "$NET_NAME" \
        -c limits.cpu=1 \
        -c limits.memory=512MB

      # Inject bigBangEnv service configured for this specific role
      incus exec "$CONTAINER_NAME" -- apt-get update -y
      incus exec "$CONTAINER_NAME" -- apt-get install -y python3 python3-venv git
      incus exec "$CONTAINER_NAME" -- git clone https://github.com/pmwasim/bigBangEnv.git /opt/bigbang/repo
      incus exec "$CONTAINER_NAME" -- python3 -m venv /opt/bigbang/venv
      incus exec "$CONTAINER_NAME" -- /opt/bigbang/venv/bin/pip install -e "/opt/bigbang/repo[dev]"
      echo "[✓] Environment $CONTAINER_NAME is live and synchronized."
    fi
  done

  echo "=========================================================="
  echo " [✓] System Tier $SYSTEM_NAME is live across 4 environments!"
  incus list "bb-${SYSTEM_NAME}-"
  echo "=========================================================="
}

status_tier() {
  echo "Listing all active bigBangEnv environment tiers:"
  incus list
}

case "$ACTION" in
  spawn)  spawn_tier ;;
  status) status_tier ;;
  *) echo "Usage: $0 {spawn|status} [system-name]" ;;
esac
