#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL="${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}"
APP_VARIANT="${APP_VARIANT:-upstream_deploy_coding_agent}"
DATASET="${DATASET:-ScaleAI/SWE-bench_Pro}"
SPLIT="${SPLIT:-test}"
HINT_PROFILE="${HINT_PROFILE:-high-reuse}"
HINT_PROVIDER="${HINT_PROVIDER:-agentbench}"
START_INDEX="${START_INDEX:-0}"
END_INDEX="${END_INDEX:-4}"
PROMPT_EVOLUTION_VALUE_CHAR_LIMIT="${PROMPT_EVOLUTION_VALUE_CHAR_LIMIT:-1000}"
WORKFLOW_MODE="${AGENTBENCH_WORKFLOW_MODE:-phased}"
BATCH_ID="${BATCH_ID:-agentbench_batch_$(date +%Y%m%d_%H%M%S)}"

BATCH_DIR="experiments/reports/batches/${BATCH_ID}"
PROGRESS_CSV="${BATCH_DIR}/progress_overview.csv"
PROGRESS_LOG="${BATCH_DIR}/progress.log"
mkdir -p "${BATCH_DIR}"

latest_result_dir() {
  ls -td experiments/raw/agentbench/results/* 2>/dev/null | head -1 || true
}

append_progress_row() {
  local run_id="$1"
  RUN_ID="$run_id" PROGRESS_CSV="$PROGRESS_CSV" python3 - <<'PY'
import csv
import os
from pathlib import Path

run_id = os.environ["RUN_ID"]
progress_csv = Path(os.environ["PROGRESS_CSV"])
overview_csv = Path("experiments/reports/all_runs_overview.csv")
if not overview_csv.exists():
    raise SystemExit(0)

rows = list(csv.DictReader(overview_csv.open()))
row = next((row for row in rows if row.get("run_id") == run_id), None)
if row is None:
    raise SystemExit(0)

fieldnames = list(row.keys())
write_header = not progress_csv.exists()
with progress_csv.open("a", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
    if write_header:
        writer.writeheader()
    writer.writerow(row)
PY
}

echo "Batch ID: ${BATCH_ID}" | tee -a "${PROGRESS_LOG}"
echo "Model: ${MODEL}" | tee -a "${PROGRESS_LOG}"
echo "Frontend URL: ${FRONTEND_URL}" | tee -a "${PROGRESS_LOG}"
echo "Hint profile: ${HINT_PROFILE}" | tee -a "${PROGRESS_LOG}"
echo "Hint provider: ${HINT_PROVIDER}" | tee -a "${PROGRESS_LOG}"
echo "Progress log: ${PROGRESS_LOG}" | tee -a "${PROGRESS_LOG}"
echo "Progress CSV: ${PROGRESS_CSV}" | tee -a "${PROGRESS_LOG}"
echo | tee -a "${PROGRESS_LOG}"

for INDEX in $(seq "${START_INDEX}" "${END_INDEX}"); do
  echo "===== Running SWE-bench index ${INDEX} =====" | tee -a "${PROGRESS_LOG}"
  BEFORE_RESULT="$(latest_result_dir)"

  status=0
  AGENTBENCH_WORKFLOW_MODE="${WORKFLOW_MODE}" \
  "${PYTHON_BIN}" agentbench/deepagents_swebench_single_host.py \
    --app-variant "${APP_VARIANT}" \
    --frontend-url "${FRONTEND_URL}" \
    --model "${MODEL}" \
    --dataset "${DATASET}" \
    --split "${SPLIT}" \
    --index "${INDEX}" \
    --hint-provider "${HINT_PROVIDER}" \
    --hint-profile "${HINT_PROFILE}" \
    --prompt-evolution-value-char-limit "${PROMPT_EVOLUTION_VALUE_CHAR_LIMIT}" \
    --quiet-checkpoints \
  || status=$?

  AFTER_RESULT="$(latest_result_dir)"
  if [[ -n "${AFTER_RESULT}" ]]; then
    "${PYTHON_BIN}" experiments/scripts/agentbench_report/build_run_report.py \
      --agentbench-result-dir "${AFTER_RESULT}" \
      --transfer-log experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl >/dev/null 2>&1 || true
  fi

  if [[ -n "${AFTER_RESULT}" && "${AFTER_RESULT}" != "${BEFORE_RESULT}" ]]; then
    RUN_ID="$(basename "${AFTER_RESULT}")"
    append_progress_row "${RUN_ID}"
    {
      echo "Run complete: ${RUN_ID}"
      echo "Run report: experiments/reports/runs/${RUN_ID}"
      echo "Latest overview: experiments/reports/latest_runs_overview.md"
      echo "All runs overview: experiments/reports/all_runs_overview.csv"
      echo "Latest execution prompts: experiments/reports/latest_runs_execution_prompts.md"
      echo "All execution prompts: experiments/reports/all_runs_execution_prompts.csv"
      echo "Exit status: ${status}"
      echo
    } | tee -a "${PROGRESS_LOG}"
  else
    {
      echo "No new result directory detected for index ${INDEX}"
      echo "Exit status: ${status}"
      echo
    } | tee -a "${PROGRESS_LOG}"
  fi

  if [[ "${status}" -ne 0 ]]; then
    echo "Index ${INDEX} failed; continuing" | tee -a "${PROGRESS_LOG}"
    echo | tee -a "${PROGRESS_LOG}"
  fi
done

echo "Batch finished." | tee -a "${PROGRESS_LOG}"
echo "Progress log: ${PROGRESS_LOG}" | tee -a "${PROGRESS_LOG}"
echo "Progress CSV: ${PROGRESS_CSV}" | tee -a "${PROGRESS_LOG}"
