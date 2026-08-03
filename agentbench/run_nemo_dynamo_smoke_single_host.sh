#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL="${1:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}"
NEMO_DYNAMO_START_MODE="${NEMO_DYNAMO_START_MODE:-clean}"
NEMO_DYNAMO_SMOKE_ID="${NEMO_DYNAMO_SMOKE_ID:-nemo_dynamo_smoke_$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="${OUT_DIR:-experiments/reports/nemo_dynamo_smoke/${NEMO_DYNAMO_SMOKE_ID}}"
SMOKE_LOG="${OUT_DIR}/dynamo_smoke_test.log"
DRIVER_LOG="${OUT_DIR}/nemo_dynamo_smoke_driver.log"
STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE:-0}"

mkdir -p "${OUT_DIR}"

detect_tool_parser() {
  local model_lc
  model_lc="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  if [[ "${model_lc}" == *"qwen3-coder"* || "${model_lc}" == *"qwen3_coder"* || "${model_lc}" == *"qwen3.5"* || "${model_lc}" == *"qwen3-5"* ]]; then
    echo "qwen3_coder"
    return
  fi
  echo "hermes"
}

detect_reasoning_parser() {
  local model_lc
  model_lc="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  if [[ "${model_lc}" == *"qwen3-coder"* || "${model_lc}" == *"qwen3_coder"* || "${model_lc}" == *"qwen3.5"* || "${model_lc}" == *"qwen3-5"* ]]; then
    echo "qwen3"
    return
  fi
  echo ""
}

DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER:-$(detect_tool_parser "${MODEL}")}"
DYN_REASONING_PARSER="${DYN_REASONING_PARSER:-$(detect_reasoning_parser "${MODEL}")}"

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

    echo "Smoke test attempt ${attempt} failed; waiting ${MODEL_SMOKE_DELAY_SECS}s." >> "${smoke_log}"
    sleep "${MODEL_SMOKE_DELAY_SECS}"
  done

  echo "Smoke test failed for ${model}. See ${smoke_log}" | tee -a "${DRIVER_LOG}" >&2
  return 1
}

cat <<EOF | tee -a "${DRIVER_LOG}"
========================================
NEMO DYNAMO SMOKE
========================================
Model: ${MODEL}
Frontend URL: ${FRONTEND_URL}
Start mode: ${NEMO_DYNAMO_START_MODE}
Tool-call parser: ${DYN_TOOL_CALL_PARSER}
Reasoning parser: ${DYN_REASONING_PARSER:-<unset>}
Output dir: ${OUT_DIR}
EOF

if [[ "${NEMO_DYNAMO_START_MODE}" = "clean" ]]; then
  echo "Stopping Dynamo..." | tee -a "${DRIVER_LOG}"
  ./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true

  agentbench_print_model_readiness_active_banner | tee -a "${DRIVER_LOG}"
  echo "Starting Dynamo for ${MODEL}..." | tee -a "${DRIVER_LOG}"
  DYNAMO_MODEL_PATH="${MODEL}" \
  DYNAMO_SERVED_MODEL_NAME="${MODEL}" \
  DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER}" \
  DYN_REASONING_PARSER="${DYN_REASONING_PARSER}" \
  ./run_dynamo_single_host.sh start >> "${DRIVER_LOG}" 2>&1
elif [[ "${NEMO_DYNAMO_START_MODE}" = "reuse" ]]; then
  echo "Reusing live Dynamo runtime." | tee -a "${DRIVER_LOG}"
else
  echo "Unsupported NEMO_DYNAMO_START_MODE=${NEMO_DYNAMO_START_MODE}. Use clean or reuse." >&2
  exit 2
fi

smoke_test_model "${MODEL}" "${SMOKE_LOG}"
agentbench_print_model_readiness_go_banner | tee -a "${DRIVER_LOG}"

if [[ "${MODEL_COOLDOWN_SECS}" -gt 0 ]]; then
  echo "Cooldown: ${MODEL_COOLDOWN_SECS}s" | tee -a "${DRIVER_LOG}"
  sleep "${MODEL_COOLDOWN_SECS}"
fi

OUT_DIR="${OUT_DIR}" \
PYTHON_BIN="${PYTHON_BIN}" \
FRONTEND_URL="${FRONTEND_URL}" \
./agentbench/debug_nemo_dynamo_nvext.sh "${MODEL}" 2>&1 | tee -a "${DRIVER_LOG}"

if [[ "${STOP_DYNAMO_WHEN_DONE}" = "1" ]]; then
  echo "Stopping Dynamo after NeMo smoke..." | tee -a "${DRIVER_LOG}"
  ./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true
fi

echo "NeMo Dynamo smoke complete."
echo "Output dir: ${OUT_DIR}"
