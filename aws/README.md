# AWS Runbook

This is the operational guide for bringing up `kv_cache_offloading` on EC2 instances and running it without repeating the earlier debugging process.

## Assumptions

- OS: Amazon Linux 2023
- either:
  - a GPU worker instance with NVIDIA hardware, or
  - a simpler non-GPU head/frontend instance
- Project is uploaded to `~/kv_cache_offloading`
- Persistent Docker data should live on a separate attached EBS volume
- SGLang model cache should also live on that persistent EBS volume

Recommended worker GPU family for Dynamo:
- use `g5.xlarge` or `g5.2xlarge`
- do not use `g4dn.xlarge` for Dynamo workers in this setup

Why:
- the published NVIDIA Dynamo support matrix is Ampere or newer
- `g4dn.xlarge` uses a T4 GPU, which is Turing-based
- that mismatch leads to worker runtime failures such as:
  - `no kernel image is available for execution on the device`

## 1. Upload the Repo From Local

From your Mac:

```bash
/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/aws/upload.sh
```

## 2. First-Time EC2 Setup

### GPU worker instance

SSH into the instance, then run:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh
```

This installs:

- Docker
- NVIDIA driver
- NVIDIA container toolkit

If the script installs the NVIDIA driver for the first time, reboot:

```bash
sudo reboot
```

For GPU worker nodes in the current setup, you are still expected to use:
- `./aws/prepare_docker_ebs.sh`
- `./aws/recover_docker_mount.sh`
- `./aws/check_ec2_ready.sh`

Those are still active parts of the worker-node flow because the workers are the machines that benefit from persistent Docker/model cache storage.

If you are using the newer, simpler worker flow with a large root disk and no separate Docker/cache EBS volume, use:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh rootdisk
newgrp docker
./aws/check_ec2_rootdisk_worker_ready.sh
```

This verifies:
- `nvidia-smi`
- Docker GPU support
- `Docker Root Dir` is `/var/lib/docker`
- root-disk free space is healthy

If you launched the worker with a `50 GiB` root disk, it is normal for the default root-disk check to be slightly strict. In that case you can run:

```bash
MIN_ROOT_FREE_GB=40 ./aws/check_ec2_rootdisk_worker_ready.sh
```

If you already have a worker that was previously configured for `/mnt/docker-data` and you want to convert it to the simpler root-disk layout, use:

```bash
cd ~/kv_cache_offloading
sudo ./aws/switch_worker_to_rootdisk.sh
newgrp docker
MIN_ROOT_FREE_GB=40 ./aws/check_ec2_rootdisk_worker_ready.sh
```

That script:
- removes the Docker `data-root` override
- removes the Docker mount dependency on `/mnt/docker-data`
- removes the `/mnt/docker-data` entry from `/etc/fstab`
- reconfigures the NVIDIA Docker runtime
- restarts Docker

Recommended worker instance types:
- `g5.xlarge` for the smallest supported worker
- `g5.2xlarge` if you want more memory headroom

### Simpler head/frontend instance

Use this on a fresh **non-GPU** head/frontend node:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_docker.sh
```

This installs:

- Docker

and adds `ec2-user` to the Docker group.

If Docker access still fails in the current shell after running it:

```bash
newgrp docker
```

or log out and SSH back in.

### If you enlarge the root EBS volume later

If you increase the head node’s root EBS volume size in AWS and want Linux to use the extra space, run:

```bash
cd ~/kv_cache_offloading
sudo ./aws/expand_root_fs.sh
```

This is the reusable version of the manual steps:

```bash
lsblk
df -h /
sudo growpart /dev/nvme0n1 1
sudo xfs_growfs -d /
df -h /
```

This is especially useful for:
- simpler head/frontend nodes
- any fresh EC2 instance where the root disk is too small for Docker images

## 3. Attach and Prepare a Persistent EBS Volume for Docker

In AWS:

1. Create a new EBS volume in the same availability zone as the EC2 instance.
2. Attach it to the instance.

On the instance, identify the new device:

```bash
lsblk -f
```

Then prepare it for Docker. If the new volume appears as `/dev/nvme1n1`, run:

```bash
cd ~/kv_cache_offloading
sudo DOCKER_DATA_DEVICE=/dev/nvme1n1 ./aws/prepare_docker_ebs.sh
```

Verify:

```bash
df -h /mnt/docker-data
docker info | grep "Docker Root Dir"
```

Expected:

- `/mnt/docker-data` backed by `/dev/nvme1n1`
- `Docker Root Dir: /mnt/docker-data`

By default, `run_docker_sglang.sh` now uses:

```bash
SGLANG_CACHE_DIR=/mnt/docker-data/sglang_cache
VLLM_CACHE_DIR=/mnt/docker-data/vllm_cache
```

This keeps model downloads and cache files off the small root disk.

## 4. Standard Readiness Check Before Running

On the instance:

```bash
cd ~/kv_cache_offloading
EXPECTED_DOCKER_DEVICE=/dev/nvme1n1 ./aws/check_ec2_ready.sh
```

If everything is healthy, you should see all `PASS`.

## 5. Recovery After a Stop/Start or Reboot

If the instance was restarted and Docker storage is not mounted correctly:

```bash
cd ~/kv_cache_offloading
sudo DOCKER_DATA_DEVICE=/dev/nvme1n1 ./aws/recover_docker_mount.sh
EXPECTED_DOCKER_DEVICE=/dev/nvme1n1 ./aws/check_ec2_ready.sh
```

If the readiness check still fails, inspect:

```bash
df -h /mnt/docker-data
docker info | grep "Docker Root Dir"
lsblk -f
```

## 6. Launch the Workload

On the instance:

```bash
cd ~/kv_cache_offloading
./run_docker_sglang.sh
```

## 7. If You Change Scripts Locally

Re-upload from your Mac:

```bash
/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/aws/upload.sh
```

Then rerun on EC2:

```bash
cd ~/kv_cache_offloading
EXPECTED_DOCKER_DEVICE=/dev/nvme1n1 ./aws/check_ec2_ready.sh
./run_docker_sglang.sh
```

## 8. Useful Quick Checks

GPU on host:

```bash
nvidia-smi
```

Docker GPU path:

```bash
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

Docker storage:

```bash
df -h /mnt/docker-data
docker info | grep "Docker Root Dir"
```

Disk/device layout:

```bash
lsblk -f
```

## 9. Important Notes

- Do not rely on EC2 instance store for Docker data if you plan to stop/start the instance.
- Use a persistent EBS volume for `/mnt/docker-data`.
- The attached EBS device name may not always be `/dev/nvme1n1`; always confirm with `lsblk -f`.
- If the Docker disk device changes, pass the correct value through `DOCKER_DATA_DEVICE` and `EXPECTED_DOCKER_DEVICE`.

## 10. Minimal Command Flow

### Fresh instance

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh
sudo reboot
cd ~/kv_cache_offloading
lsblk -f
sudo DOCKER_DATA_DEVICE=/dev/nvme1n1 ./aws/prepare_docker_ebs.sh
EXPECTED_DOCKER_DEVICE=/dev/nvme1n1 ./aws/check_ec2_ready.sh
./run_docker_sglang.sh
```

### Fresh head/frontend instance

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_docker.sh
newgrp docker
./run_dynamo_head.sh start
```

### Fresh head/frontend instance with a bigger root disk

If you first increase the root EBS volume size in AWS:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_docker.sh
sudo ./aws/expand_root_fs.sh
newgrp docker
./run_dynamo_head.sh start
```

### Existing instance after restart

```bash
cd ~/kv_cache_offloading
sudo DOCKER_DATA_DEVICE=/dev/nvme1n1 ./aws/recover_docker_mount.sh
EXPECTED_DOCKER_DEVICE=/dev/nvme1n1 ./aws/check_ec2_ready.sh
./run_docker_sglang.sh
```
