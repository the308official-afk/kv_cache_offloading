#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_CONFIG="${SCRIPT_DIR}/agentbench/model_config.sh"
if [[ -f "${MODEL_CONFIG}" ]]; then
  # Shared AgentBench defaults; explicit shell env still overrides these below.
  # shellcheck disable=SC1090
  source "${MODEL_CONFIG}"
fi

ACTION="${1:-start}"
LOG_MODE="${2:-}"

HOST_HOME_DIR="${HOST_HOME_DIR:-$HOME}"
DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH:-${AGENTBENCH_MODEL:-Qwen/Qwen2.5-0.5B}}"
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
  logs-head   Show only head/frontend logs
  logs-worker Show only worker logs
  test    Send a basic chat request through the local frontend

Environment overrides:
  DYNAMO_MODEL_PATH        Default: ${DYNAMO_MODEL_PATH}
  DYNAMO_SERVED_MODEL_NAME Default: ${DYNAMO_SERVED_MODEL_NAME}
  DYNAMO_FRONTEND_PORT     Default: ${DYNAMO_FRONTEND_PORT}
  HEAD_PRIVATE_IP          Default: ${HEAD_PRIVATE_IP}
  ETCD_ENDPOINTS           Default: ${ETCD_ENDPOINTS}
  NATS_SERVER              Default: ${NATS_SERVER}
  DYN_RUNTIME_JSON_LOGS    Default: ${DYN_RUNTIME_JSON_LOGS:-}
  DYN_TOOL_CALL_PARSER     Default: ${DYN_TOOL_CALL_PARSER:-<unset>}
  WORKER_DEV_MODE          Default: ${WORKER_DEV_MODE:-0}
  WORKER_DEV_SOURCE_ROOT   Default: ${WORKER_DEV_SOURCE_ROOT:-<unset>}
  WORKER_DEV_BINDINGS_ROOT Default: ${WORKER_DEV_BINDINGS_ROOT:-<unset>}

Notes:
  - This mode is intended for single-host GH200 or similar development setups.
  - It is good for functional testing, HintBench, and live-shim iteration.
  - It is not a substitute for a real multi-worker research deployment.
EOF
}

wait_for_model_registration() {
  local retries="${MODEL_READY_RETRIES:-120}"
  local delay="${MODEL_READY_DELAY_SECS:-2}"
  local models_url="http://127.0.0.1:${DYNAMO_FRONTEND_PORT}/v1/models"
  local expected_model="${DYNAMO_SERVED_MODEL_NAME:-${DYNAMO_MODEL_PATH}}"
  local response=""

  for ((i=1; i<=retries; i++)); do
    response="$(curl -fsS "${models_url}" 2>/dev/null || true)"
    if [[ -n "${response}" ]] && echo "${response}" | grep -Fq "\"id\":\"${expected_model}\""; then
      return 0
    fi

    if ! ./run_dynamo_worker.sh status >/dev/null 2>&1; then
      echo "Worker status check failed while waiting for model registration." >&2
    fi

    sleep "${delay}"
  done

  cat >&2 <<EOF
Timed out waiting for model registration in the frontend.

Expected model:
  ${expected_model}

Checked endpoint:
  ${models_url}

Recent frontend logs:
EOF
  ./run_dynamo_head.sh logs || true
  echo >&2
  echo "Recent worker logs:" >&2
  ./run_dynamo_worker.sh logs || true
  exit 1
}

start_all() {
  HEAD_PRIVATE_IP="${HEAD_PRIVATE_IP}" \
  ETCD_ENDPOINTS="${ETCD_ENDPOINTS}" \
  NATS_SERVER="${NATS_SERVER}" \
  DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH}" \
  DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER:-}" \
  DYN_RUNTIME_JSON_LOGS="${DYN_RUNTIME_JSON_LOGS:-}" \
  DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT}" \
  ./run_dynamo_head.sh start

  DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH}" \
  DYNAMO_SERVED_MODEL_NAME="${DYNAMO_SERVED_MODEL_NAME}" \
  ETCD_ENDPOINTS="${ETCD_ENDPOINTS}" \
  NATS_SERVER="${NATS_SERVER}" \
  DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER:-}" \
  DYN_RUNTIME_JSON_LOGS="${DYN_RUNTIME_JSON_LOGS:-}" \
  SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN="${SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN:-}" \
  WORKER_PROFILE_MODE="${WORKER_PROFILE_MODE:-}" \
  WORKER_PROFILE_DIR="${WORKER_PROFILE_DIR:-}" \
  WORKER_PROFILE_BASENAME="${WORKER_PROFILE_BASENAME:-}" \
  WORKER_PROFILE_TRACE="${WORKER_PROFILE_TRACE:-}" \
  WORKER_PROFILE_EXTRA_ARGS="${WORKER_PROFILE_EXTRA_ARGS:-}" \
  WORKER_PROFILE_NSYS_DIR="${WORKER_PROFILE_NSYS_DIR:-}" \
  WORKER_PROFILE_NCU_DIR="${WORKER_PROFILE_NCU_DIR:-}" \
  WORKER_PROFILE_NCU_METRICS="${WORKER_PROFILE_NCU_METRICS:-}" \
  WORKER_PROFILE_NCU_KERNEL_NAME="${WORKER_PROFILE_NCU_KERNEL_NAME:-}" \
  WORKER_PROFILE_NCU_EXTRA_ARGS="${WORKER_PROFILE_NCU_EXTRA_ARGS:-}" \
  WORKER_DEV_MODE="${WORKER_DEV_MODE:-0}" \
  WORKER_DEV_SOURCE_ROOT="${WORKER_DEV_SOURCE_ROOT:-}" \
  WORKER_DEV_BINDINGS_ROOT="${WORKER_DEV_BINDINGS_ROOT:-}" \
  ./run_dynamo_worker.sh start

  wait_for_model_registration

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
  if [[ "${LOG_MODE}" = "-f" || "${LOG_MODE}" = "--follow" ]]; then
    echo "===== head (follow) ====="
    ./run_dynamo_head.sh logs -f &
    local head_pid=$!
    echo
    echo "===== worker (follow) ====="
    ./run_dynamo_worker.sh logs -f &
    local worker_pid=$!

    cleanup_followers() {
      kill "${head_pid}" "${worker_pid}" >/dev/null 2>&1 || true
    }

    trap cleanup_followers INT TERM EXIT
    wait "${head_pid}" "${worker_pid}"
    trap - INT TERM EXIT
    return
  fi

  echo "===== head ====="
  ./run_dynamo_head.sh logs "${LOG_MODE}" || true
  echo
  echo "===== worker ====="
  ./run_dynamo_worker.sh logs "${LOG_MODE}" || true
}

show_head_logs() {
  ./run_dynamo_head.sh logs "${LOG_MODE}"
}

show_worker_logs() {
  ./run_dynamo_worker.sh logs "${LOG_MODE}"
}

test_basic() {
  DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH}" ./run_dynamo_head.sh test
}

case "${ACTION}" in
  start) start_all ;;
  stop) stop_all ;;
  status) show_status ;;
  logs) show_logs ;;
  logs-head) show_head_logs ;;
  logs-worker) show_worker_logs ;;
  test) test_basic ;;
  help|-h|--help) usage ;;
  *)
    echo "Unknown command: ${ACTION}" >&2
    usage
    exit 1
    ;;
esac
