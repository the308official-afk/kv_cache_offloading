#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ -f agentbench/model_config.sh ]]; then
  # shellcheck disable=SC1091
  source agentbench/model_config.sh
fi

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
TIMER_PYTHON_BIN="${TIMER_PYTHON_BIN:-python3}"
MODEL="${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct}}}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions}"
APP_VARIANT="${APP_VARIANT:-upstream_deploy_coding_agent}"
DATASET="${DATASET:-ScaleAI/SWE-bench_Pro}"
SPLIT="${SPLIT:-test}"
INDEX="${INDEX:-0}"
HINT_PROVIDER="${HINT_PROVIDER:-agentbench}"
HINT_PROFILE="${HINT_PROFILE:-high-reuse}"
PROFILES="${PROFILES:-off light timing full}"
OUT_CSV="${OUT_CSV:-experiments/reports/sglang_logging_profile_walltime.csv}"
GEN_READY_RETRIES="${GEN_READY_RETRIES:-180}"
GEN_READY_DELAY_SECS="${GEN_READY_DELAY_SECS:-2}"
WORKER_EXTRA_ARGS_DEFAULT="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --enable-hierarchical-cache --mem-fraction-static 0.7 --hicache-ratio 1"
WORKER_EXTRA_ARGS="${WORKER_EXTRA_ARGS:-${WORKER_EXTRA_ARGS_DEFAULT}}"

mkdir -p "$(dirname "${OUT_CSV}")"
printf 'profile,run_seconds,run_id\n' > "${OUT_CSV}"

latest_result_dir() {
  ls -td experiments/raw/agentbench/results/* 2>/dev/null | head -1 || true
}

timestamp_seconds() {
  "${TIMER_PYTHON_BIN}" - <<'PY'
import time
print(f"{time.time():.6f}")
PY
}

elapsed_seconds() {
  "${TIMER_PYTHON_BIN}" - "$1" "$2" <<'PY'
import sys
start = float(sys.argv[1])
end = float(sys.argv[2])
print(f"{end - start:.3f}")
PY
}

wait_for_generation_ready() {
  local model_name="${DYNAMO_SERVED_MODEL_NAME:-${MODEL}}"
  local url="${FRONTEND_URL}"
  local response=""

  for ((attempt=1; attempt<=GEN_READY_RETRIES; attempt++)); do
    response="$(
      curl -fsS "${url}" \
        -H "Content-Type: application/json" \
        -d "{
          \"model\": \"${model_name}\",
          \"messages\": [{\"role\": \"user\", \"content\": \"Reply with exactly: OK\"}],
          \"max_tokens\": 4
        }" 2>&1 || true
    )"
    if [[ "${response}" == *'"choices"'* ]]; then
      return 0
    fi
    echo "Waiting for generation readiness (${attempt}/${GEN_READY_RETRIES})..."
    sleep "${GEN_READY_DELAY_SECS}"
  done

  echo "Dynamo did not become generation-ready." >&2
  echo "Last response:" >&2
  echo "${response}" >&2
  echo >&2
  ./run_dynamo_single_host.sh logs-worker || true
  return 1
}

read -r -a PROFILE_LIST <<< "${PROFILES}"
TOTAL_PROFILES="${#PROFILE_LIST[@]}"

for INDEX_IN_PROFILES in "${!PROFILE_LIST[@]}"; do
  PROFILE="${PROFILE_LIST[$INDEX_IN_PROFILES]}"
  PROFILE_NUMBER="$((INDEX_IN_PROFILES + 1))"
  echo "===== SGLang logging profile ${PROFILE_NUMBER}/${TOTAL_PROFILES}: ${PROFILE} ====="
  ./run_dynamo_single_host.sh stop

  WORKER_EXTRA_ARGS="${WORKER_EXTRA_ARGS}" \
  WORKER_SGLANG_DEV_MODE="${WORKER_SGLANG_DEV_MODE:-1}" \
  WORKER_SGLANG_SOURCE_ROOT="${WORKER_SGLANG_SOURCE_ROOT:-${SGLANG_ROOT:-}}" \
  SGLANG_TRANSFER_LOG=1 \
  SGLANG_TRANSFER_LOG_PROFILE="${PROFILE}" \
  SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=0 \
  DYN_RUNTIME_JSON_LOGS="${DYN_RUNTIME_JSON_LOGS:-1}" \
  DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER:-hermes}" \
  DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH:-${MODEL}}" \
  DYNAMO_SERVED_MODEL_NAME="${DYNAMO_SERVED_MODEL_NAME:-${MODEL}}" \
  FRONTEND_IMAGE="${FRONTEND_IMAGE:-}" \
  WORKER_IMAGE="${WORKER_IMAGE:-}" \
  ./run_dynamo_single_host.sh start

  wait_for_generation_ready

  before_result="$(latest_result_dir)"
  start_time="$(timestamp_seconds)"

  AGENTBENCH_WORKFLOW_MODE="${AGENTBENCH_WORKFLOW_MODE:-phased}" \
  "${PYTHON_BIN}" agentbench/deepagents_swebench_single_host.py \
    --app-variant "${APP_VARIANT}" \
    --frontend-url "${FRONTEND_URL}" \
    --model "${MODEL}" \
    --dataset "${DATASET}" \
    --split "${SPLIT}" \
    --index "${INDEX}" \
    --hint-provider "${HINT_PROVIDER}" \
    --hint-profile "${HINT_PROFILE}" \
    --prompt-evolution-value-char-limit "${PROMPT_EVOLUTION_VALUE_CHAR_LIMIT:-1000}" \
    --quiet-checkpoints

  end_time="$(timestamp_seconds)"
  run_seconds="$(elapsed_seconds "${start_time}" "${end_time}")"
  after_result="$(latest_result_dir)"
  run_id=""
  if [[ -n "${after_result}" && "${after_result}" != "${before_result}" ]]; then
    run_id="$(basename "${after_result}")"
  fi

  printf '%s,%s,%s\n' "${PROFILE}" "${run_seconds}" "${run_id}" >> "${OUT_CSV}"
  echo "Completed profile ${PROFILE_NUMBER}/${TOTAL_PROFILES}: profile=${PROFILE} run_seconds=${run_seconds} run_id=${run_id:-unknown}"
  echo
done

echo "All ${TOTAL_PROFILES} logging-profile timing runs completed."
echo "Wall-clock comparison written to: ${OUT_CSV}"
