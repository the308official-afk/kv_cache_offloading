#!/bin/bash

set -euo pipefail

ACTION="${1:-start}"
LOG_MODE="${2:-}"

HOST_HOME_DIR="${HOST_HOME_DIR:-$HOME}"
HEAD_STATE_DIR="${HEAD_STATE_DIR:-${HOST_HOME_DIR}/kv_cache_offloading/dynamo_head_state}"
HEAD_LOG_DIR="${HEAD_LOG_DIR:-${HEAD_STATE_DIR}/logs}"
ETCD_DATA_DIR="${ETCD_DATA_DIR:-${HEAD_STATE_DIR}/etcd-data}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.2}"
ETCD_IMAGE="${ETCD_IMAGE:-quay.io/coreos/etcd:v3.5.14}"
NATS_IMAGE="${NATS_IMAGE:-nats:2.10-alpine}"
FRONTEND_CONTAINER_NAME="${FRONTEND_CONTAINER_NAME:-dynamo-frontend}"
ETCD_CONTAINER_NAME="${ETCD_CONTAINER_NAME:-dynamo-etcd}"
NATS_CONTAINER_NAME="${NATS_CONTAINER_NAME:-dynamo-nats}"
DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT:-8000}"
DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH:-Qwen/Qwen2.5-1.5B}"
DYNAMO_DISCOVERY_BACKEND="${DYNAMO_DISCOVERY_BACKEND:-etcd}"
DYNAMO_ROUTER_MODE="${DYNAMO_ROUTER_MODE:-kv}"
DYNAMO_KV_CACHE_BLOCK_SIZE="${DYNAMO_KV_CACHE_BLOCK_SIZE:-64}"
HEAD_PRIVATE_IP="${HEAD_PRIVATE_IP:-}"
ETCD_ENDPOINTS="${ETCD_ENDPOINTS:-}"
NATS_SERVER="${NATS_SERVER:-}"
ROUTER_EXTRA_ARGS="${ROUTER_EXTRA_ARGS:---no-router-kv-events --router-queue-threshold 4.0}"

detect_head_private_ip() {
  if [[ -n "${HEAD_PRIVATE_IP}" ]]; then
    return
  fi

  HEAD_PRIVATE_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  if [[ -z "${HEAD_PRIVATE_IP}" ]]; then
    echo "Could not determine head private IP. Set HEAD_PRIVATE_IP explicitly." >&2
    exit 1
  fi
}

initialize_endpoints() {
  detect_head_private_ip
  ETCD_ENDPOINTS="${ETCD_ENDPOINTS:-http://${HEAD_PRIVATE_IP}:2379}"
  NATS_SERVER="${NATS_SERVER:-nats://${HEAD_PRIVATE_IP}:4222}"
}

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  start   Start etcd, nats-server, and dynamo.frontend on the head node
  stop    Stop and remove the head-node containers
  status  Show container status
  logs    Show recent logs for etcd, nats, and the frontend
  test    Send a simple chat completion request to the frontend
  test-priority  Send a request with nvext.agent_hints.priority

Environment overrides:
  FRONTEND_IMAGE         Default: ${FRONTEND_IMAGE}
  DYNAMO_MODEL_PATH      Default: ${DYNAMO_MODEL_PATH}
  DYNAMO_FRONTEND_PORT   Default: ${DYNAMO_FRONTEND_PORT}
  DYNAMO_KV_CACHE_BLOCK_SIZE Default: ${DYNAMO_KV_CACHE_BLOCK_SIZE}
  HEAD_PRIVATE_IP        Default: auto-detected from hostname -I
  ETCD_ENDPOINTS         Default: auto-derived as http://<head-private-ip>:2379
  NATS_SERVER            Default: auto-derived as nats://<head-private-ip>:4222
  ROUTER_EXTRA_ARGS      Default: ${ROUTER_EXTRA_ARGS}

Notes:
  - This head-node flow is intentionally simple and avoids /mnt/docker-data.
  - It runs KV-router mode with --no-router-kv-events by default, so workers
    do not need KV event publishing just to get a first multi-node experiment.
EOF
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker is not installed or not on PATH." >&2
    echo "Run: sudo ./aws/bootstrap_ec2_docker.sh" >&2
    exit 1
  fi
}

ensure_dirs() {
  mkdir -p "${HEAD_LOG_DIR}" "${ETCD_DATA_DIR}"
}

container_exists() {
  docker ps -a --format '{{.Names}}' | grep -Fxq "$1"
}

container_running() {
  docker ps --format '{{.Names}}' | grep -Fxq "$1"
}

start_etcd() {
  if container_exists "${ETCD_CONTAINER_NAME}"; then
    docker rm -f "${ETCD_CONTAINER_NAME}" >/dev/null 2>&1 || true
  fi

  docker run -d \
    --name "${ETCD_CONTAINER_NAME}" \
    --network host \
    -v "${ETCD_DATA_DIR}:/etcd-data" \
    "${ETCD_IMAGE}" \
    /usr/local/bin/etcd \
    --name dynamo-etcd \
    --data-dir /etcd-data \
    --listen-client-urls http://0.0.0.0:2379 \
    --advertise-client-urls "${ETCD_ENDPOINTS}" >/dev/null
}

start_nats() {
  if container_exists "${NATS_CONTAINER_NAME}"; then
    docker rm -f "${NATS_CONTAINER_NAME}" >/dev/null 2>&1 || true
  fi

  docker run -d \
    --name "${NATS_CONTAINER_NAME}" \
    --network host \
    "${NATS_IMAGE}" \
    -js >/dev/null
}

start_frontend() {
  if container_exists "${FRONTEND_CONTAINER_NAME}"; then
    docker rm -f "${FRONTEND_CONTAINER_NAME}" >/dev/null 2>&1 || true
  fi

  docker run -d \
    --name "${FRONTEND_CONTAINER_NAME}" \
    --network host \
    -e ETCD_ENDPOINTS="${ETCD_ENDPOINTS}" \
    -e NATS_SERVER="${NATS_SERVER}" \
    -e DYN_RUNTIME_JSON_LOGS="${DYN_RUNTIME_JSON_LOGS:-}" \
    -e HF_TOKEN="${HF_TOKEN:-}" \
    "${FRONTEND_IMAGE}" \
    bash -lc "python3 -m dynamo.frontend \
      --http-port '${DYNAMO_FRONTEND_PORT}' \
      --router-mode '${DYNAMO_ROUTER_MODE}' \
      --kv-cache-block-size '${DYNAMO_KV_CACHE_BLOCK_SIZE}' \
      ${ROUTER_EXTRA_ARGS}" >/dev/null
}

wait_for_container() {
  local name="$1"
  local retries=30
  local delay=1
  for ((i=1; i<=retries; i++)); do
    if container_running "${name}"; then
      return 0
    fi
    sleep "${delay}"
  done
  echo "Container ${name} did not stay running." >&2
  exit 1
}

wait_for_frontend() {
  local retries=60
  local delay=2
  for ((i=1; i<=retries; i++)); do
    if curl -fsS "http://127.0.0.1:${DYNAMO_FRONTEND_PORT}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay}"
  done
  echo "Frontend did not become healthy on port ${DYNAMO_FRONTEND_PORT}." >&2
  exit 1
}

show_status() {
  docker ps -a --filter "name=^${ETCD_CONTAINER_NAME}$"
  docker ps -a --filter "name=^${NATS_CONTAINER_NAME}$"
  docker ps -a --filter "name=^${FRONTEND_CONTAINER_NAME}$"
}

show_logs() {
  if [[ "${LOG_MODE}" = "-f" || "${LOG_MODE}" = "--follow" ]]; then
    echo "===== frontend (follow) ====="
    docker logs -f --tail 200 "${FRONTEND_CONTAINER_NAME}" || true
  else
    echo "===== etcd ====="
    docker logs --tail 120 "${ETCD_CONTAINER_NAME}" || true
    echo
    echo "===== nats ====="
    docker logs --tail 120 "${NATS_CONTAINER_NAME}" || true
    echo
    echo "===== frontend ====="
    docker logs --tail 200 "${FRONTEND_CONTAINER_NAME}" || true
  fi
}

stop_all() {
  docker rm -f "${FRONTEND_CONTAINER_NAME}" >/dev/null 2>&1 || true
  docker rm -f "${NATS_CONTAINER_NAME}" >/dev/null 2>&1 || true
  docker rm -f "${ETCD_CONTAINER_NAME}" >/dev/null 2>&1 || true
}

test_basic() {
  curl "http://127.0.0.1:${DYNAMO_FRONTEND_PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"${DYNAMO_MODEL_PATH}\",
      \"messages\": [{\"role\": \"user\", \"content\": \"Reply with exactly: OK\"}],
      \"max_tokens\": 10
    }"
}

test_priority() {
  curl "http://127.0.0.1:${DYNAMO_FRONTEND_PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"${DYNAMO_MODEL_PATH}\",
      \"messages\": [{\"role\": \"user\", \"content\": \"Say hello in one short sentence.\"}],
      \"max_tokens\": 20,
      \"nvext\": {
        \"agent_hints\": {
          \"priority\": 10,
          \"osl\": 64
        }
      }
    }"
}

start_all() {
  require_docker
  initialize_endpoints
  ensure_dirs
  start_etcd
  wait_for_container "${ETCD_CONTAINER_NAME}"
  start_nats
  wait_for_container "${NATS_CONTAINER_NAME}"
  start_frontend
  wait_for_container "${FRONTEND_CONTAINER_NAME}"
  wait_for_frontend

  cat <<EOF
Dynamo head node is ready.

etcd endpoint: ${ETCD_ENDPOINTS}
nats endpoint: ${NATS_SERVER}
frontend:      http://127.0.0.1:${DYNAMO_FRONTEND_PORT}
model name:    ${DYNAMO_MODEL_PATH}
kv block size: ${DYNAMO_KV_CACHE_BLOCK_SIZE}

Next steps:
  $0 status
  $0 logs
  $0 test
EOF
}

case "${ACTION}" in
  start) start_all ;;
  stop) stop_all ;;
  status) show_status ;;
  logs) show_logs ;;
  test) test_basic ;;
  test-priority) test_priority ;;
  help|-h|--help) usage ;;
  *)
    echo "Unknown command: ${ACTION}" >&2
    usage
    exit 1
    ;;
esac
