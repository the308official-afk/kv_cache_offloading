#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh
if [[ -f runtime_instrumentation/dynamo_machine_profile.sh ]]; then
  # shellcheck disable=SC1091
  source runtime_instrumentation/dynamo_machine_profile.sh
fi
source runtime_instrumentation/precise_sglang_helper.sh

MODEL_LIST_FILE="${MODEL_LIST_FILE:-agentbench/model_lists/multi_model_batch.txt}"
RETENTION_PROBE_ID="${RETENTION_PROBE_ID:-retention_probe_$(date +%Y%m%d_%H%M%S)}"
RETENTION_ATTRIBUTION_MODE="${RETENTION_ATTRIBUTION_MODE:-precise}"
KV_TIER_MODES="${KV_TIER_MODES:-gpu_only}"
CONTROL_HINT_PROFILE="${CONTROL_HINT_PROFILE:-none}"
PROTECTED_HINT_PROFILES="${PROTECTED_HINT_PROFILES:-high-priority}"
CONTROL_CACHE_CONTROL_PROFILE="${CONTROL_CACHE_CONTROL_PROFILE:-off}"
PROTECTED_CACHE_CONTROL_PROFILES="${PROTECTED_CACHE_CONTROL_PROFILES:-off}"
DISTRACTOR_CACHE_CONTROL_PROFILE="${DISTRACTOR_CACHE_CONTROL_PROFILE:-off}"
CACHE_CONTROL_REQUIRE_HIERARCHICAL_CACHE="${CACHE_CONTROL_REQUIRE_HIERARCHICAL_CACHE:-1}"
PROTECTED_INPUT_LEN="${PROTECTED_INPUT_LEN:-14000}"
DISTRACTOR_INPUT_LEN="${DISTRACTOR_INPUT_LEN:-14000}"
DISTRACTOR_COUNT="${DISTRACTOR_COUNT:-100}"
RANDOM_OUTPUT_LEN="${RANDOM_OUTPUT_LEN:-1}"
RETENTION_PROBE_SEED="${RETENTION_PROBE_SEED:-42}"
IGNORE_EOS="${IGNORE_EOS:-1}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-600}"
MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS:-17146}"
CONTEXT_RESERVE_TOKENS="${CONTEXT_RESERVE_TOKENS:-2048}"
RETENTION_TOP_LEVEL_PRIORITY_MODE="${RETENTION_TOP_LEVEL_PRIORITY_MODE:-auto}"
RETENTION_REQUEST_CONTEXT_MODE="${RETENTION_REQUEST_CONTEXT_MODE:-auto}"
RETENTION_PROMPT_ISOLATION_MODE="${RETENTION_PROMPT_ISOLATION_MODE:-disjoint}"
RETENTION_REQUEST_SOURCE="${RETENTION_REQUEST_SOURCE:-synthetic}"
RETENTION_SWEBENCH_DATASET="${RETENTION_SWEBENCH_DATASET:-ScaleAI/SWE-bench_Pro}"
RETENTION_SWEBENCH_SPLIT="${RETENTION_SWEBENCH_SPLIT:-test}"
RETENTION_SWEBENCH_INDEX="${RETENTION_SWEBENCH_INDEX:-0}"
RETENTION_SWEBENCH_INSTANCE_ID="${RETENTION_SWEBENCH_INSTANCE_ID:-}"
RETENTION_SWEBENCH_DISTRACTOR_START_INDEX="${RETENTION_SWEBENCH_DISTRACTOR_START_INDEX:--1}"
RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE="${RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE:-0}"
RETENTION_TRAJECTORY_PROMPT_CATALOG="${RETENTION_TRAJECTORY_PROMPT_CATALOG:-experiments/reports/latest_swebench_trajectory_prompt_catalog.csv}"
RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX="${RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX:-0}"
RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID="${RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID:-}"
RETENTION_TRAJECTORY_PROTECTED_STAGE="${RETENTION_TRAJECTORY_PROTECTED_STAGE:-patch_generation}"
RETENTION_TRAJECTORY_STAGES="${RETENTION_TRAJECTORY_STAGES:-planning execution patch_generation review}"
RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE="${RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE:-${RETENTION_TRAJECTORY_REPLAY_HEADER_MODE:-task_stage}}"
RETENTION_TRAJECTORY_REPLAY_HEADER_MODE="${RETENTION_TRAJECTORY_REPLAY_HEADER_MODE:-${RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE}}"
RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX="${RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX:--1}"
RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE="${RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE:-0}"
CACHE_CONTROL_EPHEMERAL_TTL="${CACHE_CONTROL_EPHEMERAL_TTL:-1h}"
CACHE_CONTROL_DOC_MODE="${CACHE_CONTROL_DOC_MODE:-1}"
CACHE_CONTROL_STRICT_DOC_MODE="${CACHE_CONTROL_STRICT_DOC_MODE:-0}"
CACHE_CONTROL_FRONTEND_FLAG_MODE="${CACHE_CONTROL_FRONTEND_FLAG_MODE:-auto}"
CACHE_CONTROL_PINNED_RATIO="${CACHE_CONTROL_PINNED_RATIO:-0.1}"
CACHE_CONTROL_HICACHE_WRITE_POLICY="${CACHE_CONTROL_HICACHE_WRITE_POLICY:-write_through}"
SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-full}"
SGLANG_TRANSFER_LOG_OVERHEAD_TIMING="${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING:-0}"
RETENTION_MATRIX_APPEND="${RETENTION_MATRIX_APPEND:-0}"
MEM_FRACTION_STATIC="${MEM_FRACTION_STATIC:-0.7}"
GPU_ONLY_MEM_FRACTION_STATIC="${GPU_ONLY_MEM_FRACTION_STATIC:-${MEM_FRACTION_STATIC}}"
GPU_CPU_MEM_FRACTION_STATIC="${GPU_CPU_MEM_FRACTION_STATIC:-${MEM_FRACTION_STATIC}}"
GPU_CPU_STORAGE_MEM_FRACTION_STATIC="${GPU_CPU_STORAGE_MEM_FRACTION_STATIC:-${MEM_FRACTION_STATIC}}"
HICACHE_RATIO="${HICACHE_RATIO:-1}"
HICACHE_STORAGE_BACKEND="${HICACHE_STORAGE_BACKEND:-file}"
HICACHE_STORAGE_PREFETCH_POLICY="${HICACHE_STORAGE_PREFETCH_POLICY:-wait_complete}"
HICACHE_WRITE_POLICY="${HICACHE_WRITE_POLICY:-}"
HICACHE_EXTRA_ARGS="${HICACHE_EXTRA_ARGS:-}"
FILE_STORAGE_PATH="${FILE_STORAGE_PATH:-/hicache-storage}"
HOST_FILE_STORAGE_PATH="${HOST_FILE_STORAGE_PATH:-/mnt/docker-data/hicache_storage}"
WORKER_BASE_ARGS="${WORKER_BASE_ARGS:---enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority}"
WORKER_EXTRA_ARGS_SUFFIX="${WORKER_EXTRA_ARGS_SUFFIX:-}"
MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES:-${AGENTBENCH_MODEL_SMOKE_RETRIES}}"
MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS:-${AGENTBENCH_MODEL_SMOKE_DELAY_SECS}}"
MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS:-${AGENTBENCH_MODEL_COOLDOWN_SECS}}"
STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE:-0}"
STOP_ON_PROBE_FAILURE="${STOP_ON_PROBE_FAILURE:-0}"
REQUIRE_PRECISE_KV="${REQUIRE_PRECISE_KV:-1}"
AUTO_BUILD_PRECISE_IMAGES="${AUTO_BUILD_PRECISE_IMAGES:-1}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-local/dynamo-frontend:runtime-json-logs}"
WORKER_IMAGE="${WORKER_IMAGE:-local/dynamo-sglang:runtime-json-logs}"
CUSTOM_RUNTIME_IMAGES_MODE="${CUSTOM_RUNTIME_IMAGES_MODE:-0}"
CUSTOM_RUNTIME_SGLANG_ROOT="${CUSTOM_RUNTIME_SGLANG_ROOT:-}"
EXPERIMENT_RESET_MODE="${EXPERIMENT_RESET_MODE:-restart}"
EXPERIMENT_RESET_STATE_FILE="${EXPERIMENT_RESET_STATE_FILE:-experiments/runtime_state/active_runtime_signature.txt}"
PYTHON_BIN="${PYTHON_BIN:-}"
CLI_MODELS=("$@")

BATCH_DIR="experiments/reports/retention_probe_batches/${RETENTION_PROBE_ID}"
BATCH_LOG="${BATCH_DIR}/retention_probe_progress.log"
BATCH_PROGRESS="${BATCH_DIR}/retention_probe_progress.csv"
BATCH_SUMMARY="${BATCH_DIR}/retention_probe_batch_summary.md"
BATCH_MATRIX="${BATCH_DIR}/design_space_retention_matrix.csv"
GLOBAL_MATRIX="experiments/reports/design_space_retention_matrix.csv"
LATEST_PROBE_PROGRESS="experiments/reports/latest_retention_probe_progress.csv"
LATEST_PROBE_MATRIX="experiments/reports/latest_retention_probe_matrix.csv"
LATEST_PROBE_REQUESTS="experiments/reports/latest_retention_probe_requests.csv"
LATEST_PROBE_SUMMARY="experiments/reports/latest_retention_probe_summary.md"
mkdir -p "${BATCH_DIR}"

DEFAULT_ROUTER_EXTRA_ARGS="--no-router-kv-events --router-queue-threshold 4.0"
CACHE_CONTROL_DOC_FRONTEND_FLAG_ACTIVE=0
CACHE_CONTROL_DOC_FRONTEND_FLAG_SUPPORTED=0
CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS="not_checked"
CACHE_CONTROL_DOC_PIN_PATH_STATUS="not_checked"
CACHE_CONTROL_DOC_ROUTER_EXTRA_ARGS="${ROUTER_EXTRA_ARGS:-${DEFAULT_ROUTER_EXTRA_ARGS}}"

usage() {
  cat <<EOF
Usage:
  $0 [model ...]

Examples:
  RETENTION_ATTRIBUTION_MODE=light \\
  DISTRACTOR_COUNT=2 \\
  PROTECTED_INPUT_LEN=500 \\
  DISTRACTOR_INPUT_LEN=500 \\
  $0 Qwen/Qwen2.5-Coder-7B-Instruct

  RETENTION_PROBE_ID="retention_probe_\$(date +%Y%m%d_%H%M%S)" \\
  RETENTION_ATTRIBUTION_MODE=precise \\
  KV_TIER_MODES="gpu_only" \\
  PROTECTED_HINT_PROFILES="high-priority high-reuse" \\
  DISTRACTOR_COUNT=100 \\
  PROTECTED_INPUT_LEN=14000 \\
  DISTRACTOR_INPUT_LEN=14000 \\
  SGLANG_TRANSFER_LOG_PROFILE=full \\
  $0 Qwen/Qwen2.5-Coder-7B-Instruct

Model source priority:
  1. positional model arguments
  2. MODELS='model-a,model-b'
  3. MODEL_LIST_FILE, one model per line
EOF
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

case "${RETENTION_ATTRIBUTION_MODE}" in
  light)
    REQUIRE_PRECISE_KV=0
    ;;
  precise)
    REQUIRE_PRECISE_KV=1
    ;;
  *)
    echo "Unknown RETENTION_ATTRIBUTION_MODE: ${RETENTION_ATTRIBUTION_MODE}" >&2
    echo "Valid values: light precise" >&2
    exit 2
    ;;
esac

cache_control_profile_enabled() {
  local profile="${1:-}"
  local lowered
  lowered="$(printf '%s' "${profile}" | tr '[:upper:]' '[:lower:]')"
  case "${lowered}" in
    ""|none|off|disable|disabled|no-cache-control|no_cache_control)
      return 1
      ;;
    *)
      return 0
      ;;
  esac
}

cache_control_requested() {
  if cache_control_profile_enabled "${CONTROL_CACHE_CONTROL_PROFILE}"; then
    return 0
  fi
  if cache_control_profile_enabled "${DISTRACTOR_CACHE_CONTROL_PROFILE}"; then
    return 0
  fi
  local profile
  for profile in ${PROTECTED_CACHE_CONTROL_PROFILES}; do
    if cache_control_profile_enabled "${profile}"; then
      return 0
    fi
  done
  return 1
}

normalize_kv_tier_modes_for_cache_control() {
  if [[ "${CACHE_CONTROL_REQUIRE_HIERARCHICAL_CACHE}" != "1" ]]; then
    return
  fi
  if ! cache_control_requested; then
    return
  fi

  local changed=0
  local mode
  local -a normalized_modes=()
  local -A seen_modes=()
  for mode in ${KV_TIER_MODES}; do
    if [[ "${mode}" = "gpu_only" ]]; then
      mode="gpu_cpu"
      changed=1
    fi
    if [[ -z "${seen_modes[${mode}]:-}" ]]; then
      normalized_modes+=("${mode}")
      seen_modes["${mode}"]=1
    fi
  done

  if [[ "${#normalized_modes[@]}" -gt 0 ]]; then
    KV_TIER_MODES="${normalized_modes[*]}"
  fi

  if [[ "${changed}" = "1" ]]; then
    cat <<EOF
Cache-control retention note:
  cache_control is enabled for this run, so gpu_only was promoted to gpu_cpu.
  This keeps hierarchical cache on by default for cache-control experiments.
  Set CACHE_CONTROL_REQUIRE_HIERARCHICAL_CACHE=0 to force gpu_only anyway.
EOF
  fi
}

dynamo_frontend_supports_cache_control_flag() {
  local frontend_args="upstream/dynamo/components/src/dynamo/frontend/frontend_args.py"
  local frontend_main="upstream/dynamo/components/src/dynamo/frontend/main.py"
  if grep -q -- "--enable-cache-control" "${frontend_args}" 2>/dev/null; then
    return 0
  fi
  if grep -q "router_enable_cache_control" "${frontend_main}" 2>/dev/null; then
    return 0
  fi
  return 1
}

dynamo_source_has_cache_pin_path() {
  if rg -n "pin_prefix|pin_expiry|router_enable_cache_control" \
    upstream/dynamo/components upstream/dynamo/lib \
    -S >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

configure_cache_control_doc_mode() {
  CACHE_CONTROL_DOC_ROUTER_EXTRA_ARGS="${ROUTER_EXTRA_ARGS:-${DEFAULT_ROUTER_EXTRA_ARGS}}"
  CACHE_CONTROL_DOC_FRONTEND_FLAG_ACTIVE=0
  CACHE_CONTROL_DOC_FRONTEND_FLAG_SUPPORTED=0
  CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS="disabled"
  CACHE_CONTROL_DOC_PIN_PATH_STATUS="not_requested"

  if [[ "${CACHE_CONTROL_DOC_MODE}" != "1" ]]; then
    return
  fi
  if ! cache_control_requested; then
    return
  fi

  if [[ -z "${HICACHE_WRITE_POLICY}" ]]; then
    HICACHE_WRITE_POLICY="${CACHE_CONTROL_HICACHE_WRITE_POLICY}"
  fi
  if [[ -z "${SGLANG_HICACHE_MAX_PINNED_RATIO:-}" ]]; then
    SGLANG_HICACHE_MAX_PINNED_RATIO="${CACHE_CONTROL_PINNED_RATIO}"
  fi

  if dynamo_frontend_supports_cache_control_flag; then
    CACHE_CONTROL_DOC_FRONTEND_FLAG_SUPPORTED=1
    case "${CACHE_CONTROL_FRONTEND_FLAG_MODE}" in
      auto|force|require)
        if [[ " ${CACHE_CONTROL_DOC_ROUTER_EXTRA_ARGS} " != *" --enable-cache-control "* ]]; then
          CACHE_CONTROL_DOC_ROUTER_EXTRA_ARGS="${CACHE_CONTROL_DOC_ROUTER_EXTRA_ARGS} --enable-cache-control"
        fi
        CACHE_CONTROL_DOC_FRONTEND_FLAG_ACTIVE=1
        CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS="enabled"
        ;;
      disable)
        CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS="supported_but_disabled"
        ;;
      *)
        CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS="unknown_mode_${CACHE_CONTROL_FRONTEND_FLAG_MODE}"
        ;;
    esac
  else
    CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS="unsupported_in_pinned_source"
    if [[ "${CACHE_CONTROL_FRONTEND_FLAG_MODE}" = "require" ]]; then
      echo "Cache-control doc mode error: frontend --enable-cache-control flag not found in pinned Dynamo source." >&2
      exit 1
    fi
  fi

  if dynamo_source_has_cache_pin_path; then
    CACHE_CONTROL_DOC_PIN_PATH_STATUS="source_signals_found"
  else
    CACHE_CONTROL_DOC_PIN_PATH_STATUS="source_signals_missing"
    if [[ "${CACHE_CONTROL_STRICT_DOC_MODE}" = "1" ]]; then
      echo "Cache-control doc mode error: no cache pin source signals (pin_prefix / pin_expiry / router_enable_cache_control) found." >&2
      exit 1
    fi
  fi

  cat <<EOF
Cache-control doc mode:
  frontend_flag_mode: ${CACHE_CONTROL_FRONTEND_FLAG_MODE}
  frontend_flag_status: ${CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS}
  hicache_write_policy: ${HICACHE_WRITE_POLICY:-off}
  sglang_hicache_max_pinned_ratio: ${SGLANG_HICACHE_MAX_PINNED_RATIO:-off}
  source_pin_path_status: ${CACHE_CONTROL_DOC_PIN_PATH_STATUS}
EOF
}

choose_python() {
  if [[ -n "${PYTHON_BIN}" ]]; then
    echo "${PYTHON_BIN}"
    return
  fi
  if command -v python3.11 >/dev/null 2>&1; then
    echo "python3.11"
    return
  fi
  echo "python3"
}

PYTHON_BIN="$(choose_python)"
normalize_kv_tier_modes_for_cache_control
configure_cache_control_doc_mode

safe_name() {
  echo "$1" | tr '/:.' '___' | tr -cs 'A-Za-z0-9_-' '_'
}

load_models() {
  if [[ "${#CLI_MODELS[@]}" -gt 0 ]]; then
    printf '%s\n' "${CLI_MODELS[@]}" | tr ',' '\n' | awk '{$1=$1}; NF && $1 !~ /^#/'
    return
  fi

  if [[ -n "${MODELS:-}" ]]; then
    printf '%s\n' "${MODELS}" | tr ',' '\n' | awk '{$1=$1}; NF && $1 !~ /^#/'
    return
  fi

  if [[ ! -f "${MODEL_LIST_FILE}" ]]; then
    cat >&2 <<EOF
Model list file not found:
  ${MODEL_LIST_FILE}

Create it with one model per line, pass MODELS='model-a,model-b', or pass
models directly as positional arguments.
EOF
    exit 1
  fi

  awk '{$1=$1}; NF && $1 !~ /^#/' "${MODEL_LIST_FILE}"
}

require_precise_kv_ready() {
  if [[ "${REQUIRE_PRECISE_KV}" != "1" ]]; then
    return 0
  fi
  prepare_precise_sglang_for_run "precise KV attribution" "" "transfer"
  RESOLVED_SGLANG_ROOT="${PREPARED_SGLANG_ROOT:-$(resolve_precise_sglang_root || true)}"
}

ensure_precise_runtime_images() {
  if [[ "${REQUIRE_PRECISE_KV}" != "1" ]]; then
    return 0
  fi
  echo "Ensuring machine-specific precise runtime images..." | tee -a "${BATCH_LOG}"
  local -a cmd=(
    ./runtime_instrumentation/ensure_precise_runtime_ready.sh
    --machine-profile "${DYNAMO_MACHINE_PROFILE:-}"
  )
  if [[ "${AUTO_BUILD_PRECISE_IMAGES}" = "1" ]]; then
    cmd+=(--build-if-missing)
  fi
  if [[ "${INTERACTIVE_BUILD_PROGRESS:-0}" = "1" && -t 1 ]]; then
    echo "Interactive build progress enabled for precise runtime image checks." | tee -a "${BATCH_LOG}"
    echo "Note: live Docker build output will stream to the terminal instead of being mirrored line-by-line into this log." | tee -a "${BATCH_LOG}"
    AUTO_BUILD_PRECISE_IMAGES="${AUTO_BUILD_PRECISE_IMAGES}" \
      "${cmd[@]}"
  else
    AUTO_BUILD_PRECISE_IMAGES="${AUTO_BUILD_PRECISE_IMAGES}" \
      "${cmd[@]}" | tee -a "${BATCH_LOG}"
  fi
}

check_precise_kv_runtime_ready() {
  local log_file="$1"
  if [[ "${RETENTION_ATTRIBUTION_MODE}" != "precise" ]]; then
    return 0
  fi
  echo "Running precise KV-attribution preflight..." | tee -a "${BATCH_LOG}" "${log_file}"
  LOG_FILE="${log_file}" \
    ./runtime_instrumentation/check_precise_attribution_ready.sh transfer | tee -a "${BATCH_LOG}"
}

require_retention_probe_script_ready() {
  local probe_script="experiments/scripts/retention_probe/run_kv_retention_probe.py"
  if [[ ! -f "${probe_script}" ]]; then
    echo "Retention probe script not found: ${probe_script}" >&2
    exit 1
  fi
  if ! grep -q 'PROMPT_GENERATOR_VERSION = "cache-word-v4"' "${probe_script}"; then
    cat >&2 <<EOF
Retention probe script is stale:
  ${probe_script}

Expected prompt generator version: cache-word-v4.
Sync the latest repo changes to EC2 before running this experiment.
EOF
    exit 1
  fi
}

storage_host_path_for_mode() {
  local model_safe="$1"
  local kv_tier_mode="$2"
  local profile_safe="${3:-shared}"
  echo "${HOST_FILE_STORAGE_PATH%/}/${RETENTION_PROBE_ID}/${model_safe}/${kv_tier_mode}/${profile_safe}"
}

worker_args_for_kv_tier_mode() {
  local kv_tier_mode="$1"
  local mem_fraction="${MEM_FRACTION_STATIC}"

  case "${kv_tier_mode}" in
    gpu_only)
      mem_fraction="${GPU_ONLY_MEM_FRACTION_STATIC}"
      ;;
    gpu_cpu)
      mem_fraction="${GPU_CPU_MEM_FRACTION_STATIC}"
      ;;
    gpu_cpu_storage)
      mem_fraction="${GPU_CPU_STORAGE_MEM_FRACTION_STATIC}"
      ;;
    *)
      echo "Unknown KV_TIER_MODE: ${kv_tier_mode}" >&2
      echo "Valid values: gpu_only gpu_cpu gpu_cpu_storage" >&2
      exit 2
      ;;
  esac

  local args="${WORKER_BASE_ARGS} --mem-fraction-static ${mem_fraction}"

  case "${kv_tier_mode}" in
    gpu_only)
      ;;
    gpu_cpu)
      args="${args} --enable-hierarchical-cache --hicache-ratio ${HICACHE_RATIO}"
      if [[ -n "${HICACHE_WRITE_POLICY}" ]]; then
        args="${args} --hicache-write-policy ${HICACHE_WRITE_POLICY}"
      fi
      ;;
    gpu_cpu_storage)
      args="${args} --enable-hierarchical-cache --hicache-ratio ${HICACHE_RATIO}"
      if [[ -n "${HICACHE_WRITE_POLICY}" ]]; then
        args="${args} --hicache-write-policy ${HICACHE_WRITE_POLICY}"
      fi
      args="${args} --hicache-storage-backend ${HICACHE_STORAGE_BACKEND}"
      args="${args} --hicache-storage-prefetch-policy ${HICACHE_STORAGE_PREFETCH_POLICY}"
      args="${args} --file-storage-path ${FILE_STORAGE_PATH}"
      ;;
  esac

  if [[ -n "${HICACHE_EXTRA_ARGS}" ]]; then
    args="${args} ${HICACHE_EXTRA_ARGS}"
  fi
  if [[ -n "${WORKER_EXTRA_ARGS_SUFFIX}" ]]; then
    args="${args} ${WORKER_EXTRA_ARGS_SUFFIX}"
  fi

  echo "${args}"
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

worker_stopped() {
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  local running
  running="$(docker inspect dynamo-sglang-worker --format '{{.State.Running}}' 2>/dev/null || true)"
  [[ "${running}" = "false" ]]
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
    echo "Smoke test ${attempt}/${MODEL_SMOKE_RETRIES} for ${model}" | tee -a "${BATCH_LOG}"
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
      echo "Smoke test passed for ${model}" | tee -a "${BATCH_LOG}"
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
  echo "Smoke test failed for ${model}. See ${smoke_log}" | tee -a "${BATCH_LOG}" >&2
  return 1
}

init_progress_file() {
  if [[ ! -f "${BATCH_PROGRESS}" ]]; then
    printf '%s\n' "retention_probe_id,retention_attribution_mode,model,kv_tier_mode,hint_profile,cache_control_profile,arm_role,run_id,status,summary_csv,requests_csv" > "${BATCH_PROGRESS}"
  fi
}

init_matrices() {
  if [[ "${RETENTION_MATRIX_APPEND}" = "1" ]]; then
    return
  fi
  rm -f "${BATCH_MATRIX}" "${GLOBAL_MATRIX}"
}

reset_latest_probe_reports() {
  rm -f \
    "${LATEST_PROBE_PROGRESS}" \
    "${LATEST_PROBE_MATRIX}" \
    "${LATEST_PROBE_REQUESTS}" \
    "${LATEST_PROBE_SUMMARY}"
}

append_progress() {
  local model="$1"
  local kv_tier_mode="$2"
  local hint_profile="$3"
  local cache_control_profile="$4"
  local arm_role="$5"
  local run_id="$6"
  local status="$7"
  local summary_csv="experiments/reports/retention_probe/${run_id}/retention_probe_summary.csv"
  local requests_csv="experiments/reports/retention_probe/${run_id}/retention_probe_requests.csv"

  "${PYTHON_BIN}" - <<'PY' "${BATCH_PROGRESS}" "${RETENTION_PROBE_ID}" "${RETENTION_ATTRIBUTION_MODE}" "${model}" "${kv_tier_mode}" "${hint_profile}" "${cache_control_profile}" "${arm_role}" "${run_id}" "${status}" "${summary_csv}" "${requests_csv}"
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
row = {
    "retention_probe_id": sys.argv[2],
    "retention_attribution_mode": sys.argv[3],
    "model": sys.argv[4],
    "kv_tier_mode": sys.argv[5],
    "hint_profile": sys.argv[6],
    "cache_control_profile": sys.argv[7],
    "arm_role": sys.argv[8],
    "run_id": sys.argv[9],
    "status": sys.argv[10],
    "summary_csv": sys.argv[11],
    "requests_csv": sys.argv[12],
}
fields = [
    "retention_probe_id",
    "retention_attribution_mode",
    "model",
    "kv_tier_mode",
    "hint_profile",
    "cache_control_profile",
    "arm_role",
    "run_id",
    "status",
    "summary_csv",
    "requests_csv",
]
with path.open("a", encoding="utf-8", newline="") as handle:
    csv.DictWriter(handle, fieldnames=fields, lineterminator="\n").writerow(row)
PY
}

run_probe() {
  local model="$1"
  local kv_tier_mode="$2"
  local hint_profile="$3"
  local cache_control_profile="$4"
  local arm_role="$5"
  local run_id="$6"
  local worker_runtime_log="$7"
  local -a command

  command=(
    "${PYTHON_BIN}"
    experiments/scripts/retention_probe/run_kv_retention_probe.py
    --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions"
    --model "${model}"
    --run-id "${run_id}"
    --request-source "${RETENTION_REQUEST_SOURCE}"
    --swebench-dataset "${RETENTION_SWEBENCH_DATASET}"
    --swebench-split "${RETENTION_SWEBENCH_SPLIT}"
    --swebench-index "${RETENTION_SWEBENCH_INDEX}"
    --swebench-instance-id "${RETENTION_SWEBENCH_INSTANCE_ID}"
    --swebench-distractor-start-index "${RETENTION_SWEBENCH_DISTRACTOR_START_INDEX}"
    --trajectory-prompt-catalog "${RETENTION_TRAJECTORY_PROMPT_CATALOG}"
    --trajectory-protected-task-index "${RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX}"
    --trajectory-protected-instance-id "${RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID}"
    --trajectory-protected-stage "${RETENTION_TRAJECTORY_PROTECTED_STAGE}"
    --trajectory-stages "${RETENTION_TRAJECTORY_STAGES}"
    --trajectory-prompt-prefix-mode "${RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE}"
    --trajectory-distractor-start-task-index "${RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX}"
    --kv-tier-mode "${kv_tier_mode}"
    --protected-hint-profile "${hint_profile}"
    --distractor-hint-profile none
    --protected-cache-control-profile "${cache_control_profile}"
    --distractor-cache-control-profile "${DISTRACTOR_CACHE_CONTROL_PROFILE}"
    --protected-input-len "${PROTECTED_INPUT_LEN}"
    --distractor-input-len "${DISTRACTOR_INPUT_LEN}"
    --distractor-count "${DISTRACTOR_COUNT}"
    --random-output-len "${RANDOM_OUTPUT_LEN}"
    --seed "${RETENTION_PROBE_SEED}"
    --prompt-isolation-mode "${RETENTION_PROMPT_ISOLATION_MODE}"
    --request-timeout "${REQUEST_TIMEOUT}"
    --max-context-tokens "${MAX_CONTEXT_TOKENS}"
    --context-reserve-tokens "${CONTEXT_RESERVE_TOKENS}"
    --top-level-priority-mode "${RETENTION_TOP_LEVEL_PRIORITY_MODE}"
    --request-context-mode "${RETENTION_REQUEST_CONTEXT_MODE}"
    --cache-control-doc-mode "${CACHE_CONTROL_DOC_MODE}"
    --cache-control-frontend-flag-status "${CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS}"
    --cache-control-pin-path-status "${CACHE_CONTROL_DOC_PIN_PATH_STATUS}"
    --cache-control-pinned-ratio "${SGLANG_HICACHE_MAX_PINNED_RATIO:-}"
    --cache-control-write-policy "${HICACHE_WRITE_POLICY:-}"
    --matrix-path "${BATCH_MATRIX}"
    --skip-matrix-write
    --cache-event-log experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl
    --worker-runtime-log "${worker_runtime_log}"
  )
  if [[ "${IGNORE_EOS}" = "1" ]]; then
    command+=(--ignore-eos)
  fi
  if [[ "${RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE}" = "1" ]]; then
    command+=(--swebench-allow-distractor-reuse)
  fi
  if [[ "${RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE}" = "1" ]]; then
    command+=(--trajectory-allow-distractor-reuse)
  fi

  echo "Running retention probe: model=${model} kv_tier=${kv_tier_mode} hint_profile=${hint_profile} cache_control_profile=${cache_control_profile} arm_role=${arm_role} run_id=${run_id}" | tee -a "${BATCH_LOG}"
  if "${command[@]}" 2>&1 | tee -a "${BATCH_LOG}"; then
    append_progress "${model}" "${kv_tier_mode}" "${hint_profile}" "${cache_control_profile}" "${arm_role}" "${run_id}" "ok"
    return 0
  fi

  append_progress "${model}" "${kv_tier_mode}" "${hint_profile}" "${cache_control_profile}" "${arm_role}" "${run_id}" "failed"
  if [[ "${STOP_ON_PROBE_FAILURE}" = "1" ]]; then
    echo "Probe failed and STOP_ON_PROBE_FAILURE=1." >&2
    exit 1
  fi
  return 1
}

postprocess_probe() {
  local model="$1"
  local kv_tier_mode="$2"
  local hint_profile="$3"
  local cache_control_profile="$4"
  local run_id="$5"
  local worker_runtime_log="$6"
  local -a command

  command=(
    "${PYTHON_BIN}"
    experiments/scripts/retention_probe/run_kv_retention_probe.py
    --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions"
    --model "${model}"
    --run-id "${run_id}"
    --request-source "${RETENTION_REQUEST_SOURCE}"
    --swebench-dataset "${RETENTION_SWEBENCH_DATASET}"
    --swebench-split "${RETENTION_SWEBENCH_SPLIT}"
    --swebench-index "${RETENTION_SWEBENCH_INDEX}"
    --swebench-instance-id "${RETENTION_SWEBENCH_INSTANCE_ID}"
    --swebench-distractor-start-index "${RETENTION_SWEBENCH_DISTRACTOR_START_INDEX}"
    --trajectory-prompt-catalog "${RETENTION_TRAJECTORY_PROMPT_CATALOG}"
    --trajectory-protected-task-index "${RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX}"
    --trajectory-protected-instance-id "${RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID}"
    --trajectory-protected-stage "${RETENTION_TRAJECTORY_PROTECTED_STAGE}"
    --trajectory-stages "${RETENTION_TRAJECTORY_STAGES}"
    --trajectory-prompt-prefix-mode "${RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE}"
    --trajectory-distractor-start-task-index "${RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX}"
    --kv-tier-mode "${kv_tier_mode}"
    --protected-hint-profile "${hint_profile}"
    --distractor-hint-profile none
    --protected-cache-control-profile "${cache_control_profile}"
    --distractor-cache-control-profile "${DISTRACTOR_CACHE_CONTROL_PROFILE}"
    --protected-input-len "${PROTECTED_INPUT_LEN}"
    --distractor-input-len "${DISTRACTOR_INPUT_LEN}"
    --distractor-count "${DISTRACTOR_COUNT}"
    --random-output-len "${RANDOM_OUTPUT_LEN}"
    --seed "${RETENTION_PROBE_SEED}"
    --prompt-isolation-mode "${RETENTION_PROMPT_ISOLATION_MODE}"
    --request-timeout "${REQUEST_TIMEOUT}"
    --max-context-tokens "${MAX_CONTEXT_TOKENS}"
    --context-reserve-tokens "${CONTEXT_RESERVE_TOKENS}"
    --top-level-priority-mode "${RETENTION_TOP_LEVEL_PRIORITY_MODE}"
    --request-context-mode "${RETENTION_REQUEST_CONTEXT_MODE}"
    --cache-control-doc-mode "${CACHE_CONTROL_DOC_MODE}"
    --cache-control-frontend-flag-status "${CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS}"
    --cache-control-pin-path-status "${CACHE_CONTROL_DOC_PIN_PATH_STATUS}"
    --cache-control-pinned-ratio "${SGLANG_HICACHE_MAX_PINNED_RATIO:-}"
    --cache-control-write-policy "${HICACHE_WRITE_POLICY:-}"
    --matrix-path "${BATCH_MATRIX}"
    --skip-matrix-write
    --postprocess-only
    --cache-event-log experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl
    --worker-runtime-log "${worker_runtime_log}"
  )
  if [[ "${IGNORE_EOS}" = "1" ]]; then
    command+=(--ignore-eos)
  fi
  if [[ "${RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE}" = "1" ]]; then
    command+=(--swebench-allow-distractor-reuse)
  fi
  if [[ "${RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE}" = "1" ]]; then
    command+=(--trajectory-allow-distractor-reuse)
  fi

  echo "Postprocessing retention probe with worker runtime log: ${worker_runtime_log}" | tee -a "${BATCH_LOG}"
  "${command[@]}" 2>&1 | tee -a "${BATCH_LOG}"
}

capture_worker_runtime_log() {
  local out_path="$1"
  mkdir -p "$(dirname "${out_path}")"
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  docker logs dynamo-sglang-worker > "${out_path}" 2>&1
}

capture_frontend_runtime_log() {
  local out_path="$1"
  mkdir -p "$(dirname "${out_path}")"
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  docker logs dynamo-frontend > "${out_path}" 2>&1
}

rebuild_batch_matrix() {
  "${PYTHON_BIN}" - <<'PY' "${BATCH_PROGRESS}" "${BATCH_MATRIX}"
import csv
import sys
from pathlib import Path

progress_path = Path(sys.argv[1])
matrix_path = Path(sys.argv[2])
if not progress_path.exists():
    raise SystemExit(0)

rows = []
fieldnames = None
with progress_path.open(encoding="utf-8", newline="") as handle:
    progress_rows = list(csv.DictReader(handle))

for progress_row in progress_rows:
    summary_path = Path(progress_row.get("summary_csv", ""))
    if not summary_path.exists():
        continue
    with summary_path.open(encoding="utf-8", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    if not summary_rows:
        continue
    if fieldnames is None:
        fieldnames = list(summary_rows[0].keys())
    rows.extend(summary_rows)

if fieldnames is None:
    matrix_path.unlink(missing_ok=True)
    raise SystemExit(0)

matrix_path.parent.mkdir(parents=True, exist_ok=True)
with matrix_path.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
PY
}

build_runtime_signature() {
  local model="$1"
  local kv_tier_mode="$2"
  local worker_extra_args="$3"
  local sglang_root="$4"
  local host_file_storage_path="$5"
  local file_storage_path="$6"
  printf '%s\n' \
    "model=${model}" \
    "attribution_mode=${RETENTION_ATTRIBUTION_MODE}" \
    "frontend_image=${FRONTEND_IMAGE}" \
    "worker_image=${WORKER_IMAGE}" \
    "worker_extra_args=${worker_extra_args}" \
    "router_extra_args=${CACHE_CONTROL_DOC_ROUTER_EXTRA_ARGS}" \
    "sglang_root=${sglang_root}" \
    "host_file_storage_path=${host_file_storage_path}" \
    "file_storage_path=${file_storage_path}" \
    "custom_runtime_images_mode=${CUSTOM_RUNTIME_IMAGES_MODE}" \
    "custom_runtime_sglang_root=${CUSTOM_RUNTIME_SGLANG_ROOT}" \
    "runtime_stack=standard" | \
    shasum -a 256 | awk '{print $1}'
}

runtime_reset_env_cmd() {
  local signature="$1"
  shift
  env \
    FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}" \
    EXPERIMENT_RUNTIME_SIGNATURE="${signature}" \
    EXPERIMENT_RESET_STATE_FILE="${EXPERIMENT_RESET_STATE_FILE}" \
    EXPERIMENT_EXPECTED_MODEL="${MODEL_NAME}" \
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

iter_probe_arms() {
  printf 'control\t%s\t%s\n' "${CONTROL_HINT_PROFILE}" "${CONTROL_CACHE_CONTROL_PROFILE}"
  for hint_profile in ${PROTECTED_HINT_PROFILES}; do
    for cache_control_profile in ${PROTECTED_CACHE_CONTROL_PROFILES}; do
      if [[ "${hint_profile}" = "${CONTROL_HINT_PROFILE}" && "${cache_control_profile}" = "${CONTROL_CACHE_CONTROL_PROFILE}" ]]; then
        continue
      fi
      printf 'protected\t%s\t%s\n' "${hint_profile}" "${cache_control_profile}"
    done
  done
}

start_dynamo_for_profile() {
  local model="$1"
  local kv_tier_mode="$2"
  local worker_extra_args="$3"
  local sglang_root="$4"
  local host_file_storage_path="$5"
  local file_storage_path="$6"
  local smoke_log="$7"
  local runtime_signature

  runtime_signature="$(build_runtime_signature \
    "${model}" \
    "${kv_tier_mode}" \
    "${worker_extra_args}" \
    "${sglang_root}" \
    "${host_file_storage_path}" \
    "${file_storage_path}")"

  if [[ "${EXPERIMENT_RESET_MODE}" != "restart" ]] && runtime_reuse_ready "${runtime_signature}" >/dev/null 2>&1; then
    echo "Reusing live Dynamo runtime with EXPERIMENT_RESET_MODE=${EXPERIMENT_RESET_MODE}..." | tee -a "${BATCH_LOG}"
    if [[ "${EXPERIMENT_RESET_MODE}" = "flush" ]]; then
      runtime_flush "${runtime_signature}" | tee -a "${BATCH_LOG}"
      echo "KV cache flush complete. Reusing current worker/frontend stack." | tee -a "${BATCH_LOG}"
      print_flush_ready_banner | tee -a "${BATCH_LOG}"
    else
      echo "No runtime reset requested; reusing current worker/frontend stack as-is." | tee -a "${BATCH_LOG}"
    fi
    if check_precise_kv_runtime_ready "${smoke_log}"; then
      agentbench_print_model_readiness_go_banner | tee -a "${BATCH_LOG}"
      if [[ "${RETENTION_ATTRIBUTION_MODE}" = "precise" ]]; then
        precise_print_go_summary "transfer" "${BATCH_LOG}"
      fi
      runtime_mark_active "${runtime_signature}"
      return 0
    fi
    echo "Reused runtime failed precise preflight; falling back to a clean Dynamo restart for this run." | tee -a "${BATCH_LOG}"
    ./run_dynamo_single_host.sh stop >> "${BATCH_LOG}" 2>&1 || true
  fi

  {
    echo "Stopping Dynamo..."
  } | tee -a "${BATCH_LOG}"
  ./run_dynamo_single_host.sh stop >> "${BATCH_LOG}" 2>&1 || true

  agentbench_print_model_readiness_active_banner | tee -a "${BATCH_LOG}"
  echo "Starting Dynamo for ${model} with KV tier ${kv_tier_mode}..." | tee -a "${BATCH_LOG}"
  local -a env_vars
  local -a env_cmd
  local use_custom_runtime_stack=0
  env_vars=(
    "DYNAMO_MODEL_PATH=${model}"
    "DYNAMO_SERVED_MODEL_NAME=${model}"
    "WORKER_EXTRA_ARGS=${worker_extra_args}"
    "DYN_TOOL_CALL_PARSER=hermes"
    "ROUTER_EXTRA_ARGS=${CACHE_CONTROL_DOC_ROUTER_EXTRA_ARGS}"
    "SGLANG_HICACHE_MAX_PINNED_RATIO=${SGLANG_HICACHE_MAX_PINNED_RATIO:-}"
  )
  env_cmd=(env)

  if [[ "${CUSTOM_RUNTIME_IMAGES_MODE}" = "1" ]]; then
    use_custom_runtime_stack=1
  fi

  if [[ -n "${host_file_storage_path}" ]]; then
    env_vars+=("HICACHE_STORAGE_HOST_PATH=${host_file_storage_path}")
  fi
  if [[ -n "${file_storage_path}" ]]; then
    env_vars+=("HICACHE_STORAGE_CONTAINER_PATH=${file_storage_path}")
  fi

  if [[ "${RETENTION_ATTRIBUTION_MODE}" = "precise" ]]; then
    use_custom_runtime_stack=1
    env_vars+=(
      "WORKER_SGLANG_DEV_MODE=1"
      "WORKER_SGLANG_SOURCE_ROOT=${sglang_root}"
      "SGLANG_TRANSFER_LOG=1"
      "SGLANG_TRANSFER_LOG_PROFILE=${SGLANG_TRANSFER_LOG_PROFILE}"
      "SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING}"
      "DYN_RUNTIME_JSON_LOGS=1"
      "FRONTEND_IMAGE=${FRONTEND_IMAGE}"
      "WORKER_IMAGE=${WORKER_IMAGE}"
    )
  fi

  if [[ "${use_custom_runtime_stack}" != "1" ]]; then
    env_cmd+=(
      -u FRONTEND_IMAGE
      -u WORKER_IMAGE
      -u WORKER_SGLANG_DEV_MODE
      -u WORKER_SGLANG_SOURCE_ROOT
    )
  else
    env_vars+=(
      "FRONTEND_IMAGE=${FRONTEND_IMAGE}"
      "WORKER_IMAGE=${WORKER_IMAGE}"
    )
    if [[ "${RETENTION_ATTRIBUTION_MODE}" != "precise" && -n "${CUSTOM_RUNTIME_SGLANG_ROOT}" ]]; then
      env_vars+=(
        "WORKER_SGLANG_DEV_MODE=1"
        "WORKER_SGLANG_SOURCE_ROOT=${CUSTOM_RUNTIME_SGLANG_ROOT}"
      )
    fi
  fi

  env_cmd+=(
    -u SGLANG_TRANSFER_LOG
    -u SGLANG_TRANSFER_LOG_PROFILE
    -u SGLANG_TRANSFER_LOG_OVERHEAD_TIMING
    -u DYN_RUNTIME_JSON_LOGS
    -u HICACHE_STORAGE_HOST_PATH
    -u HICACHE_STORAGE_CONTAINER_PATH
  )

  if ! "${env_cmd[@]}" "${env_vars[@]}" ./run_dynamo_single_host.sh start >> "${BATCH_LOG}" 2>&1; then
    precise_report_runtime_start_failure "KV retention probe" "${BATCH_LOG}"
    exit 1
  fi

  smoke_test_model "${model}" "${smoke_log}"
  check_precise_kv_runtime_ready "${smoke_log}"
  agentbench_print_model_readiness_go_banner | tee -a "${BATCH_LOG}"
  if [[ "${RETENTION_ATTRIBUTION_MODE}" = "precise" ]]; then
    precise_print_go_summary "transfer" "${BATCH_LOG}"
  fi

  if [[ "${MODEL_COOLDOWN_SECS}" -gt 0 ]]; then
    echo "Cooldown: ${MODEL_COOLDOWN_SECS}s" | tee -a "${BATCH_LOG}"
    sleep "${MODEL_COOLDOWN_SECS}"
  fi

  if [[ "${EXPERIMENT_RESET_MODE}" = "flush" ]]; then
    echo "Checking live KV cache flush endpoint before requests..." | tee -a "${BATCH_LOG}"
    runtime_check_flush "${runtime_signature}" | tee -a "${BATCH_LOG}"
    print_flush_ready_banner | tee -a "${BATCH_LOG}"
  fi

  runtime_mark_active "${runtime_signature}"
}

write_batch_summary() {
  rebuild_batch_matrix
  cp "${BATCH_PROGRESS}" "${LATEST_PROBE_PROGRESS}"

  "${PYTHON_BIN}" - <<'PY' "${BATCH_PROGRESS}" "${BATCH_SUMMARY}" "${BATCH_MATRIX}" "${GLOBAL_MATRIX}" "${LATEST_PROBE_MATRIX}" "${RETENTION_PROBE_ID}" "${BATCH_LOG}" "${LATEST_PROBE_REQUESTS}"
import csv
import sys
from pathlib import Path

progress_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
batch_matrix_path = Path(sys.argv[3])
global_matrix_path = Path(sys.argv[4])
latest_matrix_path = Path(sys.argv[5])
probe_id = sys.argv[6]
log_path = sys.argv[7]
latest_requests_path = Path(sys.argv[8])

progress_rows = []
if progress_path.exists():
    with progress_path.open(encoding="utf-8", newline="") as handle:
        progress_rows = list(csv.DictReader(handle))

public_rows = []
public_fields = [
    "status",
    "probe_id",
    "model",
    "kv_tier",
    "arm",
    "hint_profile",
    "protected_cache",
    "distractors",
    "first_status",
    "replay_status",
    "first_ms",
    "replay_ms",
    "replay_delta_ms",
    "replay_speedup",
    "kv_cap",
    "ctx_len",
    "a_tokens",
    "d1_tokens",
    "kv_left_after_a",
    "replay_cached",
    "replay_reuse",
    "survived",
    "survival_source",
    "req_prio_status",
    "req_prio_values",
    "worker_prio_status",
    "worker_prio_values",
    "replay_evicts",
    "replay_evict_cache",
    "replay_evict_cache_match",
    "replay_evict_hint_match",
    "replay_evict_status",
    "effect_status",
]

models = sorted({row.get("model", "") for row in progress_rows if row.get("model")})
tiers = sorted({row.get("kv_tier_mode", "") for row in progress_rows if row.get("kv_tier_mode")})
profiles = sorted({row.get("hint_profile", "") for row in progress_rows if row.get("hint_profile")})
cache_profiles = sorted({row.get("cache_control_profile", "") for row in progress_rows if row.get("cache_control_profile")})
ok = sum(1 for row in progress_rows if row.get("status") == "ok")
failed = sum(1 for row in progress_rows if row.get("status") == "failed")

request_rows = []
request_fieldnames = None
for progress_row in progress_rows:
    requests_path_str = progress_row.get("requests_csv", "")
    if not requests_path_str:
        continue
    requests_path = Path(requests_path_str)
    if not requests_path.exists():
        continue
    with requests_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if rows and request_fieldnames is None:
        request_fieldnames = list(rows[0].keys())
    request_rows.extend(rows)

if request_fieldnames:
    latest_requests_path.parent.mkdir(parents=True, exist_ok=True)
    with latest_requests_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=request_fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(request_rows)
else:
    latest_requests_path.unlink(missing_ok=True)

for progress_row in progress_rows:
    summary_csv = Path(progress_row.get("summary_csv", ""))
    public_summary = summary_csv.with_name("retention_probe_public_summary.csv")
    if not public_summary.exists():
        continue
    with public_summary.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        continue
    row = dict(rows[0])
    row["status"] = progress_row.get("status", "")
    row["probe_id"] = progress_row.get("retention_probe_id", "")
    row["arm"] = progress_row.get("arm_role", "")
    public_rows.append(row)

if public_rows:
    global_matrix_path.parent.mkdir(parents=True, exist_ok=True)
    with global_matrix_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=public_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(public_rows)
    latest_matrix_path.parent.mkdir(parents=True, exist_ok=True)
    with latest_matrix_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=public_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(public_rows)
else:
    global_matrix_path.unlink(missing_ok=True)
    latest_matrix_path.unlink(missing_ok=True)

lines = [
    f"# KV Retention Probe Batch: {probe_id}",
    "",
    "## Scope",
    "",
    f"- Attribution mode: {progress_rows[0].get('retention_attribution_mode', 'unknown') if progress_rows else 'unknown'}",
    f"- Models: {', '.join(models) if models else 'none'}",
    f"- KV tier modes: {', '.join(tiers) if tiers else 'none'}",
    f"- Hint profiles: {', '.join(profiles) if profiles else 'none'}",
    f"- Cache-control profiles: {', '.join(cache_profiles) if cache_profiles else 'none'}",
    "",
    "## Results",
    "",
    f"- Probe runs: {len(progress_rows)}",
    f"- Successful: {ok}",
    f"- Failed: {failed}",
    "",
    "## Files",
    "",
    f"- Progress CSV: `{progress_path}`",
    f"- Batch retention matrix: `{batch_matrix_path}`",
    f"- Latest/current retention matrix: `{global_matrix_path}`",
    f"- Latest probe progress: `experiments/reports/latest_retention_probe_progress.csv`",
    f"- Latest probe matrix: `experiments/reports/latest_retention_probe_matrix.csv`",
    f"- Latest probe requests: `experiments/reports/latest_retention_probe_requests.csv`",
    f"- Progress log: `{log_path}`",
    "",
]
summary_path.write_text("\n".join(lines), encoding="utf-8")
PY
  cp "${BATCH_SUMMARY}" "${LATEST_PROBE_SUMMARY}"
}

MODELS_TO_RUN=()
while IFS= read -r MODEL_LINE; do
  MODELS_TO_RUN+=("${MODEL_LINE}")
done < <(load_models)
if [[ "${#MODELS_TO_RUN[@]}" -eq 0 ]]; then
  echo "No models to run." >&2
  exit 1
fi

RESOLVED_SGLANG_ROOT="$(resolve_precise_sglang_root || true)"
ensure_precise_runtime_images
require_precise_kv_ready
if [[ "${RETENTION_ATTRIBUTION_MODE}" = "precise" ]]; then
  precise_print_local_ready_summary "transfer" "${BATCH_LOG}"
fi
require_retention_probe_script_ready
init_progress_file
init_matrices
reset_latest_probe_reports

{
  echo "Retention probe ID: ${RETENTION_PROBE_ID}"
  echo "Machine profile: ${DYNAMO_MACHINE_PROFILE:-<unset>}"
  echo "Frontend image: ${FRONTEND_IMAGE}"
  echo "Worker image: ${WORKER_IMAGE}"
  echo "Auto-build precise images: ${AUTO_BUILD_PRECISE_IMAGES}"
  echo "Attribution mode: ${RETENTION_ATTRIBUTION_MODE}"
  echo "Models: ${#MODELS_TO_RUN[@]}"
  printf '  %s\n' "${MODELS_TO_RUN[@]}"
  echo "KV tier modes: ${KV_TIER_MODES}"
  echo "Control hint profile: ${CONTROL_HINT_PROFILE}"
  echo "Protected hint profiles: ${PROTECTED_HINT_PROFILES}"
  echo "Control cache-control profile: ${CONTROL_CACHE_CONTROL_PROFILE}"
  echo "Protected cache-control profiles: ${PROTECTED_CACHE_CONTROL_PROFILES}"
  echo "Distractor cache-control profile: ${DISTRACTOR_CACHE_CONTROL_PROFILE}"
  echo "Request source: ${RETENTION_REQUEST_SOURCE}"
  if [[ "${RETENTION_REQUEST_SOURCE}" = "swebench_dataset" ]]; then
    echo "SWE-bench dataset: ${RETENTION_SWEBENCH_DATASET}"
    echo "SWE-bench split: ${RETENTION_SWEBENCH_SPLIT}"
    echo "SWE-bench protected index: ${RETENTION_SWEBENCH_INDEX}"
    echo "SWE-bench protected instance_id: ${RETENTION_SWEBENCH_INSTANCE_ID:-auto}"
    echo "SWE-bench distractor start index: ${RETENTION_SWEBENCH_DISTRACTOR_START_INDEX}"
    echo "SWE-bench distractor reuse allowed: ${RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE}"
  elif [[ "${RETENTION_REQUEST_SOURCE}" = "swebench_trajectory" ]]; then
    echo "SWE-bench trajectory catalog: ${RETENTION_TRAJECTORY_PROMPT_CATALOG}"
    echo "SWE-bench trajectory protected task index: ${RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX}"
    echo "SWE-bench trajectory protected instance_id: ${RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID:-auto}"
    echo "SWE-bench trajectory protected stage: ${RETENTION_TRAJECTORY_PROTECTED_STAGE}"
    echo "SWE-bench trajectory distractor stages: ${RETENTION_TRAJECTORY_STAGES}"
    echo "SWE-bench trajectory prompt prefix mode: ${RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE}"
    echo "SWE-bench trajectory distractor start task index: ${RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX}"
    echo "SWE-bench trajectory distractor reuse allowed: ${RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE}"
  fi
  echo "Distractor count: ${DISTRACTOR_COUNT}"
  echo "Protected input len: ${PROTECTED_INPUT_LEN}"
  echo "Distractor input len: ${DISTRACTOR_INPUT_LEN}"
  echo "Retention prompt isolation mode: ${RETENTION_PROMPT_ISOLATION_MODE}"
  echo "Random output len: ${RANDOM_OUTPUT_LEN}"
  echo "Max context tokens: ${MAX_CONTEXT_TOKENS}"
  echo "Context reserve tokens: ${CONTEXT_RESERVE_TOKENS}"
  echo "Top-level priority mode: ${RETENTION_TOP_LEVEL_PRIORITY_MODE}"
  echo "Default cache-control TTL: ${CACHE_CONTROL_EPHEMERAL_TTL}"
  echo "Cache-control doc mode: ${CACHE_CONTROL_DOC_MODE}"
  echo "Cache-control frontend flag status: ${CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS}"
  echo "Cache-control source pin-path status: ${CACHE_CONTROL_DOC_PIN_PATH_STATUS}"
  echo "Cache-control pinned ratio: ${SGLANG_HICACHE_MAX_PINNED_RATIO:-off}"
  echo "HiCache write policy: ${HICACHE_WRITE_POLICY:-off}"
  echo "Mem fraction static: ${MEM_FRACTION_STATIC}"
  echo "GPU-only mem fraction static: ${GPU_ONLY_MEM_FRACTION_STATIC}"
  if [[ "${RETENTION_ATTRIBUTION_MODE}" = "precise" ]]; then
    echo "SGLang transfer log profile: ${SGLANG_TRANSFER_LOG_PROFILE}"
    echo "SGLang root: ${RESOLVED_SGLANG_ROOT:-<unset>}"
  else
    echo "SGLang transfer log profile: disabled in light mode"
    echo "SGLang root: not required in light mode"
  fi
  echo "Output dir: ${BATCH_DIR}"
  echo
} | tee -a "${BATCH_LOG}"

if cache_control_requested; then
  cat <<EOF | tee -a "${BATCH_LOG}"
Note:
  cache_control is enabled in this run.
  Doc-aligned prerequisites now attempt to turn on:
    - hierarchical cache
    - HiCache write-through
    - nonzero HiCache pinned ratio
    - frontend --enable-cache-control when supported by the pinned source

  Current source checks for this run:
    - frontend flag status: ${CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS}
    - source pin path status: ${CACHE_CONTROL_DOC_PIN_PATH_STATUS}

  Treat this run as:
    - metadata receipt / forwarding proof
    - worker-side observability proof
    - empirical behavior check
  and only treat it as confirmed TTL pinning proof if the runtime under test
  also exposes a real cache-pin execution path.

EOF
fi

for MODEL_NAME in "${MODELS_TO_RUN[@]}"; do
  MODEL_SAFE_NAME="$(safe_name "${MODEL_NAME}")"

  for KV_TIER_MODE in ${KV_TIER_MODES}; do
    KV_TIER_SAFE_NAME="$(safe_name "${KV_TIER_MODE}")"
    CURRENT_WORKER_EXTRA_ARGS="$(worker_args_for_kv_tier_mode "${KV_TIER_MODE}")"

    {
      echo "===== Model: ${MODEL_NAME} | KV tier: ${KV_TIER_MODE} ====="
      echo "Worker args: ${CURRENT_WORKER_EXTRA_ARGS}"
      echo "Each hint profile below gets an isolated runtime reset so cache state stays isolated."
    } | tee -a "${BATCH_LOG}"

    while IFS=$'\t' read -r ARM_ROLE HINT_PROFILE CACHE_CONTROL_PROFILE; do
      [[ -n "${HINT_PROFILE}" ]] || continue
      HINT_SAFE_NAME="$(safe_name "${HINT_PROFILE}")"
      CACHE_CONTROL_SAFE_NAME="$(safe_name "${CACHE_CONTROL_PROFILE}")"
      CURRENT_FILE_STORAGE_PATH=""
      CURRENT_HOST_FILE_STORAGE_PATH=""
      SMOKE_LOG="${BATCH_DIR}/${MODEL_SAFE_NAME}_${KV_TIER_SAFE_NAME}_${HINT_SAFE_NAME}_${CACHE_CONTROL_SAFE_NAME}_smoke_test.log"
      WORKER_RUNTIME_LOG="${BATCH_DIR}/${MODEL_SAFE_NAME}_${KV_TIER_SAFE_NAME}_${HINT_SAFE_NAME}_${CACHE_CONTROL_SAFE_NAME}_worker_runtime.log"
      FRONTEND_RUNTIME_LOG="${BATCH_DIR}/${MODEL_SAFE_NAME}_${KV_TIER_SAFE_NAME}_${HINT_SAFE_NAME}_${CACHE_CONTROL_SAFE_NAME}_frontend_runtime.log"

      if [[ "${KV_TIER_MODE}" = "gpu_cpu_storage" ]]; then
        CURRENT_FILE_STORAGE_PATH="${FILE_STORAGE_PATH}"
        CURRENT_HOST_FILE_STORAGE_PATH="$(storage_host_path_for_mode "${MODEL_SAFE_NAME}" "${KV_TIER_MODE}" "${HINT_SAFE_NAME}_${CACHE_CONTROL_SAFE_NAME}")"
        rm -rf "${CURRENT_HOST_FILE_STORAGE_PATH}" 2>/dev/null || true
        mkdir -p "${CURRENT_HOST_FILE_STORAGE_PATH}" 2>/dev/null || true
      fi

      {
        echo "--- Arm role: ${ARM_ROLE} | Hint profile: ${HINT_PROFILE} | Cache-control profile: ${CACHE_CONTROL_PROFILE} (reset mode: ${EXPERIMENT_RESET_MODE}) ---"
      } | tee -a "${BATCH_LOG}"

      start_dynamo_for_profile \
        "${MODEL_NAME}" \
        "${KV_TIER_MODE}" \
        "${CURRENT_WORKER_EXTRA_ARGS}" \
        "${RESOLVED_SGLANG_ROOT}" \
        "${CURRENT_HOST_FILE_STORAGE_PATH}" \
        "${CURRENT_FILE_STORAGE_PATH}" \
        "${SMOKE_LOG}"

      RUN_ID_SUFFIX="${HINT_SAFE_NAME}_${CACHE_CONTROL_SAFE_NAME}"
      if [[ "${ARM_ROLE}" = "control" ]]; then
        RUN_ID_SUFFIX="${HINT_SAFE_NAME}_${CACHE_CONTROL_SAFE_NAME}_control"
      fi

      if run_probe \
        "${MODEL_NAME}" \
        "${KV_TIER_MODE}" \
        "${HINT_PROFILE}" \
        "${CACHE_CONTROL_PROFILE}" \
        "${ARM_ROLE}" \
        "${RETENTION_PROBE_ID}_${MODEL_SAFE_NAME}_${KV_TIER_SAFE_NAME}_${RUN_ID_SUFFIX}" \
        "${WORKER_RUNTIME_LOG}"; then
        sleep 2

        capture_frontend_runtime_log "${FRONTEND_RUNTIME_LOG}" || \
          echo "Warning: could not capture frontend runtime log for ${HINT_PROFILE}" | tee -a "${BATCH_LOG}"

        if capture_worker_runtime_log "${WORKER_RUNTIME_LOG}"; then
          postprocess_probe \
            "${MODEL_NAME}" \
            "${KV_TIER_MODE}" \
            "${HINT_PROFILE}" \
            "${CACHE_CONTROL_PROFILE}" \
            "${RETENTION_PROBE_ID}_${MODEL_SAFE_NAME}_${KV_TIER_SAFE_NAME}_${RUN_ID_SUFFIX}" \
            "${WORKER_RUNTIME_LOG}"
        else
          echo "Warning: could not capture worker runtime log for ${HINT_PROFILE}" | tee -a "${BATCH_LOG}"
        fi
      else
        echo "Skipping postprocess for failed probe arm: model=${MODEL_NAME} kv_tier=${KV_TIER_MODE} hint_profile=${HINT_PROFILE} cache_control_profile=${CACHE_CONTROL_PROFILE} arm_role=${ARM_ROLE}" | tee -a "${BATCH_LOG}"
      fi
    done < <(iter_probe_arms)
  done
done

if [[ "${STOP_DYNAMO_WHEN_DONE}" = "1" ]]; then
  echo "Stopping Dynamo after retention probe..." | tee -a "${BATCH_LOG}"
  ./run_dynamo_single_host.sh stop >> "${BATCH_LOG}" 2>&1 || true
  runtime_clear_active
fi

write_batch_summary

echo
echo "Retention probe complete."
echo "Batch summary: ${BATCH_SUMMARY}"
echo "Progress CSV:   ${BATCH_PROGRESS}"
echo "Batch matrix:   ${BATCH_MATRIX}"
echo "Latest matrix:  ${GLOBAL_MATRIX}"
echo "Latest probe progress: ${LATEST_PROBE_PROGRESS}"
echo "Latest probe matrix:   ${LATEST_PROBE_MATRIX}"
echo "Latest probe requests: ${LATEST_PROBE_REQUESTS}"
echo "Latest probe summary:  ${LATEST_PROBE_SUMMARY}"
