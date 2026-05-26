#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

MODEL="${MODEL:-Qwen/Qwen2.5-7B-Instruct}"
PROMPT_TOKEN_TARGET="${PROMPT_TOKEN_TARGET:-8192}"
MAX_TOKENS="${MAX_TOKENS:-256}"
DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT:-8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:${DYNAMO_FRONTEND_PORT}/v1/chat/completions}"
RUN_STAMP="$(date +%Y%m%d_%H%M%S)"
RUN_NAME="${RUN_NAME:-profile-decode_${RUN_STAMP}_ctx${PROMPT_TOKEN_TARGET}_out${MAX_TOKENS}}"
PROFILE_DIR="${PROFILE_DIR:-${SCRIPT_DIR}/profiles/${RUN_NAME}}"
RESULTS_ROOT="${RESULTS_ROOT:-${SCRIPT_DIR}/results/${RUN_NAME}}"
NSYS_BASENAME="${NSYS_BASENAME:-${RUN_NAME}}"
PROFILE_MODE="${PROFILE_MODE:-nsys}"
PROFILE_READY_RETRIES="${PROFILE_READY_RETRIES:-30}"
PROFILE_READY_DELAY_SECS="${PROFILE_READY_DELAY_SECS:-5}"
PROFILE_READY_REQUEST_TIMEOUT_SECS="${PROFILE_READY_REQUEST_TIMEOUT_SECS:-20}"
PROFILE_STOP_TIMEOUT_SECS="${PROFILE_STOP_TIMEOUT_SECS:-120}"
MODEL_READY_RETRIES="${MODEL_READY_RETRIES:-600}"
MODEL_READY_DELAY_SECS="${MODEL_READY_DELAY_SECS:-2}"
WORKER_PROFILE_TRACE="${WORKER_PROFILE_TRACE:-cuda,nvtx,cublas}"
WORKER_PROFILE_EXTRA_ARGS="${WORKER_PROFILE_EXTRA_ARGS:---sample=none --cuda-event-trace=false --cuda-graph-trace=node}"
WORKER_PROFILE_NSYS_DIR="${WORKER_PROFILE_NSYS_DIR:-}"

if [[ "${PROFILE_MODE}" = "nsys" && -z "${WORKER_PROFILE_NSYS_DIR}" ]] && command -v nsys >/dev/null 2>&1; then
  NSYS_COMMAND_PATH="$(readlink -f "$(command -v nsys)")"
  NSYS_COMMAND_DIR="$(dirname "${NSYS_COMMAND_PATH}")"
  if [[ "$(basename "${NSYS_COMMAND_DIR}")" = target-linux-* ]]; then
    WORKER_PROFILE_NSYS_DIR="$(dirname "${NSYS_COMMAND_DIR}")"
  else
    WORKER_PROFILE_NSYS_DIR="${NSYS_COMMAND_DIR}"
  fi
fi

mkdir -p "${PROFILE_DIR}" "${RESULTS_ROOT}"

cd "${REPO_ROOT}"

cleanup() {
  local status=$?
  if [[ ${status} -ne 0 ]]; then
    capture_stack_logs
    stop_profiled_stack >/dev/null 2>&1 || true
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
  # Give nsys a chance to flush the .nsys-rep before the normal cleanup path
  # removes containers. docker rm -f can kill the profiler too abruptly.
  docker stop -t "${PROFILE_STOP_TIMEOUT_SECS}" dynamo-sglang-worker >/dev/null 2>&1 || true
  ./run_dynamo_single_host.sh stop
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
  echo "Saved logs:" >&2
  echo "  ${PROFILE_DIR}/dynamo-frontend.log" >&2
  echo "  ${PROFILE_DIR}/dynamo-sglang-worker.log" >&2
  echo "  ${PROFILE_DIR}/generation-readiness-last-response.txt" >&2
  print_stack_log_tails
  return 1
}

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
DYNAMO_MODEL_PATH="${MODEL}" \
DYNAMO_SERVED_MODEL_NAME="${MODEL}" \
DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT}" \
FRONTEND_IMAGE="${FRONTEND_IMAGE:-local/dynamo-frontend:runtime-json-logs}" \
WORKER_IMAGE="${WORKER_IMAGE:-local/dynamo-sglang:runtime-json-logs}" \
./run_dynamo_single_host.sh start

wait_for_generation_ready

python3.11 "${SCRIPT_DIR}/run_decode_sweep.py" \
  --frontend-url "${FRONTEND_URL}" \
  --model "${MODEL}" \
  --prompt-token-targets "${PROMPT_TOKEN_TARGET}" \
  --max-tokens-list "${MAX_TOKENS}" \
  --repeats 1 \
  --results-root "${RESULTS_ROOT}" \
  --fail-on-error

capture_stack_logs

stop_profiled_stack
trap - EXIT

REPORT_PATH="${PROFILE_DIR}/${NSYS_BASENAME}.nsys-rep"
QDSTRM_PATH="${PROFILE_DIR}/${NSYS_BASENAME}.qdstrm"
SQLITE_PATH="${PROFILE_DIR}/${NSYS_BASENAME}.sqlite"

echo
echo "Profile directory: ${PROFILE_DIR}"
echo "Measurement directory: ${RESULTS_ROOT}"

if [[ "${PROFILE_MODE}" != "nsys" ]]; then
  echo
  echo "PROFILE_MODE=${PROFILE_MODE}; skipping Nsight report export and kernel classification."
  echo "Measurement directory: ${RESULTS_ROOT}"
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
  python3.11 "${SCRIPT_DIR}/analyze_nsys_sqlite.py" \
    --sqlite "${SQLITE_PATH}" \
    --out-dir "${PROFILE_DIR}/kernel_analysis"
  if [[ -f "${PROFILE_DIR}/kernel_analysis/kernel_classification.json" ]]; then
    python3.11 "${SCRIPT_DIR}/estimate_lpx_speedup.py" \
      --classification-json "${PROFILE_DIR}/kernel_analysis/kernel_classification.json" \
      --completion-tokens "${MAX_TOKENS}" \
      --out-dir "${PROFILE_DIR}/kernel_analysis/lpx_what_if"
  fi
else
  cat <<EOF
SQLite export not found yet.

Export manually on a machine with Nsight Systems CLI:

  nsys export --force-overwrite true --type sqlite --output "${SQLITE_PATH}" "${REPORT_PATH}"

If only the raw .qdstrm exists, first import it with the matching Nsight Systems
QdstrmImporter version:

  QdstrmImporter -i "${QDSTRM_PATH}" -o "${REPORT_PATH}"

Then classify kernels:

  python3.11 "${SCRIPT_DIR}/analyze_nsys_sqlite.py" \\
    --sqlite "${SQLITE_PATH}" \\
    --out-dir "${PROFILE_DIR}/kernel_analysis"

Then run the LPX what-if estimate:

  python3.11 "${SCRIPT_DIR}/estimate_lpx_speedup.py" \\
    --classification-json "${PROFILE_DIR}/kernel_analysis/kernel_classification.json" \\
    --completion-tokens "${MAX_TOKENS}" \\
    --out-dir "${PROFILE_DIR}/kernel_analysis/lpx_what_if"
EOF
fi
