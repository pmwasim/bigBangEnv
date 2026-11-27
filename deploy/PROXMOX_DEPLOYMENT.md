# bigBangEnv — Proxmox Isolated Deployment Guide

This guide details how to deploy **bigBangEnv** as an autonomous, long-running agent OS on Proxmox VE in **complete isolation** from VM100, VM200, or other existing virtual machines.

---

## 1. Strict Isolation Guarantee

> **Hard Security & Operational Boundary**:
> - bigBangEnv runs within its own dedicated node boundary (default ID `300`, hostname `bigbang-node`).
> - The deployment scripts explicitly guard against touching IDs `100` (`agentic-ai-node`), `200`, or any existing VM/LXC instance.
> - Storage, filesystem, process space, network stack, and systemd units are fully segregated.
> - If the organism experiences memory exhaustion, cell panics, quarantine events, or rapid I/O churn, other hosts remain entirely unaffected.

---

## 2. Resource & Topology Blueprint

| Parameter | Specification | Notes |
|---|---|---|
| **Target Host** | Proxmox VE 8.x (`192.168.1.215`) | Hypervisor |
| **Node Type** | LXC Container (recommended) or QEMU KVM | LXC uses <60MB base RAM |
| **Default ID** | `300` | Customizable via `NODE_ID` (never 100/200) |
| **vCPUs** | 2 cores | Configurable |
| **RAM** | 2048 MB (with 1024 MB swap) | Ample for rule brain or local model |
| **Disk** | 20 GB (`local-lvm` or `local-zfs`) | Holds state, logs, and trace |
| **OS** | Debian 12 / Ubuntu 24.04 minimal | Clean headless environment |
| **Service** | `bigbang.service` | `systemd` daemon with auto-restart |

---

## 3. Directory Layout on the Target Node

```
/opt/bigbang/
├── repo/                      # Source code (git clone https://github.com/pmwasim/bigBangEnv.git)
└── venv/                      # Dedicated Python 3.11/3.12 virtual environment

/etc/bigbang/
└── bigbang.conf               # Service configuration (intervals, brain, paths)

/var/lib/bigbang/              # Strict organism boundary (bigbang:bigbang, 0750)
├── state/                     # Snapshot, trace, host cursor, config, ledger
│   ├── config.json
│   ├── snapshot.json
│   ├── host.json
│   ├── ledger.json
│   ├── trace.jsonl
│   └── HALT                   # Kill switch file (if halted)
├── issues/                    # Ingestion drop-in directory for *.json files
└── commands.txt               # Privileged owner command stream

/etc/logrotate.d/bigbang       # Daily log rotation for trace.jsonl
/etc/systemd/system/
└── bigbang.service            # Sandboxed systemd service definition
```

---

## 4. Automated 1-Step Provisioning

### From the Proxmox Host (`192.168.1.215`)

1. Copy the `deploy/` directory to your Proxmox host:
   ```bash
   scp -r deploy/ root@192.168.1.215:/root/bigbang-deploy/
   ```

2. SSH into Proxmox and run the provisioner:
   ```bash
   ssh root@192.168.1.215
   cd /root/bigbang-deploy
   chmod +x *.sh
   ./proxmox-provision.sh
   ```

What the script does:
- Validates that target ID `300` does not collide with VM100 or VM200.
- Creates an unprivileged LXC container with nested virtualization.
- Sets up users, virtual environment, and installs `bigbang` in editable mode.
- Runs the test suite (`pytest`) to verify kernel determinism inside the container.
- Installs and enables `bigbang.service`.

---

## 5. Daily Operations & Monitoring

All commands can be run inside the container (e.g. via `pct enter 300` or `ssh bigbang@<node-ip>`):

### Check Live Status
```bash
systemctl status bigbang.service
/opt/bigbang/venv/bin/python -m bigbang status --state /var/lib/bigbang/state
```

### Tail the Event Trace
```bash
# Stream last 15 kernel decisions
/opt/bigbang/venv/bin/python -m bigbang trace --state /var/lib/bigbang/state --tail 15

# Filter for security vetos and declassifications
/opt/bigbang/venv/bin/python -m bigbang trace --state /var/lib/bigbang/state --event blocked --event declassify
```

### Feed New Unprivileged Issues
```bash
cat << 'EOF' > /var/lib/bigbang/issues/1001.json
{
  "id": 1001,
  "title": "[feature] enhance membrane filtering",
  "body": "request to add semantic trust boundary"
}
EOF
```

### Feed Privileged Owner Commands
```bash
echo "label 1001 triaged" >> /var/lib/bigbang/commands.txt
echo "close 1001" >> /var/lib/bigbang/commands.txt
```

### Safe Kill Switch (Orderly Shutdown)
```bash
# Graceful stop via systemd (calls bigbang halt internally)
systemctl stop bigbang.service

# Or manually trigger kernel kill switch directly
/opt/bigbang/venv/bin/python -m bigbang halt --state /var/lib/bigbang/state --reason "operator pause"
```

### Revive / Restart
```bash
# Clear halt and start again
systemctl start bigbang.service
```

---

## 6. Long-Term Autonomous Operations

1. **Infinite Runtime Loop**: The daemon runs with `--forever --resume --interval 1.0`, taking 1 tick per second.
2. **Log & Trace Compaction**: `/etc/logrotate.d/bigbang` rotates `trace.jsonl` daily with `copytruncate` and retains 14 compressed archives, ensuring disk storage never overflows.
3. **Reboot Recovery**: `onboot: 1` in Proxmox and `Restart=on-failure` in systemd ensure that upon any hypervisor reboot, `bigBangEnv` restores its exact state snapshot and resumes ticking autonomously.
