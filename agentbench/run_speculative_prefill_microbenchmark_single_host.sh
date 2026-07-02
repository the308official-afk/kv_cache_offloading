#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh
if [[ -f runtime_instrumentation/dynamo_machine_profile.sh ]]; then
  # shellcheck disable=SC1091
  source runtime_instrumentation/dynamo_machine_profile.sh
fi

CONTRACT_PATH="${CONTRACT_PATH:-contracts/speculative_prefill_microbenchmark.contract.sh}"
CONTRACT_DOC_PATH="${CONTRACT_DOC_PATH:-contracts/speculative_prefill_microbenchmark.contract.md}"
if [[ ! -f "${CONTRACT_PATH}" ]]; then
  echo "Missing machine-readable contract: ${CONTRACT_PATH}" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "${CONTRACT_PATH}"

MODEL="${1:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}"
BASE_ID="${SPEC_PREFILL_ID:-speculative_prefill_microbenchmark_$(date +%Y%m%d_%H%M%S)}"
PYTHON_BIN="${PYTHON_BIN:-}"

MICROBENCH_LATEST_PREFIX="experiments/reports/latest_speculative_prefill_microbenchmark"
MICROBENCH_OUT_DIR="experiments/reports/speculative_prefill_microbenchmark/${BASE_ID}"
SHARED_CHART_DIR="experiments/charts"
LATEST_POINTERS=(
  "${MICROBENCH_LATEST_PREFIX}_contract_sh_path.txt"
  "${MICROBENCH_LATEST_PREFIX}_contract_doc_path.txt"
  "${MICROBENCH_LATEST_PREFIX}_last_mode.txt"
  "${MICROBENCH_LATEST_PREFIX}_last_probe_run_id.txt"
  "${MICROBENCH_LATEST_PREFIX}_last_sweep_run_ids.txt"
  "${MICROBENCH_LATEST_PREFIX}_plot_matrix_path.txt"
)
LATEST_REPORT_OUTPUTS=(
  "${MICROBENCH_LATEST_PREFIX}_matrix.csv"
  "${MICROBENCH_LATEST_PREFIX}_summary.csv"
  "${MICROBENCH_LATEST_PREFIX}_summary.md"
  "${MICROBENCH_LATEST_PREFIX}_run_contract.json"
  "${MICROBENCH_LATEST_PREFIX}_turnb_latency.svg"
  "${MICROBENCH_LATEST_PREFIX}_turnb_cached.svg"
  "${MICROBENCH_LATEST_PREFIX}_chart_manifest.json"
)

LAST_PROBE_RUN_ID=""
LAST_SWEEP_RUN_IDS=()

banner() {
  cat <<EOF
========================================
$1
========================================
EOF
}

prepare_shared_chart_dir() {
  mkdir -p "${SHARED_CHART_DIR}"
  find "${SHARED_CHART_DIR}" -maxdepth 1 -type f ! \( -name '*.svg' -o -name '*.csv' \) -delete
}

usage() {
  cat <<EOF
Usage:
  ./agentbench/run_speculative_prefill_microbenchmark_single_host.sh [model]

Modes:
  SPEC_PREFILL_MODE=probe   one live speculative-prefill run
  SPEC_PREFILL_MODE=sweep   multiple live runs over one sweep axis
  SPEC_PREFILL_MODE=all     sweep, then plot (default)
  SPEC_PREFILL_MODE=plot    rebuild charts from one existing matrix CSV
EOF
}

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

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${MODEL}" ]]; then
  echo "No model specified. Pass it as an argument or set MODEL / MODEL_NAME." >&2
  exit 1
fi

if [[ ! -x "${SPEC_PREFILL_PROBE_HELPER}" ]]; then
  echo "Speculative-prefill helper is missing or not executable: ${SPEC_PREFILL_PROBE_HELPER}" >&2
  exit 1
fi

print_contract_summary() {
  banner "SPECULATIVE PREFILL MICROBENCH CONTRACT"
  cat <<EOF
Contract file: ${CONTRACT_PATH}
Contract doc: ${CONTRACT_DOC_PATH}
Mode: ${SPEC_PREFILL_MODE}
Model: ${MODEL}
Machine profile: ${DYNAMO_MACHINE_PROFILE:-default}

Public wrapper:
  ${SPEC_PREFILL_PUBLIC_WRAPPER}

Internal helper:
  probe=${SPEC_PREFILL_PROBE_HELPER}

Runtime stack:
  dynamo_source_dir=${SPEC_PREFILL_DYNAMO_SOURCE_DIR}
  sglang_source_image=${SPEC_PREFILL_SGLANG_SOURCE_IMAGE}
  sglang_source_dir=${SPEC_PREFILL_SGLANG_SOURCE_DIR}
  frontend_image=${SPEC_PREFILL_FRONTEND_IMAGE}
  worker_image=${SPEC_PREFILL_WORKER_IMAGE}

Workload defaults:
  turn_a_words=${SPEC_PREFILL_TURN_A_WORDS}
  turn_b_words=${SPEC_PREFILL_TURN_B_WORDS}
  output_tokens=${SPEC_PREFILL_OUTPUT_TOKENS}
  warmup_wait_ms=${SPEC_PREFILL_WARMUP_WAIT_MS}
  sweep_axis=${SPEC_PREFILL_SWEEP_AXIS}
  sweep_values=${SPEC_PREFILL_SWEEP_VALUES}

Runtime defaults:
  attribution_mode=${SPEC_PREFILL_ATTRIBUTION_MODE}
  request_context_mode=${SPEC_PREFILL_REQUEST_CONTEXT_MODE}
  transfer_log_profile=${SGLANG_TRANSFER_LOG_PROFILE}
  worker_base_args=${WORKER_BASE_ARGS}
EOF
  printf '%s\n' "${CONTRACT_PATH}" > "${MICROBENCH_LATEST_PREFIX}_contract_sh_path.txt"
  printf '%s\n' "${CONTRACT_DOC_PATH}" > "${MICROBENCH_LATEST_PREFIX}_contract_doc_path.txt"
  printf '%s\n' "${SPEC_PREFILL_MODE}" > "${MICROBENCH_LATEST_PREFIX}_last_mode.txt"
}

clear_microbenchmark_latest_pointers() {
  rm -f "${LATEST_POINTERS[@]}"
}

reset_microbenchmark_outputs() {
  rm -f "${LATEST_REPORT_OUTPUTS[@]}"
  rm -rf "${MICROBENCH_OUT_DIR}"
  mkdir -p "${MICROBENCH_OUT_DIR}"
}

reset_microbenchmark_plot_outputs() {
  rm -f \
    "${MICROBENCH_LATEST_PREFIX}_turnb_latency.svg" \
    "${MICROBENCH_LATEST_PREFIX}_turnb_cached.svg" \
    "${MICROBENCH_LATEST_PREFIX}_chart_manifest.json"
  rm -rf "${MICROBENCH_OUT_DIR}"
  mkdir -p "${MICROBENCH_OUT_DIR}"
}

write_run_contract() {
  "${PYTHON_BIN}" - <<'PY' \
    "${MICROBENCH_OUT_DIR}/run_contract.json" \
    "${MODEL}" \
    "${CONTRACT_PATH}" \
    "${CONTRACT_DOC_PATH}" \
    "${SPEC_PREFILL_MODE}"
import json
import os
import sys

out_path = sys.argv[1]
model = sys.argv[2]
contract_sh = sys.argv[3]
contract_md = sys.argv[4]
mode = sys.argv[5]
keys = [
    "DYNAMO_MACHINE_PROFILE",
    "SPEC_PREFILL_MODE",
    "SPEC_PREFILL_ID",
    "SPEC_PREFILL_DYNAMO_SOURCE_DIR",
    "SPEC_PREFILL_SGLANG_SOURCE_IMAGE",
    "SPEC_PREFILL_SGLANG_SOURCE_DIR",
    "SPEC_PREFILL_FRONTEND_IMAGE",
    "SPEC_PREFILL_WORKER_IMAGE",
    "SPEC_PREFILL_ATTRIBUTION_MODE",
    "SPEC_PREFILL_REQUEST_CONTEXT_MODE",
    "SPEC_PREFILL_TURN_A_WORDS",
    "SPEC_PREFILL_TURN_B_WORDS",
    "SPEC_PREFILL_OUTPUT_TOKENS",
    "SPEC_PREFILL_WARMUP_WAIT_MS",
    "SPEC_PREFILL_SWEEP_AXIS",
    "SPEC_PREFILL_SWEEP_VALUES",
    "SGLANG_TRANSFER_LOG_PROFILE",
    "WORKER_BASE_ARGS",
    "MODEL_READY_RETRIES",
    "MODEL_READY_DELAY_SECS",
    "MODEL_READY_STABLE_HITS",
    "MODEL_SMOKE_RETRIES",
    "MODEL_SMOKE_DELAY_SECS",
    "MODEL_COOLDOWN_SECS",
]
payload = {k: os.environ.get(k, "") for k in keys}
payload["model"] = model
payload["contract_sh"] = contract_sh
payload["contract_md"] = contract_md
payload["mode"] = mode
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
  cp -f "${MICROBENCH_OUT_DIR}/run_contract.json" "${MICROBENCH_LATEST_PREFIX}_run_contract.json"
}

update_run_contract_with_helper_ids() {
  local sweep_csv=""
  if [[ "${#LAST_SWEEP_RUN_IDS[@]}" -gt 0 ]]; then
    local IFS=,
    sweep_csv="${LAST_SWEEP_RUN_IDS[*]}"
  fi
  "${PYTHON_BIN}" - <<'PY' "${MICROBENCH_OUT_DIR}/run_contract.json" "${LAST_PROBE_RUN_ID}" "${sweep_csv}"
import json
import sys
path = sys.argv[1]
probe_run_id = sys.argv[2]
sweep_run_ids = [item for item in sys.argv[3].split(",") if item]
with open(path, encoding="utf-8") as fh:
    payload = json.load(fh)
payload["probe_run_id"] = probe_run_id
payload["sweep_run_ids"] = sweep_run_ids
with open(path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
  cp -f "${MICROBENCH_OUT_DIR}/run_contract.json" "${MICROBENCH_LATEST_PREFIX}_run_contract.json"
}

build_microbenchmark_report() {
  local sweep_csv=""
  if [[ "${#LAST_SWEEP_RUN_IDS[@]}" -gt 0 ]]; then
    local IFS=,
    sweep_csv="${LAST_SWEEP_RUN_IDS[*]}"
  fi
  "${PYTHON_BIN}" experiments/scripts/speculative_prefill/build_speculative_prefill_microbenchmark_report.py \
    --run-id "${BASE_ID}" \
    --mode "${SPEC_PREFILL_MODE}" \
    --model "${MODEL}" \
    --out-dir "${MICROBENCH_OUT_DIR}" \
    --contract-sh "${CONTRACT_PATH}" \
    --contract-md "${CONTRACT_DOC_PATH}" \
    --probe-run-id "${LAST_PROBE_RUN_ID}" \
    --sweep-run-ids "${sweep_csv}" \
    --sweep-axis "${SPEC_PREFILL_SWEEP_AXIS}" \
    --sweep-values "${SPEC_PREFILL_SWEEP_VALUES}"
  cp -f "${MICROBENCH_OUT_DIR}/microbenchmark_matrix.csv" "${MICROBENCH_LATEST_PREFIX}_matrix.csv"
  cp -f "${MICROBENCH_OUT_DIR}/microbenchmark_summary.csv" "${MICROBENCH_LATEST_PREFIX}_summary.csv"
  cp -f "${MICROBENCH_OUT_DIR}/microbenchmark_summary.md" "${MICROBENCH_LATEST_PREFIX}_summary.md"
  cp -f "${MICROBENCH_OUT_DIR}/run_contract.json" "${MICROBENCH_LATEST_PREFIX}_run_contract.json"
}

build_microbenchmark_charts() {
  local matrix_csv="$1"
  prepare_shared_chart_dir
  if [[ -f "${matrix_csv}" ]]; then
    cp -f "${matrix_csv}" "${SHARED_CHART_DIR}/latest_speculative_prefill_microbenchmark_matrix.csv"
  fi
  "${PYTHON_BIN}" experiments/scripts/speculative_prefill/plot_speculative_prefill_microbenchmark.py \
    --matrix-csv "${matrix_csv}" \
    --out-dir "${MICROBENCH_OUT_DIR}/charts"
  if [[ -f "${MICROBENCH_OUT_DIR}/charts/turnb_latency.svg" ]]; then
    cp -f "${MICROBENCH_OUT_DIR}/charts/turnb_latency.svg" "${MICROBENCH_LATEST_PREFIX}_turnb_latency.svg"
    cp -f "${MICROBENCH_OUT_DIR}/charts/turnb_latency.svg" "${SHARED_CHART_DIR}/latest_speculative_prefill_microbenchmark_turnb_latency.svg"
  fi
  if [[ -f "${MICROBENCH_OUT_DIR}/charts/turnb_cached.svg" ]]; then
    cp -f "${MICROBENCH_OUT_DIR}/charts/turnb_cached.svg" "${MICROBENCH_LATEST_PREFIX}_turnb_cached.svg"
    cp -f "${MICROBENCH_OUT_DIR}/charts/turnb_cached.svg" "${SHARED_CHART_DIR}/latest_speculative_prefill_microbenchmark_turnb_cached.svg"
  fi
  if [[ -f "${MICROBENCH_OUT_DIR}/charts/chart_manifest.json" ]]; then
    cp -f "${MICROBENCH_OUT_DIR}/charts/chart_manifest.json" "${MICROBENCH_LATEST_PREFIX}_chart_manifest.json"
  fi
}

run_probe_mode() {
  local run_id="${BASE_ID}__probe"
  banner "SPECULATIVE PREFILL MICROBENCH PROBE"
  env \
    DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}" \
    FRONTEND_IMAGE="${SPEC_PREFILL_FRONTEND_IMAGE}" \
    WORKER_IMAGE="${SPEC_PREFILL_WORKER_IMAGE}" \
    SPEC_PREFILL_ID="${run_id}" \
    SPEC_PREFILL_ATTRIBUTION_MODE="${SPEC_PREFILL_ATTRIBUTION_MODE}" \
    SPEC_PREFILL_REQUEST_CONTEXT_MODE="${SPEC_PREFILL_REQUEST_CONTEXT_MODE}" \
    SPEC_PREFILL_TURN_A_WORDS="${SPEC_PREFILL_TURN_A_WORDS}" \
    SPEC_PREFILL_TURN_B_WORDS="${SPEC_PREFILL_TURN_B_WORDS}" \
    SPEC_PREFILL_OUTPUT_TOKENS="${SPEC_PREFILL_OUTPUT_TOKENS}" \
    SPEC_PREFILL_WARMUP_WAIT_MS="${SPEC_PREFILL_WARMUP_WAIT_MS}" \
    SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
    MODEL_READY_RETRIES="${MODEL_READY_RETRIES}" \
    MODEL_READY_DELAY_SECS="${MODEL_READY_DELAY_SECS}" \
    MODEL_READY_STABLE_HITS="${MODEL_READY_STABLE_HITS}" \
    MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES}" \
    MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS}" \
    MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS}" \
    STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE}" \
    WORKER_BASE_ARGS="${WORKER_BASE_ARGS}" \
    AUTO_BUILD_PRECISE_IMAGES="${AUTO_BUILD_PRECISE_IMAGES}" \
    "${SPEC_PREFILL_PROBE_HELPER}" "${MODEL}"
  printf '%s\n' "${run_id}" > "${MICROBENCH_LATEST_PREFIX}_last_probe_run_id.txt"
  LAST_PROBE_RUN_ID="${run_id}"
}

run_sweep_mode() {
  local sweep_axis="${SPEC_PREFILL_SWEEP_AXIS}"
  local -a sweep_values
  read -r -a sweep_values <<< "${SPEC_PREFILL_SWEEP_VALUES}"
  if [[ "${#sweep_values[@]}" -eq 0 ]]; then
    echo "Sweep mode needs at least one value in SPEC_PREFILL_SWEEP_VALUES." >&2
    exit 2
  fi
  banner "SPECULATIVE PREFILL MICROBENCH SWEEP"
  echo "Sweep axis: ${sweep_axis}"
  echo "Sweep values: ${SPEC_PREFILL_SWEEP_VALUES}"
  LAST_SWEEP_RUN_IDS=()
  local idx=0
  for value in "${sweep_values[@]}"; do
    idx=$((idx + 1))
    local run_id="${BASE_ID}__sweep_${idx}"
    echo "[${idx}/${#sweep_values[@]}] ${sweep_axis}=${value}"
    env \
      DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}" \
      FRONTEND_IMAGE="${SPEC_PREFILL_FRONTEND_IMAGE}" \
      WORKER_IMAGE="${SPEC_PREFILL_WORKER_IMAGE}" \
      SPEC_PREFILL_ID="${run_id}" \
      SPEC_PREFILL_ATTRIBUTION_MODE="${SPEC_PREFILL_ATTRIBUTION_MODE}" \
      SPEC_PREFILL_REQUEST_CONTEXT_MODE="${SPEC_PREFILL_REQUEST_CONTEXT_MODE}" \
      SPEC_PREFILL_TURN_A_WORDS="${SPEC_PREFILL_TURN_A_WORDS}" \
      SPEC_PREFILL_TURN_B_WORDS="${SPEC_PREFILL_TURN_B_WORDS}" \
      SPEC_PREFILL_OUTPUT_TOKENS="${SPEC_PREFILL_OUTPUT_TOKENS}" \
      SPEC_PREFILL_WARMUP_WAIT_MS="${SPEC_PREFILL_WARMUP_WAIT_MS}" \
      SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
      MODEL_READY_RETRIES="${MODEL_READY_RETRIES}" \
      MODEL_READY_DELAY_SECS="${MODEL_READY_DELAY_SECS}" \
      MODEL_READY_STABLE_HITS="${MODEL_READY_STABLE_HITS}" \
      MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES}" \
      MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS}" \
      MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS}" \
      STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE}" \
      WORKER_BASE_ARGS="${WORKER_BASE_ARGS}" \
      AUTO_BUILD_PRECISE_IMAGES="${AUTO_BUILD_PRECISE_IMAGES}" \
      "${sweep_axis}=${value}" \
      "${SPEC_PREFILL_PROBE_HELPER}" "${MODEL}"
    LAST_SWEEP_RUN_IDS+=("${run_id}")
  done
  if [[ "${#LAST_SWEEP_RUN_IDS[@]}" -gt 0 ]]; then
    printf '%s\n' "${LAST_SWEEP_RUN_IDS[*]}" > "${MICROBENCH_LATEST_PREFIX}_last_sweep_run_ids.txt"
  fi
}

run_plot_mode() {
  local matrix_csv="${SPEC_PREFILL_PLOT_MATRIX_CSV:-${MICROBENCH_LATEST_PREFIX}_matrix.csv}"
  if [[ ! -f "${matrix_csv}" ]]; then
    echo "Plot mode needs a matrix CSV to read from." >&2
    echo "Set SPEC_PREFILL_PLOT_MATRIX_CSV or run probe/all first." >&2
    exit 2
  fi
  banner "SPECULATIVE PREFILL MICROBENCH PLOT"
  echo "Building charts from: ${matrix_csv}"
  printf '%s\n' "${matrix_csv}" > "${MICROBENCH_LATEST_PREFIX}_plot_matrix_path.txt"
  build_microbenchmark_charts "${matrix_csv}"
}

print_final_status() {
  banner "SPECULATIVE PREFILL MICROBENCH READY"
  if [[ "${SPEC_PREFILL_MODE}" = "plot" ]]; then
    cat <<EOF
Run directory: ${MICROBENCH_OUT_DIR}
Run contract: ${MICROBENCH_OUT_DIR}/run_contract.json
Chart source matrix: ${SPEC_PREFILL_PLOT_MATRIX_CSV:-${MICROBENCH_LATEST_PREFIX}_matrix.csv}
Turn B latency chart: ${MICROBENCH_OUT_DIR}/charts/turnb_latency.svg
Turn B cached chart: ${MICROBENCH_OUT_DIR}/charts/turnb_cached.svg
EOF
    return
  fi
  cat <<EOF
Run directory: ${MICROBENCH_OUT_DIR}
Run contract: ${MICROBENCH_OUT_DIR}/run_contract.json
Microbenchmark matrix: ${MICROBENCH_OUT_DIR}/microbenchmark_matrix.csv
Microbenchmark summary: ${MICROBENCH_OUT_DIR}/microbenchmark_summary.csv
Microbenchmark summary md: ${MICROBENCH_OUT_DIR}/microbenchmark_summary.md
Turn B latency chart: ${MICROBENCH_OUT_DIR}/charts/turnb_latency.svg
Turn B cached chart: ${MICROBENCH_OUT_DIR}/charts/turnb_cached.svg
Last probe run id: ${LAST_PROBE_RUN_ID:-<none>}
Sweep run ids: ${LAST_SWEEP_RUN_IDS[*]:-<none>}
EOF
}

clear_microbenchmark_latest_pointers
if [[ "${SPEC_PREFILL_MODE}" = "plot" ]]; then
  reset_microbenchmark_plot_outputs
else
  reset_microbenchmark_outputs
fi

print_contract_summary
write_run_contract

case "${SPEC_PREFILL_MODE}" in
  probe)
    run_probe_mode
    ;;
  sweep)
    run_sweep_mode
    ;;
  all)
    run_sweep_mode
    ;;
  plot)
    run_plot_mode
    ;;
  *)
    echo "Unknown SPEC_PREFILL_MODE: ${SPEC_PREFILL_MODE}" >&2
    usage >&2
    exit 2
    ;;
esac

update_run_contract_with_helper_ids
if [[ "${SPEC_PREFILL_MODE}" != "plot" ]]; then
  build_microbenchmark_report
  build_microbenchmark_charts "${MICROBENCH_OUT_DIR}/microbenchmark_matrix.csv"
fi

print_final_status
