#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_SCRIPT="${SCRIPT_DIR}/runtime_instrumentation/dynamo_machine_profile.sh"
if [[ -f "${PROFILE_SCRIPT}" ]]; then
  # shellcheck disable=SC1090
  source "${PROFILE_SCRIPT}"
fi

ACTION="${1:-start}"
LOG_MODE="${2:-}"

HOST_HOME_DIR="${HOST_HOME_DIR:-$HOME}"
PERSISTENT_DATA_ROOT="${PERSISTENT_DATA_ROOT:-/mnt/docker-data}"
DYNAMO_CACHE_DIR="${DYNAMO_CACHE_DIR:-${PERSISTENT_DATA_ROOT}/dynamo_cache}"
WORKER_IMAGE="${WORKER_IMAGE:-nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.2}"
WORKER_CONTAINER_NAME="${WORKER_CONTAINER_NAME:-dynamo-sglang-worker}"
DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH:-Qwen/Qwen2.5-1.5B}"
DYNAMO_SERVED_MODEL_NAME="${DYNAMO_SERVED_MODEL_NAME:-${DYNAMO_MODEL_PATH}}"
DYNAMO_DISCOVERY_BACKEND="${DYNAMO_DISCOVERY_BACKEND:-etcd}"
DYNAMO_PAGE_SIZE="${DYNAMO_PAGE_SIZE:-64}"
ETCD_ENDPOINTS="${ETCD_ENDPOINTS:-}"
NATS_SERVER="${NATS_SERVER:-}"
WORKER_EXTRA_ARGS="${WORKER_EXTRA_ARGS:---enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority}"
WORKER_DEV_MODE="${WORKER_DEV_MODE:-0}"
WORKER_DEV_SOURCE_ROOT="${WORKER_DEV_SOURCE_ROOT:-${SCRIPT_DIR}/upstream/dynamo/components/src/dynamo}"
WORKER_DEV_BINDINGS_ROOT="${WORKER_DEV_BINDINGS_ROOT:-${SCRIPT_DIR}/upstream/dynamo/lib/bindings/python/src/dynamo}"
WORKER_SGLANG_DEV_MODE="${WORKER_SGLANG_DEV_MODE:-0}"
WORKER_SGLANG_SOURCE_ROOT="${WORKER_SGLANG_SOURCE_ROOT:-${SCRIPT_DIR}/upstream/sglang/python/sglang}"
HICACHE_STORAGE_HOST_PATH="${HICACHE_STORAGE_HOST_PATH:-${HOST_FILE_STORAGE_PATH:-}}"
HICACHE_STORAGE_CONTAINER_PATH="${HICACHE_STORAGE_CONTAINER_PATH:-${FILE_STORAGE_PATH:-/hicache-storage}}"
SGLANG_TRANSFER_LOG="${SGLANG_TRANSFER_LOG:-}"
SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-}"
SGLANG_TRANSFER_LOG_DIR="${SGLANG_TRANSFER_LOG_DIR:-${SCRIPT_DIR}/experiments/raw/sglang_transfer_logs}"
SGLANG_TRANSFER_LOG_BASENAME="${SGLANG_TRANSFER_LOG_BASENAME:-sglang_transfer_events_$(date +%Y%m%d_%H%M%S)_$$}"
SGLANG_TRANSFER_LOG_PATH="${SGLANG_TRANSFER_LOG_PATH:-}"
SGLANG_TRANSFER_LOG_FULL_TOKENS="${SGLANG_TRANSFER_LOG_FULL_TOKENS:-}"
SGLANG_TRANSFER_LOG_TOKEN_PREVIEW="${SGLANG_TRANSFER_LOG_TOKEN_PREVIEW:-}"
SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS="${SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS:-}"
SGLANG_TRANSFER_LOG_INDEX_PREVIEW="${SGLANG_TRANSFER_LOG_INDEX_PREVIEW:-}"
SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT="${SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT:-32}"
SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC="${SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC:-}"
SGLANG_TRANSFER_LOG_SYNC_TIMING="${SGLANG_TRANSFER_LOG_SYNC_TIMING:-}"
SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS="${SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS:-}"
SGLANG_TRANSFER_LOG_OVERHEAD_TIMING="${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING:-}"
SGLANG_TRANSFER_LOG_VERBOSE="${SGLANG_TRANSFER_LOG_VERBOSE:-}"
SGLANG_HICACHE_MAX_PINNED_RATIO="${SGLANG_HICACHE_MAX_PINNED_RATIO:-}"
WORKER_PROFILE_MODE="${WORKER_PROFILE_MODE:-}"
WORKER_PROFILE_DIR="${WORKER_PROFILE_DIR:-${SCRIPT_DIR}/experiments/raw/lpx_decode_split/profiles}"
WORKER_PROFILE_BASENAME="${WORKER_PROFILE_BASENAME:-dynamo-sglang-worker-$(date +%Y%m%d_%H%M%S)}"
WORKER_PROFILE_TRACE="${WORKER_PROFILE_TRACE:-cuda,nvtx,cublas}"
WORKER_PROFILE_EXTRA_ARGS="${WORKER_PROFILE_EXTRA_ARGS:---sample=none --cuda-event-trace=false}"
WORKER_PROFILE_NSYS_DIR="${WORKER_PROFILE_NSYS_DIR:-}"
WORKER_PROFILE_NCU_DIR="${WORKER_PROFILE_NCU_DIR:-}"
WORKER_PROFILE_NCU_METRICS="${WORKER_PROFILE_NCU_METRICS:-dram__bytes_read.sum,dram__bytes_write.sum}"
WORKER_PROFILE_NCU_KERNEL_NAME="${WORKER_PROFILE_NCU_KERNEL_NAME:-}"
WORKER_PROFILE_NCU_EXTRA_ARGS="${WORKER_PROFILE_NCU_EXTRA_ARGS:---target-processes all --replay-mode kernel --kernel-name-base demangled}"

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  start   Start one SGLang worker on this GPU node
  stop    Stop and remove the worker container
  status  Show the worker container status
  logs    Show recent worker logs
  logs-follow  Follow worker logs in real time
  shell   Open a shell inside the worker container

Required for start:
  ETCD_ENDPOINTS must point at the head node, for example:
    ETCD_ENDPOINTS=http://172.31.x.x:2379

Recommended worker hardware:
  Use G5-class workers (for example g5.xlarge or g5.2xlarge).
  Do not use g4dn/T4 workers for this Dynamo runtime. The published
  Dynamo support matrix is Ampere or newer, and T4 workers fail at runtime.

Environment overrides:
  WORKER_IMAGE          Default: ${WORKER_IMAGE}
  DYNAMO_MODEL_PATH     Default: ${DYNAMO_MODEL_PATH}
  DYNAMO_SERVED_MODEL_NAME Default: ${DYNAMO_SERVED_MODEL_NAME}
  DYNAMO_PAGE_SIZE      Default: ${DYNAMO_PAGE_SIZE}
  DYNAMO_CACHE_DIR      Default: ${DYNAMO_CACHE_DIR}
  WORKER_CONTAINER_NAME Default: ${WORKER_CONTAINER_NAME}
  ETCD_ENDPOINTS        Default: ${ETCD_ENDPOINTS:-<unset>}
  NATS_SERVER           Default: ${NATS_SERVER}
  DYN_TOOL_CALL_PARSER  Default: ${DYN_TOOL_CALL_PARSER:-<unset>}
  SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN Default: ${SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN:-<unset>}
  WORKER_EXTRA_ARGS     Default: ${WORKER_EXTRA_ARGS}
  WORKER_DEV_MODE       Default: ${WORKER_DEV_MODE}
  WORKER_DEV_SOURCE_ROOT Default: ${WORKER_DEV_SOURCE_ROOT}
  WORKER_DEV_BINDINGS_ROOT Default: ${WORKER_DEV_BINDINGS_ROOT}
  WORKER_SGLANG_DEV_MODE Default: ${WORKER_SGLANG_DEV_MODE}
  WORKER_SGLANG_SOURCE_ROOT Default: ${WORKER_SGLANG_SOURCE_ROOT}
  HICACHE_STORAGE_HOST_PATH Default: ${HICACHE_STORAGE_HOST_PATH:-<unset>} (host dir for file-backed HiCache storage)
  HICACHE_STORAGE_CONTAINER_PATH Default: ${HICACHE_STORAGE_CONTAINER_PATH}
  SGLANG_TRANSFER_LOG   Default: ${SGLANG_TRANSFER_LOG:-<unset>} (set to 1 to enable patched transfer logs)
  SGLANG_TRANSFER_LOG_PROFILE Default: ${SGLANG_TRANSFER_LOG_PROFILE:-<unset>} (off, light, timing, full)
  SGLANG_TRANSFER_LOG_DIR Default: ${SGLANG_TRANSFER_LOG_DIR}
  SGLANG_TRANSFER_LOG_BASENAME Default: ${SGLANG_TRANSFER_LOG_BASENAME}
  SGLANG_TRANSFER_LOG_PATH Default: ${SGLANG_TRANSFER_LOG_PATH:-<stderr only>}
  SGLANG_TRANSFER_LOG_FULL_TOKENS Default: ${SGLANG_TRANSFER_LOG_FULL_TOKENS:-<unset>}
  SGLANG_TRANSFER_LOG_TOKEN_PREVIEW Default: ${SGLANG_TRANSFER_LOG_TOKEN_PREVIEW}
  SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS Default: ${SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS}
  SGLANG_TRANSFER_LOG_INDEX_PREVIEW Default: ${SGLANG_TRANSFER_LOG_INDEX_PREVIEW}
  SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT Default: ${SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT}
  SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC Default: ${SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC}
  SGLANG_TRANSFER_LOG_SYNC_TIMING Default: ${SGLANG_TRANSFER_LOG_SYNC_TIMING}
  SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS Default: ${SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS:-<unset>}
  SGLANG_TRANSFER_LOG_OVERHEAD_TIMING Default: ${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING:-<unset>}
  SGLANG_TRANSFER_LOG_VERBOSE Default: ${SGLANG_TRANSFER_LOG_VERBOSE}
  SGLANG_HICACHE_MAX_PINNED_RATIO Default: ${SGLANG_HICACHE_MAX_PINNED_RATIO:-<unset>}
  WORKER_PROFILE_MODE   Default: ${WORKER_PROFILE_MODE:-<unset>} (set to nsys or ncu)
  WORKER_PROFILE_DIR    Default: ${WORKER_PROFILE_DIR}
  WORKER_PROFILE_BASENAME Default: ${WORKER_PROFILE_BASENAME}
  WORKER_PROFILE_TRACE  Default: ${WORKER_PROFILE_TRACE}
  WORKER_PROFILE_EXTRA_ARGS Default: ${WORKER_PROFILE_EXTRA_ARGS}
  WORKER_PROFILE_NSYS_DIR Default: ${WORKER_PROFILE_NSYS_DIR:-<unset>} (host dir containing nsys)
  WORKER_PROFILE_NCU_DIR Default: ${WORKER_PROFILE_NCU_DIR:-<unset>} (host dir containing ncu)
  WORKER_PROFILE_NCU_METRICS Default: ${WORKER_PROFILE_NCU_METRICS}
  WORKER_PROFILE_NCU_KERNEL_NAME Default: ${WORKER_PROFILE_NCU_KERNEL_NAME:-<unset>}
  WORKER_PROFILE_NCU_EXTRA_ARGS Default: ${WORKER_PROFILE_NCU_EXTRA_ARGS}
  DYNAMO_MACHINE_PROFILE Default: ${DYNAMO_MACHINE_PROFILE:-<unset>}
EOF
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker is not installed or not on PATH." >&2
    exit 1
  fi
}

check_gpu_compatibility() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "nvidia-smi is not available. Run: sudo ./aws/bootstrap_ec2_gpu.sh" >&2
    exit 1
  fi

  local gpu_names
  gpu_names="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || true)"

  if [[ -z "${gpu_names}" ]]; then
    echo "Could not detect GPU name with nvidia-smi." >&2
    exit 1
  fi

  if echo "${gpu_names}" | grep -qi '\bT4\b'; then
    cat >&2 <<EOF
Unsupported worker GPU detected:
${gpu_names}

This Dynamo + SGLang runtime expects Ampere-or-newer GPUs.
Use G5-class workers such as g5.xlarge or g5.2xlarge instead of g4dn/T4.
EOF
    exit 1
  fi
}

ensure_dirs() {
  sudo mkdir -p "${DYNAMO_CACHE_DIR}"
  sudo chmod 777 "${DYNAMO_CACHE_DIR}"
  if [[ "${WORKER_PROFILE_MODE}" = "nsys" || "${WORKER_PROFILE_MODE}" = "ncu" ]]; then
    mkdir -p "${WORKER_PROFILE_DIR}"
  fi
  if [[ -n "${HICACHE_STORAGE_HOST_PATH}" ]]; then
    sudo mkdir -p "${HICACHE_STORAGE_HOST_PATH}"
    sudo chmod 777 "${HICACHE_STORAGE_HOST_PATH}" || true
  fi
  if [[ "${SGLANG_TRANSFER_LOG}" = "1" && -n "${SGLANG_TRANSFER_LOG_PATH}" ]]; then
    sudo mkdir -p "${SGLANG_TRANSFER_LOG_DIR}"
    sudo chmod 777 "${SGLANG_TRANSFER_LOG_DIR}" || true
    if [[ "${SGLANG_TRANSFER_LOG_PATH}" == /transfer-logs/* ]]; then
      local transfer_log_name
      transfer_log_name="$(basename "${SGLANG_TRANSFER_LOG_PATH}")"
      ln -sfn "${transfer_log_name}" "${SGLANG_TRANSFER_LOG_DIR}/latest_sglang_transfer_events.jsonl"
      echo "SGLang transfer log: ${SGLANG_TRANSFER_LOG_DIR}/${transfer_log_name}"
      echo "SGLang transfer latest: ${SGLANG_TRANSFER_LOG_DIR}/latest_sglang_transfer_events.jsonl"
    else
      echo "SGLang transfer log path is outside /transfer-logs: ${SGLANG_TRANSFER_LOG_PATH}"
    fi
  elif [[ "${SGLANG_TRANSFER_LOG}" = "1" ]]; then
    echo "SGLang transfer file logging disabled; patched transfer events will go to container stderr only."
  fi
}

initialize_endpoints() {
  if [[ -z "${ETCD_ENDPOINTS}" ]]; then
    echo "ETCD_ENDPOINTS is required. Example: ETCD_ENDPOINTS=http://172.31.x.x:2379" >&2
    exit 1
  fi

  if [[ -z "${NATS_SERVER}" ]]; then
    local etcd_host
    etcd_host="$(echo "${ETCD_ENDPOINTS}" | sed -E 's#^https?://([^:/]+).*$#\1#')"
    if [[ -z "${etcd_host}" || "${etcd_host}" = "${ETCD_ENDPOINTS}" ]]; then
      echo "Could not derive NATS_SERVER from ETCD_ENDPOINTS='${ETCD_ENDPOINTS}'. Set NATS_SERVER explicitly." >&2
      exit 1
    fi
    NATS_SERVER="nats://${etcd_host}:4222"
  fi
}

validate_worker_dev_source() {
  local common_dir="${WORKER_DEV_SOURCE_ROOT}/common"
  local sglang_dir="${WORKER_DEV_SOURCE_ROOT}/sglang"
  local health_check_file="${WORKER_DEV_BINDINGS_ROOT}/health_check.py"
  local runtime_dir="${WORKER_DEV_BINDINGS_ROOT}/runtime"

  if [[ ! -d "${common_dir}" || ! -d "${sglang_dir}" ]]; then
    cat >&2 <<EOF
WORKER_DEV_MODE is enabled, but WORKER_DEV_SOURCE_ROOT does not look valid:
  ${WORKER_DEV_SOURCE_ROOT}

Expected to find:
  ${common_dir}
  ${sglang_dir}
EOF
    exit 1
  fi

  if [[ ! -f "${health_check_file}" || ! -d "${runtime_dir}" ]]; then
    cat >&2 <<EOF
WORKER_DEV_MODE is enabled, but WORKER_DEV_BINDINGS_ROOT does not look valid:
  ${WORKER_DEV_BINDINGS_ROOT}

Expected to find:
  ${health_check_file}
  ${runtime_dir}
EOF
    exit 1
  fi
}

validate_worker_sglang_source() {
  if [[ ! -f "${WORKER_SGLANG_SOURCE_ROOT}/__init__.py" ]]; then
    cat >&2 <<EOF
WORKER_SGLANG_DEV_MODE is enabled, but WORKER_SGLANG_SOURCE_ROOT does not look like a Python sglang package:
  ${WORKER_SGLANG_SOURCE_ROOT}

Expected to find:
  ${WORKER_SGLANG_SOURCE_ROOT}/__init__.py
EOF
    exit 1
  fi
}

container_exists() {
  docker ps -a --format '{{.Names}}' | grep -Fxq "${WORKER_CONTAINER_NAME}"
}

container_running() {
  docker ps --format '{{.Names}}' | grep -Fxq "${WORKER_CONTAINER_NAME}"
}

start_worker() {
  require_docker
  check_gpu_compatibility
  initialize_endpoints
  ensure_dirs

  local -a docker_args
  docker_args=(
    -d
    --gpus all
    --network host
    --name "${WORKER_CONTAINER_NAME}"
    -v "${DYNAMO_CACHE_DIR}:/models/hfcache"
    -e ETCD_ENDPOINTS="${ETCD_ENDPOINTS}"
    -e NATS_SERVER="${NATS_SERVER}"
    -e DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER:-}"
    -e DYN_RUNTIME_JSON_LOGS="${DYN_RUNTIME_JSON_LOGS:-}"
    -e SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN="${SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN:-}"
    -e SGLANG_TRANSFER_LOG="${SGLANG_TRANSFER_LOG:-}"
    -e SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-}"
    -e SGLANG_TRANSFER_LOG_PATH="${SGLANG_TRANSFER_LOG_PATH:-}"
    -e SGLANG_TRANSFER_LOG_FULL_TOKENS="${SGLANG_TRANSFER_LOG_FULL_TOKENS:-}"
    -e SGLANG_TRANSFER_LOG_TOKEN_PREVIEW="${SGLANG_TRANSFER_LOG_TOKEN_PREVIEW:-}"
    -e SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS="${SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS:-}"
    -e SGLANG_TRANSFER_LOG_INDEX_PREVIEW="${SGLANG_TRANSFER_LOG_INDEX_PREVIEW:-}"
    -e SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT="${SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT:-}"
    -e SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC="${SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC:-}"
    -e SGLANG_TRANSFER_LOG_SYNC_TIMING="${SGLANG_TRANSFER_LOG_SYNC_TIMING:-}"
    -e SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS="${SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS:-}"
    -e SGLANG_TRANSFER_LOG_OVERHEAD_TIMING="${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING:-}"
    -e SGLANG_TRANSFER_LOG_VERBOSE="${SGLANG_TRANSFER_LOG_VERBOSE:-}"
    -e SGLANG_HICACHE_MAX_PINNED_RATIO="${SGLANG_HICACHE_MAX_PINNED_RATIO:-}"
    -e HF_TOKEN="${HF_TOKEN:-}"
  )

  local worker_pythonpath_prefix=""
  if [[ "${WORKER_DEV_MODE}" = "1" ]]; then
    validate_worker_dev_source
    # Override only the Python worker sources so compiled wheel extensions remain in use.
    docker_args+=(
      -v "${WORKER_DEV_SOURCE_ROOT}/common:/workspace/components/src/dynamo/common:ro"
      -v "${WORKER_DEV_SOURCE_ROOT}/sglang:/workspace/components/src/dynamo/sglang:ro"
      -v "${WORKER_DEV_BINDINGS_ROOT}/health_check.py:/workspace/lib/bindings/python/src/dynamo/health_check.py:ro"
      -v "${WORKER_DEV_BINDINGS_ROOT}/runtime:/workspace/lib/bindings/python/src/dynamo/runtime:ro"
    )
    worker_pythonpath_prefix="/workspace/components/src:/workspace/lib/bindings/python/src:"
  fi

  if [[ "${WORKER_SGLANG_DEV_MODE}" = "1" ]]; then
    validate_worker_sglang_source
    docker_args+=(
      -v "${WORKER_SGLANG_SOURCE_ROOT}:/workspace/sglang_transfer_overlay/sglang:ro"
    )
    worker_pythonpath_prefix="/workspace/sglang_transfer_overlay:${worker_pythonpath_prefix}"
  fi

  if [[ "${SGLANG_TRANSFER_LOG}" = "1" && "${SGLANG_TRANSFER_LOG_PATH}" == /transfer-logs/* ]]; then
    docker_args+=(
      -v "${SGLANG_TRANSFER_LOG_DIR}:/transfer-logs"
    )
  fi

  if [[ -n "${HICACHE_STORAGE_HOST_PATH}" ]]; then
    docker_args+=(
      -v "${HICACHE_STORAGE_HOST_PATH}:${HICACHE_STORAGE_CONTAINER_PATH}"
    )
  fi

  if [[ -n "${worker_pythonpath_prefix}" ]]; then
    docker_args+=(
      -e PYTHONPATH="${worker_pythonpath_prefix}"
    )
  fi

  if [[ "${WORKER_PROFILE_MODE}" = "nsys" || "${WORKER_PROFILE_MODE}" = "ncu" ]]; then
    docker_args+=(
      -v "${WORKER_PROFILE_DIR}:/profiles"
    )
  fi

  if [[ "${WORKER_PROFILE_MODE}" = "nsys" ]]; then
    if [[ -n "${WORKER_PROFILE_NSYS_DIR}" ]]; then
      if [[ ! -x "${WORKER_PROFILE_NSYS_DIR}/nsys" && ! -x "${WORKER_PROFILE_NSYS_DIR}/target-linux-x64/nsys" ]]; then
        echo "WORKER_PROFILE_NSYS_DIR must contain nsys or target-linux-x64/nsys: ${WORKER_PROFILE_NSYS_DIR}" >&2
        exit 1
      fi
      docker_args+=(
        -v "${WORKER_PROFILE_NSYS_DIR}:/opt/host-nsys-package:ro"
      )
    fi
  fi

  if [[ "${WORKER_PROFILE_MODE}" = "ncu" ]]; then
    if [[ -n "${WORKER_PROFILE_NCU_DIR}" ]]; then
      if [[ ! -x "${WORKER_PROFILE_NCU_DIR}/ncu" && ! -x "${WORKER_PROFILE_NCU_DIR}/target/linux-desktop-glibc_2_11_3-x64/ncu" && ! -x "${WORKER_PROFILE_NCU_DIR}/target-linux-x64/ncu" ]]; then
        echo "WORKER_PROFILE_NCU_DIR must contain ncu or a target/.../ncu binary: ${WORKER_PROFILE_NCU_DIR}" >&2
        exit 1
      fi
      docker_args+=(
        -v "${WORKER_PROFILE_NCU_DIR}:/opt/host-ncu-package:ro"
      )
    fi
  fi

  if container_exists; then
    docker rm -f "${WORKER_CONTAINER_NAME}" >/dev/null 2>&1 || true
  fi

  local worker_launcher="exec"
  if [[ "${WORKER_PROFILE_MODE}" = "nsys" ]]; then
    if [[ -n "${WORKER_PROFILE_NSYS_DIR}" ]]; then
      worker_launcher="mkdir -p /tmp/host-nsys && if [ -x /opt/host-nsys-package/nsys ]; then ln -sf /opt/host-nsys-package/nsys /tmp/host-nsys/nsys; elif [ -x /opt/host-nsys-package/target-linux-x64/nsys ]; then ln -sf /opt/host-nsys-package/target-linux-x64/nsys /tmp/host-nsys/nsys; else echo 'ERROR: mounted host nsys is not executable.' >&2; exit 127; fi; /tmp/host-nsys/nsys --version; exec /tmp/host-nsys/nsys profile --force-overwrite=true --trace='${WORKER_PROFILE_TRACE}' --output='/profiles/${WORKER_PROFILE_BASENAME}' ${WORKER_PROFILE_EXTRA_ARGS}"
    else
      worker_launcher="command -v nsys >/dev/null || { echo 'ERROR: nsys is not available in the worker image.' >&2; exit 127; }; nsys --version; exec nsys profile --force-overwrite=true --trace='${WORKER_PROFILE_TRACE}' --output='/profiles/${WORKER_PROFILE_BASENAME}' ${WORKER_PROFILE_EXTRA_ARGS}"
    fi
  fi
  if [[ "${WORKER_PROFILE_MODE}" = "ncu" ]]; then
    local ncu_kernel_arg=""
    if [[ -n "${WORKER_PROFILE_NCU_KERNEL_NAME}" ]]; then
      ncu_kernel_arg="--kernel-name '${WORKER_PROFILE_NCU_KERNEL_NAME}'"
    fi
    if [[ -n "${WORKER_PROFILE_NCU_DIR}" ]]; then
      worker_launcher="mkdir -p /tmp/host-ncu && if [ -x /opt/host-ncu-package/ncu ]; then ln -sf /opt/host-ncu-package/ncu /tmp/host-ncu/ncu; elif [ -x /opt/host-ncu-package/target/linux-desktop-glibc_2_11_3-x64/ncu ]; then ln -sf /opt/host-ncu-package/target/linux-desktop-glibc_2_11_3-x64/ncu /tmp/host-ncu/ncu; elif [ -x /opt/host-ncu-package/target-linux-x64/ncu ]; then ln -sf /opt/host-ncu-package/target-linux-x64/ncu /tmp/host-ncu/ncu; else echo 'ERROR: mounted host ncu is not executable.' >&2; exit 127; fi; /tmp/host-ncu/ncu --version; exec /tmp/host-ncu/ncu --force-overwrite --export='/profiles/${WORKER_PROFILE_BASENAME}' --metrics '${WORKER_PROFILE_NCU_METRICS}' ${ncu_kernel_arg} ${WORKER_PROFILE_NCU_EXTRA_ARGS}"
    else
      worker_launcher="command -v ncu >/dev/null || { echo 'ERROR: ncu is not available in the worker image. Set WORKER_PROFILE_NCU_DIR to a host Nsight Compute directory.' >&2; exit 127; }; ncu --version; exec ncu --force-overwrite --export='/profiles/${WORKER_PROFILE_BASENAME}' --metrics '${WORKER_PROFILE_NCU_METRICS}' ${ncu_kernel_arg} ${WORKER_PROFILE_NCU_EXTRA_ARGS}"
    fi
  fi

  docker run \
    "${docker_args[@]}" \
    "${WORKER_IMAGE}" \
    bash -lc "${worker_launcher} python3 -m dynamo.sglang \
      --model-path '${DYNAMO_MODEL_PATH}' \
      --served-model-name '${DYNAMO_SERVED_MODEL_NAME}' \
      --discovery-backend '${DYNAMO_DISCOVERY_BACKEND}' \
      --page-size '${DYNAMO_PAGE_SIZE}' \
      ${WORKER_EXTRA_ARGS}" >/dev/null

  sleep 3

  if ! container_running; then
    echo "Worker container did not stay running." >&2
    docker logs "${WORKER_CONTAINER_NAME}" || true
    exit 1
  fi

  cat <<EOF
Dynamo worker is starting.

Container: ${WORKER_CONTAINER_NAME}
Image:     ${WORKER_IMAGE}
Model:     ${DYNAMO_MODEL_PATH}
etcd:      ${ETCD_ENDPOINTS}
page size: ${DYNAMO_PAGE_SIZE}
machine profile: ${DYNAMO_MACHINE_PROFILE:-default}
dev mode:  ${WORKER_DEV_MODE}
sglang dev: ${WORKER_SGLANG_DEV_MODE}
transfer log: ${SGLANG_TRANSFER_LOG:-off}
transfer profile: ${SGLANG_TRANSFER_LOG_PROFILE:-auto}
transfer log path: ${SGLANG_TRANSFER_LOG_PATH:-<stderr only>}
sync timing: ${SGLANG_TRANSFER_LOG_SYNC_TIMING:-auto}
semantic tokens: ${SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS:-auto}
overhead timing: ${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING:-off}
verbose log: ${SGLANG_TRANSFER_LOG_VERBOSE:-auto}
hicache max pinned ratio: ${SGLANG_HICACHE_MAX_PINNED_RATIO:-off}
hicache storage host path: ${HICACHE_STORAGE_HOST_PATH:-off}
hicache storage container path: ${HICACHE_STORAGE_CONTAINER_PATH}
profile:   ${WORKER_PROFILE_MODE:-off}
nsys dir:  ${WORKER_PROFILE_NSYS_DIR:-image default}
ncu dir:   ${WORKER_PROFILE_NCU_DIR:-image default}

Next steps:
  $0 status
  $0 logs
EOF
}

show_status() {
  docker ps -a --filter "name=^${WORKER_CONTAINER_NAME}$"
}

show_logs() {
  if [[ "${LOG_MODE}" = "-f" || "${LOG_MODE}" = "--follow" ]]; then
    docker logs -f --tail 200 "${WORKER_CONTAINER_NAME}" || true
  else
    docker logs --tail 200 "${WORKER_CONTAINER_NAME}" || true
  fi
}

follow_logs() {
  docker logs -f --tail 200 "${WORKER_CONTAINER_NAME}" || true
}

open_shell() {
  docker exec -it "${WORKER_CONTAINER_NAME}" bash
}

stop_worker() {
  docker rm -f "${WORKER_CONTAINER_NAME}" >/dev/null 2>&1 || true
}

case "${ACTION}" in
  start) start_worker ;;
  stop) stop_worker ;;
  status) show_status ;;
  logs) show_logs ;;
  logs-follow) follow_logs ;;
  shell) open_shell ;;
  help|-h|--help) usage ;;
  *)
    echo "Unknown command: ${ACTION}" >&2
    usage
    exit 1
    ;;
esac
