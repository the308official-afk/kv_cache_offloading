# AWS Setup Notes

AWS-specific setup for running `kv_cache_offloading` on GPU EC2 machines.

---------------------------------------------------------------------------------------------------------------------------------------

## 1. Instance Requirements

Recommended baseline:

- OS: Amazon Linux 2023
- GPU: Ampere-or-newer NVIDIA GPU
- Root disk: 200-300 GB if using root-disk Docker storage
- Python: 3.11
- Docker with NVIDIA Container Toolkit

For the smallest supported worker class, use a G5-family instance such as
`g5.xlarge` or `g5.2xlarge`. Avoid T4/G4dn workers for this Dynamo/SGLang
runtime path.

---------------------------------------------------------------------------------------------------------------------------------------

## 2. Upload Repo

From the local machine:

```bash
./aws/upload.sh
```

`./aws/upload.sh` intentionally excludes `upstream/dynamo/`. Build and
instrument Dynamo from a local checkout on the EC2 machine instead of uploading
your local `upstream/dynamo` tree.

Then SSH to the EC2 machine and work from:

```bash
cd ~/kv_cache_offloading
```

---------------------------------------------------------------------------------------------------------------------------------------

## 3. Bootstrap GPU, Docker, And Python

For the simple root-disk flow:

```bash
sudo dnf install -y python3.11 python3.11-pip git

cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh rootdisk
newgrp docker
./aws/check_ec2_rootdisk_worker_ready.sh
```

If the NVIDIA driver was installed for the first time, reboot before running GPU
containers:

```bash
sudo reboot
```

After reconnecting:

```bash
cd ~/kv_cache_offloading
newgrp docker
./aws/check_ec2_rootdisk_worker_ready.sh
```

---------------------------------------------------------------------------------------------------------------------------------------

## 4. Storage Notes

The instrumented Dynamo build and model cache can consume a lot of disk.

Useful checks:

```bash
df -h /
docker system df
```

If root disk usage is too high, prune unused Docker data carefully:

```bash
docker container prune -f
docker image prune -f
docker builder prune -f --filter until=24h
```

For a full cleanup when you are willing to rebuild/pull images again:

```bash
docker system prune -af
docker builder prune -af
```

---------------------------------------------------------------------------------------------------------------------------------------

## 5. Architecture Note

G5 instances are `x86_64` and build `linux/amd64` Docker images.

If moving to an ARM64 machine, rebuild Dynamo images natively there instead of
copying G5-built images.

Check host architecture:

```bash
uname -m
```

Check image architecture after a build:

```bash
docker image inspect local/dynamo-frontend:runtime-json-logs --format '{{.Architecture}}'
docker image inspect local/dynamo-sglang:runtime-json-logs --format '{{.Architecture}}'
```

---------------------------------------------------------------------------------------------------------------------------------------

## 6. Continue With Main Workflow

After AWS setup is complete, use the root README starting from Machine Setup's
Python dependency install, then run preflight, smoke test, instrumented build,
runtime start, AgentBench, and verification.
