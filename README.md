# kv_cache_offloading

This repository contains the code and helper scripts for running the `kv_cache_offloading` workflow on a GPU EC2 instance.

## Main Operational Docs

For the full EC2/AWS runbook, see:

- [aws/README.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/aws/README.md)

That guide covers:

- uploading the repo to EC2
- first-time GPU instance setup
- preparing a persistent EBS volume for Docker
- storing model caches on the persistent EBS volume
- restart recovery
- readiness checks
- launching the workload

## Common Local Command

Upload the latest repo state from your local machine:

```bash
/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/aws/upload.sh
```

What it does:
- copies the current local repo to your EC2 instance
- use this again after any local script or code change

## Common EC2 Command Flow

On the EC2 instance:

```bash
cd ~/kv_cache_offloading
EXPECTED_DOCKER_DEVICE=/dev/nvme1n1 ./aws/check_ec2_ready.sh
./run_docker_sglang.sh
```

What it does:
- `check_ec2_ready.sh` verifies GPU access, Docker storage, and the expected mounted EBS disk
- `run_docker_sglang.sh` starts your main SGLang-based workload flow

Note:
- replace `/dev/nvme1n1` with the actual Docker EBS device on that instance
- on one of your recent instances this was `/dev/nvme2n1`

## EC2 Helper Scripts

### `./aws/bootstrap_ec2_gpu.sh`

Use this on a fresh GPU EC2 instance:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh
```

What it does:
- installs Docker
- installs the NVIDIA driver
- installs NVIDIA container support for Docker

### `./aws/bootstrap_ec2_docker.sh`

Use this on a fresh **non-GPU** EC2 instance such as the simplified Dynamo head/frontend node:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_docker.sh
```

What it does:
- installs Docker
- enables and starts the Docker service
- adds `ec2-user` to the Docker group

Use this for:
- the simpler Dynamo head/frontend node

Do not use this instead of the GPU bootstrap on worker nodes.

### `./aws/prepare_docker_ebs.sh`

Use this once on a fresh instance after attaching the persistent EBS volume you want Docker to use:

```bash
cd ~/kv_cache_offloading
sudo DOCKER_DATA_DEVICE=/dev/nvme1n1 ./aws/prepare_docker_ebs.sh
```

What it does:
- formats the attached EBS disk if needed
- mounts it at `/mnt/docker-data`
- configures Docker to use `/mnt/docker-data`
- sets up boot-time mounting

### `./aws/recover_docker_mount.sh`

Use this after a restart if Docker storage is not mounted correctly:

```bash
cd ~/kv_cache_offloading
sudo DOCKER_DATA_DEVICE=/dev/nvme1n1 ./aws/recover_docker_mount.sh
```

What it does:
- remounts the Docker EBS volume
- restores Docker’s data root to `/mnt/docker-data`
- helps recover from mount issues after reboot or stop/start

### `./aws/check_ec2_ready.sh`

Use this before long runs:

```bash
cd ~/kv_cache_offloading
EXPECTED_DOCKER_DEVICE=/dev/nvme1n1 ./aws/check_ec2_ready.sh
```

What it does:
- checks that the NVIDIA driver is working
- checks that Docker can see the GPU
- checks that Docker root is `/mnt/docker-data`
- checks that `/mnt/docker-data` is backed by the expected EBS disk

### `./aws/expand_root_fs.sh`

Use this after you increase the **root EBS volume size in AWS** and want the instance to actually see the larger `/` filesystem:

```bash
cd ~/kv_cache_offloading
sudo ./aws/expand_root_fs.sh
```

What it does:
- installs `growpart` if needed
- expands the root partition
- grows the XFS filesystem mounted at `/`
- prints `lsblk` and `df -h /` before and after

Use this for:
- simple head/frontend nodes where you want a bigger root disk instead of extra Docker/EBS complexity
- any future EC2 instance where you enlarge the root volume in AWS

## Main SGLang Script

### `./run_docker_sglang.sh`

Use this for your main SGLang experiments:

```bash
cd ~/kv_cache_offloading
./run_docker_sglang.sh
```

What it does:
- launches your existing SGLang experiment workflow
- uses persistent cache paths under `/mnt/docker-data`
- mounts your local modified `sglang` tree into the container

## Dynamo Test Script

## Multi-Node Dynamo Scripts

These are the scripts to use for the 3-machine experiment:

- **head/frontend node**: [run_dynamo_head.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/run_dynamo_head.sh)
- **worker GPU nodes**: [run_dynamo_worker.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/run_dynamo_worker.sh)

Recommended machine roles:
- head/frontend node: simpler node, no special `/mnt/docker-data` dependency required
- worker A: GPU worker
- worker B: GPU worker

Recommended worker instance types:
- `g5.xlarge` for the smallest supported multi-node worker
- `g5.2xlarge` if you want more memory headroom

Do not use `g4dn.xlarge` for Dynamo workers in this setup.
The published NVIDIA Dynamo support matrix is Ampere or newer, and `g4dn`
workers use T4 GPUs, which fail at runtime with kernel-image errors.

### `./run_dynamo_head.sh start`

Run this on the **head/frontend node**:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_docker.sh
./run_dynamo_head.sh start
```

What it does:
- starts `etcd`
- starts `nats-server -js`
- starts `dynamo.frontend`
- runs the frontend in KV-router mode
- uses `--no-router-kv-events` by default for a simpler first distributed experiment

Why this is the recommended head-node flow:
- it avoids the fragile Docker EBS mount complexity on the frontend
- the frontend does not need model weights or a GPU
- it is a cleaner control-plane node

Preparation note:
- if this is a brand new head node, run `sudo ./aws/bootstrap_ec2_docker.sh` first
- if Docker group membership was just added, log out and SSH back in before using `./run_dynamo_head.sh`

### `./run_dynamo_head.sh status`

```bash
cd ~/kv_cache_offloading
./run_dynamo_head.sh status
```

What it does:
- shows whether the head-node containers are running

### `./run_dynamo_head.sh logs`

```bash
cd ~/kv_cache_offloading
./run_dynamo_head.sh logs
```

What it does:
- shows logs for:
  - `etcd`
  - `nats-server`
  - `dynamo.frontend`

### `./run_dynamo_head.sh test`

```bash
cd ~/kv_cache_offloading
./run_dynamo_head.sh test
```

What it does:
- sends a simple OpenAI-style request to the frontend on port `8000`

### `./run_dynamo_head.sh test-priority`

```bash
cd ~/kv_cache_offloading
./run_dynamo_head.sh test-priority
```

What it does:
- sends a request with `nvext.agent_hints.priority`
- useful to confirm that the request-metadata path still works in the multi-node setup

### `./run_dynamo_worker.sh start`

Run this on **each worker node**.

Use a **G5-class worker** here, not `g4dn.xlarge`.

Before starting, you need the **private IP of the head node**.

Example:

```bash
cd ~/kv_cache_offloading
ETCD_ENDPOINTS=http://172.31.84.204:2379 ./run_dynamo_worker.sh start
```

What it does:
- starts one SGLang worker on that GPU machine
- registers with the head node’s `etcd`
- mounts the worker cache directory
- uses the stable Dynamo + SGLang image

Important:
- run this separately on worker A and worker B
- both workers should use the same model
- you may want to set unique container names per worker if you prefer, though it is not required because they are on separate machines
- if a worker is `g4dn`/T4-based, this runtime is the wrong fit; move that worker to `g5.xlarge` or `g5.2xlarge`

### `./run_dynamo_worker.sh status`

```bash
cd ~/kv_cache_offloading
./run_dynamo_worker.sh status
```

What it does:
- shows whether that worker container is running

### `./run_dynamo_worker.sh logs`

```bash
cd ~/kv_cache_offloading
./run_dynamo_worker.sh logs
```

What it does:
- shows the worker logs
- use this first if the worker does not stay up

### `./run_dynamo_worker.sh stop`

```bash
cd ~/kv_cache_offloading
./run_dynamo_worker.sh stop
```

What it does:
- stops and removes the worker container on that machine

## Recommended Multi-Node Flow

### On the head/frontend node

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_docker.sh
./run_dynamo_head.sh start
./run_dynamo_head.sh status
./run_dynamo_head.sh logs
hostname -I (workers would need this IP)
```

### On worker A

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh rootdisk
newgrp docker
./aws/check_ec2_rootdisk_worker_ready.sh
ETCD_ENDPOINTS=http://<head-private-ip>:2379 ./run_dynamo_worker.sh start
./run_dynamo_worker.sh status
./run_dynamo_worker.sh logs
```

Recommended worker instance: `g5.xlarge` or `g5.2xlarge`

### On worker B

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh rootdisk
newgrp docker
./aws/check_ec2_rootdisk_worker_ready.sh
ETCD_ENDPOINTS=http://<head-private-ip>:2379 ./run_dynamo_worker.sh start
./run_dynamo_worker.sh status
./run_dynamo_worker.sh logs
```

Recommended worker instance: `g5.xlarge` or `g5.2xlarge`

### Back on the head/frontend node

```bash
cd ~/kv_cache_offloading
./run_dynamo_head.sh test
./run_dynamo_head.sh test-priority
```

### Exact startup example for your current topology

If your current head node private IP is `172.31.92.60`, this is the exact startup sequence:

#### Head/frontend node

```bash
cd ~/kv_cache_offloading
./run_dynamo_head.sh start
./run_dynamo_head.sh status
./run_dynamo_head.sh logs
./run_dynamo_head.sh stop
```

#### Worker A

```bash
cd ~/kv_cache_offloading
./aws/check_ec2_rootdisk_worker_ready.sh
ETCD_ENDPOINTS=http://172.31.92.60:2379 ./run_dynamo_worker.sh start
./run_dynamo_worker.sh status
./run_dynamo_worker.sh logs
./run_dynamo_worker.sh stop
```

#### Worker B

```bash
cd ~/kv_cache_offloading
./aws/check_ec2_rootdisk_worker_ready.sh
ETCD_ENDPOINTS=http://172.31.92.60:2379 ./run_dynamo_worker.sh start
./run_dynamo_worker.sh status
./run_dynamo_worker.sh logs
./run_dynamo_worker.sh stop
```

### `./aws/check_ec2_rootdisk_worker_ready.sh`

Use this on the newer, simpler GPU worker setup where Docker stays on the root disk and you are **not** using `/mnt/docker-data`.

```bash
cd ~/kv_cache_offloading
./aws/check_ec2_rootdisk_worker_ready.sh
```

What it does:
- checks that `nvidia-smi` works
- checks that Docker GPU support works
- checks that `Docker Root Dir` is `/var/lib/docker`
- checks that `/` has enough free space

Default expectation:
- at least `50G` free on `/`

Optional override:

```bash
MIN_ROOT_FREE_GB=30 ./aws/check_ec2_rootdisk_worker_ready.sh
```

### `./aws/switch_worker_to_rootdisk.sh`

Use this if a worker was previously configured to use `/mnt/docker-data` and you want to convert it to the simpler root-disk Docker layout.

```bash
cd ~/kv_cache_offloading
sudo ./aws/switch_worker_to_rootdisk.sh
newgrp docker
MIN_ROOT_FREE_GB=40 ./aws/check_ec2_rootdisk_worker_ready.sh
```

What it does:
- removes Docker’s `/mnt/docker-data` data-root override
- removes the Docker systemd mount dependency for `/mnt/docker-data`
- removes the `/mnt/docker-data` line from `/etc/fstab`
- reconfigures the NVIDIA Docker runtime
- restarts Docker

To find the head node’s current private IP in the future, run this on the head node:

```bash
hostname -I
```

What this proves:
- the frontend can see registered workers
- the workers can serve requests through the head node
- you have moved beyond the single-box Dynamo test setup

### Worker instance cost comparison

For `us-east-1` on-demand pricing, the rough comparison is:

- `g4dn.xlarge`: about `$0.526/hour`
- `g5.xlarge`: about `$1.006/hour`
- `g5.2xlarge`: about `$1.212/hour`

That means compared with `g4dn.xlarge`:

- `g5.xlarge` is about `$0.48/hour` more per worker
- `g5.2xlarge` is about `$0.686/hour` more per worker

For a 2-worker setup, the rough totals are:

- `2 x g4dn.xlarge`: about `$1.052/hour`
- `2 x g5.xlarge`: about `$2.012/hour`
- `2 x g5.2xlarge`: about `$2.424/hour`

Why the higher cost is worth it here:

- `g4dn.xlarge` uses a T4 GPU and is not a good fit for the published Dynamo worker support matrix
- `g5.xlarge` and `g5.2xlarge` use A10G GPUs, which are Ampere-based and much better aligned with this runtime

### `./run_docker_dynamo.sh start`

Use this to start the stock Dynamo + stock SGLang local test stack:

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh start
```

What it does:
- creates the persistent Dynamo cache and log directories if needed
- starts a Docker container from `nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.2`
- starts `dynamo.frontend` inside the container
- starts `dynamo.sglang` inside the container
- configures the worker to use:
  - model `Qwen/Qwen2.5-0.5B`
  - `--enable-priority-scheduling`
  - `--radix-eviction-policy lru`

In simple terms:
- this gives you a small, local Dynamo test environment
- Dynamo is the coordinator/front door
- SGLang is the actual inference worker behind it

### `./run_docker_dynamo.sh start-priority`

Use this only as an experiment:

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh start-priority
```

What it does:
- switches to the documented pre-release image `nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.1.0-dev.1`
- forces `--radix-eviction-policy priority`
- tries to start the same Dynamo + SGLang stack in “priority eviction” mode

Important note:
- NVIDIA’s release artifacts list `1.1.0-dev.1` as the available pre-release SGLang runtime image
- but the release docs also show it still uses SGLang `v0.5.9`, the same backend version family as the stable runtime
- so this mode is worth testing, but it may still reject `priority`

### `./run_docker_dynamo.sh start-kv`

Use this when you want a more meaningful Dynamo experiment than a plain smoke test:

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh start-kv
```

What it does:
- starts the stable `1.0.2` runtime image
- enables frontend KV-router mode with:
  - `--router-mode kv`
  - `--router-queue-threshold 4.0`
- enables worker cache reporting with:
  - `--enable-cache-report`

Why this mode matters:
- it is a better base for observing cache-aware behavior
- it lets follow-up responses report `usage.prompt_tokens_details.cached_tokens`
- it is the recommended mode for speculative-prefill experiments

### `./run_docker_dynamo.sh test`

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh test
```

What it does:
- sends a simple OpenAI-style chat request to the Dynamo frontend on `localhost:8000`
- this is the basic smoke test that tells you the stack is responding

### `./run_docker_dynamo.sh test-priority`

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh test-priority
```

What it does:
- sends a test request with `nvext.agent_hints.priority`
- this is the simplest way to try the “agent-aware” request metadata path

Note:
- when calling Dynamo through raw `curl`, `nvext` belongs directly in the JSON body
- `extra_body={...}` is the Python OpenAI client convenience form shown in NVIDIA’s docs, not a literal HTTP field

Compatibility note:
- the released SGLang runtime image you tested still rejects `--radix-eviction-policy priority`
- the stable default is therefore `lru`
- if you want to try the documented experimental image, use:
  `./run_docker_dynamo.sh start-priority`
- if NVIDIA ships a future runtime image that really supports `priority`, you can also override manually:
  `DYNAMO_EVICTION_POLICY=priority DYNAMO_IMAGE=<new-image> ./run_docker_dynamo.sh start`

### `./run_docker_dynamo.sh test-specprefill-control`

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh test-specprefill-control
```

What it does:
- runs a two-turn conversation without speculative prefill
- prints a JSON summary of the second turn
- includes:
  - `cached_tokens`
  - second-turn timing
  - the generated follow-up reply

### `./run_docker_dynamo.sh test-specprefill`

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh test-specprefill
```

What it does:
- runs the same two-turn conversation
- enables `nvext.agent_hints.speculative_prefill=true` on the first turn
- prints a JSON summary for the second turn

### `./run_docker_dynamo.sh test-specprefill-ab`

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh test-specprefill-ab
```

What it does:
- runs both the control and speculative-prefill variants back to back
- prints a short side-by-side summary comparing:
  - `cached_tokens`
  - second-turn total time in milliseconds

How to interpret it:
- if the speculative-prefill run shows higher `cached_tokens`, that suggests more warm-prefix reuse
- if it also shows lower second-turn time, that is evidence the hint helped

### `./run_docker_dynamo.sh status`

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh status
```

What it does:
- shows whether the Dynamo container exists
- shows whether the frontend and worker processes are running inside it

### `./run_docker_dynamo.sh logs`

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh logs
```

What it does:
- prints the frontend and worker log tails from inside the container
- use this first if `start`, `test`, or `test-priority` fails

### `./run_docker_dynamo.sh shell`

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh shell
```

What it does:
- opens an interactive shell inside the running Dynamo container
- use this when you want to inspect the runtime manually

### `./run_docker_dynamo.sh stop`

```bash
cd ~/kv_cache_offloading
./run_docker_dynamo.sh stop
```

What it does:
- stops and removes the Dynamo test container

## Recommended Dynamo Test Flow

On the EC2 instance:

```bash
cd ~/kv_cache_offloading
EXPECTED_DOCKER_DEVICE=/dev/nvme2n1 ./aws/check_ec2_ready.sh
./run_docker_dynamo.sh stop
./run_docker_dynamo.sh start-kv
./run_docker_dynamo.sh status
./run_docker_dynamo.sh logs
./run_docker_dynamo.sh test
./run_docker_dynamo.sh test-priority
./run_docker_dynamo.sh test-specprefill-ab
```

What this sequence means:
- `start-kv` brings up the stable Dynamo stack with KV-router mode and cache reporting
- `test` checks the normal request path
- `test-priority` checks the request-metadata path
- `test-specprefill-ab` gives you a concrete A/B check for warm-prefix reuse
- `logs` helps you debug anything that failed
