#!/bin/bash

set -euo pipefail

EXPECTED_DOCKER_ROOT="${EXPECTED_DOCKER_ROOT:-/var/lib/docker}"
ROOT_MOUNT="${ROOT_MOUNT:-/}"
MIN_ROOT_FREE_GB="${MIN_ROOT_FREE_GB:-50}"

pass() {
  echo "[PASS] $1"
}

fail() {
  echo "[FAIL] $1"
}

check_gpu() {
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    pass "NVIDIA driver is installed and GPU is visible"
  else
    fail "nvidia-smi failed; GPU driver may be missing or broken"
  fi
}

check_docker_runtime() {
  local runtimes
  runtimes="$(docker info 2>/dev/null | grep 'Runtimes:' || true)"
  if echo "$runtimes" | grep -q 'nvidia'; then
    pass "Docker has the NVIDIA runtime"
  else
    if docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1; then
      pass "Docker GPU support works even though a named nvidia runtime is not listed"
    else
      fail "Docker does not list the NVIDIA runtime and GPU test container failed"
    fi
  fi
}

check_docker_root() {
  local docker_root
  docker_root="$(docker info 2>/dev/null | awk -F': ' '/Docker Root Dir/ {print $2}' || true)"
  if [ "$docker_root" = "$EXPECTED_DOCKER_ROOT" ]; then
    pass "Docker Root Dir is $EXPECTED_DOCKER_ROOT"
  else
    fail "Docker Root Dir is '$docker_root' but expected '$EXPECTED_DOCKER_ROOT'"
  fi
}

check_root_free_space() {
  local avail_kb avail_gb
  avail_kb="$(df -Pk "$ROOT_MOUNT" | awk 'NR==2 {print $4}')"
  avail_gb=$((avail_kb / 1024 / 1024))
  if [ "$avail_gb" -ge "$MIN_ROOT_FREE_GB" ]; then
    pass "$ROOT_MOUNT has ${avail_gb}G free"
  else
    fail "$ROOT_MOUNT has only ${avail_gb}G free; expected at least ${MIN_ROOT_FREE_GB}G"
  fi
}

check_gpu_container() {
  if docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1; then
    pass "GPU works inside Docker"
  else
    fail "GPU test container failed"
  fi
}

main() {
  check_gpu
  check_docker_runtime
  check_docker_root
  check_root_free_space
  check_gpu_container
}

main "$@"
