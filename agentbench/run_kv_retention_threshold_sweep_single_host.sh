#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh

MODEL_LIST_FILE="${MODEL_LIST_FILE:-agentbench/model_lists/multi_model_batch.txt}"
RETENTION_SWEEP_ID="${RETENTION_SWEEP_ID:-retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)}"
RETENTION_ATTRIBUTION_MODE="${RETENTION_ATTRIBUTION_MODE:-precise}"
RETENTION_REQUEST_CONTEXT_MODE="${RETENTION_REQUEST_CONTEXT_MODE:-auto}"
DISTRACTOR_COUNTS="${DISTRACTOR_COUNTS:-25 50 75 100 125 150}"
KV_TIER_MODES="${KV_TIER_MODES:-gpu_only}"
CONTROL_HINT_PROFILE="${CONTROL_HINT_PROFILE:-none}"
PROTECTED_HINT_PROFILES="${PROTECTED_HINT_PROFILES:-high-priority}"
CONTROL_CACHE_CONTROL_PROFILE="${CONTROL_CACHE_CONTROL_PROFILE:-off}"
PROTECTED_CACHE_CONTROL_PROFILES="${PROTECTED_CACHE_CONTROL_PROFILES:-off}"
PROTECTED_INPUT_LEN="${PROTECTED_INPUT_LEN:-14000}"
DISTRACTOR_INPUT_LEN="${DISTRACTOR_INPUT_LEN:-14000}"
RANDOM_OUTPUT_LEN="${RANDOM_OUTPUT_LEN:-1}"
MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS:-17146}"
CONTEXT_RESERVE_TOKENS="${CONTEXT_RESERVE_TOKENS:-2048}"
GPU_ONLY_MEM_FRACTION_STATIC="${GPU_ONLY_MEM_FRACTION_STATIC:-0.62}"
CACHE_CONTROL_EPHEMERAL_TTL="${CACHE_CONTROL_EPHEMERAL_TTL:-1h}"
SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-full}"
SGLANG_TRANSFER_LOG_OVERHEAD_TIMING="${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING:-0}"
STOP_ON_PROBE_FAILURE="${STOP_ON_PROBE_FAILURE:-0}"
STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE:-1}"
RETENTION_MATCH_EVENT_MIN="${RETENTION_MATCH_EVENT_MIN:-1}"
RETENTION_MIN_SPEEDUP_RATIO="${RETENTION_MIN_SPEEDUP_RATIO:-1.05}"
RETENTION_MIN_LATENCY_GAIN_MS="${RETENTION_MIN_LATENCY_GAIN_MS:-100}"
PYTHON_BIN="${PYTHON_BIN:-}"
CLI_MODELS=("$@")

SWEEP_DIR="experiments/reports/retention_threshold_sweeps/${RETENTION_SWEEP_ID}"
SWEEP_LOG="${SWEEP_DIR}/retention_threshold_sweep.log"
SWEEP_PROGRESS="${SWEEP_DIR}/retention_threshold_sweep_progress.csv"
SWEEP_MATRIX="${SWEEP_DIR}/retention_threshold_matrix.csv"
SWEEP_COMPARISON="${SWEEP_DIR}/retention_threshold_comparison.csv"
SWEEP_SUMMARY="${SWEEP_DIR}/retention_threshold_summary.md"
LATEST_PROGRESS="${LATEST_RETENTION_THRESHOLD_PROGRESS:-experiments/reports/retention_threshold_sweep_progress.csv}"
LATEST_MATRIX="${LATEST_RETENTION_THRESHOLD_MATRIX:-experiments/reports/retention_threshold_matrix.csv}"
LATEST_COMPARISON="${LATEST_RETENTION_THRESHOLD_COMPARISON:-experiments/reports/retention_threshold_comparison.csv}"
LATEST_SUMMARY="${LATEST_RETENTION_THRESHOLD_SUMMARY:-experiments/reports/retention_threshold_summary.md}"
mkdir -p "${SWEEP_DIR}"

usage() {
  cat <<EOF
Usage:
  $0 [model ...]

Examples:
  RETENTION_ATTRIBUTION_MODE=light \\
  DISTRACTOR_COUNTS="2 10 20" \\
  PROTECTED_INPUT_LEN=8000 \\
  DISTRACTOR_INPUT_LEN=2000 \\
  $0 Qwen/Qwen2.5-Coder-7B-Instruct

  RETENTION_SWEEP_ID="retention_threshold_sweep_\$(date +%Y%m%d_%H%M%S)" \\
  RETENTION_ATTRIBUTION_MODE=precise \\
  DISTRACTOR_COUNTS="25 50 75 100 125 150" \\
  KV_TIER_MODES="gpu_only" \\
  CONTROL_HINT_PROFILE=none \\
  PROTECTED_HINT_PROFILES="high-priority" \\
  GPU_ONLY_MEM_FRACTION_STATIC=0.62 \\
  SGLANG_TRANSFER_LOG_PROFILE=full \\
  $0 Qwen/Qwen2.5-Coder-7B-Instruct

  RETENTION_ATTRIBUTION_MODE=light \\
  DISTRACTOR_COUNTS="2 10 20" \\
  CONTROL_HINT_PROFILE=none \\
  PROTECTED_HINT_PROFILES=none \\
  CONTROL_CACHE_CONTROL_PROFILE=off \\
  PROTECTED_CACHE_CONTROL_PROFILES="ephemeral:1h" \\
  $0 Qwen/Qwen2.5-Coder-7B-Instruct

This runs the retention probe repeatedly with rising distractor counts, then
builds a threshold report showing when prompt A stops surviving for control vs
protected hint runs.
EOF
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

case "${RETENTION_ATTRIBUTION_MODE}" in
  light|precise)
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

init_progress_file() {
  printf '%s\n' "retention_sweep_id,retention_attribution_mode,model,kv_tier_mode,distractor_count,retention_probe_id,batch_matrix,status" > "${SWEEP_PROGRESS}"
}

reset_latest_threshold_reports() {
  rm -f \
    "${LATEST_PROGRESS}" \
    "${LATEST_MATRIX}" \
    "${LATEST_COMPARISON}" \
    "${LATEST_SUMMARY}"
}

append_progress_row() {
  "${PYTHON_BIN}" - <<'PY' \
    "${SWEEP_PROGRESS}" \
    "${RETENTION_SWEEP_ID}" \
    "${RETENTION_ATTRIBUTION_MODE}" \
    "$1" \
    "$2" \
    "$3" \
    "$4" \
    "$5" \
    "$6"
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
row = {
    "retention_sweep_id": sys.argv[2],
    "retention_attribution_mode": sys.argv[3],
    "model": sys.argv[4],
    "kv_tier_mode": sys.argv[5],
    "distractor_count": sys.argv[6],
    "retention_probe_id": sys.argv[7],
    "batch_matrix": sys.argv[8],
    "status": sys.argv[9],
}
fields = list(row.keys())
with path.open("a", encoding="utf-8", newline="") as handle:
    csv.DictWriter(handle, fieldnames=fields, lineterminator="\n").writerow(row)
PY
}

rebuild_threshold_reports() {
  local sweep_status="$1"
  "${PYTHON_BIN}" experiments/scripts/retention_probe/build_retention_threshold_report.py \
    --progress-csv "${SWEEP_PROGRESS}" \
    --out-matrix "${SWEEP_MATRIX}" \
    --out-comparison "${SWEEP_COMPARISON}" \
    --out-summary-md "${SWEEP_SUMMARY}" \
    --control-hint-profile "${CONTROL_HINT_PROFILE}" \
    --control-cache-control-profile "${CONTROL_CACHE_CONTROL_PROFILE}" \
    --match-event-min "${RETENTION_MATCH_EVENT_MIN}" \
    --min-speedup-ratio "${RETENTION_MIN_SPEEDUP_RATIO}" \
    --min-latency-gain-ms "${RETENTION_MIN_LATENCY_GAIN_MS}" \
    --sweep-status "${sweep_status}"

  cp "${SWEEP_PROGRESS}" "${LATEST_PROGRESS}"
  cp "${SWEEP_MATRIX}" "${LATEST_MATRIX}"
  cp "${SWEEP_COMPARISON}" "${LATEST_COMPARISON}"
  cp "${SWEEP_SUMMARY}" "${LATEST_SUMMARY}"
}

MODELS_TO_RUN=()
while IFS= read -r MODEL_LINE; do
  MODELS_TO_RUN+=("${MODEL_LINE}")
done < <(load_models)
if [[ "${#MODELS_TO_RUN[@]}" -eq 0 ]]; then
  echo "No models to run." >&2
  exit 1
fi

reset_latest_threshold_reports
init_progress_file

{
  echo "Retention threshold sweep ID: ${RETENTION_SWEEP_ID}"
  echo "Attribution mode: ${RETENTION_ATTRIBUTION_MODE}"
  echo "Models: ${#MODELS_TO_RUN[@]}"
  printf '  %s\n' "${MODELS_TO_RUN[@]}"
  echo "KV tier modes: ${KV_TIER_MODES}"
  echo "Control hint profile: ${CONTROL_HINT_PROFILE}"
  echo "Protected hint profiles: ${PROTECTED_HINT_PROFILES}"
  echo "Control cache-control profile: ${CONTROL_CACHE_CONTROL_PROFILE}"
  echo "Protected cache-control profiles: ${PROTECTED_CACHE_CONTROL_PROFILES}"
  echo "Distractor counts: ${DISTRACTOR_COUNTS}"
  echo "Protected input len: ${PROTECTED_INPUT_LEN}"
  echo "Distractor input len: ${DISTRACTOR_INPUT_LEN}"
  echo "Random output len: ${RANDOM_OUTPUT_LEN}"
  echo "Max context tokens: ${MAX_CONTEXT_TOKENS}"
  echo "Context reserve tokens: ${CONTEXT_RESERVE_TOKENS}"
  echo "GPU-only mem fraction static: ${GPU_ONLY_MEM_FRACTION_STATIC}"
  echo "Default cache-control TTL: ${CACHE_CONTROL_EPHEMERAL_TTL}"
  echo "SGLang transfer log profile: ${SGLANG_TRANSFER_LOG_PROFILE}"
  echo "Output dir: ${SWEEP_DIR}"
  echo
} | tee -a "${SWEEP_LOG}"

for MODEL_NAME in "${MODELS_TO_RUN[@]}"; do
  MODEL_SAFE_NAME="$(safe_name "${MODEL_NAME}")"

  for KV_TIER_MODE in ${KV_TIER_MODES}; do
    KV_TIER_SAFE_NAME="$(safe_name "${KV_TIER_MODE}")"

    for DISTRACTOR_COUNT in ${DISTRACTOR_COUNTS}; do
      PROBE_ID="${RETENTION_SWEEP_ID}_${MODEL_SAFE_NAME}_${KV_TIER_SAFE_NAME}_d${DISTRACTOR_COUNT}"
      BATCH_MATRIX="experiments/reports/retention_probe_batches/${PROBE_ID}/design_space_retention_matrix.csv"

      {
        echo "===== Sweep cell ====="
        echo "model=${MODEL_NAME}"
        echo "kv_tier_mode=${KV_TIER_MODE}"
        echo "distractor_count=${DISTRACTOR_COUNT}"
        echo "retention_probe_id=${PROBE_ID}"
      } | tee -a "${SWEEP_LOG}"

      if RETENTION_PROBE_ID="${PROBE_ID}" \
        KV_TIER_MODES="${KV_TIER_MODE}" \
        RETENTION_ATTRIBUTION_MODE="${RETENTION_ATTRIBUTION_MODE}" \
        RETENTION_REQUEST_CONTEXT_MODE="${RETENTION_REQUEST_CONTEXT_MODE}" \
        CONTROL_HINT_PROFILE="${CONTROL_HINT_PROFILE}" \
        PROTECTED_HINT_PROFILES="${PROTECTED_HINT_PROFILES}" \
        PROTECTED_INPUT_LEN="${PROTECTED_INPUT_LEN}" \
        DISTRACTOR_INPUT_LEN="${DISTRACTOR_INPUT_LEN}" \
        DISTRACTOR_COUNT="${DISTRACTOR_COUNT}" \
        RANDOM_OUTPUT_LEN="${RANDOM_OUTPUT_LEN}" \
        MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS}" \
        CONTEXT_RESERVE_TOKENS="${CONTEXT_RESERVE_TOKENS}" \
        GPU_ONLY_MEM_FRACTION_STATIC="${GPU_ONLY_MEM_FRACTION_STATIC}" \
        SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
        SGLANG_TRANSFER_LOG_OVERHEAD_TIMING="${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING}" \
        STOP_ON_PROBE_FAILURE="${STOP_ON_PROBE_FAILURE}" \
        STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE}" \
        ./agentbench/run_kv_retention_probe_single_host.sh "${MODEL_NAME}" \
        2>&1 | tee -a "${SWEEP_LOG}"; then
        append_progress_row "${MODEL_NAME}" "${KV_TIER_MODE}" "${DISTRACTOR_COUNT}" "${PROBE_ID}" "${BATCH_MATRIX}" "ok"
        rebuild_threshold_reports "partial"
      else
        append_progress_row "${MODEL_NAME}" "${KV_TIER_MODE}" "${DISTRACTOR_COUNT}" "${PROBE_ID}" "${BATCH_MATRIX}" "failed"
        rebuild_threshold_reports "partial"
        if [[ "${STOP_ON_PROBE_FAILURE}" = "1" ]]; then
          echo "Stopping threshold sweep because STOP_ON_PROBE_FAILURE=1" | tee -a "${SWEEP_LOG}" >&2
          exit 1
        fi
      fi
    done
  done
done

rebuild_threshold_reports "complete"

echo
echo "Retention threshold sweep complete."
echo "Progress CSV:    ${SWEEP_PROGRESS}"
echo "Sweep matrix:    ${SWEEP_MATRIX}"
echo "Comparison CSV:  ${SWEEP_COMPARISON}"
echo "Summary Markdown:${SWEEP_SUMMARY}"
echo "Latest progress: ${LATEST_PROGRESS}"
echo "Latest matrix:   ${LATEST_MATRIX}"
echo "Latest compare:  ${LATEST_COMPARISON}"
echo "Latest summary:  ${LATEST_SUMMARY}"
