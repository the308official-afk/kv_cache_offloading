#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh

MODEL_LIST_FILE="${MODEL_LIST_FILE:-agentbench/model_lists/multi_model_batch.txt}"
START_INDEX="${START_INDEX:-0}"
END_INDEX="${END_INDEX:-4}"
HINT_PROFILE="${HINT_PROFILE:-high-reuse}"
HINT_PROVIDER="${HINT_PROVIDER:-agentbench}"
MULTI_MODEL_BATCH_ID="${MULTI_MODEL_BATCH_ID:-multi_model_batch_$(date +%Y%m%d_%H%M%S)}"
MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES:-60}"
MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS:-10}"
MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS:-30}"
STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE:-0}"
CLI_MODELS=("$@")

MULTI_MODEL_DIR="experiments/reports/batches/${MULTI_MODEL_BATCH_ID}"
MULTI_MODEL_LOG="${MULTI_MODEL_DIR}/multi_model_progress.log"
MULTI_MODEL_CSV="${MULTI_MODEL_DIR}/multi_model_overview.csv"
GLOBAL_CSV="experiments/reports/multi_model_batch_overview.csv"
mkdir -p "${MULTI_MODEL_DIR}"

usage() {
  cat <<EOF
Usage:
  $0 [model ...]

Examples:
  $0 Qwen/Qwen2.5-Coder-7B-Instruct Qwen/Qwen2.5-7B-Instruct
  MODELS='model-a,model-b' $0
  MODEL_LIST_FILE=agentbench/model_lists/multi_model_batch.txt $0

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

safe_model_name() {
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

append_overview_header_if_needed() {
  local path="$1"
  if [[ ! -f "${path}" ]]; then
    echo "multi_model_batch_id,model,hint_profile,hint_provider,start_index,end_index,task_count,completed_count,failed_count,batch_id,progress_csv" > "${path}"
  fi
}

append_overview_row() {
  local model="$1"
  local batch_id="$2"
  local progress_csv="$3"
  local task_count="$4"

  MODEL_VALUE="${model}" \
  BATCH_ID_VALUE="${batch_id}" \
  PROGRESS_CSV_VALUE="${progress_csv}" \
  TASK_COUNT_VALUE="${task_count}" \
  MULTI_MODEL_BATCH_ID_VALUE="${MULTI_MODEL_BATCH_ID}" \
  HINT_PROFILE_VALUE="${HINT_PROFILE}" \
  HINT_PROVIDER_VALUE="${HINT_PROVIDER}" \
  START_INDEX_VALUE="${START_INDEX}" \
  END_INDEX_VALUE="${END_INDEX}" \
  MULTI_MODEL_CSV="${MULTI_MODEL_CSV}" \
  GLOBAL_CSV="${GLOBAL_CSV}" \
  python3 - <<'PY'
import csv
import os
from pathlib import Path

fields = [
    "multi_model_batch_id",
    "model",
    "hint_profile",
    "hint_provider",
    "start_index",
    "end_index",
    "task_count",
    "completed_count",
    "failed_count",
    "batch_id",
    "progress_csv",
]

progress_csv = Path(os.environ["PROGRESS_CSV_VALUE"])
task_count = int(os.environ["TASK_COUNT_VALUE"])
completed_count = 0
if progress_csv.exists():
    with progress_csv.open(encoding="utf-8", newline="") as handle:
        completed_count = sum(1 for _ in csv.DictReader(handle))

row = {
    "multi_model_batch_id": os.environ["MULTI_MODEL_BATCH_ID_VALUE"],
    "model": os.environ["MODEL_VALUE"],
    "hint_profile": os.environ["HINT_PROFILE_VALUE"],
    "hint_provider": os.environ["HINT_PROVIDER_VALUE"],
    "start_index": os.environ["START_INDEX_VALUE"],
    "end_index": os.environ["END_INDEX_VALUE"],
    "task_count": task_count,
    "completed_count": completed_count,
    "failed_count": max(task_count - completed_count, 0),
    "batch_id": os.environ["BATCH_ID_VALUE"],
    "progress_csv": str(progress_csv),
}

for path_env in ("MULTI_MODEL_CSV", "GLOBAL_CSV"):
    path = Path(os.environ[path_env])
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        if write_header:
            writer.writeheader()
        writer.writerow(row)
PY
}

smoke_test_model() {
  local model="$1"
  local smoke_log="$2"
  local frontend_port="${DYNAMO_FRONTEND_PORT:-8000}"
  local chat_url="http://127.0.0.1:${frontend_port}/v1/chat/completions"
  local models_url="http://127.0.0.1:${frontend_port}/v1/models"
  local registered_models
  local payload

  for ((attempt=1; attempt<=MODEL_SMOKE_RETRIES; attempt++)); do
    echo "Smoke test ${attempt}/${MODEL_SMOKE_RETRIES} for ${model}" | tee -a "${MULTI_MODEL_LOG}"
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

    payload="$(python3 -c 'import json, sys; print(json.dumps({"model": sys.argv[1], "messages": [{"role": "user", "content": "Reply with exactly: OK"}], "max_tokens": 10}))' "${model}")"
    if curl -fsS "${chat_url}" \
      -H "Content-Type: application/json" \
      -d "${payload}" >> "${smoke_log}" 2>&1; then
      echo "Smoke test passed for ${model}" | tee -a "${MULTI_MODEL_LOG}"
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

  echo "Smoke test failed for ${model}. See ${smoke_log}" | tee -a "${MULTI_MODEL_LOG}" >&2
  return 1
}

MODELS_TO_RUN=()
while IFS= read -r MODEL_LINE; do
  MODELS_TO_RUN+=("${MODEL_LINE}")
done < <(load_models)
if [[ "${#MODELS_TO_RUN[@]}" -eq 0 ]]; then
  echo "No models to run." >&2
  exit 1
fi

append_overview_header_if_needed "${MULTI_MODEL_CSV}"
append_overview_header_if_needed "${GLOBAL_CSV}"

TASK_COUNT=$((END_INDEX - START_INDEX + 1))

{
  echo "Multi-model batch ID: ${MULTI_MODEL_BATCH_ID}"
  echo "Models: ${#MODELS_TO_RUN[@]}"
  printf '  %s\n' "${MODELS_TO_RUN[@]}"
  echo "Task range: ${START_INDEX}-${END_INDEX}"
  echo "Hint profile: ${HINT_PROFILE}"
  echo "Hint provider: ${HINT_PROVIDER}"
  echo "Output dir: ${MULTI_MODEL_DIR}"
  echo
} | tee -a "${MULTI_MODEL_LOG}"

for MODEL_NAME in "${MODELS_TO_RUN[@]}"; do
  MODEL_SAFE_NAME="$(safe_model_name "${MODEL_NAME}")"
  MODEL_BATCH_ID="${MULTI_MODEL_BATCH_ID}_${MODEL_SAFE_NAME}"
  MODEL_BATCH_DIR="experiments/reports/batches/${MODEL_BATCH_ID}"
  SMOKE_LOG="${MULTI_MODEL_DIR}/${MODEL_SAFE_NAME}_smoke_test.log"

  {
    echo "===== Model: ${MODEL_NAME} ====="
    echo "Model batch ID: ${MODEL_BATCH_ID}"
    echo "Stopping Dynamo..."
  } | tee -a "${MULTI_MODEL_LOG}"

  ./run_dynamo_single_host.sh stop >> "${MULTI_MODEL_LOG}" 2>&1 || true

  echo "Starting Dynamo for ${MODEL_NAME}..." | tee -a "${MULTI_MODEL_LOG}"
  DYNAMO_MODEL_PATH="${MODEL_NAME}" \
  DYNAMO_SERVED_MODEL_NAME="${MODEL_NAME}" \
  ./run_dynamo_single_host.sh start >> "${MULTI_MODEL_LOG}" 2>&1

  smoke_test_model "${MODEL_NAME}" "${SMOKE_LOG}"

  if [[ "${MODEL_COOLDOWN_SECS}" -gt 0 ]]; then
    echo "Cooldown: ${MODEL_COOLDOWN_SECS}s" | tee -a "${MULTI_MODEL_LOG}"
    sleep "${MODEL_COOLDOWN_SECS}"
  fi

  echo "Running SWE-bench batch for ${MODEL_NAME}..." | tee -a "${MULTI_MODEL_LOG}"
  START_INDEX="${START_INDEX}" \
  END_INDEX="${END_INDEX}" \
  HINT_PROFILE="${HINT_PROFILE}" \
  HINT_PROVIDER="${HINT_PROVIDER}" \
  MODEL="${MODEL_NAME}" \
  MODEL_NAME="${MODEL_NAME}" \
  BATCH_ID="${MODEL_BATCH_ID}" \
  ./agentbench/run_swebench_batch_single_host.sh 2>&1 | tee -a "${MULTI_MODEL_LOG}"

  append_overview_row \
    "${MODEL_NAME}" \
    "${MODEL_BATCH_ID}" \
    "${MODEL_BATCH_DIR}/progress_overview.csv" \
    "${TASK_COUNT}"

  {
    echo "Completed model: ${MODEL_NAME}"
    echo "Model progress CSV: ${MODEL_BATCH_DIR}/progress_overview.csv"
    echo
  } | tee -a "${MULTI_MODEL_LOG}"
done

if [[ "${STOP_DYNAMO_WHEN_DONE}" = "1" ]]; then
  echo "Stopping Dynamo after multi-model batch..." | tee -a "${MULTI_MODEL_LOG}"
  ./run_dynamo_single_host.sh stop >> "${MULTI_MODEL_LOG}" 2>&1 || true
fi

{
  echo "Multi-model batch finished."
  echo "Overview: ${MULTI_MODEL_CSV}"
  echo "Global overview: ${GLOBAL_CSV}"
  echo "Log: ${MULTI_MODEL_LOG}"
} | tee -a "${MULTI_MODEL_LOG}"
