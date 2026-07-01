#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh
if [[ -f runtime_instrumentation/dynamo_machine_profile.sh ]]; then
  # shellcheck disable=SC1091
  source runtime_instrumentation/dynamo_machine_profile.sh
fi
source runtime_instrumentation/precise_sglang_helper.sh

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL="${1:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}"
SPEC_PREFILL_ID="${SPEC_PREFILL_ID:-speculative_prefill_$(date +%Y%m%d_%H%M%S)}"
SPEC_PREFILL_ATTRIBUTION_MODE="${SPEC_PREFILL_ATTRIBUTION_MODE:-precise}"
SPEC_PREFILL_REQUEST_CONTEXT_MODE="${SPEC_PREFILL_REQUEST_CONTEXT_MODE:-auto}"
SPEC_PREFILL_TURN_A_WORDS="${SPEC_PREFILL_TURN_A_WORDS:-4000}"
SPEC_PREFILL_TURN_B_WORDS="${SPEC_PREFILL_TURN_B_WORDS:-512}"
SPEC_PREFILL_OUTPUT_TOKENS="${SPEC_PREFILL_OUTPUT_TOKENS:-64}"
SPEC_PREFILL_WARMUP_WAIT_MS="${SPEC_PREFILL_WARMUP_WAIT_MS:-500}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-600}"
SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-full}"
MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES:-${AGENTBENCH_MODEL_SMOKE_RETRIES}}"
MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS:-${AGENTBENCH_MODEL_SMOKE_DELAY_SECS}}"
MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS:-${AGENTBENCH_MODEL_COOLDOWN_SECS}}"
STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE:-0}"
WORKER_BASE_ARGS="${WORKER_BASE_ARGS:---enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority}"
SGLANG_ROOT="${SGLANG_ROOT:-}"
AUTO_BUILD_PRECISE_IMAGES="${AUTO_BUILD_PRECISE_IMAGES:-1}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-local/dynamo-frontend:runtime-json-logs}"
WORKER_IMAGE="${WORKER_IMAGE:-local/dynamo-sglang:runtime-json-logs}"

RUN_DIR="experiments/reports/speculative_prefill/${SPEC_PREFILL_ID}"
DRIVER_LOG="${RUN_DIR}/speculative_prefill_driver.log"
SMOKE_LOG="${RUN_DIR}/speculative_prefill_smoke_test.log"
WORKER_RUNTIME_LOG="${RUN_DIR}/speculative_prefill_worker_runtime.log"
mkdir -p "${RUN_DIR}"

prepare_precise_specprefill_sglang() {
  if [[ "${SPEC_PREFILL_ATTRIBUTION_MODE}" != "precise" ]]; then
    return 0
  fi
  prepare_precise_sglang_for_run "precise speculative-prefill attribution" "${DRIVER_LOG}" "specprefill"
}

ensure_precise_specprefill_runtime_images() {
  if [[ "${SPEC_PREFILL_ATTRIBUTION_MODE}" != "precise" ]]; then
    return 0
  fi
  echo "Ensuring machine-specific precise runtime images..." | tee -a "${DRIVER_LOG}"
  local -a cmd=(
    ./runtime_instrumentation/ensure_precise_runtime_ready.sh
    --machine-profile "${DYNAMO_MACHINE_PROFILE:-}"
  )
  if [[ "${AUTO_BUILD_PRECISE_IMAGES}" = "1" ]]; then
    cmd+=(--build-if-missing)
  fi
  if [[ "${INTERACTIVE_BUILD_PROGRESS:-0}" = "1" && -t 1 ]]; then
    echo "Interactive build progress enabled for precise runtime image checks." | tee -a "${DRIVER_LOG}"
    echo "Note: live Docker build output will stream to the terminal instead of being mirrored line-by-line into this log." | tee -a "${DRIVER_LOG}"
    AUTO_BUILD_PRECISE_IMAGES="${AUTO_BUILD_PRECISE_IMAGES}" \
      "${cmd[@]}"
  else
    AUTO_BUILD_PRECISE_IMAGES="${AUTO_BUILD_PRECISE_IMAGES}" \
      "${cmd[@]}" | tee -a "${DRIVER_LOG}"
  fi
}

ensure_precise_specprefill_dynamo_source() {
  if [[ "${SPEC_PREFILL_ATTRIBUTION_MODE}" != "precise" ]]; then
    return 0
  fi
  local dynamo_root="${SOURCE_DIR:-$(resolve_precise_dynamo_root || true)}"
  if [[ -n "${dynamo_root}" ]] && _precise_dynamo_require_markers "${dynamo_root}" specprefill; then
    return 0
  fi

  echo "Preparing instrumented Dynamo source for speculative-prefill attribution..." | tee -a "${DRIVER_LOG}"
  ./runtime_instrumentation/prepare_instrumented_dynamo_source.sh | tee -a "${DRIVER_LOG}"

  dynamo_root="${SOURCE_DIR:-$(resolve_precise_dynamo_root || true)}"
  if [[ -z "${dynamo_root}" ]] || ! _precise_dynamo_require_markers "${dynamo_root}" specprefill; then
    echo "Speculative-prefill markers are still missing after Dynamo source preparation." | tee -a "${DRIVER_LOG}" >&2
    return 1
  fi

  if [[ "${AUTO_BUILD_PRECISE_IMAGES}" = "1" ]]; then
    echo "Rebuilding machine-specific precise runtime images to include speculative-prefill markers..." | tee -a "${DRIVER_LOG}"
    if [[ "${INTERACTIVE_BUILD_PROGRESS:-0}" = "1" && -t 1 ]]; then
      echo "Interactive build progress enabled for speculative-prefill image rebuild." | tee -a "${DRIVER_LOG}"
      echo "Note: live Docker build output will stream to the terminal instead of being mirrored line-by-line into this log." | tee -a "${DRIVER_LOG}"
      LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
        ./runtime_instrumentation/build_instrumented_dynamo_images.sh
    else
      LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
        ./runtime_instrumentation/build_instrumented_dynamo_images.sh | tee -a "${DRIVER_LOG}"
    fi
  fi
}

check_precise_specprefill_runtime_ready() {
  if [[ "${SPEC_PREFILL_ATTRIBUTION_MODE}" != "precise" ]]; then
    return 0
  fi
  echo "Running precise speculative-prefill preflight..." | tee -a "${DRIVER_LOG}"
  LOG_FILE="${DRIVER_LOG}" \
    ./runtime_instrumentation/check_precise_attribution_ready.sh specprefill
}

usage() {
  cat <<EOF
Usage:
  $0 [model]

Examples:
  $0 Qwen/Qwen2.5-Coder-7B-Instruct
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

warn_if_worker_runtime_missing() {
  local worker_runtime_log="$1"
  if [[ ! -f "${worker_runtime_log}" ]]; then
    return 0
  fi
  if ! grep -q '\[RUNTIME_JSON\]' "${worker_runtime_log}"; then
    {
      echo
      echo "WARNING: captured worker log contains no [RUNTIME_JSON] lines."
      echo "This usually means the worker image was not built from prepared/instrumented Dynamo source."
      echo
    } | tee -a "${DRIVER_LOG}" >&2
  fi
}

ensure_precise_specprefill_dynamo_source
ensure_precise_specprefill_runtime_images
prepare_precise_specprefill_sglang
if [[ "${SPEC_PREFILL_ATTRIBUTION_MODE}" = "precise" ]]; then
  precise_print_local_ready_summary "specprefill" "${DRIVER_LOG}"
fi

{
  echo "Speculative prefill run ID: ${SPEC_PREFILL_ID}"
  echo "Model: ${MODEL}"
  echo "Machine profile: ${DYNAMO_MACHINE_PROFILE:-<unset>}"
  echo "Frontend image: ${FRONTEND_IMAGE}"
  echo "Worker image: ${WORKER_IMAGE}"
  echo "Auto-build precise images: ${AUTO_BUILD_PRECISE_IMAGES}"
  echo "Attribution mode: ${SPEC_PREFILL_ATTRIBUTION_MODE}"
  echo "Turn A input words: ${SPEC_PREFILL_TURN_A_WORDS}"
  echo "Turn B input words: ${SPEC_PREFILL_TURN_B_WORDS}"
  echo "Output length tokens: ${SPEC_PREFILL_OUTPUT_TOKENS}"
  echo "Warmup wait ms: ${SPEC_PREFILL_WARMUP_WAIT_MS}"
  echo "Request-context mode: ${SPEC_PREFILL_REQUEST_CONTEXT_MODE}"
  echo "Driver log: ${DRIVER_LOG}"
  echo "Smoke log: ${SMOKE_LOG}"
  echo "Worker runtime log: ${WORKER_RUNTIME_LOG}"
  echo
  echo "Stopping Dynamo..."
} | tee -a "${DRIVER_LOG}"

./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true

agentbench_print_model_readiness_active_banner | tee -a "${DRIVER_LOG}"
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
if [[ "${SPEC_PREFILL_ATTRIBUTION_MODE}" = "precise" ]]; then
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
check_precise_specprefill_runtime_ready
agentbench_print_model_readiness_go_banner | tee -a "${DRIVER_LOG}"
if [[ "${SPEC_PREFILL_ATTRIBUTION_MODE}" = "precise" ]]; then
  precise_print_go_summary "specprefill" "${DRIVER_LOG}"
fi

if [[ "${MODEL_COOLDOWN_SECS}" -gt 0 ]]; then
  echo "Cooldown: ${MODEL_COOLDOWN_SECS}s" | tee -a "${DRIVER_LOG}"
  sleep "${MODEL_COOLDOWN_SECS}"
fi

probe_cmd=(
  "${PYTHON_BIN}"
  experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py
  --frontend-url "${FRONTEND_URL}"
  --model "${MODEL}"
  --run-id "${SPEC_PREFILL_ID}"
  --attribution-mode "${SPEC_PREFILL_ATTRIBUTION_MODE}"
  --request-context-mode "${SPEC_PREFILL_REQUEST_CONTEXT_MODE}"
  --turn-a-words "${SPEC_PREFILL_TURN_A_WORDS}"
  --turn-b-words "${SPEC_PREFILL_TURN_B_WORDS}"
  --output-len-tokens "${SPEC_PREFILL_OUTPUT_TOKENS}"
  --warmup-wait-ms "${SPEC_PREFILL_WARMUP_WAIT_MS}"
  --request-timeout "${REQUEST_TIMEOUT}"
  --worker-runtime-log "${WORKER_RUNTIME_LOG}"
)

echo "Running speculative-prefill probe..." | tee -a "${DRIVER_LOG}"
"${probe_cmd[@]}" 2>&1 | tee -a "${DRIVER_LOG}"

if capture_worker_runtime_log "${WORKER_RUNTIME_LOG}"; then
  echo "Captured worker runtime log: ${WORKER_RUNTIME_LOG}" | tee -a "${DRIVER_LOG}"
  warn_if_worker_runtime_missing "${WORKER_RUNTIME_LOG}"
fi

echo "Rebuilding report with worker-side evidence..." | tee -a "${DRIVER_LOG}"
"${probe_cmd[@]}" --postprocess-only 2>&1 | tee -a "${DRIVER_LOG}"

if [[ "${STOP_DYNAMO_WHEN_DONE}" = "1" ]]; then
  echo "Stopping Dynamo after speculative-prefill probe..." | tee -a "${DRIVER_LOG}"
  ./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true
fi

{
  echo
  echo "Speculative-prefill probe finished."
  echo "Run dir: ${RUN_DIR}"
  echo "Requests CSV: ${RUN_DIR}/speculative_prefill_requests.csv"
  echo "Matrix CSV: ${RUN_DIR}/speculative_prefill_matrix.csv"
  echo "Summary CSV: ${RUN_DIR}/speculative_prefill_summary.csv"
  echo "Summary MD: ${RUN_DIR}/speculative_prefill_summary.md"
} | tee -a "${DRIVER_LOG}"
