# GH200 Setup and Test Run Guide

This document is a self-contained, step-by-step guide for setting up and running
the replay-deadline pressure experiments on a GH200 machine from scratch. It
covers every dependency, version, path, and workaround needed to reproduce the
experiments.

---

## Table of Contents

1. [Machine Requirements](#1-machine-requirements)
2. [Architecture Warning — Do Not Copy venvs from EC2](#2-architecture-warning)
3. [Network Layout — Jump Host](#3-network-layout--jump-host)
4. [Step 1 — Sync the Repo to GH200](#step-1--sync-the-repo-to-gh200)
5. [Step 2 — SSH Into GH200](#step-2--ssh-into-gh200)
6. [Step 3 — Build Python Venvs on GH200](#step-3--build-python-venvs-on-gh200)
7. [Step 4 — Install Node.js ARM64](#step-4--install-nodejs-arm64)
8. [Step 5 — Pre-Create Required Directories](#step-5--pre-create-required-directories)
9. [Step 6 — Smoke Test the Harnesses (no GPU needed)](#step-6--smoke-test-the-harnesses-no-gpu-needed)
10. [Step 7 — Docker Setup (required for GPU runs)](#step-7--docker-setup-required-for-gpu-runs)
11. [Step 8 — Per-Session Setup (run every new shell)](#step-8--per-session-setup-run-every-new-shell)
12. [Step 9 — Hatcher Sentinel Run (first GPU run)](#step-9--hatcher-sentinel-run-first-gpu-run)
13. [Step 10 — Full 7-Harness Apples-to-Apples Run](#step-10--full-7-harness-apples-to-apples-run)
14. [Step 11 — GH200-Scaled Pressure Run](#step-11--gh200-scaled-pressure-run)
15. [Step 12 — Download Results](#step-12--download-results)
16. [Updating Code from Another Machine](#updating-code-from-another-machine)
17. [Hardware Profiles Reference](#hardware-profiles-reference)
18. [Pressure Levels Reference](#pressure-levels-reference)
19. [Known Issues and Workarounds](#known-issues-and-workarounds)
20. [Path Reference](#path-reference)

---

## 1. Machine Requirements

| Item | Requirement |
| --- | --- |
| GPU | NVIDIA Grace Hopper 200 (GH200) |
| CPU architecture | `aarch64` / `arm64` |
| GPU driver | 570.x series (CUDA 12.8 max on bare metal) |
| Docker | Must be installed and able to run `--gpus all` |
| Docker image | `lmsysorg/sglang:latest` (ships Python 3.12 + its own CUDA runtime) |
| Python on host | Python 3.11 (needed for NAT and Hermes venvs) |
| Node.js on host | Current LTS via nvm — the GH200 system Node v12 OOM-crashes |
| Model cache | `/home/central/ojaiyeob/dynamo_model_cache` (NFS-mounted on this GH200) |
| Home directory | `/home/central/ojaiyeob` (NFS-mounted; use `/tmp` paths for Docker cache) |
| Project directory on GH200 | `~/agentic_hardware` → resolves to `/home/central/ojaiyeob/agentic_hardware` |

---

## 2. Architecture Warning

The GH200 is `aarch64`. The EC2 machine is `x86_64`. Python wheels and
compiled C extensions are architecture-specific and are **not portable**.

**Never copy `.venv/`, `node_modules/`, or any installed venv from EC2 to
GH200.** The sync script already excludes these directories. Always rebuild them
directly on GH200 after syncing the source code.

---

## 3. Network Layout — Jump Host

The GH200 machine (`gracehopper`) is not directly reachable from the public
internet. All connections go through a jump/bastion host.

| Variable | Default value |
| --- | --- |
| `AGENTIC_GH200_USER` | `ojaiyeob` |
| `AGENTIC_GH200_HOST` | `gracehopper` |
| `AGENTIC_GH200_JUMP_HOST` | `falcon.7elements.com` |
| `AGENTIC_GH200_JUMP_PORT` | `1337` |
| `AGENTIC_GH200_REMOTE_DIR` | `/home/central/ojaiyeob/agentic_hardware` |

Override any of these by exporting the variable before running the helper
scripts, for example:

```bash
export AGENTIC_GH200_USER="ojaiyeob"
export AGENTIC_GH200_HOST="gracehopper"
export AGENTIC_GH200_JUMP_HOST="falcon.7elements.com"
export AGENTIC_GH200_JUMP_PORT="1337"
```

SSH multiplexing is enabled automatically (`ControlMaster=auto`,
`ControlPersist=10m`) so subsequent connections reuse the first tunnel.

---

## Step 1 — Sync the Repo to GH200

Run this from your **local machine** inside the repo root:

```bash
./gh200/sync_to_gh200.sh
```

What it does:
- rsync over the jump host using the SSH options above
- Excludes `.git/`, `.venv/`, `venv/`, `node_modules/`, `artifacts/`,
  `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`,
  `*.log`, `tmp/`, `.DS_Store`
- Protects any existing `artifacts/` directory on the remote so experiment
  results are never overwritten by a sync
- Sets execute bits (`chmod ugo=rwX`) so shell scripts are runnable after sync
- Clears stale `.pyc` files on the remote after transfer

Dry-run preview (no files transferred):

```bash
./gh200/sync_to_gh200.sh --dry
```

---

## Step 2 — SSH Into GH200

```bash
./gh200/ssh_to_gh200.sh
```

Or to run a single remote command:

```bash
./gh200/ssh_to_gh200.sh 'uname -m'   # should print: aarch64
```

---

## Step 3 — Build Python Venvs on GH200

SSH into GH200 first, then run:

```bash
cd ~/agentic_hardware/sglang_direct_kv

INSTALL_SYSTEM_DEPS=0 bash scripts/setup_gh200.sh
```

**Critical: always pass `INSTALL_SYSTEM_DEPS=0`.**
Without it, `apt-get` triggers a pre-existing DKMS conflict
(`nvidia-fs` version mismatch) in the GH200 image and aborts the script before
any venvs are created.

The script creates three venvs:

| Venv path | Python | Purpose |
| --- | --- | --- |
| `~/agentic_hardware/sglang_direct_kv/.venv` | 3.11 | Main project environment (smoke tests, report builder, workload driver) |
| `~/agentic_hardware/.venvs/nat_py311` | 3.11 | NeMo Agent Toolkit (NAT). Install with `nvidia-nat[langchain]` — the plain `nvidia-nat` package is missing LangChain support. |
| `~/agentic_hardware/.venvs/hermes_agent_py311` | 3.11 | Hermes Agent CLI |

After the script finishes, activate the main project venv:

```bash
source ~/agentic_hardware/sglang_direct_kv/.venv/bin/activate
```

Binaries produced:

| Binary | Path |
| --- | --- |
| `nat` | `~/agentic_hardware/.venvs/nat_py311/bin/nat` |
| `hermes` | `~/agentic_hardware/.venvs/hermes_agent_py311/bin/hermes` |

---

## Step 4 — Install Node.js ARM64

The native CLI harnesses (codex, claude_code, opencode, qwen_code,
pi_agent_harness, openclaw) require Node.js. The GH200 system ships Node v12,
which OOM-crashes under the workload. Install a current LTS build via nvm:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source "$HOME/.nvm/nvm.sh"
nvm install --lts
node -p "process.arch"   # must print: arm64
```

If `node` is missing after reopening a session, add the nvm init lines to your
shell profile manually:

```bash
echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.bashrc
echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> ~/.bashrc
source ~/.bashrc
```

Verify after reopening:

```bash
node --version           # e.g. v22.x.x
node -p "process.arch"  # must print: arm64
```

---

## Step 5 — Pre-Create Required Directories

Run once on GH200 before the first experiment:

```bash
mkdir -p ~/agentic_hardware/sglang_direct_kv/artifacts/results
mkdir -p ~/agentic_hardware/sglang_direct_kv/src/agentic_kv.egg-info
```

The `artifacts/results` directory must exist before Docker writes output files.
The `egg-info` directory must exist before the package is importable inside the
container.

---

## Step 6 — Smoke Test the Harnesses (no GPU needed)

This test verifies all harness CLIs can reach and negotiate with the inspection
gateway. It runs without a GPU using a fake local SGLang backend.

```bash
cd ~/agentic_hardware/sglang_direct_kv
source .venv/bin/activate

HARNESS_NAT_BIN=$HOME/agentic_hardware/.venvs/nat_py311/bin/nat \
HARNESS_HERMES_BIN=$HOME/agentic_hardware/.venvs/hermes_agent_py311/bin/hermes \
python scripts/smoke_multi_harness_wireability.py \
  --harnesses codex claude_code opencode qwen_code pi_agent_harness openclaw nemo_agent_toolkit hermes_agent
```

Expected output for all 8 harnesses:

```
propagated replay priority through gateway
```

If any harness fails here, fix it before running GPU experiments.

---

## Step 7 — Docker Setup (required for GPU runs)

### Why Docker is required

The GH200 driver is 570.x series, which supports CUDA 12.8 at most. The
pip-installable `torch` package pulls a CUDA 13.0 build. The bare `.venv`
therefore cannot see the GPU. The `lmsysorg/sglang` Docker image bundles its
own CUDA runtime and works with the existing driver.

### Verify the image

```bash
docker images | grep lmsysorg/sglang
```

If missing, pull it:

```bash
docker pull lmsysorg/sglang:latest
```

### SGLang version note

The Docker image ships SGLang 0.5.8. That version **removed**
`--disable-piecewise-cuda-graph`. All experiment runs must override
`EXTRA_SERVER_ARGS` to use only flags that exist in 0.5.8:

```
EXTRA_SERVER_ARGS='--disable-cuda-graph --disable-overlap-schedule'
```

The `--default-priority-value` flag is version-detected at runtime by the
experiment scripts, so no manual flag change is needed for that one.

### Harness limitation in Docker

The `lmsysorg/sglang:latest` container ships Python 3.12. The `nat` and
`hermes` binaries depend on Python 3.11 compiled C extensions (`pydantic-core`,
etc.) installed in the host `.venvs/nat_py311` and `.venvs/hermes_agent_py311`
venvs. Those extensions cannot load inside the Python 3.12 container.

Until the GH200 driver is upgraded to support a bare `.venv` without Docker:

- Run **7 harnesses** via Docker: `hatcher codex claude_code opencode qwen_code pi_agent_harness openclaw`
- **Exclude** `nemo_agent_toolkit` and `hermes_agent` from Docker runs

### Model cache location

The model cache lives at:

```
/home/central/ojaiyeob/dynamo_model_cache
```

This path is also available as `~/dynamo_model_cache` on GH200.

---

## Step 8 — Per-Session Setup (run every new shell)

These two steps must be done once per login session before any Docker GPU run.

### 8a — Load nvm so Node is on PATH

```bash
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
```

### 8b — Create temp files Docker needs

Docker runs as your user UID (`-u $(id -u):$(id -g)`). The torch library tries
to look up the username for that UID in `/etc/passwd`. The NFS-mounted
`/etc/passwd` does not contain the UID when running inside the container, so
torch crashes on startup. A minimal single-line passwd entry fixes it.

```bash
mkdir -p /tmp/gh200home
echo "ojaiyeob:x:$(id -u):$(id -g)::/tmp/gh200home:/bin/bash" > /tmp/gh200_passwd
```

Replace `ojaiyeob` with your actual username if different.

---

## Step 9 — Hatcher Sentinel Run (first GPU run)

This is the recommended first Docker GPU run. It uses only the in-repo Hatcher
control harness with 3 pressure levels (P0, P3, P5) and both modes. Run it
first to verify the Docker setup is working end-to-end before launching the
full harness set.

Always run inside `screen` so the experiment survives a terminal disconnect:

```bash
screen -S gh200_experiment
# Detach any time with: Ctrl+A then D
# Reattach with:        screen -r gh200_experiment
```

Then run the Docker command:

```bash
docker run --rm --gpus all \
  -u $(id -u):$(id -g) \
  -v ~/agentic_hardware:/workspace/agentic_hardware \
  -v ~/agentic_hardware:/home/central/ojaiyeob/agentic_hardware \
  -v ~/dynamo_model_cache:/tmp/hfcache \
  -v ~/.nvm:/tmp/gh200home/.nvm \
  -v /tmp/gh200_passwd:/etc/passwd:ro \
  -v /tmp/gh200home:/tmp/gh200home \
  -e HF_HOME=/tmp/hfcache \
  -e NVM_DIR=/tmp/gh200home/.nvm \
  -e HOME=/tmp/gh200home \
  -e TORCHINDUCTOR_CACHE_DIR=/tmp/gh200home/torchinductor \
  lmsysorg/sglang:latest \
  bash -c "
    source /tmp/gh200home/.nvm/nvm.sh 2>/dev/null || true
    cd /workspace/agentic_hardware/sglang_direct_kv
    EXTRA_SERVER_ARGS='--disable-cuda-graph --disable-overlap-schedule' \
    HARNESS_NAT_BIN=/workspace/agentic_hardware/.venvs/nat_py311/bin/nat \
    HARNESS_HERMES_BIN=/workspace/agentic_hardware/.venvs/hermes_agent_py311/bin/hermes \
    HARDWARE_PROFILE=ec2_a10g \
    HARNESSES=hatcher \
    PRESSURE_LEVELS='p0_control p3_high p5_boss_queue' \
    MODES='no_prefetch e2e_priority_hints' \
    REPORT_BUILDER_MODE=lightweight \
    REPORT_LABEL=\"gh200_apples_to_apples_\$(date +%Y%m%d_%H%M%S)\" \
    bash scripts/run_native_harness_deadline_pressure.sh \
      Qwen/Qwen2.5-Coder-7B-Instruct
  "
```

Expected result: 6 cases complete (2 modes × 3 pressure levels) and the script
prints `Done.` with a report path.

### Docker flag explanations

| Flag | Reason |
| --- | --- |
| `--gpus all` | Expose the GH200 GPU to the container |
| `-u $(id -u):$(id -g)` | Write output files as your user, not root. Without this, `artifacts/` becomes root-owned and you cannot delete or overwrite files from the host. |
| `-v ~/agentic_hardware:/workspace/agentic_hardware` | Primary repo mount used by the experiment scripts |
| `-v ~/agentic_hardware:/home/central/ojaiyeob/agentic_hardware` | Secondary mount at the absolute host path. The `nat` and `hermes` binaries have shebangs pointing to absolute host paths (e.g. `/home/central/ojaiyeob/agentic_hardware/.venvs/...`). Without this second mount the shebangs cannot resolve inside the container. |
| `-v ~/dynamo_model_cache:/tmp/hfcache` | Mounts the model cache to a path your UID owns. Mounting to `/root/.cache` causes permission errors when running as non-root. |
| `-v ~/.nvm:/tmp/gh200home/.nvm` | Makes nvm (and the ARM64 Node.js LTS) available inside the container |
| `-v /tmp/gh200_passwd:/etc/passwd:ro` | Provides a passwd entry for your UID so torch can look up the username. Without this torch crashes on startup. |
| `-v /tmp/gh200home:/tmp/gh200home` | Gives torch a writable directory for its inductor cache |
| `-e HF_HOME=/tmp/hfcache` | Tells HuggingFace to load models from the mounted cache |
| `-e NVM_DIR=/tmp/gh200home/.nvm` | Points nvm to the mounted `.nvm` directory |
| `-e HOME=/tmp/gh200home` | Sets HOME to a writable directory (the NFS home is not writable as non-root inside the container) |
| `-e TORCHINDUCTOR_CACHE_DIR=...` | Keeps the torch inductor cache inside the writable `/tmp/gh200home` |

### Cleaning up root-owned files from a previous run

If a prior run left root-owned files in `artifacts/` that you cannot delete,
use Docker to remove them (the container runs as the same UID that created
them):

```bash
docker run --rm \
  -v ~/agentic_hardware:/workspace/agentic_hardware \
  lmsysorg/sglang:latest \
  rm -rf /workspace/agentic_hardware/sglang_direct_kv/artifacts

mkdir -p ~/agentic_hardware/sglang_direct_kv/artifacts/results
```

---

## Step 10 — Full 7-Harness Apples-to-Apples Run

Run this after the hatcher sentinel passes. Uses `HARDWARE_PROFILE=ec2_a10g`
so results are directly comparable to the EC2 baseline.

NAT (`nemo_agent_toolkit`) and Hermes (`hermes_agent`) are excluded because
they require Python 3.11 C extensions that cannot load in the Python 3.12
Docker container.

```bash
screen -S gh200_experiment   # or reattach: screen -r gh200_experiment

docker run --rm --gpus all \
  -u $(id -u):$(id -g) \
  -v ~/agentic_hardware:/workspace/agentic_hardware \
  -v ~/agentic_hardware:/home/central/ojaiyeob/agentic_hardware \
  -v ~/dynamo_model_cache:/tmp/hfcache \
  -v ~/.nvm:/tmp/gh200home/.nvm \
  -v /tmp/gh200_passwd:/etc/passwd:ro \
  -v /tmp/gh200home:/tmp/gh200home \
  -e HF_HOME=/tmp/hfcache \
  -e NVM_DIR=/tmp/gh200home/.nvm \
  -e HOME=/tmp/gh200home \
  -e TORCHINDUCTOR_CACHE_DIR=/tmp/gh200home/torchinductor \
  lmsysorg/sglang:latest \
  bash -c "
    source /tmp/gh200home/.nvm/nvm.sh 2>/dev/null || true
    cd /workspace/agentic_hardware/sglang_direct_kv
    EXTRA_SERVER_ARGS='--disable-cuda-graph --disable-overlap-schedule' \
    HARNESS_NAT_BIN=/workspace/agentic_hardware/.venvs/nat_py311/bin/nat \
    HARNESS_HERMES_BIN=/workspace/agentic_hardware/.venvs/hermes_agent_py311/bin/hermes \
    HARDWARE_PROFILE=ec2_a10g \
    HARNESSES='hatcher codex claude_code opencode qwen_code pi_agent_harness openclaw' \
    PRESSURE_LEVELS='p0_control p3_high p5_boss_queue' \
    MODES='no_prefetch e2e_priority_hints' \
    REPORT_BUILDER_MODE=lightweight \
    REPORT_LABEL=\"gh200_apples_to_apples_\$(date +%Y%m%d_%H%M%S)\" \
    bash scripts/run_native_harness_deadline_pressure.sh \
      Qwen/Qwen2.5-Coder-7B-Instruct
  "
```

Expected: 42 cases complete (7 harnesses × 2 modes × 3 pressure levels).

---

## Step 11 — GH200-Scaled Pressure Run

Run this after the apples-to-apples run passes. Uses `HARDWARE_PROFILE=gh200`
which increases token budget, HiCache size, filler count, and concurrency to
find the GH200's own replay-deadline cliff.

```bash
docker run --rm --gpus all \
  -u $(id -u):$(id -g) \
  -v ~/agentic_hardware:/workspace/agentic_hardware \
  -v ~/agentic_hardware:/home/central/ojaiyeob/agentic_hardware \
  -v ~/dynamo_model_cache:/tmp/hfcache \
  -v ~/.nvm:/tmp/gh200home/.nvm \
  -v /tmp/gh200_passwd:/etc/passwd:ro \
  -v /tmp/gh200home:/tmp/gh200home \
  -e HF_HOME=/tmp/hfcache \
  -e NVM_DIR=/tmp/gh200home/.nvm \
  -e HOME=/tmp/gh200home \
  -e TORCHINDUCTOR_CACHE_DIR=/tmp/gh200home/torchinductor \
  lmsysorg/sglang:latest \
  bash -c "
    source /tmp/gh200home/.nvm/nvm.sh 2>/dev/null || true
    cd /workspace/agentic_hardware/sglang_direct_kv
    EXTRA_SERVER_ARGS='--disable-cuda-graph --disable-overlap-schedule' \
    HARNESS_NAT_BIN=/workspace/agentic_hardware/.venvs/nat_py311/bin/nat \
    HARNESS_HERMES_BIN=/workspace/agentic_hardware/.venvs/hermes_agent_py311/bin/hermes \
    HARDWARE_PROFILE=gh200 \
    HARNESSES='hatcher codex claude_code opencode qwen_code pi_agent_harness openclaw' \
    PRESSURE_LEVELS='p0_control p1_mild p2_medium p3_high p4_cliff p5_boss_queue' \
    MODES='no_prefetch e2e_priority_hints' \
    REPORT_BUILDER_MODE=lightweight \
    REPORT_LABEL=\"gh200_scaled_deadline_pressure_\$(date +%Y%m%d_%H%M%S)\" \
    bash scripts/run_native_harness_deadline_pressure.sh \
      Qwen/Qwen2.5-Coder-7B-Instruct
  "
```

Expected: 84 cases complete (7 harnesses × 2 modes × 6 pressure levels).

---

## Step 12 — Download Results

Run from your **local machine**:

```bash
# Latest HTML report only
./gh200/download.sh

# Full artifacts directory
./gh200/download.sh --all
```

Files produced locally:

| Local path | Content |
| --- | --- |
| `sglang_direct_kv/artifacts/results/latest_master_report.html` | Latest report |
| `latest_master_report.html` | Copy at repo root |
| `sglang_direct_kv/artifacts/results/reports/<REPORT_LABEL>/master_report.html` | Archived copy |

---

## Updating Code from Another Machine

This setup is modular for source code changes. The Docker container mounts the
repo as a live volume (`-v ~/agentic_hardware:/workspace/agentic_hardware`), so
files synced to GH200 are immediately visible inside the container — no Docker
rebuild or image pull is needed.

### The update workflow

**On your development machine** — commit or stage your changes, then re-run the
sync:

```bash
./gh200/sync_to_gh200.sh
```

The sync is safe to run at any time. It protects the remote `artifacts/`
directory (`--filter='protect sglang_direct_kv/artifacts/'`) so no experiment
results are overwritten.

**On GH200** — what you need to do next depends on what changed:

| What changed | Action on GH200 |
| --- | --- |
| Modified `.py` files or scripts (no new dependencies) | Nothing — the editable install resolves imports directly from the source tree |
| New `.py` files inside the existing package structure | Nothing — editable install picks them up immediately |
| New top-level Python package directory added | `source .venv/bin/activate && pip install -e .` |
| `requirements.txt` changed (new or updated dependency) | `source .venv/bin/activate && pip install -r requirements.txt` |
| New dependency needed by NAT (`nemo_agent_toolkit`) | `~/agentic_hardware/.venvs/nat_py311/bin/pip install <package>` |
| New dependency needed by Hermes | `~/agentic_hardware/.venvs/hermes_agent_py311/bin/pip install <package>` |
| New shell script added under `scripts/` | Nothing — `sync_to_gh200.sh` sets execute bits (`chmod ugo=rwX`) during transfer |
| New config file under `configs/` | Nothing — scripts load configs at runtime from the synced path |

### What never needs to change

- The Docker image (`lmsysorg/sglang:latest`) — it only provides the CUDA
  runtime and the SGLang server. All experiment Python code, scripts, and
  configs run from the mounted repo volume.
- The venvs — unless `requirements.txt` or package structure changed (see
  table above).
- The per-session setup (Step 8) — `/tmp/gh200_passwd` and `/tmp/gh200home`
  are independent of source code.

### The one gotcha: stale egg-info

If the package structure changes enough that
`sglang_direct_kv/src/agentic_kv.egg-info` becomes stale, you may see import
errors when running scripts. Fix:

```bash
cd ~/agentic_hardware/sglang_direct_kv
source .venv/bin/activate
pip install -e .
```

This is fast (a few seconds) and safe to run after any sync that touches the
package structure.

### Decision guide

```
Did requirements.txt change?
  Yes → pip install -r requirements.txt inside .venv
  No  → Did you add a new top-level package directory?
          Yes → pip install -e . inside .venv
          No  → sync is sufficient, nothing else needed
```

---

## Hardware Profiles Reference

Hardware profiles live in `sglang_direct_kv/configs/hardware/`.

### `ec2_a10g` — apples-to-apples comparison profile

| Parameter | Value |
| --- | --- |
| `MAX_TOTAL_TOKENS` | 24576 |
| `HICACHE_SIZE_GB` | 8 |
| `MEM_FRACTION_STATIC` | 0.72 |
| `REPORT_BUILDER_MODE` | lightweight |
| `GPU_UTIL_SAMPLE_INTERVAL_MS` | 100 |

Pressure knobs:

| Level | `tool_wait_ms` | `target_prompt_tokens` | `filler_sessions` | `filler_prompt_tokens` | `session_count` | `concurrency` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P0 control | 500 | 1024 | 0 | 768 | 1 | 1 |
| P1 mild | 250 | 2048 | 8 | 1024 | 1 | 4 |
| P2 medium | 100 | 3072 | 16 | 1536 | 1 | 6 |
| P3 high | 50 | 4096 | 32 | 1536 | 1 | 8 |
| P4 cliff | 25 | 4096 | 48 | 2048 | 1 | 10 |
| P5 boss queue | 50 | 4096 | 4 | 2048 | 4 | 12 |

### `gh200` — GH200-scaled pressure profile

| Parameter | Value |
| --- | --- |
| `MAX_TOTAL_TOKENS` | 98304 |
| `HICACHE_SIZE_GB` | 32 |
| `MEM_FRACTION_STATIC` | 0.80 |
| `REPORT_BUILDER_MODE` | lightweight |
| `GPU_UTIL_SAMPLE_INTERVAL_MS` | 100 |

Pressure knobs:

| Level | `tool_wait_ms` | `target_prompt_tokens` | `filler_sessions` | `filler_prompt_tokens` | `session_count` | `concurrency` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P0 control | 500 | 1024 | 0 | 768 | 1 | 1 |
| P1 mild | 250 | 2048 | 16 | 1536 | 1 | 8 |
| P2 medium | 100 | 4096 | 32 | 2048 | 1 | 12 |
| P3 high | 50 | 4096 | 64 | 2048 | 1 | 16 |
| P4 cliff | 25 | 8192 | 96 | 3072 | 1 | 24 |
| P5 boss queue | 50 | 8192 | 8 | 3072 | 8 | 32 |

---

## Pressure Levels Reference

| Level | Name | Primary stressor |
| --- | --- | --- |
| `p0_control` | Control | Easy baseline — long tool wait, small prompt, no fillers |
| `p1_mild` | Mild pressure | Shorter wait, modest context, small filler count |
| `p2_medium` | Medium pressure | More queue and KV pressure |
| `p3_high` | Queue pressure | One urgent replay behind 32–64 filler requests |
| `p4_cliff` | Deadline cliff | Very short wait plus large KV and heavier backend pressure |
| `p5_boss_queue` | Boss queue | Many urgent replays compete simultaneously |

Sentinel runs use `p0_control p3_high p5_boss_queue`. Full ladder runs use all
six levels.

---

## Known Issues and Workarounds

### DKMS conflict on apt-get

`apt-get` on this GH200 image hits a pre-existing `nvidia-fs` version mismatch
that aborts. **Always pass `INSTALL_SYSTEM_DEPS=0`** to `setup_gh200.sh`.

### torch crashes with "uid not found"

torch calls `getpwuid()` to look up the username. When running as a non-root
UID inside Docker against an NFS-mounted `/etc/passwd`, the UID entry is
missing. Fix: create `/tmp/gh200_passwd` with a single line for your UID and
bind-mount it as `/etc/passwd:ro` (see Step 8b).

### torch cannot write its cache

The NFS home directory is not writable for non-root UIDs inside the container.
Fix: set `HOME=/tmp/gh200home` and `TORCHINDUCTOR_CACHE_DIR=/tmp/gh200home/torchinductor`
and bind-mount `/tmp/gh200home` into the container.

### `--disable-piecewise-cuda-graph` is not recognized

SGLang 0.5.8 (the Docker image version) removed this flag. Use:

```
EXTRA_SERVER_ARGS='--disable-cuda-graph --disable-overlap-schedule'
```

### root-owned files block re-runs

If a run that was not started with `-u $(id -u):$(id -g)` left root-owned
files, the host user cannot delete or overwrite them. Remove with Docker:

```bash
docker run --rm \
  -v ~/agentic_hardware:/workspace/agentic_hardware \
  lmsysorg/sglang:latest \
  rm -rf /workspace/agentic_hardware/sglang_direct_kv/artifacts
mkdir -p ~/agentic_hardware/sglang_direct_kv/artifacts/results
```

### NAT and Hermes fail inside Docker

`nemo_agent_toolkit` and `hermes_agent` depend on Python 3.11 compiled C
extensions. The Docker image ships Python 3.12. These two harnesses are
excluded from all Docker-based runs. The smoke test in Step 6 can verify them
on the host using the Python 3.11 venvs.

### Node not found inside Docker

The `source /tmp/gh200home/.nvm/nvm.sh 2>/dev/null || true` line at the start
of the Docker bash command loads nvm from the bind-mounted `~/.nvm`. If Node
is still not found, verify that `~/.nvm` on the host contains the correct LTS
binary and that the bind-mount path is correct.

### NVM install warns "no shell profile found"

This is harmless. Add the init lines to `~/.bashrc` manually as shown in
Step 4.

---

## Path Reference

| Path | Description |
| --- | --- |
| `~/agentic_hardware/sglang_direct_kv/` | Main experiment directory (inside container: `/workspace/agentic_hardware/sglang_direct_kv/`) |
| `~/agentic_hardware/sglang_direct_kv/.venv/` | Main project Python 3.11 venv |
| `~/agentic_hardware/.venvs/nat_py311/` | NAT Python 3.11 venv |
| `~/agentic_hardware/.venvs/hermes_agent_py311/` | Hermes Python 3.11 venv |
| `~/agentic_hardware/sglang_direct_kv/artifacts/results/` | Experiment output root |
| `~/agentic_hardware/sglang_direct_kv/artifacts/results/latest_master_report.html` | Latest HTML report |
| `~/agentic_hardware/sglang_direct_kv/artifacts/results/reports/<LABEL>/` | Archived run output |
| `~/dynamo_model_cache` | HuggingFace model cache (NFS) |
| `/tmp/gh200home` | Writable temp home for Docker runs |
| `/tmp/gh200_passwd` | Single-line passwd file for torch UID lookup |
| `sglang_direct_kv/configs/hardware/ec2_a10g.env` | EC2 hardware profile |
| `sglang_direct_kv/configs/hardware/gh200.env` | GH200 hardware profile |
| `sglang_direct_kv/scripts/setup_gh200.sh` | Venv setup script |
| `sglang_direct_kv/scripts/run_native_harness_deadline_pressure.sh` | Native-harness experiment runner |
| `sglang_direct_kv/scripts/run_harness_deadline_pressure.sh` | Main experiment orchestrator |
| `sglang_direct_kv/scripts/smoke_multi_harness_wireability.py` | No-GPU harness smoke test |
| `gh200/sync_to_gh200.sh` | rsync repo to GH200 |
| `gh200/ssh_to_gh200.sh` | SSH to GH200 |
| `gh200/download.sh` | Download results from GH200 |
