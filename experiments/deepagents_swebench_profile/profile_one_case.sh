#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

MODEL="${MODEL:-Qwen/Qwen2.5-7B-Instruct}"
DATASET="${DATASET:-ScaleAI/SWE-bench_Pro}"
SPLIT="${SPLIT:-test}"
TASK_INDEX="${TASK_INDEX:-0}"
INSTANCE_ID="${INSTANCE_ID:-}"
APP_VARIANT="${APP_VARIANT:-local}"
AGENTBENCH_WORKFLOW_MODE="${AGENTBENCH_WORKFLOW_MODE:-phased}"
PROMPT_EVOLUTION_VALUE_CHAR_LIMIT="${PROMPT_EVOLUTION_VALUE_CHAR_LIMIT:-1000}"
DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT:-8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:${DYNAMO_FRONTEND_PORT}/v1/chat/completions}"
RUN_STAMP="$(date +%Y%m%d_%H%M%S)"
TASK_LABEL="${INSTANCE_ID:-idx${TASK_INDEX}}"
TASK_LABEL="$(printf "%s" "${TASK_LABEL}" | tr '/: ' '___')"
RUN_NAME="${RUN_NAME:-profile-swebench_${RUN_STAMP}_${TASK_LABEL}}"
PROFILE_DIR="${PROFILE_DIR:-${SCRIPT_DIR}/profiles/${RUN_NAME}}"
NSYS_BASENAME="${NSYS_BASENAME:-${RUN_NAME}}"
PROFILE_MODE="${PROFILE_MODE:-nsys}"
PROFILE_READY_RETRIES="${PROFILE_READY_RETRIES:-30}"
PROFILE_READY_DELAY_SECS="${PROFILE_READY_DELAY_SECS:-5}"
PROFILE_READY_REQUEST_TIMEOUT_SECS="${PROFILE_READY_REQUEST_TIMEOUT_SECS:-20}"
PROFILE_STOP_TIMEOUT_SECS="${PROFILE_STOP_TIMEOUT_SECS:-240}"
MODEL_READY_RETRIES="${MODEL_READY_RETRIES:-600}"
MODEL_READY_DELAY_SECS="${MODEL_READY_DELAY_SECS:-2}"
WORKER_PROFILE_TRACE="${WORKER_PROFILE_TRACE:-cuda,nvtx,cublas}"
WORKER_PROFILE_EXTRA_ARGS="${WORKER_PROFILE_EXTRA_ARGS:---sample=none --cuda-event-trace=false --cuda-graph-trace=node}"
WORKER_PROFILE_NSYS_DIR="${WORKER_PROFILE_NSYS_DIR:-}"
CONTEXT_LENGTH="${CONTEXT_LENGTH:-65536}"
WORKER_EXTRA_ARGS="${WORKER_EXTRA_ARGS:---enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length ${CONTEXT_LENGTH}}"

if [[ "${PROFILE_MODE}" = "nsys" && -z "${WORKER_PROFILE_NSYS_DIR}" ]] && command -v nsys >/dev/null 2>&1; then
  NSYS_COMMAND_PATH="$(readlink -f "$(command -v nsys)")"
  NSYS_COMMAND_DIR="$(dirname "${NSYS_COMMAND_PATH}")"
  if [[ "$(basename "${NSYS_COMMAND_DIR}")" = target-linux-* ]]; then
    WORKER_PROFILE_NSYS_DIR="$(dirname "${NSYS_COMMAND_DIR}")"
  else
    WORKER_PROFILE_NSYS_DIR="${NSYS_COMMAND_DIR}"
  fi
fi

mkdir -p "${PROFILE_DIR}"
cd "${REPO_ROOT}"

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "ERROR: required command not found: ${command_name}" >&2
    exit 1
  fi
}

capture_stack_logs() {
  docker logs --tail 300 dynamo-frontend > "${PROFILE_DIR}/dynamo-frontend.log" 2>&1 || true
  docker logs --tail 500 dynamo-sglang-worker > "${PROFILE_DIR}/dynamo-sglang-worker.log" 2>&1 || true
  docker logs dynamo-sglang-worker > "${PROFILE_DIR}/dynamo-sglang-worker.full.log" 2>&1 || true
  docker ps -a --filter name=dynamo-sglang-worker \
    --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Command}}' \
    > "${PROFILE_DIR}/docker-worker-state.txt" 2>&1 || true
  docker inspect dynamo-sglang-worker > "${PROFILE_DIR}/docker-worker-inspect.json" 2>&1 || true
}

print_stack_log_tails() {
  echo
  echo "===== frontend log tail =====" >&2
  tail -120 "${PROFILE_DIR}/dynamo-frontend.log" >&2 || true
  echo
  echo "===== worker log tail =====" >&2
  tail -180 "${PROFILE_DIR}/dynamo-sglang-worker.log" >&2 || true
}

stop_profiled_stack() {
  docker stop -t "${PROFILE_STOP_TIMEOUT_SECS}" dynamo-sglang-worker >/dev/null 2>&1 || true
  ./run_dynamo_single_host.sh stop
}

cleanup() {
  local status=$?
  if [[ ${status} -ne 0 ]]; then
    capture_stack_logs
    stop_profiled_stack >/dev/null 2>&1 || true
  fi
}

wait_for_generation_ready() {
  local attempt
  local response_file="${PROFILE_DIR}/generation-readiness-last-response.txt"
  for ((attempt=1; attempt<=PROFILE_READY_RETRIES; attempt++)); do
    echo "Checking profiled worker generation readiness (${attempt}/${PROFILE_READY_RETRIES})..."
    if curl -fsS \
      --connect-timeout 3 \
      --max-time "${PROFILE_READY_REQUEST_TIMEOUT_SECS}" \
      "${FRONTEND_URL}" \
      -H 'Content-Type: application/json' \
      -d "{
        \"model\": \"${MODEL}\",
        \"messages\": [
          {\"role\": \"user\", \"content\": \"Reply with exactly: ok\"}
        ],
        \"max_tokens\": 4,
        \"temperature\": 0
      }" > "${response_file}" 2>&1; then
      return 0
    fi
    echo "Profiled worker is not generation-ready yet. Last response:"
    tail -40 "${response_file}" || true
    sleep "${PROFILE_READY_DELAY_SECS}"
  done

  echo "ERROR: profiled worker did not become generation-ready." >&2
  capture_stack_logs
  print_stack_log_tails
  return 1
}

run_agentbench_case() {
  local -a cmd
  cmd=(
    python3.11 agentbench/deepagents_swebench_single_host.py
    --app-variant "${APP_VARIANT}"
    --frontend-url "${FRONTEND_URL}"
    --model "${MODEL}"
    --dataset "${DATASET}"
    --split "${SPLIT}"
    --prompt-evolution-value-char-limit "${PROMPT_EVOLUTION_VALUE_CHAR_LIMIT}"
  )

  if [[ -n "${INSTANCE_ID}" ]]; then
    cmd+=(--instance-id "${INSTANCE_ID}")
  else
    cmd+=(--index "${TASK_INDEX}")
  fi
  if [[ -n "${CSV_PATH:-}" ]]; then
    cmd+=(--csv-path "${CSV_PATH}")
  fi
  if [[ -n "${JSON_PATH:-}" ]]; then
    cmd+=(--json-path "${JSON_PATH}")
  fi
  if [[ -n "${REPO_PATH:-}" ]]; then
    cmd+=(--repo-path "${REPO_PATH}")
  fi
  if [[ -n "${REPO_URL:-}" ]]; then
    cmd+=(--repo-url "${REPO_URL}")
  fi
  if [[ "${NO_AUTO_REPO_CHECKOUT:-0}" = "1" ]]; then
    cmd+=(--no-auto-repo-checkout)
  fi

  printf "%q " "${cmd[@]}" > "${PROFILE_DIR}/agentbench-command.txt"
  printf "\n" >> "${PROFILE_DIR}/agentbench-command.txt"
  AGENTBENCH_WORKFLOW_MODE="${AGENTBENCH_WORKFLOW_MODE}" "${cmd[@]}" 2>&1 | tee "${PROFILE_DIR}/agentbench-run.log"
}

require_command docker
require_command curl
require_command python3.11

trap cleanup EXIT

./run_dynamo_single_host.sh stop

WORKER_PROFILE_MODE="${PROFILE_MODE}" \
WORKER_PROFILE_DIR="${PROFILE_DIR}" \
WORKER_PROFILE_BASENAME="${NSYS_BASENAME}" \
WORKER_PROFILE_TRACE="${WORKER_PROFILE_TRACE}" \
WORKER_PROFILE_EXTRA_ARGS="${WORKER_PROFILE_EXTRA_ARGS}" \
WORKER_PROFILE_NSYS_DIR="${WORKER_PROFILE_NSYS_DIR}" \
MODEL_READY_RETRIES="${MODEL_READY_RETRIES}" \
MODEL_READY_DELAY_SECS="${MODEL_READY_DELAY_SECS}" \
DYN_RUNTIME_JSON_LOGS="${DYN_RUNTIME_JSON_LOGS:-1}" \
DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER:-hermes}" \
SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN="${SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN:-1}" \
WORKER_EXTRA_ARGS="${WORKER_EXTRA_ARGS}" \
DYNAMO_MODEL_PATH="${MODEL}" \
DYNAMO_SERVED_MODEL_NAME="${MODEL}" \
DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT}" \
FRONTEND_IMAGE="${FRONTEND_IMAGE:-local/dynamo-frontend:runtime-json-logs}" \
WORKER_IMAGE="${WORKER_IMAGE:-local/dynamo-sglang:runtime-json-logs}" \
./run_dynamo_single_host.sh start

wait_for_generation_ready
run_agentbench_case

AGENTBENCH_RESULT_DIR="$(ls -td agentbench/results/* 2>/dev/null | head -1 || true)"
if [[ -n "${AGENTBENCH_RESULT_DIR}" ]]; then
  printf "%s\n" "${AGENTBENCH_RESULT_DIR}" > "${PROFILE_DIR}/agentbench-result-dir.txt"
fi

capture_stack_logs
stop_profiled_stack
trap - EXIT

REPORT_PATH="${PROFILE_DIR}/${NSYS_BASENAME}.nsys-rep"
QDSTRM_PATH="${PROFILE_DIR}/${NSYS_BASENAME}.qdstrm"
SQLITE_PATH="${PROFILE_DIR}/${NSYS_BASENAME}.sqlite"

echo
echo "Profile directory: ${PROFILE_DIR}"
echo "AgentBench result directory: ${AGENTBENCH_RESULT_DIR:-<not found>}"

if [[ "${PROFILE_MODE}" != "nsys" ]]; then
  echo
  echo "PROFILE_MODE=${PROFILE_MODE}; skipping Nsight report export and kernel classification."
  exit 0
fi

if [[ -f "${REPORT_PATH}" ]]; then
  echo "Nsight report: ${REPORT_PATH}"
else
  echo "WARNING: expected Nsight report not found: ${REPORT_PATH}" >&2
  if [[ -f "${QDSTRM_PATH}" ]]; then
    echo "Nsight raw stream: ${QDSTRM_PATH}" >&2
    echo "The worker captured data, but this environment did not import .qdstrm to .nsys-rep." >&2
    if command -v QdstrmImporter >/dev/null 2>&1; then
      echo "Importing raw Nsight stream with QdstrmImporter..."
      rm -f "${REPORT_PATH}"
      QdstrmImporter -i "${QDSTRM_PATH}" -o "${REPORT_PATH}" || true
    fi
  fi
fi

if command -v nsys >/dev/null 2>&1 && [[ -f "${REPORT_PATH}" ]]; then
  nsys export --force-overwrite true --type sqlite --output "${SQLITE_PATH}" "${REPORT_PATH}" || true
fi

if [[ -f "${SQLITE_PATH}" ]]; then
  python3.11 experiments/lpx_decode_split/analyze_nsys_sqlite.py \
    --sqlite "${SQLITE_PATH}" \
    --worker-log "${PROFILE_DIR}/dynamo-sglang-worker.full.log" \
    --out-dir "${PROFILE_DIR}/kernel_analysis"

  verify_cmd=(python3.11 "${SCRIPT_DIR}/verify_profile_run.py" --profile-dir "${PROFILE_DIR}")
  if [[ -n "${AGENTBENCH_RESULT_DIR}" ]]; then
    verify_cmd+=(--agentbench-result-dir "${AGENTBENCH_RESULT_DIR}")
  fi
  "${verify_cmd[@]}"
else
  cat <<EOF
SQLite export not found yet.

Export manually on a machine with Nsight Systems CLI:

  nsys export --force-overwrite true --type sqlite --output "${SQLITE_PATH}" "${REPORT_PATH}"

Then classify kernels:

  python3.11 experiments/lpx_decode_split/analyze_nsys_sqlite.py \\
    --sqlite "${SQLITE_PATH}" \\
    --worker-log "${PROFILE_DIR}/dynamo-sglang-worker.full.log" \\
    --out-dir "${PROFILE_DIR}/kernel_analysis"

Then verify phase coverage:

  python3.11 "${SCRIPT_DIR}/verify_profile_run.py" \\
    --profile-dir "${PROFILE_DIR}" \\
    ${AGENTBENCH_RESULT_DIR:+--agentbench-result-dir "${AGENTBENCH_RESULT_DIR}"}
EOF
fi
