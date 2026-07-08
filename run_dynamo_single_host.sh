#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_SCRIPT="${SCRIPT_DIR}/runtime_instrumentation/dynamo_machine_profile.sh"
if [[ -f "${PROFILE_SCRIPT}" ]]; then
  # shellcheck disable=SC1090
  source "${PROFILE_SCRIPT}"
fi
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
MODEL_READY_RETRIES="${MODEL_READY_RETRIES:-${AGENTBENCH_MODEL_READY_RETRIES:-900}}"
MODEL_READY_DELAY_SECS="${MODEL_READY_DELAY_SECS:-${AGENTBENCH_MODEL_READY_DELAY_SECS:-3}}"
MODEL_READY_STABLE_HITS="${MODEL_READY_STABLE_HITS:-${AGENTBENCH_MODEL_READY_STABLE_HITS:-2}}"
MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES:-${AGENTBENCH_MODEL_SMOKE_RETRIES:-180}}"
MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS:-${AGENTBENCH_MODEL_SMOKE_DELAY_SECS:-15}}"
MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS:-${AGENTBENCH_MODEL_COOLDOWN_SECS:-60}}"

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
  DYNAMO_MACHINE_PROFILE   Default: ${DYNAMO_MACHINE_PROFILE:-<unset>}
  DYN_TOOL_CALL_PARSER     Default: ${DYN_TOOL_CALL_PARSER:-<unset>}
  MODEL_READY_RETRIES      Default: ${MODEL_READY_RETRIES}
  MODEL_READY_DELAY_SECS   Default: ${MODEL_READY_DELAY_SECS}
  MODEL_READY_STABLE_HITS  Default: ${MODEL_READY_STABLE_HITS}
  MODEL_SMOKE_RETRIES      Default: ${MODEL_SMOKE_RETRIES}
  MODEL_SMOKE_DELAY_SECS   Default: ${MODEL_SMOKE_DELAY_SECS}
  MODEL_COOLDOWN_SECS      Default: ${MODEL_COOLDOWN_SECS}
  WORKER_DEV_MODE          Default: ${WORKER_DEV_MODE:-0}
  WORKER_DEV_SOURCE_ROOT   Default: ${WORKER_DEV_SOURCE_ROOT:-<unset>}
  WORKER_DEV_BINDINGS_ROOT Default: ${WORKER_DEV_BINDINGS_ROOT:-<unset>}
  WORKER_SGLANG_DEV_MODE   Default: ${WORKER_SGLANG_DEV_MODE:-0}
  WORKER_SGLANG_SOURCE_ROOT Default: ${WORKER_SGLANG_SOURCE_ROOT:-<unset>}
  HICACHE_STORAGE_HOST_PATH Default: ${HICACHE_STORAGE_HOST_PATH:-${HOST_FILE_STORAGE_PATH:-<unset>}}
  HICACHE_STORAGE_CONTAINER_PATH Default: ${HICACHE_STORAGE_CONTAINER_PATH:-${FILE_STORAGE_PATH:-/hicache-storage}}
  SGLANG_TRANSFER_LOG      Default: ${SGLANG_TRANSFER_LOG:-<unset>}
  SGLANG_TRANSFER_LOG_PROFILE Default: ${SGLANG_TRANSFER_LOG_PROFILE:-<unset>} (off, light, timing, full)
  SGLANG_TRANSFER_LOG_DIR  Default: ${SGLANG_TRANSFER_LOG_DIR:-<unset>}
  SGLANG_TRANSFER_LOG_BASENAME Default: ${SGLANG_TRANSFER_LOG_BASENAME:-<unset>}
  SGLANG_TRANSFER_LOG_PATH Default: ${SGLANG_TRANSFER_LOG_PATH:-<stderr only>}
  SGLANG_TRANSFER_LOG_FULL_TOKENS Default: ${SGLANG_TRANSFER_LOG_FULL_TOKENS:-<unset>}
  SGLANG_TRANSFER_LOG_TOKEN_PREVIEW Default: ${SGLANG_TRANSFER_LOG_TOKEN_PREVIEW:-<unset>}
  SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS Default: ${SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS:-<unset>}
  SGLANG_TRANSFER_LOG_INDEX_PREVIEW Default: ${SGLANG_TRANSFER_LOG_INDEX_PREVIEW:-<unset>}
  SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT Default: ${SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT:-<unset>}
  SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC Default: ${SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC:-<unset>}
  SGLANG_TRANSFER_LOG_SYNC_TIMING Default: ${SGLANG_TRANSFER_LOG_SYNC_TIMING:-<unset>}
  SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS Default: ${SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS:-<unset>}
  SGLANG_TRANSFER_LOG_OVERHEAD_TIMING Default: ${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING:-<unset>}
  SGLANG_TRANSFER_LOG_VERBOSE Default: ${SGLANG_TRANSFER_LOG_VERBOSE:-<unset>}

Notes:
  - This mode is intended for single-host GH200 or similar development setups.
  - It is good for functional testing, HintBench, and live-shim iteration.
  - It is not a substitute for a real multi-worker research deployment.
  - Patched SGLang transfer events go to worker stderr by default; set
    SGLANG_TRANSFER_LOG_PATH to a real path if you explicitly want file output.
EOF
}

wait_for_model_registration() {
  local retries="${MODEL_READY_RETRIES:-120}"
  local delay="${MODEL_READY_DELAY_SECS:-2}"
  local models_url="http://127.0.0.1:${DYNAMO_FRONTEND_PORT}/v1/models"
  local expected_model="${DYNAMO_SERVED_MODEL_NAME:-${DYNAMO_MODEL_PATH}}"
  local response=""
  local stable_hits=0
  local required_stable_hits="${MODEL_READY_STABLE_HITS:-2}"

  for ((i=1; i<=retries; i++)); do
    response="$(curl -fsS "${models_url}" 2>/dev/null || true)"
    if [[ -n "${response}" ]] && echo "${response}" | grep -Fq "\"id\":\"${expected_model}\""; then
      stable_hits=$((stable_hits + 1))
      if [[ "${stable_hits}" -ge "${required_stable_hits}" ]]; then
        return 0
      fi
    else
      stable_hits=0
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
  ROUTER_EXTRA_ARGS="${ROUTER_EXTRA_ARGS:-}" \
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
  WORKER_SGLANG_DEV_MODE="${WORKER_SGLANG_DEV_MODE:-0}" \
  WORKER_SGLANG_SOURCE_ROOT="${WORKER_SGLANG_SOURCE_ROOT:-}" \
  HICACHE_STORAGE_HOST_PATH="${HICACHE_STORAGE_HOST_PATH:-${HOST_FILE_STORAGE_PATH:-}}" \
  HICACHE_STORAGE_CONTAINER_PATH="${HICACHE_STORAGE_CONTAINER_PATH:-${FILE_STORAGE_PATH:-}}" \
  HOST_FILE_STORAGE_PATH="${HOST_FILE_STORAGE_PATH:-}" \
  FILE_STORAGE_PATH="${FILE_STORAGE_PATH:-}" \
  SGLANG_TRANSFER_LOG="${SGLANG_TRANSFER_LOG:-}" \
  SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-}" \
  SGLANG_TRANSFER_LOG_DIR="${SGLANG_TRANSFER_LOG_DIR:-}" \
  SGLANG_TRANSFER_LOG_BASENAME="${SGLANG_TRANSFER_LOG_BASENAME:-}" \
  SGLANG_TRANSFER_LOG_PATH="${SGLANG_TRANSFER_LOG_PATH:-}" \
  SGLANG_TRANSFER_LOG_FULL_TOKENS="${SGLANG_TRANSFER_LOG_FULL_TOKENS:-}" \
  SGLANG_TRANSFER_LOG_TOKEN_PREVIEW="${SGLANG_TRANSFER_LOG_TOKEN_PREVIEW:-}" \
  SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS="${SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS:-}" \
  SGLANG_TRANSFER_LOG_INDEX_PREVIEW="${SGLANG_TRANSFER_LOG_INDEX_PREVIEW:-}" \
  SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT="${SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT:-}" \
  SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC="${SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC:-}" \
  SGLANG_TRANSFER_LOG_SYNC_TIMING="${SGLANG_TRANSFER_LOG_SYNC_TIMING:-}" \
  SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS="${SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS:-}" \
  SGLANG_TRANSFER_LOG_OVERHEAD_TIMING="${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING:-}" \
  SGLANG_TRANSFER_LOG_VERBOSE="${SGLANG_TRANSFER_LOG_VERBOSE:-}" \
  SGLANG_HICACHE_MAX_PINNED_RATIO="${SGLANG_HICACHE_MAX_PINNED_RATIO:-}" \
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
