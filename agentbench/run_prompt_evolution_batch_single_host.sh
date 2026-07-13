#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL="${1:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}"
START_INDEX="${START_INDEX:-0}"
END_INDEX="${END_INDEX:-5}"
HINT_PROFILE="${HINT_PROFILE:-high-reuse}"
HINT_PROVIDER="${HINT_PROVIDER:-agentbench}"
PROMPT_EVOLUTION_VALUE_CHAR_LIMIT="${PROMPT_EVOLUTION_VALUE_CHAR_LIMIT:-1000}"
AGENTBENCH_WORKFLOW_MODE="${AGENTBENCH_WORKFLOW_MODE:-phased}"
PROMPT_EVOLUTION_BATCH_ID="${PROMPT_EVOLUTION_BATCH_ID:-prompt_evolution_batch_$(date +%Y%m%d_%H%M%S)}"
MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES:-${AGENTBENCH_MODEL_SMOKE_RETRIES}}"
MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS:-${AGENTBENCH_MODEL_SMOKE_DELAY_SECS}}"
MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS:-${AGENTBENCH_MODEL_COOLDOWN_SECS}}"
STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE:-0}"

BATCH_DIR="experiments/reports/batches/${PROMPT_EVOLUTION_BATCH_ID}"
DRIVER_LOG="${BATCH_DIR}/prompt_evolution_batch_driver.log"
SMOKE_LOG="${BATCH_DIR}/prompt_evolution_batch_smoke_test.log"
mkdir -p "${BATCH_DIR}"

usage() {
  cat <<EOF
Usage:
  $0 [model]

Examples:
  $0 Qwen/Qwen2.5-Coder-7B-Instruct
  MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct' $0

This wrapper:
  1. stops Dynamo
  2. starts Dynamo with the selected model
  3. waits for /v1/models registration
  4. runs a smoke-test request
  5. launches the SWE-bench prompt-evolution batch
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

smoke_test_model() {
  local model="$1"
  local smoke_log="$2"
  local frontend_port="${DYNAMO_FRONTEND_PORT:-8000}"
  local chat_url="http://127.0.0.1:${frontend_port}/v1/chat/completions"
  local models_url="http://127.0.0.1:${frontend_port}/v1/models"
  local registered_models
  local payload

  for ((attempt=1; attempt<=MODEL_SMOKE_RETRIES; attempt++)); do
    echo "Smoke test ${attempt}/${MODEL_SMOKE_RETRIES} for ${model}" | tee -a "${DRIVER_LOG}"
    registered_models="$(curl -fsS "${models_url}" 2>/dev/null || true)"
    {
      echo
      echo "Smoke test attempt ${attempt} for ${model}"
      echo "Registered models before chat:"
      echo "${registered_models:-<unavailable>}"
    } >> "${smoke_log}" 2>&1

    if [[ -z "${registered_models}" || "${registered_models}" != *"\"id\":\"${model}\""* ]]; then
      echo "Model is not listed yet; waiting ${MODEL_SMOKE_DELAY_SECS}s." >> "${smoke_log}"
      sleep "${MODEL_SMOKE_DELAY_SECS}"
      continue
    fi

    payload="$("${PYTHON_BIN}" -c 'import json, sys; print(json.dumps({"model": sys.argv[1], "messages": [{"role": "user", "content": "Reply with exactly: OK"}], "max_tokens": 10}))' "${model}")"
    if curl -fsS "${chat_url}" \
      -H "Content-Type: application/json" \
      -d "${payload}" >> "${smoke_log}" 2>&1; then
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
    sleep "${MODEL_SMOKE_DELAY_SECS}"
  done

  echo "Smoke test failed for ${model}. See ${smoke_log}" | tee -a "${DRIVER_LOG}" >&2
  return 1
}

{
  echo "Prompt evolution batch ID: ${PROMPT_EVOLUTION_BATCH_ID}"
  echo "Model: ${MODEL}"
  echo "Task range: ${START_INDEX}-${END_INDEX}"
  echo "Hint profile: ${HINT_PROFILE}"
  echo "Hint provider: ${HINT_PROVIDER}"
  echo "Frontend URL: ${FRONTEND_URL}"
  echo "Driver log: ${DRIVER_LOG}"
  echo "Smoke log: ${SMOKE_LOG}"
  echo
  echo "Stopping Dynamo..."
} | tee -a "${DRIVER_LOG}"

./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true

agentbench_print_model_readiness_active_banner | tee -a "${DRIVER_LOG}"
echo "Starting Dynamo for ${MODEL}..." | tee -a "${DRIVER_LOG}"
DYNAMO_MODEL_PATH="${MODEL}" \
DYNAMO_SERVED_MODEL_NAME="${MODEL}" \
./run_dynamo_single_host.sh start >> "${DRIVER_LOG}" 2>&1

smoke_test_model "${MODEL}" "${SMOKE_LOG}"
agentbench_print_model_readiness_go_banner | tee -a "${DRIVER_LOG}"

if [[ "${MODEL_COOLDOWN_SECS}" -gt 0 ]]; then
  echo "Cooldown: ${MODEL_COOLDOWN_SECS}s" | tee -a "${DRIVER_LOG}"
  sleep "${MODEL_COOLDOWN_SECS}"
fi

echo "Running prompt evolution batch for ${MODEL}..." | tee -a "${DRIVER_LOG}"
AGENTBENCH_WORKFLOW_MODE="${AGENTBENCH_WORKFLOW_MODE}" \
MODEL="${MODEL}" \
MODEL_NAME="${MODEL}" \
FRONTEND_URL="${FRONTEND_URL}" \
START_INDEX="${START_INDEX}" \
END_INDEX="${END_INDEX}" \
HINT_PROFILE="${HINT_PROFILE}" \
HINT_PROVIDER="${HINT_PROVIDER}" \
PROMPT_EVOLUTION_VALUE_CHAR_LIMIT="${PROMPT_EVOLUTION_VALUE_CHAR_LIMIT}" \
BATCH_ID="${PROMPT_EVOLUTION_BATCH_ID}" \
./agentbench/run_swebench_batch_single_host.sh 2>&1 | tee -a "${DRIVER_LOG}"

if [[ "${STOP_DYNAMO_WHEN_DONE}" = "1" ]]; then
  echo "Stopping Dynamo after prompt evolution batch..." | tee -a "${DRIVER_LOG}"
  ./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true
fi

{
  echo
  echo "Prompt evolution batch finished."
  echo "Batch dir: ${BATCH_DIR}"
  echo "Driver log: ${DRIVER_LOG}"
  echo "Smoke log: ${SMOKE_LOG}"
  echo "Progress CSV: ${BATCH_DIR}/progress_overview.csv"
  echo "Trace index CSV: ${BATCH_DIR}/task_trace_index.csv"
  echo "Trace index MD: ${BATCH_DIR}/task_trace_index.md"
  echo "Prompt evolution summary: experiments/reports/prompt_evolution_run_overview.csv"
  echo "Latest trace index CSV: experiments/reports/latest_prompt_evolution_trace_index.csv"
  echo "Latest trace index MD: experiments/reports/latest_prompt_evolution_trace_index.md"
} | tee -a "${DRIVER_LOG}"
