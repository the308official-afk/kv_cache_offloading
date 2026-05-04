#!/bin/bash

set -euo pipefail

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
WORKER_EXTRA_ARGS="${WORKER_EXTRA_ARGS:---enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru}"

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
  WORKER_EXTRA_ARGS     Default: ${WORKER_EXTRA_ARGS}
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

  if container_exists; then
    docker rm -f "${WORKER_CONTAINER_NAME}" >/dev/null 2>&1 || true
  fi

  docker run -d \
    --gpus all \
    --network host \
    --name "${WORKER_CONTAINER_NAME}" \
    -v "${DYNAMO_CACHE_DIR}:/models/hfcache" \
    -e ETCD_ENDPOINTS="${ETCD_ENDPOINTS}" \
    -e NATS_SERVER="${NATS_SERVER}" \
    -e HF_TOKEN="${HF_TOKEN:-}" \
    "${WORKER_IMAGE}" \
    bash -lc "python3 -m dynamo.sglang \
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
