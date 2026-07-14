#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3}"
TRACE_INDEX="${SWEBENCH_TRAJECTORY_TRACE_INDEX:-experiments/reports/latest_prompt_evolution_trace_index.csv}"
CATALOG_ID="${SWEBENCH_TRAJECTORY_CATALOG_ID:-swebench_trajectory_prompts_$(date +%Y%m%d_%H%M%S)}"
STAGE_FILTER="${SWEBENCH_TRAJECTORY_STAGE_FILTER:-planning execution patch_generation review}"
MIN_PROMPT_CHARS="${SWEBENCH_TRAJECTORY_MIN_PROMPT_CHARS:-200}"
MAX_TASKS="${SWEBENCH_TRAJECTORY_MAX_TASKS:-0}"
SHARED_CHART_DIR="${SHARED_CHART_DIR:-experiments/charts}"

echo "Preparing SWE-bench trajectory prompts..."
echo "Trace index: ${TRACE_INDEX}"
echo "Catalog ID: ${CATALOG_ID}"
echo "Stages: ${STAGE_FILTER}"
echo "Min prompt chars: ${MIN_PROMPT_CHARS}"
echo "Max tasks: ${MAX_TASKS}"
echo

"${PYTHON_BIN}" experiments/scripts/swebench_trajectory/build_prompt_catalog.py \
  --trace-index "${TRACE_INDEX}" \
  --catalog-id "${CATALOG_ID}" \
  --stage-filter "${STAGE_FILTER}" \
  --min-prompt-chars "${MIN_PROMPT_CHARS}" \
  --max-tasks "${MAX_TASKS}"

mkdir -p "${SHARED_CHART_DIR}"
if [[ -f experiments/reports/latest_swebench_trajectory_prompt_catalog.csv ]]; then
  cp -f experiments/reports/latest_swebench_trajectory_prompt_catalog.csv \
    "${SHARED_CHART_DIR}/exp6_swebench_trajectory_prompt_catalog.csv"
fi

echo
echo "Latest catalog CSV: experiments/reports/latest_swebench_trajectory_prompt_catalog.csv"
echo "Latest catalog JSONL: experiments/reports/latest_swebench_trajectory_prompt_catalog.jsonl"
echo "Published catalog CSV to: ${SHARED_CHART_DIR}/exp6_swebench_trajectory_prompt_catalog.csv"
