# bigBangEnv — Incus Multi-Tier Collective Systems Guide

This guide walks through deploying and operating **bigBangEnv** on a dedicated **Incus Container Incubator** on Proxmox VE (`192.168.1.215`).

---

## 1. Architectural Overview

```
Proxmox VE Physical Host (192.168.1.215)
│
├── VM 100: agentic-ai-node (PROTECTED - NOT TOUCHED)
├── VM 200: (PROTECTED - NOT TOUCHED)
│
└── VM 300: bigbang-incubator (Debian 12 + Incus System Containers)
    │
    ├── [Incus Private Bridge: bb-net-alpha (10.99.1.1/24)]
    │   ├── bb-alpha-sensor   (Level 1 Organism: Perception & World Ingest)
    │   ├── bb-alpha-reasoner (Level 1 Organism: Reasoning & Classification)
    │   ├── bb-alpha-defense  (Level 1 Organism: Deterministic Policy & Veto)
    │   └── bb-alpha-motor    (Level 1 Organism: Safe Execution)
    │
    ├── [Incus Private Bridge: bb-net-beta (10.99.2.1/24)]
    │   ├── bb-beta-planner   (Level 2 System: High-Level Goal Decomposition)
    │   └── bb-beta-motor     (Level 2 System: External System Actuators)
    │
    └── [Synaptic Mesh Link: bb-alpha-motor ───> bb-beta-planner:sensor]
```

---

## 2. Step 1: Provision the Incubator VM on Proxmox

From your MacBook, upload the deployment bundle to your Proxmox server (`192.168.1.215`):

```bash
scp -r /Users/pmwasim/Documents/WasimPrivate/Machines/bigBangEnv/deploy root@192.168.1.215:/root/bigbang-deploy/
```

SSH into the Proxmox host and run the automated provisioner:

```bash
ssh root@192.168.1.215
cd /root/bigbang-deploy
chmod +x *.sh
./proxmox-incus-vm-provision.sh
```

The script will:
- Validate that target ID `300` does not collide with VM 100, 200, or any active VM.
- Enable CPU host nested virtualization (`kvm_intel.nested=Y` or `kvm_amd.nested=1`).
- Download the official Debian 12 generic cloud image and attach it to VM 300.
- Configure Cloud-Init with 4 vCPUs, 8 GB RAM, and a 64 GB SSD disk.
- Start VM 300 and print its DHCP IP address.

---

## 3. Step 2: Bootstrap Incus Inside the Incubator VM

Once VM 300 is online (e.g. `192.168.1.185`):

```bash
ssh wasim@192.168.1.185
```

Upload or copy `deploy/` into VM 300, then execute the bootstrap script:

```bash
cd ~/deploy
chmod +x bootstrap-incus-node.sh bigbang-mesh.py
sudo ./bootstrap-incus-node.sh
```

This installs Incus, initializes the container storage pool and default `bigbang-organism` profile (with 1 vCPU and 512 MB RAM ceilings per organism), pre-caches Debian 12, and installs `/usr/local/bin/bigbang-mesh`.

---

## 4. Step 3: Orchestrate Multi-Tier Systems with `bigbang-mesh`

The `bigbang-mesh` CLI makes spinning up, interconnecting, and managing collective environments simple:

### 1. Spawn Level 1 System (Alpha: Triage & Defense)
```bash
bigbang-mesh spawn-tier alpha --subnet 10.99.1.1/24 --members sensor,reasoner,defense,motor
```
In ~5 seconds, 4 isolated system containers (`bb-alpha-sensor`, `bb-alpha-reasoner`, `bb-alpha-defense`, `bb-alpha-motor`) are online, running their own `bigBangEnv` kernels on a private bridge.

### 2. Spawn Level 2 System (Beta: Synthesis & Planning)
```bash
bigbang-mesh spawn-tier beta --subnet 10.99.2.1/24 --members planner,governor,motor
```

### 3. Establish a Synaptic Bridge Across Tiers
To have the Motor actions of Tier Alpha automatically feed into the Sensory inputs of Tier Beta:
```bash
bigbang-mesh bridge bb-alpha-motor bb-beta-planner
```

### 4. Monitor the Hierarchical Mesh
```bash
bigbang-mesh list
```
Output:
```
TIER            ORGANISM                 STATE      IPV4             TICKS    HALTED
---------------------------------------------------------------------------
alpha           sensor                   Running    10.99.1.102      142      False
alpha           reasoner                 Running    10.99.1.103      142      False
alpha           defense                  Running    10.99.1.104      142      False
alpha           motor                    Running    10.99.1.105      142      False
beta            planner                  Running    10.99.2.102      88       False
beta            governor                 Running    10.99.2.103      88       False
beta            motor                    Running    10.99.2.104      88       False
```

### 5. Stream Live Kernel Trace from Any Organism
```bash
bigbang-mesh trace bb-alpha-defense --tail 20
```

### 6. Orderly Halt of an Entire Tier
```bash
bigbang-mesh halt-tier alpha
```
Triggers `bigbang halt` across all member organisms, allowing active ticks to finalize and write their state snapshots cleanly.
