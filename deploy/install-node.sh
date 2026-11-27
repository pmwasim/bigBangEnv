#!/usr/bin/env bash
# install-node.sh
# Autonomous installer to be executed inside the isolated bigBangEnv node (Debian/Ubuntu).
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo "[1/6] Updating system packages and installing prerequisites..."
apt-get update -y
apt-get install -y --no-install-recommends \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev \
  git \
  curl \
  ca-certificates \
  logrotate

echo "[2/6] Creating isolated system user and directories..."
if ! id -u bigbang >/dev/null 2>&1; then
  useradd --system --shell /usr/sbin/nologin --home-dir /var/lib/bigbang --create-home bigbang
fi

mkdir -p /opt/bigbang
mkdir -p /var/lib/bigbang/state
mkdir -p /var/lib/bigbang/issues
mkdir -p /var/log/bigbang
mkdir -p /etc/bigbang

touch /var/lib/bigbang/commands.txt
chown -R bigbang:bigbang /var/lib/bigbang /var/log/bigbang
chmod 750 /var/lib/bigbang /var/log/bigbang

echo "[3/6] Fetching bigBangEnv repository..."
if [[ ! -d /opt/bigbang/repo/.git ]]; then
  git clone https://github.com/pmwasim/bigBangEnv.git /opt/bigbang/repo
else
  git -C /opt/bigbang/repo pull origin main
fi
chown -R root:root /opt/bigbang/repo

echo "[4/6] Initializing isolated Python virtual environment..."
python3 -m venv /opt/bigbang/venv
/opt/bigbang/venv/bin/pip install --upgrade pip setuptools wheel
/opt/bigbang/venv/bin/pip install -e "/opt/bigbang/repo[dev]"

echo "[+] Running test suite verification..."
/opt/bigbang/venv/bin/pytest /opt/bigbang/repo/tests -q

echo "[5/6] Installing configuration and systemd service..."
# Move artifacts from /root if staged there by provisioner
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/bigbang.conf" /etc/bigbang/bigbang.conf
cp "$SCRIPT_DIR/bigbang-prestart.sh" /usr/local/bin/bigbang-prestart.sh
chmod +x /usr/local/bin/bigbang-prestart.sh

cp "$SCRIPT_DIR/bigbang-logrotate.conf" /etc/logrotate.d/bigbang
cp "$SCRIPT_DIR/bigbang.service" /etc/systemd/system/bigbang.service

systemctl daemon-reload

echo "[6/6] Enabling and starting bigbang.service..."
systemctl enable bigbang.service
systemctl start bigbang.service

sleep 2
systemctl status bigbang.service --no-pager

echo "[✓] bigBangEnv service successfully installed and active!"
