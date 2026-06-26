#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

mkdir -p "$HOME/dockerx"
mkdir -p "$HOME/dlrm"

CUSTOM_MOUNT_ARGS=()
if [[ -n "${CUSTOM_DLRM_BENCH_SH:-}" ]]; then
  if [[ ! -f "${CUSTOM_DLRM_BENCH_SH}" ]]; then
    echo "CUSTOM_DLRM_BENCH_SH does not exist: ${CUSTOM_DLRM_BENCH_SH}" >&2
    exit 1
  fi
  CUSTOM_MOUNT_ARGS=(-v "${CUSTOM_DLRM_BENCH_SH}:/tmp/custom_dlrm_s_benchmark.sh:ro")
fi

docker container rm pytorch-vllm -f || true

docker run -it --rm \
  --name pytorch-vllm \
  --network=host \
  --ipc=host \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add video \
  --group-add render \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  --shm-size=64G \
  -v "$HOME/dockerx:/dockerx" \
  -v "$HOME/dlrm:/workspace/dlrm" \
  -v "/data/ojaiyeob:/workspace/data" \
  "${CUSTOM_MOUNT_ARGS[@]}" \
  -w /workspace/dlrm \
  rocm/pytorch:latest \
  bash -lc '
    set -euo pipefail

    if ! command -v git >/dev/null 2>&1; then
      apt-get update
      apt-get install -y --no-install-recommends git ca-certificates
    fi

    if [ ! -d FAMBench/.git ]; then
      git clone --recurse-submodules https://github.com/facebookresearch/FAMBench.git FAMBench
    else
      cd FAMBench
      git submodule update --init --recursive
      cd ..
    fi

    cd FAMBench/benchmarks/dlrm/ootb/bench
    if [ -f /tmp/custom_dlrm_s_benchmark.sh ]; then
      cp /tmp/custom_dlrm_s_benchmark.sh ./dlrm_s_benchmark.sh
      chmod +x ./dlrm_s_benchmark.sh
    fi
    pwd
    ls -l ./dlrm_s_benchmark.sh
  '
