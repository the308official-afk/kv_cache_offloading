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
CACHE_CONTROL_EPHEMERAL_TTL="${CACHE_CONTROL_EPHEMERAL_TTL:-1h}"
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
FRONTEND_IMAGE="${FRONTEND_IMAGE:-local/dynamo-frontend:runtime-json-logs}"
WORKER_IMAGE="${WORKER_IMAGE:-local/dynamo-sglang:runtime-json-logs}"
PYTHON_BIN="${PYTHON_BIN:-}"
CLI_MODELS=("$@")

BATCH_DIR="experiments/reports/retention_probe_batches/${RETENTION_PROBE_ID}"
BATCH_LOG="${BATCH_DIR}/retention_probe_progress.log"
BATCH_PROGRESS="${BATCH_DIR}/retention_probe_progress.csv"
BATCH_SUMMARY="${BATCH_DIR}/retention_probe_batch_summary.md"
BATCH_MATRIX="${BATCH_DIR}/design_space_retention_matrix.csv"
GLOBAL_MATRIX="experiments/reports/design_space_retention_matrix.csv"
mkdir -p "${BATCH_DIR}"

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

require_retention_probe_script_ready() {
  local probe_script="experiments/scripts/retention_probe/run_kv_retention_probe.py"
  if [[ ! -f "${probe_script}" ]]; then
    echo "Retention probe script not found: ${probe_script}" >&2
    exit 1
  fi
  if ! grep -q 'PROMPT_GENERATOR_VERSION = "cache-word-v2"' "${probe_script}"; then
    cat >&2 <<EOF
Retention probe script is stale:
  ${probe_script}

Expected prompt generator version: cache-word-v2.
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
    --kv-tier-mode "${kv_tier_mode}"
    --protected-hint-profile "${hint_profile}"
    --distractor-hint-profile none
    --protected-cache-control-profile "${cache_control_profile}"
    --distractor-cache-control-profile off
    --protected-input-len "${PROTECTED_INPUT_LEN}"
    --distractor-input-len "${DISTRACTOR_INPUT_LEN}"
    --distractor-count "${DISTRACTOR_COUNT}"
    --random-output-len "${RANDOM_OUTPUT_LEN}"
    --seed "${RETENTION_PROBE_SEED}"
    --request-timeout "${REQUEST_TIMEOUT}"
    --max-context-tokens "${MAX_CONTEXT_TOKENS}"
    --context-reserve-tokens "${CONTEXT_RESERVE_TOKENS}"
    --top-level-priority-mode "${RETENTION_TOP_LEVEL_PRIORITY_MODE}"
    --request-context-mode "${RETENTION_REQUEST_CONTEXT_MODE}"
    --matrix-path "${BATCH_MATRIX}"
    --skip-matrix-write
    --cache-event-log experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl
    --worker-runtime-log "${worker_runtime_log}"
  )
  if [[ "${IGNORE_EOS}" = "1" ]]; then
    command+=(--ignore-eos)
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
  return 0
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
    --kv-tier-mode "${kv_tier_mode}"
    --protected-hint-profile "${hint_profile}"
    --distractor-hint-profile none
    --protected-cache-control-profile "${cache_control_profile}"
    --distractor-cache-control-profile off
    --protected-input-len "${PROTECTED_INPUT_LEN}"
    --distractor-input-len "${DISTRACTOR_INPUT_LEN}"
    --distractor-count "${DISTRACTOR_COUNT}"
    --random-output-len "${RANDOM_OUTPUT_LEN}"
    --seed "${RETENTION_PROBE_SEED}"
    --request-timeout "${REQUEST_TIMEOUT}"
    --max-context-tokens "${MAX_CONTEXT_TOKENS}"
    --context-reserve-tokens "${CONTEXT_RESERVE_TOKENS}"
    --top-level-priority-mode "${RETENTION_TOP_LEVEL_PRIORITY_MODE}"
    --request-context-mode "${RETENTION_REQUEST_CONTEXT_MODE}"
    --matrix-path "${BATCH_MATRIX}"
    --skip-matrix-write
    --postprocess-only
    --cache-event-log experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl
    --worker-runtime-log "${worker_runtime_log}"
  )
  if [[ "${IGNORE_EOS}" = "1" ]]; then
    command+=(--ignore-eos)
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

  {
    echo "Stopping Dynamo..."
  } | tee -a "${BATCH_LOG}"
  ./run_dynamo_single_host.sh stop >> "${BATCH_LOG}" 2>&1 || true

  echo "Starting Dynamo for ${model} with KV tier ${kv_tier_mode}..." | tee -a "${BATCH_LOG}"
  local -a env_vars
  local -a env_cmd
  env_vars=(
    "DYNAMO_MODEL_PATH=${model}"
    "DYNAMO_SERVED_MODEL_NAME=${model}"
    "WORKER_EXTRA_ARGS=${worker_extra_args}"
    "DYN_TOOL_CALL_PARSER=hermes"
  )
  env_cmd=(
    env
    -u FRONTEND_IMAGE
    -u WORKER_IMAGE
    -u WORKER_SGLANG_DEV_MODE
    -u WORKER_SGLANG_SOURCE_ROOT
    -u SGLANG_TRANSFER_LOG
    -u SGLANG_TRANSFER_LOG_PROFILE
    -u SGLANG_TRANSFER_LOG_OVERHEAD_TIMING
    -u DYN_RUNTIME_JSON_LOGS
    -u HICACHE_STORAGE_HOST_PATH
    -u HICACHE_STORAGE_CONTAINER_PATH
  )

  if [[ -n "${host_file_storage_path}" ]]; then
    env_vars+=("HICACHE_STORAGE_HOST_PATH=${host_file_storage_path}")
  fi
  if [[ -n "${file_storage_path}" ]]; then
    env_vars+=("HICACHE_STORAGE_CONTAINER_PATH=${file_storage_path}")
  fi

  if [[ "${RETENTION_ATTRIBUTION_MODE}" = "precise" ]]; then
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

  "${env_cmd[@]}" "${env_vars[@]}" ./run_dynamo_single_host.sh start >> "${BATCH_LOG}" 2>&1

  smoke_test_model "${model}" "${smoke_log}"

  if [[ "${MODEL_COOLDOWN_SECS}" -gt 0 ]]; then
    echo "Cooldown: ${MODEL_COOLDOWN_SECS}s" | tee -a "${BATCH_LOG}"
    sleep "${MODEL_COOLDOWN_SECS}"
  fi
}

write_batch_summary() {
  rebuild_batch_matrix
  if [[ -f "${BATCH_MATRIX}" ]]; then
    mkdir -p "$(dirname "${GLOBAL_MATRIX}")"
    cp "${BATCH_MATRIX}" "${GLOBAL_MATRIX}"
  fi

  "${PYTHON_BIN}" - <<'PY' "${BATCH_PROGRESS}" "${BATCH_SUMMARY}" "${BATCH_MATRIX}" "${GLOBAL_MATRIX}" "${RETENTION_PROBE_ID}" "${BATCH_LOG}"
import csv
import sys
from pathlib import Path

progress_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
batch_matrix_path = Path(sys.argv[3])
global_matrix_path = Path(sys.argv[4])
probe_id = sys.argv[5]
log_path = sys.argv[6]

progress_rows = []
if progress_path.exists():
    with progress_path.open(encoding="utf-8", newline="") as handle:
        progress_rows = list(csv.DictReader(handle))

models = sorted({row.get("model", "") for row in progress_rows if row.get("model")})
tiers = sorted({row.get("kv_tier_mode", "") for row in progress_rows if row.get("kv_tier_mode")})
profiles = sorted({row.get("hint_profile", "") for row in progress_rows if row.get("hint_profile")})
cache_profiles = sorted({row.get("cache_control_profile", "") for row in progress_rows if row.get("cache_control_profile")})
ok = sum(1 for row in progress_rows if row.get("status") == "ok")
failed = sum(1 for row in progress_rows if row.get("status") == "failed")

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
    f"- Progress log: `{log_path}`",
    "",
]
summary_path.write_text("\n".join(lines), encoding="utf-8")
PY
}

MODELS_TO_RUN=()
while IFS= read -r MODEL_LINE; do
  MODELS_TO_RUN+=("${MODEL_LINE}")
done < <(load_models)
if [[ "${#MODELS_TO_RUN[@]}" -eq 0 ]]; then
  echo "No models to run." >&2
  exit 1
fi

RESOLVED_SGLANG_ROOT="$(resolve_sglang_root || true)"
require_precise_kv_ready
require_retention_probe_script_ready
init_progress_file
init_matrices

{
  echo "Retention probe ID: ${RETENTION_PROBE_ID}"
  echo "Attribution mode: ${RETENTION_ATTRIBUTION_MODE}"
  echo "Models: ${#MODELS_TO_RUN[@]}"
  printf '  %s\n' "${MODELS_TO_RUN[@]}"
  echo "KV tier modes: ${KV_TIER_MODES}"
  echo "Control hint profile: ${CONTROL_HINT_PROFILE}"
  echo "Protected hint profiles: ${PROTECTED_HINT_PROFILES}"
  echo "Control cache-control profile: ${CONTROL_CACHE_CONTROL_PROFILE}"
  echo "Protected cache-control profiles: ${PROTECTED_CACHE_CONTROL_PROFILES}"
  echo "Distractor count: ${DISTRACTOR_COUNT}"
  echo "Protected input len: ${PROTECTED_INPUT_LEN}"
  echo "Distractor input len: ${DISTRACTOR_INPUT_LEN}"
  echo "Random output len: ${RANDOM_OUTPUT_LEN}"
  echo "Max context tokens: ${MAX_CONTEXT_TOKENS}"
  echo "Context reserve tokens: ${CONTEXT_RESERVE_TOKENS}"
  echo "Top-level priority mode: ${RETENTION_TOP_LEVEL_PRIORITY_MODE}"
  echo "Default cache-control TTL: ${CACHE_CONTROL_EPHEMERAL_TTL}"
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

for MODEL_NAME in "${MODELS_TO_RUN[@]}"; do
  MODEL_SAFE_NAME="$(safe_name "${MODEL_NAME}")"

  for KV_TIER_MODE in ${KV_TIER_MODES}; do
    KV_TIER_SAFE_NAME="$(safe_name "${KV_TIER_MODE}")"
    CURRENT_WORKER_EXTRA_ARGS="$(worker_args_for_kv_tier_mode "${KV_TIER_MODE}")"

    {
      echo "===== Model: ${MODEL_NAME} | KV tier: ${KV_TIER_MODE} ====="
      echo "Worker args: ${CURRENT_WORKER_EXTRA_ARGS}"
      echo "Each hint profile below gets a fresh Dynamo restart so cache state stays isolated."
    } | tee -a "${BATCH_LOG}"

    while IFS=$'\t' read -r ARM_ROLE HINT_PROFILE CACHE_CONTROL_PROFILE; do
      [[ -n "${HINT_PROFILE}" ]] || continue
      HINT_SAFE_NAME="$(safe_name "${HINT_PROFILE}")"
      CACHE_CONTROL_SAFE_NAME="$(safe_name "${CACHE_CONTROL_PROFILE}")"
      CURRENT_FILE_STORAGE_PATH=""
      CURRENT_HOST_FILE_STORAGE_PATH=""
      SMOKE_LOG="${BATCH_DIR}/${MODEL_SAFE_NAME}_${KV_TIER_SAFE_NAME}_${HINT_SAFE_NAME}_${CACHE_CONTROL_SAFE_NAME}_smoke_test.log"
      WORKER_RUNTIME_LOG="${BATCH_DIR}/${MODEL_SAFE_NAME}_${KV_TIER_SAFE_NAME}_${HINT_SAFE_NAME}_${CACHE_CONTROL_SAFE_NAME}_worker_runtime.log"

      if [[ "${KV_TIER_MODE}" = "gpu_cpu_storage" ]]; then
        CURRENT_FILE_STORAGE_PATH="${FILE_STORAGE_PATH}"
        CURRENT_HOST_FILE_STORAGE_PATH="$(storage_host_path_for_mode "${MODEL_SAFE_NAME}" "${KV_TIER_MODE}" "${HINT_SAFE_NAME}_${CACHE_CONTROL_SAFE_NAME}")"
        rm -rf "${CURRENT_HOST_FILE_STORAGE_PATH}" 2>/dev/null || true
        mkdir -p "${CURRENT_HOST_FILE_STORAGE_PATH}" 2>/dev/null || true
      fi

      {
        echo "--- Arm role: ${ARM_ROLE} | Hint profile: ${HINT_PROFILE} | Cache-control profile: ${CACHE_CONTROL_PROFILE} (fresh start) ---"
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

      run_probe \
        "${MODEL_NAME}" \
        "${KV_TIER_MODE}" \
        "${HINT_PROFILE}" \
        "${CACHE_CONTROL_PROFILE}" \
        "${ARM_ROLE}" \
        "${RETENTION_PROBE_ID}_${MODEL_SAFE_NAME}_${KV_TIER_SAFE_NAME}_${RUN_ID_SUFFIX}" \
        "${WORKER_RUNTIME_LOG}"

      sleep 2

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
    done < <(iter_probe_arms)
  done
done

if [[ "${STOP_DYNAMO_WHEN_DONE}" = "1" ]]; then
  echo "Stopping Dynamo after retention probe..." | tee -a "${BATCH_LOG}"
  ./run_dynamo_single_host.sh stop >> "${BATCH_LOG}" 2>&1 || true
fi

write_batch_summary

echo
echo "Retention probe complete."
echo "Batch summary: ${BATCH_SUMMARY}"
echo "Progress CSV:   ${BATCH_PROGRESS}"
echo "Batch matrix:   ${BATCH_MATRIX}"
echo "Latest matrix:  ${GLOBAL_MATRIX}"
