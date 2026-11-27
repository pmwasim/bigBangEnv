#!/usr/bin/env bash
# bootstrap-incus-node.sh
# Bootstrap script to turn the isolated VM into an Incus Container Incubator.
# Run this inside the Incubator VM (as root or with sudo).

set -euo pipefail

echo "=========================================================="
echo " Bootstrapping Incus Container Incubator for bigBangEnv"
echo "=========================================================="

export DEBIAN_FRONTEND=noninteractive

# 1. Install prerequisites and official Zabbly Incus repository
echo "[1/5] Installing package prerequisites..."
apt-get update -y
apt-get install -y --no-install-recommends \
  curl ca-certificates gnupg git python3 python3-pip python3-venv btrfs-progs iptables

echo "[2/5] Adding official Zabbly Incus repository..."
mkdir -p /etc/apt/keyrings
curl -fsSL https://pkgs.zabbly.com/key.asc -o /etc/apt/keyrings/zabbly.asc

cat << 'EOF' > /etc/apt/sources.list.d/zabbly-incus-stable.sources
Enabled: yes
Types: deb
URIs: https://pkgs.zabbly.com/incus/stable
Suites: bookworm
Components: main
Architectures: amd64
Signed-By: /etc/apt/keyrings/zabbly.asc
EOF

apt-get update -y
apt-get install -y incus incus-client

# 2. Add current user to incus-admin group
CURRENT_USER="${SUDO_USER:-$(whoami)}"
if id -u "$CURRENT_USER" >/dev/null 2>&1; then
  usermod -aG incus-admin "$CURRENT_USER"
fi

# 3. Initialize Incus with preconfigured defaults
echo "[3/5] Initializing Incus storage pool and network bridge..."
cat << 'EOF' | incus admin init --preseed
config: {}
networks:
- config:
    ipv4.address: 10.99.0.1/24
    ipv4.nat: "true"
    ipv6.address: none
  description: "Private bigBangEnv root synaptic network"
  name: bb-root
  type: bridge
storage_pools:
- config: {}
  description: "bigBangEnv container storage pool"
  name: default
  driver: dir
profiles:
- config:
    boot.autostart: "true"
    security.nesting: "true"
    security.privileged: "false"
  description: "Default bigBangEnv organism profile"
  devices:
    root:
      path: /
      pool: default
      type: disk
    eth0:
      name: eth0
      network: bb-root
      type: nic
  name: default
cluster: null
EOF

# 4. Create specialized BigBang Organism Profile with strict resource ceilings
echo "[4/5] Creating 'bigbang-organism' profile (1 core, 512MB RAM cap)..."
incus profile copy default bigbang-organism || true
incus profile set bigbang-organism limits.cpu 1
incus profile set bigbang-organism limits.memory 512MB

# 5. Pre-fetch base Debian 12 image
echo "[5/5] Pre-caching minimal Debian 12 container image..."
incus image copy images:debian/12 local: --alias debian12-base || true

# Install bigbang-mesh manager to /usr/local/bin
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/bigbang-mesh.py" ]]; then
  cp "$SCRIPT_DIR/bigbang-mesh.py" /usr/local/bin/bigbang-mesh
  chmod +x /usr/local/bin/bigbang-mesh
fi

echo "=========================================================="
echo " [✓] Incus Container Incubator is fully initialized!"
echo " Log out and log back in (or run 'newgrp incus-admin') to enable CLI access."
echo " Test with: incus list"
echo " Orchestrate with: bigbang-mesh --help"
echo "=========================================================="
