# EC2 Setup Guide

This document captures the setup steps that were required to run `kv_cache_offloading` on a fresh GPU EC2 instance without repeating the same debugging process.

## Recommended Instance Shape

- Use a GPU-backed EC2 instance.
- Confirm the host exposes an NVIDIA GPU:

```bash
lspci | grep -i nvidia
```

If this returns no NVIDIA device, the instance type is not suitable for the current Docker workflow.

## Recommended Storage Layout

- Root EBS volume: at least `100 GiB` is safer than the original `16 GiB`.
- Extra data disk: use a separate **EBS volume** for Docker data and mount it at `/mnt/docker-data`.
- Docker should use `/mnt/docker-data` as its data root.

Important:

- Do **not** rely on EC2 instance store for Docker data if you plan to stop/start the instance.
- Instance store can disappear across stop/start.
- Use a separately attached EBS volume for persistent Docker/model/cache storage.

## 1. Resize the Root Volume If Needed

After increasing the EBS size in AWS, extend the partition and filesystem on the instance.

Check layout:

```bash
lsblk
df -hT
```

For Nitro instances like ours with `xfs` on `/dev/nvme0n1p1`:

```bash
sudo dnf install -y cloud-utils-growpart
sudo growpart /dev/nvme0n1 1
sudo xfs_growfs -d /
```

Verify:

```bash
lsblk
df -hT
```

## 2. Install Docker

```bash
sudo dnf install -y docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ec2-user
```

Log out and back in, or run:

```bash
newgrp docker
```

Verify:

```bash
docker --version
docker ps
```

## 3. Install NVIDIA Drivers

On Amazon Linux 2023:

```bash
sudo dnf install -y nvidia-release
sudo dnf install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r)
sudo dnf install -y nvidia-driver-cuda
sudo reboot
```

After reboot:

```bash
nvidia-smi
```

Expected result: the GPU appears in the `nvidia-smi` table.

## 4. Install NVIDIA Container Toolkit

```bash
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

sudo dnf install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Verify:

```bash
docker info | grep -i runtime
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

Expected result:

- Docker lists `nvidia` as a runtime.
- `nvidia-smi` works inside the container.

## 5. Prepare a Persistent EBS Volume for Docker

In AWS:

1. Create a new EBS volume in the same availability zone as the EC2 instance.
2. Attach it to the instance.
3. SSH into the instance and identify the new block device:

Check available disks:

```bash
lsblk -f
sudo blkid
```

On Nitro instances, the attached EBS volume often appears as something like `/dev/nvme1n1`.

For the first-time setup, use the helper script:

```bash
sudo DOCKER_DATA_DEVICE=/dev/nvme1n1 ./aws/prepare_docker_ebs.sh
```

What it does:

- formats the attached volume as `xfs` if needed
- mounts it at `/mnt/docker-data`
- writes the `/etc/fstab` entry using the volume UUID
- configures Docker to use `/mnt/docker-data`
- makes Docker wait for that mount before startup

If you prefer the manual path, the steps are below.

If the attached EBS volume already has an `xfs` filesystem, mount it directly. Example:

- device: `/dev/nvme1n1`
- mount point: `/mnt/docker-data`

Mount it:

```bash
sudo mkdir -p /mnt/docker-data
sudo mount /dev/nvme1n1 /mnt/docker-data
```

Make it persistent across reboot using the disk UUID:

```bash
echo 'UUID=2cfd7620-2a40-4a39-bbfd-0340e28c1a5d /mnt/docker-data xfs defaults 0 2' | sudo tee -a /etc/fstab
```

Verify:

```bash
df -h /mnt/docker-data
```

Important:

- If `df -h /mnt/docker-data` shows the root volume like `/dev/nvme0n1p1`, then the mount did not take effect.
- Docker will still fill the root disk unless `/mnt/docker-data` is truly mounted to the large volume.

## 6. Configure Docker to Use the Persistent Docker Disk

```bash
sudo systemctl stop docker
echo '{"data-root": "/mnt/docker-data"}' | sudo tee /etc/docker/daemon.json
sudo mkdir -p /etc/systemd/system/docker.service.d
cat <<'EOF' | sudo tee /etc/systemd/system/docker.service.d/mount.conf
[Unit]
RequiresMountsFor=/mnt/docker-data
EOF
sudo systemctl daemon-reload
sudo systemctl start docker
```

Verify:

```bash
docker info | grep "Docker Root Dir"
df -h /mnt/docker-data
```

Expected result:

- `Docker Root Dir: /mnt/docker-data`
- `/mnt/docker-data` is backed by the large disk, not the root filesystem

This `RequiresMountsFor` setting is important. Without it, Docker can start after reboot before the EBS volume is mounted, and then it will write into a plain `/mnt/docker-data` directory on the root filesystem.

## 7. If Docker Data Was Written Before the Mount

If Docker already wrote data into `/mnt/docker-data` before the persistent volume was mounted, that directory is just living on the root disk. Move it aside before mounting:

```bash
sudo systemctl stop docker
sudo mv /mnt/docker-data /mnt/docker-data.rootdisk
sudo mkdir -p /mnt/docker-data
sudo mount /dev/nvme1n1 /mnt/docker-data
sudo rsync -aHAX /mnt/docker-data.rootdisk/ /mnt/docker-data/
sudo systemctl start docker
```

Only remove the old copy after verifying Docker is healthy:

```bash
docker info | grep "Docker Root Dir"
df -h /mnt/docker-data
sudo rm -rf /mnt/docker-data.rootdisk
```

## 8. Project-Specific Paths

`run_docker_sglang.sh` now supports these host-side path overrides at the top of the script:

```bash
HOST_HOME_DIR="${HOST_HOME_DIR:-$HOME}"
SGLANG_ROOT="${SGLANG_ROOT:-${HOST_HOME_DIR}/sglang}"
PERSISTENT_DATA_ROOT="${PERSISTENT_DATA_ROOT:-/mnt/docker-data}"
SGLANG_CACHE_DIR="${SGLANG_CACHE_DIR:-${PERSISTENT_DATA_ROOT}/sglang_cache}"
STUDY_ROOT="${STUDY_ROOT:-${HOST_HOME_DIR}/GH200-studies}"
VLLM_ROOT="${VLLM_ROOT:-${HOST_HOME_DIR}/vllm}"
VLLM_CLIENT_DIR="${VLLM_CLIENT_DIR:-${VLLM_ROOT}/vllm_client}"
VLLM_CACHE_DIR="${VLLM_CACHE_DIR:-${PERSISTENT_DATA_ROOT}/vllm_cache}"
HICACHE_HOST_DIR="${HICACHE_HOST_DIR:-/hicache_disk}"
```

Adjust those values on a new instance if your host directory layout differs.

## 9. Preflight Checklist

Run these before starting a long experiment:

```bash
lsblk
df -h
df -h /mnt/docker-data
nvidia-smi
docker info | grep -E "Docker Root Dir|Runtime"
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

There is also a helper script for this:

```bash
./aws/check_ec2_ready.sh
```

If Docker storage is broken after a restart, recover first with:

```bash
sudo DOCKER_DATA_DEVICE=/dev/nvme1n1 ./aws/recover_docker_mount.sh
```

## 10. Running the Project

Upload the repo:

```bash
./aws/upload.sh
```

Then on the EC2 instance:

```bash
cd ~/kv_cache_offloading
./run_docker_sglang.sh
```

## Common Failure Modes

### `docker: command not found`

Docker is not installed or not on the current shell's `PATH`.

### `cannot execute: required file not found` or `$'\r': command not found`

The shell script likely has Windows CRLF line endings. Convert to Unix line endings before running.

### `could not select device driver "" with capabilities: [[gpu]]`

The instance has no GPU runtime configured for Docker. Install the NVIDIA driver and NVIDIA container toolkit.

### `no space left on device`

Most often one of these:

- root volume is too small
- `/mnt/docker-data` is not really mounted to the persistent EBS volume
- Docker data root is still pointing at the root filesystem

### `no space left on device` after reboot even though Docker Root Dir is `/mnt/docker-data`

This usually means Docker is configured to use `/mnt/docker-data`, but the persistent EBS volume was not mounted there after reboot.

Check:

```bash
df -h /mnt/docker-data
docker info | grep "Docker Root Dir"
```

If `df -h /mnt/docker-data` shows the root filesystem instead of `nvme1n1`, recover with:

```bash
sudo DOCKER_DATA_DEVICE=/dev/nvme1n1 /path/to/kv_cache_offloading/aws/recover_docker_mount.sh
```

### `nvme1n1` shows `data` with no filesystem after stop/start

That strongly suggests you were using EC2 instance store rather than a persistent EBS volume. Instance store does not survive stop/start. Recreate the Docker data volume as a real EBS volume and attach it again.
