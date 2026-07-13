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
TRACE_INDEX_CSV="${BATCH_DIR}/task_trace_index.csv"
TRACE_INDEX_MD="${BATCH_DIR}/task_trace_index.md"
REAL_REQUEST_UNITS_DIR="${BATCH_DIR}/swebench_real_request_units"
REAL_REQUEST_UNITS_CSV="${REAL_REQUEST_UNITS_DIR}/request_units.csv"
REAL_REQUEST_UNITS_SUMMARY_MD="${REAL_REQUEST_UNITS_DIR}/request_units_summary.md"
REAL_TASK_SELECTION_CSV="${REAL_REQUEST_UNITS_DIR}/task_selection.csv"
REAL_TASK_SELECTION_MD="${REAL_REQUEST_UNITS_DIR}/task_selection.md"
LATEST_TRACE_INDEX_CSV="experiments/reports/latest_prompt_evolution_trace_index.csv"
LATEST_TRACE_INDEX_MD="experiments/reports/latest_prompt_evolution_trace_index.md"
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

append_trace_index_row() {
  local run_id="$1"
  local task_index="$2"
  RUN_ID="$run_id" \
  TASK_INDEX="$task_index" \
  TRACE_INDEX_CSV="$TRACE_INDEX_CSV" \
  TRACE_INDEX_MD="$TRACE_INDEX_MD" \
  LATEST_TRACE_INDEX_CSV="$LATEST_TRACE_INDEX_CSV" \
  LATEST_TRACE_INDEX_MD="$LATEST_TRACE_INDEX_MD" \
  python3 - <<'PY'
import csv
import os
from pathlib import Path

run_id = os.environ["RUN_ID"]
task_index = os.environ["TASK_INDEX"]
trace_index_csv = Path(os.environ["TRACE_INDEX_CSV"])
trace_index_md = Path(os.environ["TRACE_INDEX_MD"])
latest_trace_index_csv = Path(os.environ["LATEST_TRACE_INDEX_CSV"])
latest_trace_index_md = Path(os.environ["LATEST_TRACE_INDEX_MD"])

overview_csv = Path("experiments/reports/all_runs_overview.csv")
overview_row = {}
if overview_csv.exists():
    rows = list(csv.DictReader(overview_csv.open()))
    overview_row = next((row for row in rows if row.get("run_id") == run_id), {}) or {}

result_dir = Path("experiments/raw/agentbench/results") / run_id
report_dir = Path("experiments/reports/runs") / run_id

row = {
    "task_index": task_index,
    "run_id": run_id,
    "repo": overview_row.get("repo", ""),
    "model": overview_row.get("model", ""),
    "hint_profile": overview_row.get("hint_profile", ""),
    "total_tool_calls": overview_row.get("total_tool_calls", ""),
    "execution_phase_tools": overview_row.get("execution_phase_tools", ""),
    "patch_nonempty": overview_row.get("patch_nonempty", ""),
    "result_dir": str(result_dir),
    "report_dir": str(report_dir),
    "prompt_evolution_report_md": str(result_dir / "prompt_evolution_report.md"),
    "prompt_evolution_report_csv": str(result_dir / "prompt_evolution_report.csv"),
    "final_model_request_json": str(result_dir / "prompt_evolution_values/03_final_model_request.json"),
    "tool_runtime_context_json": str(result_dir / "prompt_evolution_values/05_tool_runtime_context.json"),
    "runtime_preprocessing_json": str(result_dir / "prompt_evolution_values/06_runtime_preprocessing.json"),
    "model_behavior_json": str(result_dir / "prompt_evolution_values/07_model_behavior.json"),
    "phase_summary_md": str(report_dir / "phase_summary.md"),
    "phase_summary_csv": str(report_dir / "phase_summary.csv"),
    "tool_call_details_md": str(report_dir / "tool_call_details.md"),
    "tool_call_details_csv": str(report_dir / "tool_call_details.csv"),
    "workspace_patch": str(result_dir / "workspace.patch"),
}

fieldnames = list(row.keys())
existing_rows = []
if trace_index_csv.exists():
    existing_rows = list(csv.DictReader(trace_index_csv.open()))
    existing_rows = [item for item in existing_rows if item.get("run_id") != run_id]
existing_rows.append(row)
existing_rows.sort(key=lambda item: int(item.get("task_index") or 0))

trace_index_csv.parent.mkdir(parents=True, exist_ok=True)
with trace_index_csv.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(existing_rows)

latest_trace_index_csv.parent.mkdir(parents=True, exist_ok=True)
latest_trace_index_csv.write_text(trace_index_csv.read_text(encoding="utf-8"), encoding="utf-8")

lines = [
    "# Prompt Evolution Task Trace Index",
    "",
    "Each row points to the exact prompt-evolution and tool-call artifacts for one SWE-bench task in this batch.",
    "",
    "| Task | Repo | Run ID | Tools | Patch | Key files |",
    "| --- | --- | --- | --- | --- | --- |",
]
for item in existing_rows:
    key_files = "<br>".join(
        [
            f"`{item['prompt_evolution_report_md']}`",
            f"`{item['tool_call_details_md']}`",
            f"`{item['phase_summary_md']}`",
            f"`{item['model_behavior_json']}`",
        ]
    )
    lines.append(
        "| {task} | {repo} | `{run_id}` | {tools} | {patch} | {files} |".format(
            task=item.get("task_index", ""),
            repo=item.get("repo", ""),
            run_id=item.get("run_id", ""),
            tools=item.get("execution_phase_tools", "") or item.get("total_tool_calls", ""),
            patch=item.get("patch_nonempty", ""),
            files=key_files,
        )
    )

trace_index_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
latest_trace_index_md.write_text(trace_index_md.read_text(encoding="utf-8"), encoding="utf-8")
PY
}

echo "Batch ID: ${BATCH_ID}" | tee -a "${PROGRESS_LOG}"
echo "Model: ${MODEL}" | tee -a "${PROGRESS_LOG}"
echo "Frontend URL: ${FRONTEND_URL}" | tee -a "${PROGRESS_LOG}"
echo "Hint profile: ${HINT_PROFILE}" | tee -a "${PROGRESS_LOG}"
echo "Hint provider: ${HINT_PROVIDER}" | tee -a "${PROGRESS_LOG}"
echo "Progress log: ${PROGRESS_LOG}" | tee -a "${PROGRESS_LOG}"
echo "Progress CSV: ${PROGRESS_CSV}" | tee -a "${PROGRESS_LOG}"
echo "Trace index CSV: ${TRACE_INDEX_CSV}" | tee -a "${PROGRESS_LOG}"
echo "Trace index MD: ${TRACE_INDEX_MD}" | tee -a "${PROGRESS_LOG}"
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
    append_trace_index_row "${RUN_ID}" "${INDEX}"
    {
      echo "Run complete: ${RUN_ID}"
      echo "Run report: experiments/reports/runs/${RUN_ID}"
      echo "Prompt evolution trace index: ${TRACE_INDEX_MD}"
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

if [[ -f "${TRACE_INDEX_CSV}" ]]; then
  "${PYTHON_BIN}" experiments/scripts/swebench_real_task/build_request_units.py \
    --trace-index-csv "${TRACE_INDEX_CSV}" \
    --out-dir "${REAL_REQUEST_UNITS_DIR}" >/dev/null 2>&1 || true

  if [[ -f "${REAL_REQUEST_UNITS_CSV}" ]]; then
    "${PYTHON_BIN}" experiments/scripts/swebench_real_task/select_real_tasks.py \
      --request-units-csv "${REAL_REQUEST_UNITS_CSV}" \
      --out-csv "${REAL_TASK_SELECTION_CSV}" \
      --out-md "${REAL_TASK_SELECTION_MD}" >/dev/null 2>&1 || true
  fi
fi

echo "Batch finished." | tee -a "${PROGRESS_LOG}"
echo "Progress log: ${PROGRESS_LOG}" | tee -a "${PROGRESS_LOG}"
echo "Progress CSV: ${PROGRESS_CSV}" | tee -a "${PROGRESS_LOG}"
echo "Trace index CSV: ${TRACE_INDEX_CSV}" | tee -a "${PROGRESS_LOG}"
echo "Trace index MD: ${TRACE_INDEX_MD}" | tee -a "${PROGRESS_LOG}"
echo "Real request units CSV: ${REAL_REQUEST_UNITS_CSV}" | tee -a "${PROGRESS_LOG}"
echo "Real request units summary: ${REAL_REQUEST_UNITS_SUMMARY_MD}" | tee -a "${PROGRESS_LOG}"
echo "Real task selection CSV: ${REAL_TASK_SELECTION_CSV}" | tee -a "${PROGRESS_LOG}"
echo "Real task selection MD: ${REAL_TASK_SELECTION_MD}" | tee -a "${PROGRESS_LOG}"
