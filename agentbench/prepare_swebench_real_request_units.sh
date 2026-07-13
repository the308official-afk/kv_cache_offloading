#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

REAL_REQUEST_UNITS_ID="${REAL_REQUEST_UNITS_ID:-swebench_real_request_units_$(date +%Y%m%d_%H%M%S)}"
TRACE_INDEX_CSV="${TRACE_INDEX_CSV:-experiments/reports/latest_prompt_evolution_trace_index.csv}"
OUT_DIR="${OUT_DIR:-experiments/reports/swebench_real_request_units/${REAL_REQUEST_UNITS_ID}}"
LATEST_REQUEST_UNITS_CSV="${LATEST_REQUEST_UNITS_CSV:-experiments/reports/latest_swebench_real_request_units.csv}"
LATEST_REQUEST_UNITS_SUMMARY_MD="${LATEST_REQUEST_UNITS_SUMMARY_MD:-experiments/reports/latest_swebench_real_request_units_summary.md}"
LATEST_TASK_SELECTION_CSV="${LATEST_TASK_SELECTION_CSV:-experiments/reports/latest_swebench_real_task_selection.csv}"
LATEST_TASK_SELECTION_MD="${LATEST_TASK_SELECTION_MD:-experiments/reports/latest_swebench_real_task_selection.md}"
PYTHON_BIN="${PYTHON_BIN:-}"

usage() {
  cat <<EOF
Usage:
  ./agentbench/prepare_swebench_real_request_units.sh

What it does:
  - reads finished SWE-bench run artifacts already present in this repo
  - builds normalized reusable request units
  - builds a task-level selection table for Experiments 9, 11, and 12
  - refreshes the top-level latest real-task artifacts

Environment overrides:
  REAL_REQUEST_UNITS_ID
  TRACE_INDEX_CSV
  OUT_DIR
  PYTHON_BIN
EOF
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

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

banner() {
  cat <<EOF
========================================
$1
========================================
EOF
}

PYTHON_BIN="$(choose_python)"
mkdir -p "${OUT_DIR}"

REQUEST_UNITS_CSV="${OUT_DIR}/request_units.csv"
REQUEST_UNITS_SUMMARY_MD="${OUT_DIR}/request_units_summary.md"
TASK_SELECTION_CSV="${OUT_DIR}/task_selection.csv"
TASK_SELECTION_MD="${OUT_DIR}/task_selection.md"

banner "PREPARE SWE-BENCH REAL REQUEST UNITS"
echo "prep_id: ${REAL_REQUEST_UNITS_ID}"
echo "trace_index_csv: ${TRACE_INDEX_CSV}"
echo "out_dir: ${OUT_DIR}"
echo "python: ${PYTHON_BIN}"
echo

"${PYTHON_BIN}" experiments/scripts/swebench_real_task/build_request_units.py \
  --trace-index-csv "${TRACE_INDEX_CSV}" \
  --out-dir "${OUT_DIR}" \
  --latest-csv "${LATEST_REQUEST_UNITS_CSV}" \
  --latest-summary-md "${LATEST_REQUEST_UNITS_SUMMARY_MD}"

"${PYTHON_BIN}" experiments/scripts/swebench_real_task/select_real_tasks.py \
  --request-units-csv "${REQUEST_UNITS_CSV}" \
  --out-csv "${TASK_SELECTION_CSV}" \
  --out-md "${TASK_SELECTION_MD}" \
  --latest-csv "${LATEST_TASK_SELECTION_CSV}" \
  --latest-md "${LATEST_TASK_SELECTION_MD}"

echo
banner "REAL REQUEST UNITS READY"
echo "Request units CSV: ${REQUEST_UNITS_CSV}"
echo "Request units summary: ${REQUEST_UNITS_SUMMARY_MD}"
echo "Task selection CSV: ${TASK_SELECTION_CSV}"
echo "Task selection MD: ${TASK_SELECTION_MD}"
echo
echo "Latest request units CSV: ${LATEST_REQUEST_UNITS_CSV}"
echo "Latest request units summary: ${LATEST_REQUEST_UNITS_SUMMARY_MD}"
echo "Latest task selection CSV: ${LATEST_TASK_SELECTION_CSV}"
echo "Latest task selection MD: ${LATEST_TASK_SELECTION_MD}"
