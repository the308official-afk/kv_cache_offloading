#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL="${1:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}"
START_INDEX="${START_INDEX:-${PROMPT_EVOLUTION_BATCH_START_INDEX:-0}}"
END_INDEX="${END_INDEX:-${PROMPT_EVOLUTION_BATCH_END_INDEX:-5}}"
HINT_PROFILE="${HINT_PROFILE:-high-reuse}"
HINT_PROVIDER="${HINT_PROVIDER:-agentbench}"
PROMPT_EVOLUTION_VALUE_CHAR_LIMIT="${PROMPT_EVOLUTION_VALUE_CHAR_LIMIT:-1000}"
AGENTBENCH_WORKFLOW_MODE="${AGENTBENCH_WORKFLOW_MODE:-phased}"
DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER:-hermes}"
AGENTBENCH_DEEPAGENTS_SOURCE="${AGENTBENCH_DEEPAGENTS_SOURCE:-upstream}"
PROMPT_EVOLUTION_REQUIRE_TOOL_LOOP="${PROMPT_EVOLUTION_REQUIRE_TOOL_LOOP:-1}"
PROMPT_EVOLUTION_TOOL_LOOP_CASE="${PROMPT_EVOLUTION_TOOL_LOOP_CASE:-ls-read-execute}"
PROMPT_EVOLUTION_BATCH_ID="${PROMPT_EVOLUTION_BATCH_ID:-prompt_evolution_batch_$(date +%Y%m%d_%H%M%S)}"
MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES:-${AGENTBENCH_MODEL_SMOKE_RETRIES}}"
MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS:-${AGENTBENCH_MODEL_SMOKE_DELAY_SECS}}"
MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS:-${AGENTBENCH_MODEL_COOLDOWN_SECS}}"
STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE:-0}"
SHARED_CHART_DIR="${SHARED_CHART_DIR:-experiments/charts}"
DEEPAGENTS_READY_HELPER="${DEEPAGENTS_READY_HELPER:-./agentbench/ensure_deepagents_ready.sh}"

BATCH_DIR="experiments/reports/batches/${PROMPT_EVOLUTION_BATCH_ID}"
DRIVER_LOG="${BATCH_DIR}/prompt_evolution_batch_driver.log"
SMOKE_LOG="${BATCH_DIR}/prompt_evolution_batch_smoke_test.log"
TOOL_LOOP_PREFLIGHT_LOG="${BATCH_DIR}/prompt_evolution_tool_loop_preflight.log"
TOOL_LOOP_PREFLIGHT_DIR="${BATCH_DIR}/tool_loop_preflight"
mkdir -p "${BATCH_DIR}"

publish_prompt_evolution_reports() {
  mkdir -p "${SHARED_CHART_DIR}"

  local src
  for src in \
    "experiments/reports/prompt_evolution_task_summary.csv:exp6_prompt_evolution_task_summary.csv" \
    "experiments/reports/prompt_evolution_task_summary.csv:exp6_task_summary_table.csv" \
    "experiments/reports/prompt_evolution_run_overview.csv:prompt_evolution_run_overview.csv" \
    "experiments/reports/prompt_evolution_run_overview.csv:exp6_prompt_evolution_run_overview.csv" \
    "experiments/reports/prompt_evolution_run_overview.csv:exp6_run_overview_table.csv" \
    "experiments/reports/latest_prompt_evolution_trace_index.csv:exp6_prompt_evolution_trace_index.csv" \
    "experiments/reports/latest_prompt_evolution_trace_index.csv:exp6_trace_index_table.csv" \
    "experiments/reports/latest_prompt_evolution_trace_index.md:exp6_prompt_evolution_trace_index.md" \
    "experiments/reports/latest_runs_execution_prompts.md:exp6_runs_execution_prompts.md"; do
    local source_path="${src%%:*}"
    local target_name="${src##*:}"
    if [[ -f "${source_path}" ]]; then
      cp -f "${source_path}" "${SHARED_CHART_DIR}/${target_name}"
    fi
  done
}

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
  5. verifies Deep Agents can execute a real tool loop
  6. launches the SWE-bench prompt-evolution batch
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

check_deepagents_tool_loop() {
  local model="$1"
  local frontend_url="$2"

  if [[ "${PROMPT_EVOLUTION_REQUIRE_TOOL_LOOP}" != "1" ]]; then
    {
      echo "Skipping Deep Agents tool-loop preflight because PROMPT_EVOLUTION_REQUIRE_TOOL_LOOP=${PROMPT_EVOLUTION_REQUIRE_TOOL_LOOP}."
      echo "Warning: Experiment 6 may produce tool_call_count=0 if the tool loop is broken."
    } | tee -a "${DRIVER_LOG}"
    return 0
  fi

  {
    echo
    echo "Checking Deep Agents tool loop before Experiment 6 batch..."
    echo "Case: ${PROMPT_EVOLUTION_TOOL_LOOP_CASE}"
    echo "Deep Agents source: ${AGENTBENCH_DEEPAGENTS_SOURCE}"
    echo "Preflight log: ${TOOL_LOOP_PREFLIGHT_LOG}"
    echo "Preflight output dir: ${TOOL_LOOP_PREFLIGHT_DIR}"
  } | tee -a "${DRIVER_LOG}"

  rm -rf "${TOOL_LOOP_PREFLIGHT_DIR}"
  mkdir -p "${TOOL_LOOP_PREFLIGHT_DIR}"

  if ! AGENTBENCH_DEEPAGENTS_SOURCE="${AGENTBENCH_DEEPAGENTS_SOURCE}" \
    "${PYTHON_BIN}" agentbench/diagnose_deepagents_tool_loop.py \
      --frontend-url "${frontend_url}" \
      --model "${model}" \
      --case "${PROMPT_EVOLUTION_TOOL_LOOP_CASE}" \
      --output-dir "${TOOL_LOOP_PREFLIGHT_DIR}" \
      2>&1 | tee "${TOOL_LOOP_PREFLIGHT_LOG}"; then
    {
      echo
      echo "CRITICAL FAIL: Deep Agents tool-loop preflight command failed."
      echo "Experiment 6 would likely produce tool_call_count=0, so the batch is stopped."
      echo "See: ${TOOL_LOOP_PREFLIGHT_LOG}"
      echo "For deeper diagnosis, run:"
      echo "  AGENTBENCH_DEEPAGENTS_SOURCE=upstream ./agentbench/debug_prompt_evolution_tool_calls.sh ${model}"
    } | tee -a "${DRIVER_LOG}" >&2
    return 1
  fi

  "${PYTHON_BIN}" - <<'PY' "${TOOL_LOOP_PREFLIGHT_DIR}/summary.json" "${DRIVER_LOG}" "${TOOL_LOOP_PREFLIGHT_LOG}"
from __future__ import annotations

import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
driver_log = Path(sys.argv[2])
preflight_log = Path(sys.argv[3])

if not summary_path.exists():
    message = (
        "CRITICAL FAIL: Deep Agents tool-loop preflight did not write summary.json.\n"
        f"See: {preflight_log}\n"
    )
    with driver_log.open("a", encoding="utf-8") as f:
        f.write("\n" + message)
    raise SystemExit(message)

summary = json.loads(summary_path.read_text(encoding="utf-8"))
tool_calls = int(summary.get("ai_tool_call_count") or 0)
tool_messages = int(summary.get("tool_message_count") or 0)
multi_tool_loop = bool(summary.get("multi_tool_loop_observed"))
case_success = bool(summary.get("case_success"))

lines = [
    "",
    "Deep Agents tool-loop preflight result:",
    f"  tool_calls={tool_calls}",
    f"  tool_messages={tool_messages}",
    f"  multi_tool_loop_observed={multi_tool_loop}",
    f"  case_success={case_success}",
]
print("\n".join(lines))
with driver_log.open("a", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

if not case_success:
    message = (
        "CRITICAL FAIL: Deep Agents did not complete the required multi-tool loop.\n"
        "Experiment 6 would likely produce tool_call_count=0, so the batch is stopped.\n"
        f"See: {preflight_log}\n"
    )
    with driver_log.open("a", encoding="utf-8") as f:
        f.write("\n" + message)
    raise SystemExit(message)
PY

  echo "Deep Agents tool-loop preflight passed." | tee -a "${DRIVER_LOG}"
}

{
  echo "Prompt evolution batch ID: ${PROMPT_EVOLUTION_BATCH_ID}"
  echo "Model: ${MODEL}"
  echo "Task range: ${START_INDEX}-${END_INDEX}"
  echo "Hint profile: ${HINT_PROFILE}"
  echo "Hint provider: ${HINT_PROVIDER}"
  echo "Tool-call parser: ${DYN_TOOL_CALL_PARSER}"
  echo "Deep Agents source: ${AGENTBENCH_DEEPAGENTS_SOURCE}"
  echo "Require tool loop: ${PROMPT_EVOLUTION_REQUIRE_TOOL_LOOP}"
  echo "Tool-loop preflight case: ${PROMPT_EVOLUTION_TOOL_LOOP_CASE}"
  echo "Deep Agents ready helper: ${DEEPAGENTS_READY_HELPER}"
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
DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER}" \
./run_dynamo_single_host.sh start >> "${DRIVER_LOG}" 2>&1

smoke_test_model "${MODEL}" "${SMOKE_LOG}"
agentbench_print_model_readiness_go_banner | tee -a "${DRIVER_LOG}"

if [[ "${MODEL_COOLDOWN_SECS}" -gt 0 ]]; then
  echo "Cooldown: ${MODEL_COOLDOWN_SECS}s" | tee -a "${DRIVER_LOG}"
  sleep "${MODEL_COOLDOWN_SECS}"
fi

echo "Ensuring Deep Agents dependency is ready..." | tee -a "${DRIVER_LOG}"
"${DEEPAGENTS_READY_HELPER}" 2>&1 | tee -a "${DRIVER_LOG}"

check_deepagents_tool_loop "${MODEL}" "${FRONTEND_URL}"

echo "Running prompt evolution batch for ${MODEL}..." | tee -a "${DRIVER_LOG}"
AGENTBENCH_DEEPAGENTS_SOURCE="${AGENTBENCH_DEEPAGENTS_SOURCE}" \
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

publish_prompt_evolution_reports

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
  echo "Published readable Exp 6 reports to: ${SHARED_CHART_DIR}/exp6_*"
  echo "Run-overview table copy: ${SHARED_CHART_DIR}/prompt_evolution_run_overview.csv"
} | tee -a "${DRIVER_LOG}"


##
