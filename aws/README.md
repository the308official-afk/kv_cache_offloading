# AWS Runbook

This is the operational guide for bringing up `kv_cache_offloading` on a GPU EC2 instance and running it without repeating the earlier debugging process.

## Assumptions

- OS: Amazon Linux 2023
- GPU instance with NVIDIA hardware
- Project is uploaded to `~/kv_cache_offloading`
- Persistent Docker data should live on a separate attached EBS volume

## 1. Upload the Repo From Local

From your Mac:

```bash
/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/aws/upload.sh
```

## 2. First-Time EC2 Setup

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

### Existing instance after restart

```bash
cd ~/kv_cache_offloading
sudo DOCKER_DATA_DEVICE=/dev/nvme1n1 ./aws/recover_docker_mount.sh
EXPECTED_DOCKER_DEVICE=/dev/nvme1n1 ./aws/check_ec2_ready.sh
./run_docker_sglang.sh
```
