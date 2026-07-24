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
SPEC_PREFILL_TURN_A_OUTPUT_TOKENS="${SPEC_PREFILL_TURN_A_OUTPUT_TOKENS:-${SPEC_PREFILL_OUTPUT_TOKENS}}"
SPEC_PREFILL_TURN_B_OUTPUT_TOKENS="${SPEC_PREFILL_TURN_B_OUTPUT_TOKENS:-${SPEC_PREFILL_OUTPUT_TOKENS}}"
SPEC_PREFILL_WARMUP_WAIT_MS="${SPEC_PREFILL_WARMUP_WAIT_MS:-500}"
SPEC_PREFILL_REQUEST_SOURCE="${SPEC_PREFILL_REQUEST_SOURCE:-synthetic}"
SPEC_PREFILL_REAL_TURN_B_MODE="${SPEC_PREFILL_REAL_TURN_B_MODE:-source_prompt}"
SPEC_PREFILL_SWEBENCH_DATASET="${SPEC_PREFILL_SWEBENCH_DATASET:-ScaleAI/SWE-bench_Pro}"
SPEC_PREFILL_SWEBENCH_SPLIT="${SPEC_PREFILL_SWEBENCH_SPLIT:-test}"
SPEC_PREFILL_TURN_A_INDEX="${SPEC_PREFILL_TURN_A_INDEX:-0}"
SPEC_PREFILL_TURN_B_INDEX="${SPEC_PREFILL_TURN_B_INDEX:-1}"
SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET="${SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET:-2}"
SPEC_PREFILL_COMPARISON_MODE="${SPEC_PREFILL_COMPARISON_MODE:-offset}"
SPEC_PREFILL_TRAJECTORY_PROMPT_CATALOG="${SPEC_PREFILL_TRAJECTORY_PROMPT_CATALOG:-experiments/reports/latest_swebench_trajectory_prompt_catalog.csv}"
SPEC_PREFILL_TRAJECTORY_TURN_A_TASK_INDEX="${SPEC_PREFILL_TRAJECTORY_TURN_A_TASK_INDEX:-0}"
SPEC_PREFILL_TRAJECTORY_TURN_A_STAGE="${SPEC_PREFILL_TRAJECTORY_TURN_A_STAGE:-planning}"
SPEC_PREFILL_TRAJECTORY_TURN_B_TASK_INDEX="${SPEC_PREFILL_TRAJECTORY_TURN_B_TASK_INDEX:--1}"
SPEC_PREFILL_TRAJECTORY_TURN_B_STAGE="${SPEC_PREFILL_TRAJECTORY_TURN_B_STAGE:-execution}"
SPEC_PREFILL_TRAJECTORY_PROTECTED_OFFSET="${SPEC_PREFILL_TRAJECTORY_PROTECTED_OFFSET:-0}"
SPEC_PREFILL_TRAJECTORY_PROMPT_PREFIX_MODE="${SPEC_PREFILL_TRAJECTORY_PROMPT_PREFIX_MODE:-${SPEC_PREFILL_TRAJECTORY_REPLAY_HEADER_MODE:-task_stage}}"
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
EXPERIMENT_RESET_MODE="${EXPERIMENT_RESET_MODE:-restart}"
EXPERIMENT_RESET_STATE_FILE="${EXPERIMENT_RESET_STATE_FILE:-experiments/runtime_state/active_runtime_signature.txt}"

if [[ "${SPEC_PREFILL_COMPARISON_MODE}" = "same_task_isolated" ]]; then
  SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET=0
  SPEC_PREFILL_TRAJECTORY_PROTECTED_OFFSET=0
fi

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

build_runtime_signature() {
  printf '%s\n' \
    "model=${MODEL}" \
    "attribution_mode=${SPEC_PREFILL_ATTRIBUTION_MODE}" \
    "frontend_image=${FRONTEND_IMAGE}" \
    "worker_image=${WORKER_IMAGE}" \
    "worker_extra_args=${WORKER_BASE_ARGS}" \
    "router_extra_args=" \
    "sglang_root=${SGLANG_ROOT}" \
    "host_file_storage_path=" \
    "file_storage_path=" \
    "custom_runtime_images_mode=" \
    "custom_runtime_sglang_root=" \
    "runtime_stack=standard" | \
    shasum -a 256 | awk '{print $1}'
}

runtime_reset_env_cmd() {
  local signature="$1"
  shift
  env \
    FRONTEND_URL="${FRONTEND_URL}" \
    EXPERIMENT_RUNTIME_SIGNATURE="${signature}" \
    EXPERIMENT_RESET_STATE_FILE="${EXPERIMENT_RESET_STATE_FILE}" \
    EXPERIMENT_EXPECTED_MODEL="${MODEL}" \
    "$@"
}

runtime_reuse_ready() {
  local signature="$1"
  runtime_reset_env_cmd "${signature}" \
    ./runtime_instrumentation/reset_experiment_state.sh reuse-ready
}

runtime_flush() {
  local signature="$1"
  runtime_reset_env_cmd "${signature}" \
    ./runtime_instrumentation/reset_experiment_state.sh flush
}

runtime_check_flush() {
  local signature="$1"
  runtime_reset_env_cmd "${signature}" \
    ./runtime_instrumentation/reset_experiment_state.sh check-flush
}

runtime_mark_active() {
  local signature="$1"
  runtime_reset_env_cmd "${signature}" \
    ./runtime_instrumentation/reset_experiment_state.sh mark-active >/dev/null
}

runtime_clear_active() {
  env \
    EXPERIMENT_RESET_STATE_FILE="${EXPERIMENT_RESET_STATE_FILE}" \
    ./runtime_instrumentation/reset_experiment_state.sh clear-active >/dev/null
}

print_flush_ready_banner() {
  cat <<EOF
========================================
LIVE FLUSH READY (the current runtime serves /clear_kv_blocks)
========================================
EOF
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

reset_runtime_for_isolated_arm() {
  local arm_label="$1"
  if [[ "${EXPERIMENT_RESET_MODE}" = "flush" ]]; then
    echo "Flushing Dynamo for isolated ${arm_label} arm..." | tee -a "${DRIVER_LOG}"
    runtime_flush "${RUNTIME_SIGNATURE}" | tee -a "${DRIVER_LOG}"
    echo "KV cache flush complete. Reusing current worker/frontend stack." | tee -a "${DRIVER_LOG}"
    print_flush_ready_banner | tee -a "${DRIVER_LOG}"
    return 0
  fi

  if [[ "${EXPERIMENT_RESET_MODE}" != "restart" ]]; then
    echo "No runtime reset requested before isolated ${arm_label} arm; reusing current worker/frontend stack." | tee -a "${DRIVER_LOG}"
    return 0
  fi

  echo "Restarting Dynamo for isolated ${arm_label} arm..." | tee -a "${DRIVER_LOG}"
  ./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true
  runtime_clear_active

  agentbench_print_model_readiness_active_banner | tee -a "${DRIVER_LOG}"
  echo "Starting Dynamo for ${MODEL} (${arm_label} arm)..." | tee -a "${DRIVER_LOG}"
  local -a env_cmd=(
    env
    -u DYN_RUNTIME_JSON_LOGS
    -u WORKER_SGLANG_DEV_MODE
    -u WORKER_SGLANG_SOURCE_ROOT
    -u SGLANG_TRANSFER_LOG
    -u SGLANG_TRANSFER_LOG_PROFILE
  )
  local -a env_vars=(
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

  if ! "${env_cmd[@]}" "${env_vars[@]}" ./run_dynamo_single_host.sh start >> "${DRIVER_LOG}" 2>&1; then
    precise_report_runtime_start_failure "Speculative prefill microbenchmark (${arm_label} arm)" "${DRIVER_LOG}"
    exit 1
  fi

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
  runtime_mark_active "${RUNTIME_SIGNATURE}"
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
  echo "Turn A output length tokens: ${SPEC_PREFILL_TURN_A_OUTPUT_TOKENS}"
  echo "Turn B output length tokens: ${SPEC_PREFILL_TURN_B_OUTPUT_TOKENS}"
  echo "Warmup wait ms: ${SPEC_PREFILL_WARMUP_WAIT_MS}"
  echo "Request source: ${SPEC_PREFILL_REQUEST_SOURCE}"
  echo "Real Turn B mode: ${SPEC_PREFILL_REAL_TURN_B_MODE}"
  echo "SWE-bench dataset: ${SPEC_PREFILL_SWEBENCH_DATASET}"
  echo "SWE-bench split: ${SPEC_PREFILL_SWEBENCH_SPLIT}"
  echo "SWE-bench turn A index: ${SPEC_PREFILL_TURN_A_INDEX}"
  echo "SWE-bench turn B index: ${SPEC_PREFILL_TURN_B_INDEX}"
  echo "SWE-bench protected offset: ${SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET}"
  echo "Trajectory prompt catalog: ${SPEC_PREFILL_TRAJECTORY_PROMPT_CATALOG}"
  echo "Trajectory turn A task index: ${SPEC_PREFILL_TRAJECTORY_TURN_A_TASK_INDEX}"
  echo "Trajectory turn A stage: ${SPEC_PREFILL_TRAJECTORY_TURN_A_STAGE}"
  echo "Trajectory turn B task index: ${SPEC_PREFILL_TRAJECTORY_TURN_B_TASK_INDEX}"
  echo "Trajectory turn B stage: ${SPEC_PREFILL_TRAJECTORY_TURN_B_STAGE}"
  echo "Trajectory protected offset: ${SPEC_PREFILL_TRAJECTORY_PROTECTED_OFFSET}"
  echo "Trajectory prompt prefix mode: ${SPEC_PREFILL_TRAJECTORY_PROMPT_PREFIX_MODE}"
  echo "Comparison mode: ${SPEC_PREFILL_COMPARISON_MODE}"
  echo "Request-context mode: ${SPEC_PREFILL_REQUEST_CONTEXT_MODE}"
  echo "Driver log: ${DRIVER_LOG}"
  echo "Smoke log: ${SMOKE_LOG}"
  echo "Worker runtime log: ${WORKER_RUNTIME_LOG}"
} | tee -a "${DRIVER_LOG}"

RUNTIME_SIGNATURE="$(build_runtime_signature)"
if [[ "${EXPERIMENT_RESET_MODE}" != "restart" ]] && runtime_reuse_ready "${RUNTIME_SIGNATURE}" >/dev/null 2>&1; then
  echo "Reusing live Dynamo runtime with EXPERIMENT_RESET_MODE=${EXPERIMENT_RESET_MODE}..." | tee -a "${DRIVER_LOG}"
  if [[ "${EXPERIMENT_RESET_MODE}" = "flush" ]]; then
    runtime_flush "${RUNTIME_SIGNATURE}" | tee -a "${DRIVER_LOG}"
    echo "KV cache flush complete. Reusing current worker/frontend stack." | tee -a "${DRIVER_LOG}"
    print_flush_ready_banner | tee -a "${DRIVER_LOG}"
  else
    echo "No runtime reset requested; reusing current worker/frontend stack as-is." | tee -a "${DRIVER_LOG}"
  fi
  if check_precise_specprefill_runtime_ready; then
    agentbench_print_model_readiness_go_banner | tee -a "${DRIVER_LOG}"
    if [[ "${SPEC_PREFILL_ATTRIBUTION_MODE}" = "precise" ]]; then
      precise_print_go_summary "specprefill" "${DRIVER_LOG}"
    fi
    runtime_mark_active "${RUNTIME_SIGNATURE}"
  else
    if [[ "${EXPERIMENT_RESET_MODE}" = "flush" ]]; then
      echo "Reused runtime failed precise preflight during a flush run; stopping instead of restarting Dynamo." | tee -a "${DRIVER_LOG}"
      echo "Start a clean runtime before rerunning, or fix the live runtime instrumentation." | tee -a "${DRIVER_LOG}"
      exit 1
    fi
    echo "Reused runtime failed precise preflight; falling back to a clean Dynamo restart for this run." | tee -a "${DRIVER_LOG}"
    ./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true
    RUNTIME_RESTART_REQUIRED=1
  fi
else
  RUNTIME_RESTART_REQUIRED=1
fi

if [[ "${RUNTIME_RESTART_REQUIRED:-0}" = "1" ]]; then
  echo "Stopping Dynamo..." | tee -a "${DRIVER_LOG}"
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
  if ! "${env_cmd[@]}" "${env_vars[@]}" ./run_dynamo_single_host.sh start >> "${DRIVER_LOG}" 2>&1; then
    precise_report_runtime_start_failure "Speculative prefill microbenchmark" "${DRIVER_LOG}"
    exit 1
  fi

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
  if [[ "${EXPERIMENT_RESET_MODE}" = "flush" ]]; then
    echo "Checking live KV cache flush endpoint before requests..." | tee -a "${DRIVER_LOG}"
    runtime_check_flush "${RUNTIME_SIGNATURE}" | tee -a "${DRIVER_LOG}"
    print_flush_ready_banner | tee -a "${DRIVER_LOG}"
  fi
  runtime_mark_active "${RUNTIME_SIGNATURE}"
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
  --turn-a-output-len-tokens "${SPEC_PREFILL_TURN_A_OUTPUT_TOKENS}"
  --turn-b-output-len-tokens "${SPEC_PREFILL_TURN_B_OUTPUT_TOKENS}"
  --warmup-wait-ms "${SPEC_PREFILL_WARMUP_WAIT_MS}"
  --request-source "${SPEC_PREFILL_REQUEST_SOURCE}"
  --real-turn-b-mode "${SPEC_PREFILL_REAL_TURN_B_MODE}"
  --swebench-dataset "${SPEC_PREFILL_SWEBENCH_DATASET}"
  --swebench-split "${SPEC_PREFILL_SWEBENCH_SPLIT}"
  --swebench-turn-a-index "${SPEC_PREFILL_TURN_A_INDEX}"
  --swebench-turn-b-index "${SPEC_PREFILL_TURN_B_INDEX}"
  --swebench-protected-offset "${SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET}"
  --trajectory-prompt-catalog "${SPEC_PREFILL_TRAJECTORY_PROMPT_CATALOG}"
  --trajectory-turn-a-task-index "${SPEC_PREFILL_TRAJECTORY_TURN_A_TASK_INDEX}"
  --trajectory-turn-a-stage "${SPEC_PREFILL_TRAJECTORY_TURN_A_STAGE}"
  --trajectory-turn-b-task-index "${SPEC_PREFILL_TRAJECTORY_TURN_B_TASK_INDEX}"
  --trajectory-turn-b-stage "${SPEC_PREFILL_TRAJECTORY_TURN_B_STAGE}"
  --trajectory-protected-offset "${SPEC_PREFILL_TRAJECTORY_PROTECTED_OFFSET}"
  --trajectory-prompt-prefix-mode "${SPEC_PREFILL_TRAJECTORY_PROMPT_PREFIX_MODE}"
  --request-timeout "${REQUEST_TIMEOUT}"
  --worker-runtime-log "${WORKER_RUNTIME_LOG}"
)

if [[ "${SPEC_PREFILL_COMPARISON_MODE}" = "same_task_isolated" ]]; then
  CONTROL_WORKER_RUNTIME_LOG="${RUN_DIR}/speculative_prefill_worker_runtime_control.log"
  PROTECTED_WORKER_RUNTIME_LOG="${RUN_DIR}/speculative_prefill_worker_runtime_protected.log"
  rm -f \
    "${RUN_DIR}/speculative_prefill_requests.csv" \
    "${RUN_DIR}/speculative_prefill_matrix.csv" \
    "${RUN_DIR}/speculative_prefill_summary.csv" \
    "${RUN_DIR}/speculative_prefill_summary.md" \
    "${WORKER_RUNTIME_LOG}" \
    "${CONTROL_WORKER_RUNTIME_LOG}" \
    "${PROTECTED_WORKER_RUNTIME_LOG}"

  echo "Running speculative-prefill control arm with isolated cache state..." | tee -a "${DRIVER_LOG}"
  "${probe_cmd[@]}" --arm-filter control 2>&1 | tee -a "${DRIVER_LOG}"
  if capture_worker_runtime_log "${CONTROL_WORKER_RUNTIME_LOG}"; then
    echo "Captured control worker runtime log: ${CONTROL_WORKER_RUNTIME_LOG}" | tee -a "${DRIVER_LOG}"
  fi

  reset_runtime_for_isolated_arm "protected"

  echo "Running speculative-prefill protected arm with isolated cache state..." | tee -a "${DRIVER_LOG}"
  "${probe_cmd[@]}" --arm-filter protected --append-requests 2>&1 | tee -a "${DRIVER_LOG}"
  if capture_worker_runtime_log "${PROTECTED_WORKER_RUNTIME_LOG}"; then
    echo "Captured protected worker runtime log: ${PROTECTED_WORKER_RUNTIME_LOG}" | tee -a "${DRIVER_LOG}"
  fi

  {
    [[ -f "${CONTROL_WORKER_RUNTIME_LOG}" ]] && cat "${CONTROL_WORKER_RUNTIME_LOG}"
    [[ -f "${PROTECTED_WORKER_RUNTIME_LOG}" ]] && cat "${PROTECTED_WORKER_RUNTIME_LOG}"
  } > "${WORKER_RUNTIME_LOG}"
  echo "Combined isolated worker runtime log: ${WORKER_RUNTIME_LOG}" | tee -a "${DRIVER_LOG}"
  warn_if_worker_runtime_missing "${WORKER_RUNTIME_LOG}"
else
  echo "Running speculative-prefill probe..." | tee -a "${DRIVER_LOG}"
  "${probe_cmd[@]}" 2>&1 | tee -a "${DRIVER_LOG}"

  if capture_worker_runtime_log "${WORKER_RUNTIME_LOG}"; then
    echo "Captured worker runtime log: ${WORKER_RUNTIME_LOG}" | tee -a "${DRIVER_LOG}"
    warn_if_worker_runtime_missing "${WORKER_RUNTIME_LOG}"
  fi
fi

echo "Rebuilding report with worker-side evidence..." | tee -a "${DRIVER_LOG}"
"${probe_cmd[@]}" --postprocess-only 2>&1 | tee -a "${DRIVER_LOG}"

if [[ "${STOP_DYNAMO_WHEN_DONE}" = "1" ]]; then
  echo "Stopping Dynamo after speculative-prefill probe..." | tee -a "${DRIVER_LOG}"
  ./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true
  runtime_clear_active
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
