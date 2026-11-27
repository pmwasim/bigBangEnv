#!/usr/bin/env bash
# proxmox-provision.sh
# Provision a completely isolated node for bigBangEnv on Proxmox VE.
#
# HARD SAFETY CONSTRAINT:
# BigBangEnv SHALL NOT touch VM100, VM200, or any other existing workloads.
# It runs in complete isolation.
#
# Run this script directly on the Proxmox VE host (e.g. ssh root@192.168.1.215).

set -euo pipefail

NODE_ID="${NODE_ID:-300}"
NODE_HOSTNAME="${NODE_HOSTNAME:-bigbang-node}"
NODE_TYPE="${NODE_TYPE:-lxc}"          # "lxc" (recommended, lightweight) or "vm"
RAM_MB="${RAM_MB:-2048}"
CORES="${CORES:-2}"
DISK_GB="${DISK_GB:-20}"
BRIDGE="${BRIDGE:-vmbr0}"
STORAGE="${STORAGE:-local-lvm}"        # local-lvm or local-zfs
TEMPLATE_STORAGE="${TEMPLATE_STORAGE:-local}"

echo "=========================================================="
echo " bigBangEnv Proxmox Node Provisioning (Target ID: $NODE_ID)"
echo "=========================================================="

# 1. Strict Exclusion Validation
PROTECTED_IDS=(100 200)
for pid in "${PROTECTED_IDS[@]}"; do
  if [[ "$NODE_ID" -eq "$pid" ]]; then
    echo "ERROR: Node ID $NODE_ID is strictly protected and reserved. Aborting!" >&2
    exit 1
  fi
done

# Check if ID already exists on Proxmox
if pct status "$NODE_ID" >/dev/null 2>&1 || qm status "$NODE_ID" >/dev/null 2>&1; then
  echo "ERROR: ID $NODE_ID already exists on this Proxmox host. Pick an unused ID (e.g. 301, 310)." >&2
  exit 1
fi

if [[ "$NODE_TYPE" == "lxc" ]]; then
  echo "[+] Detecting Ubuntu 24.04 or Debian 12 LXC template..."
  TEMPLATE=$(pveam list "$TEMPLATE_STORAGE" | awk '/ubuntu-24.04-standard|debian-12-standard/ {print $1}' | tail -n 1 || true)

  if [[ -z "$TEMPLATE" ]]; then
    echo "[+] Downloading Debian 12 standard template..."
    pveam update
    pveam download "$TEMPLATE_STORAGE" debian-12-standard_12.7-1_amd64.tar.zst || \
    pveam download "$TEMPLATE_STORAGE" debian-12-standard_12.2-1_amd64.tar.zst
    TEMPLATE=$(pveam list "$TEMPLATE_STORAGE" | awk '/debian-12-standard/ {print $1}' | tail -n 1)
  fi

  echo "[+] Provisioning isolated LXC Container $NODE_ID ($NODE_HOSTNAME)..."
  pct create "$NODE_ID" "$TEMPLATE" \
    --hostname "$NODE_HOSTNAME" \
    --cores "$CORES" \
    --memory "$RAM_MB" \
    --swap 1024 \
    --rootfs "${STORAGE}:${DISK_GB}" \
    --net0 "name=eth0,bridge=${BRIDGE},ip=dhcp,firewall=1" \
    --unprivileged 1 \
    --features nesting=1 \
    --onboot 1 \
    --start 1

  echo "[+] Waiting for LXC network bring-up..."
  sleep 6

  NODE_IP=""
  for i in {1..15}; do
    NODE_IP=$(pct exec "$NODE_ID" -- ip -4 addr show eth0 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1 || true)
    if [[ -n "$NODE_IP" ]]; then
      break
    fi
    sleep 2
  done

  echo "[✓] LXC Container $NODE_ID is active at IP: ${NODE_IP:-DHCP lease}"

  echo "[+] Pushing node deployment script to container..."
  pct push "$NODE_ID" "$(dirname "$0")/install-node.sh" /root/install-node.sh
  pct push "$NODE_ID" "$(dirname "$0")/bigbang.service" /root/bigbang.service
  pct push "$NODE_ID" "$(dirname "$0")/bigbang.conf" /root/bigbang.conf
  pct push "$NODE_ID" "$(dirname "$0")/bigbang-prestart.sh" /root/bigbang-prestart.sh
  pct push "$NODE_ID" "$(dirname "$0")/bigbang-logrotate.conf" /root/bigbang-logrotate.conf

  echo "[+] Executing autonomous node setup inside $NODE_ID..."
  pct exec "$NODE_ID" -- bash /root/install-node.sh

  echo "=========================================================="
  echo " bigBangEnv is running autonomously in isolated LXC $NODE_ID!"
  echo " Node IP: $NODE_IP"
  echo " Check status: pct exec $NODE_ID -- systemctl status bigbang"
  echo " View live traces: pct exec $NODE_ID -- /opt/bigbang/venv/bin/python -m bigbang trace --state /var/lib/bigbang/state --tail 10"
  echo "=========================================================="

elif [[ "$NODE_TYPE" == "vm" ]]; then
  echo "[+] Provisioning isolated QEMU VM $NODE_ID ($NODE_HOSTNAME)..."
  qm create "$NODE_ID" \
    --name "$NODE_HOSTNAME" \
    --cores "$CORES" \
    --memory "$RAM_MB" \
    --net0 "virtio,bridge=${BRIDGE},firewall=1" \
    --scsihw virtio-scsi-pci \
    --scsi0 "${STORAGE}:${DISK_GB}" \
    --onboot 1 \
    --agent 1

  echo "[✓] VM $NODE_ID created. Attach your cloud-init or OS installer ISO and start."
fi
