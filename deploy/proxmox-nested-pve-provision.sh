#!/usr/bin/env bash
# proxmox-nested-pve-provision.sh
# Provision a dedicated, isolated Nested Virtualization Incubator VM on Proxmox VE.
#
# HARD SAFETY CONSTRAINT:
# BigBangEnv SHALL NOT touch VM100, VM200, or any other existing workloads.
# The Incubator VM acts as a self-contained universe for multi-environment systems.
#
# Run this script on the physical Proxmox host (e.g. ssh root@192.168.1.215).

set -euo pipefail

INCUBATOR_ID="${INCUBATOR_ID:-300}"
INCUBATOR_NAME="${INCUBATOR_NAME:-bigbang-incubator}"
CORES="${CORES:-4}"
RAM_MB="${RAM_MB:-8192}"          # 8 GB recommended for nested environments
DISK_GB="${DISK_GB:-64}"
STORAGE="${STORAGE:-local-lvm}"   # local-lvm or local-zfs
ISO_STORAGE="${ISO_STORAGE:-local}"
ISO_IMAGE="${ISO_IMAGE:-}"        # e.g. "local:iso/proxmox-ve_8.2-1.iso"
BRIDGE="${BRIDGE:-vmbr0}"

echo "=========================================================="
echo " bigBangEnv Nested Incubator Provisioner (Target ID: $INCUBATOR_ID)"
echo "=========================================================="

# 1. Strict Exclusion Validation
PROTECTED_IDS=(100 200)
for pid in "${PROTECTED_IDS[@]}"; do
  if [[ "$INCUBATOR_ID" -eq "$pid" ]]; then
    echo "ERROR: Target ID $INCUBATOR_ID is strictly protected (VM$pid). Aborting!" >&2
    exit 1
  fi
done

if qm status "$INCUBATOR_ID" >/dev/null 2>&1 || pct status "$INCUBATOR_ID" >/dev/null 2>&1; then
  echo "ERROR: ID $INCUBATOR_ID already exists on this Proxmox cluster. Choose another ID (e.g. 310)." >&2
  exit 1
fi

# 2. Check Host CPU Nested Virtualization Support
echo "[+] Verifying host nested virtualization capability..."
if [[ -f /sys/module/kvm_intel/parameters/nested ]]; then
  NESTED_STATE=$(cat /sys/module/kvm_intel/parameters/nested)
  if [[ "$NESTED_STATE" != "Y" && "$NESTED_STATE" != "1" ]]; then
    echo "[!] Enabling kvm_intel nested virtualization..."
    echo "options kvm-intel nested=Y" > /etc/modprobe.d/kvm-intel.conf
    modprobe -r kvm_intel && modprobe kvm_intel
  fi
elif [[ -f /sys/module/kvm_amd/parameters/nested ]]; then
  NESTED_STATE=$(cat /sys/module/kvm_amd/parameters/nested)
  if [[ "$NESTED_STATE" != "Y" && "$NESTED_STATE" != "1" ]]; then
    echo "[!] Enabling kvm_amd nested virtualization..."
    echo "options kvm-amd nested=1" > /etc/modprobe.d/kvm-amd.conf
    modprobe -r kvm_amd && modprobe kvm_amd
  fi
fi
echo "[✓] Host nested virtualization confirmed active."

# 3. Create the Nested VM
echo "[+] Creating VM $INCUBATOR_ID with 'cpu: host' passthrough..."
qm create "$INCUBATOR_ID" \
  --name "$INCUBATOR_NAME" \
  --cpu host \
  --cores "$CORES" \
  --memory "$RAM_MB" \
  --balloon 0 \
  --machine q35 \
  --bios ovmf \
  --efidisk0 "${STORAGE}:4,efitype=4m,pre-enrolled-keys=1" \
  --scsihw virtio-scsi-pci \
  --scsi0 "${STORAGE}:${DISK_GB},discard=on,ssd=1" \
  --net0 "virtio,bridge=${BRIDGE},firewall=1" \
  --ostype l26 \
  --onboot 1 \
  --agent 1

# Optional ISO attachment
if [[ -n "$ISO_IMAGE" ]]; then
  echo "[+] Attaching ISO $ISO_IMAGE..."
  qm set "$INCUBATOR_ID" --cdrom "$ISO_IMAGE" --boot "order=ide2;scsi0"
else
  # Check if Proxmox VE ISO exists on host
  PVE_ISO=$(pveam list "$ISO_STORAGE" 2>/dev/null | awk '/proxmox-ve.*\.iso/ {print $1}' | tail -n 1 || true)
  if [[ -n "$PVE_ISO" ]]; then
    echo "[+] Found Proxmox ISO: $PVE_ISO. Attaching..."
    qm set "$INCUBATOR_ID" --cdrom "$PVE_ISO" --boot "order=ide2;scsi0"
  fi
fi

echo "=========================================================="
echo " [✓] Nested Incubator VM $INCUBATOR_ID created successfully!"
echo " Name: $INCUBATOR_NAME"
echo " Cores: $CORES (Host CPU with full VT-x/AMD-V nested support)"
echo " RAM: ${RAM_MB} MB"
echo " Storage: ${DISK_GB} GB on $STORAGE"
echo ""
echo " Next Steps:"
echo " 1. Start the Incubator VM: qm start $INCUBATOR_ID"
echo " 2. Open Proxmox Web GUI Console on VM $INCUBATOR_ID to complete the installer."
echo " 3. Once installed, VM $INCUBATOR_ID operates as its own autonomous hypervisor,"
echo "    spawning and interconnecting multi-tiered bigBangEnv organism environments!"
echo "=========================================================="
