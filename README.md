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

## Common EC2 Command Flow

On the EC2 instance:

```bash
cd ~/kv_cache_offloading
EXPECTED_DOCKER_DEVICE=/dev/nvme1n1 ./aws/check_ec2_ready.sh
./run_docker_sglang.sh
```
