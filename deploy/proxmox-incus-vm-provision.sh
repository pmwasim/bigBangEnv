#!/usr/bin/env bash
# proxmox-incus-vm-provision.sh
# Automated Proxmox provisioner for the dedicated Incus Container Incubator VM.
#
# HARD SAFETY CONSTRAINT:
# BigBangEnv SHALL NOT touch VM100, VM200, or any other existing workloads.
# Target ID is strictly isolated (default ID 300).
#
# Run this script on the physical Proxmox host (e.g. ssh root@192.168.1.215).

set -euo pipefail

INCUBATOR_ID="${INCUBATOR_ID:-300}"
INCUBATOR_NAME="${INCUBATOR_NAME:-bigbang-incubator}"
CORES="${CORES:-2}"
RAM_MB="${RAM_MB:-2048}"          # Safe default for 32GB host alongside VM100 (24GB) + VM200 (1GB)
MIN_HOST_HEADROOM_MB="${MIN_HOST_HEADROOM_MB:-1536}"
DISK_GB="${DISK_GB:-32}"
STORAGE="${STORAGE:-local-lvm}"   # local-lvm or local-zfs
CLOUD_STORAGE="${CLOUD_STORAGE:-local}"
BRIDGE="${BRIDGE:-vmbr0}"
CI_USER="${CI_USER:-wasim}"

echo "=========================================================="
echo " bigBangEnv Incus Incubator Provisioner (Target ID: $INCUBATOR_ID)"
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

# 1b. Host RAM Headroom Guard (protects VM100 / VM200 from OOM)
AVAIL_MB=$(free -m | awk '/^Mem:/ {print $7}')
if (( AVAIL_MB - RAM_MB < MIN_HOST_HEADROOM_MB )); then
  echo "ERROR: Insufficient host RAM headroom! Available=${AVAIL_MB}MB, Requested=${RAM_MB}MB, Required headroom=${MIN_HOST_HEADROOM_MB}MB." >&2
  echo "Lower RAM_MB (e.g. RAM_MB=2048) to keep VM100 and VM200 safe." >&2
  exit 1
fi
echo "[✓] Host RAM check passed: ${AVAIL_MB}MB available; allocating ${RAM_MB}MB leaves $((AVAIL_MB - RAM_MB))MB headroom."

# 2. Verify Host Nested KVM Virtualization
echo "[+] Checking host nested virtualization..."
if [[ -f /sys/module/kvm_intel/parameters/nested ]]; then
  if [[ "$(cat /sys/module/kvm_intel/parameters/nested)" =~ ^[Yy1]$ ]]; then
    echo "[✓] Intel KVM nested virtualization active."
  else
    echo "options kvm-intel nested=Y" > /etc/modprobe.d/kvm-intel.conf
    modprobe -r kvm_intel && modprobe kvm_intel || true
  fi
elif [[ -f /sys/module/kvm_amd/parameters/nested ]]; then
  if [[ "$(cat /sys/module/kvm_amd/parameters/nested)" =~ ^[Yy1]$ ]]; then
    echo "[✓] AMD KVM nested virtualization active."
  else
    echo "options kvm-amd nested=1" > /etc/modprobe.d/kvm-amd.conf
    modprobe -r kvm_amd && modprobe kvm_amd || true
  fi
fi

# 3. Obtain or verify Debian 12 Cloud-Init Image
IMAGE_DIR="/var/lib/vz/template/iso"
IMAGE_FILE="$IMAGE_DIR/debian-12-generic-amd64.qcow2"
mkdir -p "$IMAGE_DIR"

if [[ ! -f "$IMAGE_FILE" ]]; then
  echo "[+] Downloading official Debian 12 cloud-init image..."
  curl -fsSL -o "$IMAGE_FILE" \
    "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2"
fi

# 4. Create the Incubator VM
echo "[+] Creating VM $INCUBATOR_ID with 'cpu: host'..."
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
  --net0 "virtio,bridge=${BRIDGE},firewall=1" \
  --ostype l26 \
  --onboot 1 \
  --agent 1

# 5. Import and attach Cloud-Init disk
echo "[+] Importing cloud image disk to storage $STORAGE..."
qm importdisk "$INCUBATOR_ID" "$IMAGE_FILE" "$STORAGE"
DISKPTR=$(qm config "$INCUBATOR_ID" | awk -F': ' '/unused0/ {print $2}')
qm set "$INCUBATOR_ID" --scsi0 "${DISKPTR},discard=on,ssd=1"
qm disk resize "$INCUBATOR_ID" scsi0 "${DISK_GB}G"

# Cloud-Init Drive Configuration
echo "[+] Configuring Cloud-Init drive and credentials..."
qm set "$INCUBATOR_ID" --ide2 "${STORAGE}:cloudinit"
qm set "$INCUBATOR_ID" --boot "order=scsi0"
qm set "$INCUBATOR_ID" --ciuser "$CI_USER"
qm set "$INCUBATOR_ID" --ipconfig0 "ip=dhcp"

# Copy Proxmox root's authorized_keys or current operator key into cloud-init
if [[ -f /root/.ssh/authorized_keys ]]; then
  qm set "$INCUBATOR_ID" --sshkeys /root/.ssh/authorized_keys
fi

echo "=========================================================="
echo " [✓] VM $INCUBATOR_ID ($INCUBATOR_NAME) provisioned!"
echo " Starting VM $INCUBATOR_ID..."
qm start "$INCUBATOR_ID"

echo "[+] Waiting for guest agent and IP address..."
sleep 10
GUEST_IP=""
for i in {1..20}; do
  GUEST_IP=$(qm guest cmd "$INCUBATOR_ID" network-get-interfaces 2>/dev/null | grep -oE '192\.168\.[0-9]+\.[0-9]+' | head -n 1 || true)
  if [[ -n "$GUEST_IP" ]]; then
    break
  fi
  sleep 2
done

echo "=========================================================="
echo " bigBangEnv Incus Incubator is online!"
echo " VM ID: $INCUBATOR_ID"
echo " IP: ${GUEST_IP:-Assigned via DHCP}"
echo " User: $CI_USER"
echo ""
echo " Next step:"
echo " SSH into $GUEST_IP and run the bootstrap script:"
echo "   scp -r deploy/ ${CI_USER}@${GUEST_IP}:~/deploy"
echo "   ssh ${CI_USER}@${GUEST_IP} 'sudo bash ~/deploy/bootstrap-incus-node.sh'"
echo "=========================================================="
