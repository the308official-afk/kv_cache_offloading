#!/bin/bash

set -euo pipefail

ACTION="${1:-start}"
LOG_MODE="${2:-}"

HOST_HOME_DIR="${HOST_HOME_DIR:-$HOME}"
DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH:-Qwen/Qwen2.5-0.5B}"
DYNAMO_SERVED_MODEL_NAME="${DYNAMO_SERVED_MODEL_NAME:-${DYNAMO_MODEL_PATH}}"
DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT:-8000}"
HEAD_PRIVATE_IP="${HEAD_PRIVATE_IP:-127.0.0.1}"
ETCD_ENDPOINTS="${ETCD_ENDPOINTS:-http://${HEAD_PRIVATE_IP}:2379}"
NATS_SERVER="${NATS_SERVER:-nats://${HEAD_PRIVATE_IP}:4222}"

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  start   Start the head/frontend and one local worker on this machine
  stop    Stop the local worker and head/frontend
  status  Show head and worker container status
  logs    Show head and worker logs
  test    Send a basic chat request through the local frontend

Environment overrides:
  DYNAMO_MODEL_PATH        Default: ${DYNAMO_MODEL_PATH}
  DYNAMO_SERVED_MODEL_NAME Default: ${DYNAMO_SERVED_MODEL_NAME}
  DYNAMO_FRONTEND_PORT     Default: ${DYNAMO_FRONTEND_PORT}
  HEAD_PRIVATE_IP          Default: ${HEAD_PRIVATE_IP}
  ETCD_ENDPOINTS           Default: ${ETCD_ENDPOINTS}
  NATS_SERVER              Default: ${NATS_SERVER}

Notes:
  - This mode is intended for single-host GH200 or similar development setups.
  - It is good for functional testing, HintBench, and live-shim iteration.
  - It is not a substitute for a real multi-worker research deployment.
EOF
}

start_all() {
  HEAD_PRIVATE_IP="${HEAD_PRIVATE_IP}" \
  ETCD_ENDPOINTS="${ETCD_ENDPOINTS}" \
  NATS_SERVER="${NATS_SERVER}" \
  DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH}" \
  DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT}" \
  ./run_dynamo_head.sh start

  DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH}" \
  DYNAMO_SERVED_MODEL_NAME="${DYNAMO_SERVED_MODEL_NAME}" \
  ETCD_ENDPOINTS="${ETCD_ENDPOINTS}" \
  NATS_SERVER="${NATS_SERVER}" \
  ./run_dynamo_worker.sh start

  cat <<EOF
Single-host Dynamo mode is ready.

frontend: http://127.0.0.1:${DYNAMO_FRONTEND_PORT}
etcd:     ${ETCD_ENDPOINTS}
nats:     ${NATS_SERVER}
model:    ${DYNAMO_MODEL_PATH}

Next steps:
  $0 status
  $0 logs
  $0 test
EOF
}

stop_all() {
  ./run_dynamo_worker.sh stop || true
  ./run_dynamo_head.sh stop || true
}

show_status() {
  echo "===== head ====="
  ./run_dynamo_head.sh status || true
  echo
  echo "===== worker ====="
  ./run_dynamo_worker.sh status || true
}

show_logs() {
  echo "===== head ====="
  ./run_dynamo_head.sh logs "${LOG_MODE}" || true
  echo
  echo "===== worker ====="
  ./run_dynamo_worker.sh logs "${LOG_MODE}" || true
}

test_basic() {
  DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH}" ./run_dynamo_head.sh test
}

case "${ACTION}" in
  start) start_all ;;
  stop) stop_all ;;
  status) show_status ;;
  logs) show_logs ;;
  test) test_basic ;;
  help|-h|--help) usage ;;
  *)
    echo "Unknown command: ${ACTION}" >&2
    usage
    exit 1
    ;;
esac
