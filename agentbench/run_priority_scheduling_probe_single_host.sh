#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL="${1:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}"
PRIORITY_SCHEDULING_ID="${PRIORITY_SCHEDULING_ID:-priority_scheduling_$(date +%Y%m%d_%H%M%S)}"
PRIORITY_SCHEDULING_ATTRIBUTION_MODE="${PRIORITY_SCHEDULING_ATTRIBUTION_MODE:-precise}"
LOW_PRIORITY_COUNT="${LOW_PRIORITY_COUNT:-8}"
HIGH_PRIORITY_COUNT="${HIGH_PRIORITY_COUNT:-4}"
LOW_PRIORITY_VALUE="${LOW_PRIORITY_VALUE:-1}"
HIGH_PRIORITY_VALUE="${HIGH_PRIORITY_VALUE:-10}"
PRIORITY_INPUT_LEN="${PRIORITY_INPUT_LEN:-4000}"
PRIORITY_OUTPUT_LEN="${PRIORITY_OUTPUT_LEN:-128}"
PRIORITY_ARRIVAL_GAP_MS="${PRIORITY_ARRIVAL_GAP_MS:-200}"
PRIORITY_INTER_REQUEST_GAP_MS="${PRIORITY_INTER_REQUEST_GAP_MS:-20}"
PRIORITY_TOP_LEVEL_PRIORITY_MODE="${PRIORITY_TOP_LEVEL_PRIORITY_MODE:-auto}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-600}"
SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-full}"
MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES:-60}"
MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS:-10}"
MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS:-30}"
STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE:-0}"
WORKER_BASE_ARGS="${WORKER_BASE_ARGS:---enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority}"
SGLANG_ROOT="${SGLANG_ROOT:-}"
IGNORE_EOS="${IGNORE_EOS:-0}"

RUN_DIR="experiments/reports/priority_scheduling/${PRIORITY_SCHEDULING_ID}"
DRIVER_LOG="${RUN_DIR}/priority_scheduling_driver.log"
SMOKE_LOG="${RUN_DIR}/priority_scheduling_smoke_test.log"
WORKER_RUNTIME_LOG="${RUN_DIR}/priority_scheduling_worker_runtime.log"
mkdir -p "${RUN_DIR}"

usage() {
  cat <<EOF
Usage:
  $0 [model]

Examples:
  $0 Qwen/Qwen2.5-Coder-7B-Instruct

  PRIORITY_SCHEDULING_ATTRIBUTION_MODE=precise \\
  LOW_PRIORITY_COUNT=8 \\
  HIGH_PRIORITY_COUNT=4 \\
  PRIORITY_INPUT_LEN=4000 \\
  PRIORITY_OUTPUT_LEN=128 \\
  PRIORITY_ARRIVAL_GAP_MS=200 \\
  WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \\
  $0 Qwen/Qwen2.5-Coder-7B-Instruct

This wrapper:
  1. stops Dynamo
  2. starts Dynamo with the selected model
  3. waits for /v1/models registration
  4. runs a smoke-test request
  5. runs the synthetic priority-scheduling probe
  6. captures the worker runtime log
  7. rebuilds the report with worker-side evidence
EOF
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${MODEL}" ]]; then
  echo "No model specified. Pass it as an argument or set MODEL / MODEL_NAME." >&2
  exit 1
fi

worker_stopped() {
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  local running
  running="$(docker inspect dynamo-sglang-worker --format '{{.State.Running}}' 2>/dev/null || true)"
  [[ "${running}" = "false" ]]
}

append_worker_debug_to_log() {
  local smoke_log="$1"
  if ! command -v docker >/dev/null 2>&1; then
    return
  fi
  {
    echo
    echo "==== dynamo-sglang-worker docker state ===="
    docker ps -a --filter "name=dynamo-sglang-worker" || true
    echo
    echo "==== dynamo-sglang-worker inspect state ===="
    docker inspect dynamo-sglang-worker \
      --format 'running={{.State.Running}} status={{.State.Status}} exit_code={{.State.ExitCode}} error={{.State.Error}} oom_killed={{.State.OOMKilled}}' \
      2>/dev/null || true
    echo
    echo "==== dynamo-sglang-worker logs tail ===="
    docker logs --tail 240 dynamo-sglang-worker 2>&1 || true
  } >> "${smoke_log}" 2>&1
}

smoke_test_model() {
  local model="$1"
  local smoke_log="$2"
  local frontend_port="${DYNAMO_FRONTEND_PORT:-8000}"
  local chat_url="http://127.0.0.1:${frontend_port}/v1/chat/completions"
  local models_url="http://127.0.0.1:${frontend_port}/v1/models"
  local registered_models
  local model_listed
  local payload
  local response_file
  local http_code

  for ((attempt=1; attempt<=MODEL_SMOKE_RETRIES; attempt++)); do
    echo "Smoke test ${attempt}/${MODEL_SMOKE_RETRIES} for ${model}" | tee -a "${DRIVER_LOG}"
    registered_models="$(curl -fsS "${models_url}" 2>/dev/null || true)"
    {
      echo
      echo "Smoke test attempt ${attempt} for ${model}"
      echo "Registered models before chat:"
      echo "${registered_models:-<unavailable>}"
    } >> "${smoke_log}" 2>&1

    model_listed="$(
      REGISTERED_MODELS="${registered_models}" \
      EXPECTED_MODEL="${model}" \
      "${PYTHON_BIN}" - <<'PY'
import json
import os

try:
    payload = json.loads(os.environ.get("REGISTERED_MODELS", "") or "{}")
except json.JSONDecodeError:
    print("0")
    raise SystemExit

expected = os.environ["EXPECTED_MODEL"]
for item in payload.get("data", []):
    if item.get("id") == expected:
        print("1")
        break
else:
    print("0")
PY
    )"

    if [[ "${model_listed}" != "1" ]]; then
      echo "Model is not listed yet; waiting ${MODEL_SMOKE_DELAY_SECS}s." >> "${smoke_log}"
      if worker_stopped; then
        echo "dynamo-sglang-worker is no longer running." >> "${smoke_log}"
        append_worker_debug_to_log "${smoke_log}"
        return 1
      fi
      sleep "${MODEL_SMOKE_DELAY_SECS}"
      continue
    fi

    payload="$("${PYTHON_BIN}" -c 'import json, sys; print(json.dumps({"model": sys.argv[1], "messages": [{"role": "user", "content": "Reply with exactly: OK"}], "max_tokens": 10}))' "${model}")"
    response_file="$(mktemp)"
    http_code="$(curl -sS -o "${response_file}" -w "%{http_code}" "${chat_url}" \
      -H "Content-Type: application/json" \
      -d "${payload}" 2>> "${smoke_log}" || true)"
    {
      echo "Smoke chat HTTP status: ${http_code:-<none>}"
      echo "Smoke chat response body:"
      cat "${response_file}" 2>/dev/null || true
    } >> "${smoke_log}" 2>&1
    rm -f "${response_file}"
    if [[ "${http_code}" =~ ^2[0-9][0-9]$ ]]; then
      echo "Smoke test passed for ${model}" | tee -a "${DRIVER_LOG}"
      return 0
    fi

    {
      echo
      echo "Smoke test attempt ${attempt} failed for ${model}"
      echo "URL: ${chat_url}"
      echo "Expected model: ${model}"
      echo "Waiting ${MODEL_SMOKE_DELAY_SECS}s before retry."
      echo
    } >> "${smoke_log}" 2>&1
    if worker_stopped; then
      echo "dynamo-sglang-worker stopped after smoke-test failure." >> "${smoke_log}"
      append_worker_debug_to_log "${smoke_log}"
      return 1
    fi
    sleep "${MODEL_SMOKE_DELAY_SECS}"
  done

  append_worker_debug_to_log "${smoke_log}"
  echo "Smoke test failed for ${model}. See ${smoke_log}" | tee -a "${DRIVER_LOG}" >&2
  return 1
}

capture_worker_runtime_log() {
  local out_path="$1"
  mkdir -p "$(dirname "${out_path}")"
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  docker logs dynamo-sglang-worker > "${out_path}" 2>&1
}

{
  echo "Priority scheduling run ID: ${PRIORITY_SCHEDULING_ID}"
  echo "Model: ${MODEL}"
  echo "Attribution mode: ${PRIORITY_SCHEDULING_ATTRIBUTION_MODE}"
  echo "Low-priority count: ${LOW_PRIORITY_COUNT}"
  echo "High-priority count: ${HIGH_PRIORITY_COUNT}"
  echo "Input length words: ${PRIORITY_INPUT_LEN}"
  echo "Output length tokens: ${PRIORITY_OUTPUT_LEN}"
  echo "Arrival gap ms: ${PRIORITY_ARRIVAL_GAP_MS}"
  echo "Inter-request gap ms: ${PRIORITY_INTER_REQUEST_GAP_MS}"
  echo "Top-level priority mode: ${PRIORITY_TOP_LEVEL_PRIORITY_MODE}"
  echo "Driver log: ${DRIVER_LOG}"
  echo "Smoke log: ${SMOKE_LOG}"
  echo "Worker runtime log: ${WORKER_RUNTIME_LOG}"
  echo
  echo "Stopping Dynamo..."
} | tee -a "${DRIVER_LOG}"

./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true

echo "Starting Dynamo for ${MODEL}..." | tee -a "${DRIVER_LOG}"
env_cmd=(
  env
  -u DYN_RUNTIME_JSON_LOGS
  -u WORKER_SGLANG_DEV_MODE
  -u WORKER_SGLANG_SOURCE_ROOT
  -u SGLANG_TRANSFER_LOG
  -u SGLANG_TRANSFER_LOG_PROFILE
)
env_vars=(
  "DYNAMO_MODEL_PATH=${MODEL}"
  "DYNAMO_SERVED_MODEL_NAME=${MODEL}"
  "WORKER_EXTRA_ARGS=${WORKER_BASE_ARGS}"
  "DYN_TOOL_CALL_PARSER=hermes"
)
if [[ "${PRIORITY_SCHEDULING_ATTRIBUTION_MODE}" = "precise" ]]; then
  env_vars+=("DYN_RUNTIME_JSON_LOGS=1")
  if [[ -n "${SGLANG_ROOT}" && -d "${SGLANG_ROOT}" ]]; then
    env_vars+=(
      "WORKER_SGLANG_DEV_MODE=1"
      "WORKER_SGLANG_SOURCE_ROOT=${SGLANG_ROOT}"
      "SGLANG_TRANSFER_LOG=1"
      "SGLANG_TRANSFER_LOG_PROFILE=${SGLANG_TRANSFER_LOG_PROFILE}"
    )
  fi
fi
"${env_cmd[@]}" "${env_vars[@]}" ./run_dynamo_single_host.sh start >> "${DRIVER_LOG}" 2>&1

smoke_test_model "${MODEL}" "${SMOKE_LOG}"

if [[ "${MODEL_COOLDOWN_SECS}" -gt 0 ]]; then
  echo "Cooldown: ${MODEL_COOLDOWN_SECS}s" | tee -a "${DRIVER_LOG}"
  sleep "${MODEL_COOLDOWN_SECS}"
fi

probe_cmd=(
  "${PYTHON_BIN}"
  experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py
  --frontend-url "${FRONTEND_URL}"
  --model "${MODEL}"
  --run-id "${PRIORITY_SCHEDULING_ID}"
  --attribution-mode "${PRIORITY_SCHEDULING_ATTRIBUTION_MODE}"
  --low-priority-count "${LOW_PRIORITY_COUNT}"
  --high-priority-count "${HIGH_PRIORITY_COUNT}"
  --low-priority-value "${LOW_PRIORITY_VALUE}"
  --high-priority-value "${HIGH_PRIORITY_VALUE}"
  --input-len-words "${PRIORITY_INPUT_LEN}"
  --output-len-tokens "${PRIORITY_OUTPUT_LEN}"
  --arrival-gap-ms "${PRIORITY_ARRIVAL_GAP_MS}"
  --inter-request-gap-ms "${PRIORITY_INTER_REQUEST_GAP_MS}"
  --request-timeout "${REQUEST_TIMEOUT}"
  --top-level-priority-mode "${PRIORITY_TOP_LEVEL_PRIORITY_MODE}"
  --cache-event-log experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl
  --worker-runtime-log "${WORKER_RUNTIME_LOG}"
)
if [[ "${IGNORE_EOS}" = "1" ]]; then
  probe_cmd+=(--ignore-eos)
fi

echo "Running priority scheduling probe..." | tee -a "${DRIVER_LOG}"
"${probe_cmd[@]}" 2>&1 | tee -a "${DRIVER_LOG}"

if capture_worker_runtime_log "${WORKER_RUNTIME_LOG}"; then
  echo "Captured worker runtime log: ${WORKER_RUNTIME_LOG}" | tee -a "${DRIVER_LOG}"
fi

echo "Rebuilding report with worker-side evidence..." | tee -a "${DRIVER_LOG}"
"${probe_cmd[@]}" --postprocess-only 2>&1 | tee -a "${DRIVER_LOG}"

if [[ "${STOP_DYNAMO_WHEN_DONE}" = "1" ]]; then
  echo "Stopping Dynamo after priority scheduling probe..." | tee -a "${DRIVER_LOG}"
  ./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true
fi

{
  echo
  echo "Priority scheduling probe finished."
  echo "Run dir: ${RUN_DIR}"
  echo "Requests CSV: ${RUN_DIR}/priority_scheduling_requests.csv"
  echo "Summary CSV: ${RUN_DIR}/priority_scheduling_summary.csv"
  echo "Summary MD: ${RUN_DIR}/priority_scheduling_summary.md"
} | tee -a "${DRIVER_LOG}"
