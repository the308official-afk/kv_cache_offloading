#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh
if [[ -f runtime_instrumentation/dynamo_machine_profile.sh ]]; then
  # shellcheck disable=SC1091
  source runtime_instrumentation/dynamo_machine_profile.sh
fi

CONTRACT_PATH="${CONTRACT_PATH:-contracts/priority_scheduling_microbenchmark.contract.sh}"
CONTRACT_DOC_PATH="${CONTRACT_DOC_PATH:-contracts/priority_scheduling_microbenchmark.contract.md}"
if [[ ! -f "${CONTRACT_PATH}" ]]; then
  echo "Missing machine-readable contract: ${CONTRACT_PATH}" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "${CONTRACT_PATH}"

MODEL="${1:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}"
BASE_ID="${PRIORITY_SCHEDULING_ID:-priority_scheduling_microbenchmark_$(date +%Y%m%d_%H%M%S)}"
PYTHON_BIN="${PYTHON_BIN:-}"
PRIORITY_PROBE_SEED="${PRIORITY_PROBE_SEED:-42}"
PRIORITY_SCHEDULING_SWEEP_SEED_MODE="${PRIORITY_SCHEDULING_SWEEP_SEED_MODE:-fixed}"

MICROBENCH_LATEST_PREFIX="experiments/reports/latest_priority_scheduling_microbenchmark"
MICROBENCH_OUT_DIR="experiments/reports/priority_scheduling_microbenchmark/${BASE_ID}"
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
  "${MICROBENCH_LATEST_PREFIX}_attach_gain.svg"
  "${MICROBENCH_LATEST_PREFIX}_queue_wait.svg"
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
  find "${SHARED_CHART_DIR}" -maxdepth 1 -type f ! \( -name '*.svg' -o -name '*.csv' -o -name 'README.md' \) -delete
  rm -f \
    "${SHARED_CHART_DIR}/latest_priority_scheduling_microbenchmark_matrix.csv" \
    "${SHARED_CHART_DIR}/latest_priority_scheduling_microbenchmark_attach_gain.svg" \
    "${SHARED_CHART_DIR}/latest_priority_scheduling_microbenchmark_queue_wait.svg" \
    "${SHARED_CHART_DIR}/exp11_prioritysched_matrix.csv" \
    "${SHARED_CHART_DIR}/exp11_prioritysched_priority_wins_vs_arrival_gap.svg" \
    "${SHARED_CHART_DIR}/exp11_prioritysched_wait_vs_arrival_gap.svg" \
    "${SHARED_CHART_DIR}/exp11_prioritysched_wait_gain_vs_arrival_gap.svg" \
    "${SHARED_CHART_DIR}/exp11_prioritysched_latency_vs_arrival_gap.svg" \
    "${SHARED_CHART_DIR}/exp11_prioritysched_latency_gain_vs_arrival_gap.svg"
}

usage() {
  cat <<EOF
Usage:
  ./agentbench/run_priority_scheduling_microbenchmark_single_host.sh [model]

Modes:
  PRIORITY_SCHEDULING_MODE=probe   one live priority-scheduling run
  PRIORITY_SCHEDULING_MODE=sweep   multiple live runs over one sweep axis
  PRIORITY_SCHEDULING_MODE=all     sweep, then plot (default)
  PRIORITY_SCHEDULING_MODE=plot    rebuild charts from one existing matrix CSV
EOF
}

derive_priority_probe_seed() {
  local base_seed="$1"
  local value_index="$2"
  local sweep_value="$3"
  case "${PRIORITY_SCHEDULING_SWEEP_SEED_MODE}" in
    fixed)
      echo "${base_seed}"
      ;;
    per_value)
      echo $((base_seed + value_index * 1000 + sweep_value))
      ;;
    *)
      echo "Unknown PRIORITY_SCHEDULING_SWEEP_SEED_MODE: ${PRIORITY_SCHEDULING_SWEEP_SEED_MODE}" >&2
      return 2
      ;;
  esac
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

if [[ ! -x "${PRIORITY_SCHEDULING_PROBE_HELPER}" ]]; then
  echo "Priority scheduling helper is missing or not executable: ${PRIORITY_SCHEDULING_PROBE_HELPER}" >&2
  exit 1
fi

print_contract_summary() {
  banner "PRIORITY SCHEDULING MICROBENCH CONTRACT"
  cat <<EOF
Contract file: ${CONTRACT_PATH}
Contract doc: ${CONTRACT_DOC_PATH}
Mode: ${PRIORITY_SCHEDULING_MODE}
Model: ${MODEL}
Machine profile: ${DYNAMO_MACHINE_PROFILE:-default}

Public wrapper:
  ${PRIORITY_SCHEDULING_PUBLIC_WRAPPER}

Internal helper:
  probe=${PRIORITY_SCHEDULING_PROBE_HELPER}

Runtime stack:
  dynamo_source_dir=${PRIORITY_SCHEDULING_DYNAMO_SOURCE_DIR}
  sglang_source_image=${PRIORITY_SCHEDULING_SGLANG_SOURCE_IMAGE}
  sglang_source_dir=${PRIORITY_SCHEDULING_SGLANG_SOURCE_DIR}
  frontend_image=${PRIORITY_SCHEDULING_FRONTEND_IMAGE}
  worker_image=${PRIORITY_SCHEDULING_WORKER_IMAGE}

Workload defaults:
  low_priority_count=${LOW_PRIORITY_COUNT}
  high_priority_count=${HIGH_PRIORITY_COUNT}
  low_priority_value=${LOW_PRIORITY_VALUE}
  high_priority_value=${HIGH_PRIORITY_VALUE}
  input_len_words=${PRIORITY_INPUT_LEN}
  output_len_tokens=${PRIORITY_OUTPUT_LEN}
  arrival_gap_ms=${PRIORITY_ARRIVAL_GAP_MS}
  inter_request_gap_ms=${PRIORITY_INTER_REQUEST_GAP_MS}
  sweep_axis=${PRIORITY_SCHEDULING_SWEEP_AXIS}
  sweep_values=${PRIORITY_SCHEDULING_SWEEP_VALUES}

Runtime defaults:
  attribution_mode=${PRIORITY_SCHEDULING_ATTRIBUTION_MODE}
  request_context_mode=${PRIORITY_REQUEST_CONTEXT_MODE}
  top_level_priority_mode=${PRIORITY_TOP_LEVEL_PRIORITY_MODE}
  experiment_reset_mode=${EXPERIMENT_RESET_MODE}
  transfer_log_profile=${SGLANG_TRANSFER_LOG_PROFILE}
  worker_base_args=${WORKER_BASE_ARGS}
  probe_seed=${PRIORITY_PROBE_SEED}
  sweep_seed_mode=${PRIORITY_SCHEDULING_SWEEP_SEED_MODE}
EOF
  printf '%s\n' "${CONTRACT_PATH}" > "${MICROBENCH_LATEST_PREFIX}_contract_sh_path.txt"
  printf '%s\n' "${CONTRACT_DOC_PATH}" > "${MICROBENCH_LATEST_PREFIX}_contract_doc_path.txt"
  printf '%s\n' "${PRIORITY_SCHEDULING_MODE}" > "${MICROBENCH_LATEST_PREFIX}_last_mode.txt"
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
    "${MICROBENCH_LATEST_PREFIX}_attach_gain.svg" \
    "${MICROBENCH_LATEST_PREFIX}_queue_wait.svg" \
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
    "${PRIORITY_SCHEDULING_MODE}"
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
    "PRIORITY_SCHEDULING_MODE",
    "PRIORITY_SCHEDULING_ID",
    "PRIORITY_SCHEDULING_DYNAMO_SOURCE_DIR",
    "PRIORITY_SCHEDULING_SGLANG_SOURCE_IMAGE",
    "PRIORITY_SCHEDULING_SGLANG_SOURCE_DIR",
    "PRIORITY_SCHEDULING_FRONTEND_IMAGE",
    "PRIORITY_SCHEDULING_WORKER_IMAGE",
    "PRIORITY_SCHEDULING_ATTRIBUTION_MODE",
    "PRIORITY_REQUEST_CONTEXT_MODE",
    "PRIORITY_TOP_LEVEL_PRIORITY_MODE",
    "EXPERIMENT_RESET_MODE",
    "LOW_PRIORITY_COUNT",
    "HIGH_PRIORITY_COUNT",
    "LOW_PRIORITY_VALUE",
    "HIGH_PRIORITY_VALUE",
    "PRIORITY_INPUT_LEN",
    "PRIORITY_OUTPUT_LEN",
    "PRIORITY_ARRIVAL_GAP_MS",
    "PRIORITY_INTER_REQUEST_GAP_MS",
    "PRIORITY_SCHEDULING_SWEEP_AXIS",
    "PRIORITY_SCHEDULING_SWEEP_VALUES",
    "SGLANG_TRANSFER_LOG_PROFILE",
    "WORKER_BASE_ARGS",
    "MODEL_READY_RETRIES",
    "MODEL_READY_DELAY_SECS",
    "MODEL_READY_STABLE_HITS",
    "MODEL_SMOKE_RETRIES",
    "MODEL_SMOKE_DELAY_SECS",
    "MODEL_COOLDOWN_SECS",
    "PRIORITY_PROBE_SEED",
    "PRIORITY_SCHEDULING_SWEEP_SEED_MODE",
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
  "${PYTHON_BIN}" experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py \
    --run-id "${BASE_ID}" \
    --mode "${PRIORITY_SCHEDULING_MODE}" \
    --model "${MODEL}" \
    --out-dir "${MICROBENCH_OUT_DIR}" \
    --contract-sh "${CONTRACT_PATH}" \
    --contract-md "${CONTRACT_DOC_PATH}" \
    --probe-run-id "${LAST_PROBE_RUN_ID}" \
    --sweep-run-ids "${sweep_csv}" \
    --sweep-axis "${PRIORITY_SCHEDULING_SWEEP_AXIS}" \
    --sweep-values "${PRIORITY_SCHEDULING_SWEEP_VALUES}"

  cp -f "${MICROBENCH_OUT_DIR}/microbenchmark_matrix.csv" "${MICROBENCH_LATEST_PREFIX}_matrix.csv"
  cp -f "${MICROBENCH_OUT_DIR}/microbenchmark_summary.csv" "${MICROBENCH_LATEST_PREFIX}_summary.csv"
  cp -f "${MICROBENCH_OUT_DIR}/microbenchmark_summary.md" "${MICROBENCH_LATEST_PREFIX}_summary.md"
  cp -f "${MICROBENCH_OUT_DIR}/run_contract.json" "${MICROBENCH_LATEST_PREFIX}_run_contract.json"
}

build_microbenchmark_charts() {
  local matrix_csv="$1"
  prepare_shared_chart_dir
  if [[ -f "${matrix_csv}" ]]; then
    cp -f "${matrix_csv}" "${SHARED_CHART_DIR}/exp11_prioritysched_matrix.csv"
  fi
  "${PYTHON_BIN}" experiments/scripts/priority_scheduling/plot_priority_scheduling_microbenchmark.py \
    --matrix-csv "${matrix_csv}" \
    --out-dir "${MICROBENCH_OUT_DIR}/charts"
  if [[ -f "${MICROBENCH_OUT_DIR}/charts/attach_gain.svg" ]]; then
    cp -f "${MICROBENCH_OUT_DIR}/charts/attach_gain.svg" "${MICROBENCH_LATEST_PREFIX}_attach_gain.svg"
  fi
  if [[ -f "${MICROBENCH_OUT_DIR}/charts/priority_wins.svg" ]]; then
    cp -f "${MICROBENCH_OUT_DIR}/charts/priority_wins.svg" "${MICROBENCH_LATEST_PREFIX}_attach_gain.svg"
  fi
  if [[ -f "${MICROBENCH_OUT_DIR}/charts/queue_wait.svg" ]]; then
    cp -f "${MICROBENCH_OUT_DIR}/charts/queue_wait.svg" "${MICROBENCH_LATEST_PREFIX}_queue_wait.svg"
  fi
  [[ -f "${MICROBENCH_OUT_DIR}/charts/priority_wins.svg" ]] && cp -f "${MICROBENCH_OUT_DIR}/charts/priority_wins.svg" "${MICROBENCH_LATEST_PREFIX}_priority_wins.svg"
  [[ -f "${MICROBENCH_OUT_DIR}/charts/wait_gain.svg" ]] && cp -f "${MICROBENCH_OUT_DIR}/charts/wait_gain.svg" "${MICROBENCH_LATEST_PREFIX}_wait_gain.svg"
  [[ -f "${MICROBENCH_OUT_DIR}/charts/latency_vs_arrival_gap.svg" ]] && cp -f "${MICROBENCH_OUT_DIR}/charts/latency_vs_arrival_gap.svg" "${MICROBENCH_LATEST_PREFIX}_latency_vs_arrival_gap.svg"
  [[ -f "${MICROBENCH_OUT_DIR}/charts/latency_gain.svg" ]] && cp -f "${MICROBENCH_OUT_DIR}/charts/latency_gain.svg" "${MICROBENCH_LATEST_PREFIX}_latency_gain.svg"
  [[ -f "${MICROBENCH_OUT_DIR}/charts/priority_wins.svg" ]] && cp -f "${MICROBENCH_OUT_DIR}/charts/priority_wins.svg" "${SHARED_CHART_DIR}/exp11_prioritysched_priority_wins_vs_arrival_gap.svg"
  [[ -f "${MICROBENCH_OUT_DIR}/charts/queue_wait.svg" ]] && cp -f "${MICROBENCH_OUT_DIR}/charts/queue_wait.svg" "${SHARED_CHART_DIR}/exp11_prioritysched_wait_vs_arrival_gap.svg"
  [[ -f "${MICROBENCH_OUT_DIR}/charts/wait_gain.svg" ]] && cp -f "${MICROBENCH_OUT_DIR}/charts/wait_gain.svg" "${SHARED_CHART_DIR}/exp11_prioritysched_wait_gain_vs_arrival_gap.svg"
  [[ -f "${MICROBENCH_OUT_DIR}/charts/latency_vs_arrival_gap.svg" ]] && cp -f "${MICROBENCH_OUT_DIR}/charts/latency_vs_arrival_gap.svg" "${SHARED_CHART_DIR}/exp11_prioritysched_latency_vs_arrival_gap.svg"
  [[ -f "${MICROBENCH_OUT_DIR}/charts/latency_gain.svg" ]] && cp -f "${MICROBENCH_OUT_DIR}/charts/latency_gain.svg" "${SHARED_CHART_DIR}/exp11_prioritysched_latency_gain_vs_arrival_gap.svg"
  if [[ -f "${MICROBENCH_OUT_DIR}/charts/chart_manifest.json" ]]; then
    cp -f "${MICROBENCH_OUT_DIR}/charts/chart_manifest.json" "${MICROBENCH_LATEST_PREFIX}_chart_manifest.json"
  fi
}

finalize_runtime_cleanup() {
  if [[ "${STOP_DYNAMO_WHEN_DONE}" != "1" || "${PRIORITY_SCHEDULING_MODE}" = "plot" ]]; then
    return 0
  fi
  echo "Final cleanup: stopping Dynamo once after priority scheduling microbenchmark."
  ./run_dynamo_single_host.sh stop >/dev/null 2>&1 || true
  env EXPERIMENT_RESET_STATE_FILE="${EXPERIMENT_RESET_STATE_FILE:-experiments/runtime_state/active_runtime_signature.txt}" \
    ./runtime_instrumentation/reset_experiment_state.sh clear-active >/dev/null 2>&1 || true
}

run_probe_mode() {
  local run_id="${BASE_ID}__probe"
  banner "PRIORITY SCHEDULING MICROBENCH PROBE"
  env \
    DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}" \
    FRONTEND_IMAGE="${PRIORITY_SCHEDULING_FRONTEND_IMAGE}" \
    WORKER_IMAGE="${PRIORITY_SCHEDULING_WORKER_IMAGE}" \
    PRIORITY_SCHEDULING_ID="${run_id}" \
    PRIORITY_SCHEDULING_ATTRIBUTION_MODE="${PRIORITY_SCHEDULING_ATTRIBUTION_MODE}" \
    PRIORITY_REQUEST_CONTEXT_MODE="${PRIORITY_REQUEST_CONTEXT_MODE}" \
    PRIORITY_TOP_LEVEL_PRIORITY_MODE="${PRIORITY_TOP_LEVEL_PRIORITY_MODE}" \
    LOW_PRIORITY_COUNT="${LOW_PRIORITY_COUNT}" \
    HIGH_PRIORITY_COUNT="${HIGH_PRIORITY_COUNT}" \
    LOW_PRIORITY_VALUE="${LOW_PRIORITY_VALUE}" \
    HIGH_PRIORITY_VALUE="${HIGH_PRIORITY_VALUE}" \
    PRIORITY_INPUT_LEN="${PRIORITY_INPUT_LEN}" \
    PRIORITY_OUTPUT_LEN="${PRIORITY_OUTPUT_LEN}" \
    PRIORITY_ARRIVAL_GAP_MS="${PRIORITY_ARRIVAL_GAP_MS}" \
    PRIORITY_INTER_REQUEST_GAP_MS="${PRIORITY_INTER_REQUEST_GAP_MS}" \
    REQUEST_TIMEOUT="${REQUEST_TIMEOUT}" \
    SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
    MODEL_READY_RETRIES="${MODEL_READY_RETRIES}" \
    MODEL_READY_DELAY_SECS="${MODEL_READY_DELAY_SECS}" \
    MODEL_READY_STABLE_HITS="${MODEL_READY_STABLE_HITS}" \
    MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES}" \
    MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS}" \
    MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS}" \
    STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE}" \
    WORKER_BASE_ARGS="${WORKER_BASE_ARGS}" \
    IGNORE_EOS="${IGNORE_EOS}" \
    EXPERIMENT_RESET_MODE="${EXPERIMENT_RESET_MODE}" \
    PRIORITY_PROBE_SEED="${PRIORITY_PROBE_SEED}" \
    AUTO_BUILD_PRECISE_IMAGES="${AUTO_BUILD_PRECISE_IMAGES}" \
    "${PRIORITY_SCHEDULING_PROBE_HELPER}" "${MODEL}"
  printf '%s\n' "${run_id}" > "${MICROBENCH_LATEST_PREFIX}_last_probe_run_id.txt"
  LAST_PROBE_RUN_ID="${run_id}"
}

run_sweep_mode() {
  local sweep_axis="${PRIORITY_SCHEDULING_SWEEP_AXIS}"
  local -a sweep_values
  read -r -a sweep_values <<< "${PRIORITY_SCHEDULING_SWEEP_VALUES}"
  if [[ "${#sweep_values[@]}" -eq 0 ]]; then
    echo "Sweep mode needs at least one value in PRIORITY_SCHEDULING_SWEEP_VALUES." >&2
    exit 2
  fi
  banner "PRIORITY SCHEDULING MICROBENCH SWEEP"
  echo "Sweep axis: ${sweep_axis}"
  echo "Sweep values: ${PRIORITY_SCHEDULING_SWEEP_VALUES}"
  LAST_SWEEP_RUN_IDS=()
  local idx=0
  for value in "${sweep_values[@]}"; do
    idx=$((idx + 1))
    local run_id="${BASE_ID}__sweep_${idx}"
    local run_seed
    run_seed="$(derive_priority_probe_seed "${PRIORITY_PROBE_SEED}" "${idx}" "${value}")"
    echo "[${idx}/${#sweep_values[@]}] ${sweep_axis}=${value} priority_probe_seed=${run_seed}"
    env \
      DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}" \
      FRONTEND_IMAGE="${PRIORITY_SCHEDULING_FRONTEND_IMAGE}" \
      WORKER_IMAGE="${PRIORITY_SCHEDULING_WORKER_IMAGE}" \
      PRIORITY_SCHEDULING_ID="${run_id}" \
      PRIORITY_SCHEDULING_ATTRIBUTION_MODE="${PRIORITY_SCHEDULING_ATTRIBUTION_MODE}" \
      PRIORITY_REQUEST_CONTEXT_MODE="${PRIORITY_REQUEST_CONTEXT_MODE}" \
      PRIORITY_TOP_LEVEL_PRIORITY_MODE="${PRIORITY_TOP_LEVEL_PRIORITY_MODE}" \
      LOW_PRIORITY_COUNT="${LOW_PRIORITY_COUNT}" \
      HIGH_PRIORITY_COUNT="${HIGH_PRIORITY_COUNT}" \
      LOW_PRIORITY_VALUE="${LOW_PRIORITY_VALUE}" \
      HIGH_PRIORITY_VALUE="${HIGH_PRIORITY_VALUE}" \
      PRIORITY_INPUT_LEN="${PRIORITY_INPUT_LEN}" \
      PRIORITY_OUTPUT_LEN="${PRIORITY_OUTPUT_LEN}" \
      PRIORITY_ARRIVAL_GAP_MS="${PRIORITY_ARRIVAL_GAP_MS}" \
      PRIORITY_INTER_REQUEST_GAP_MS="${PRIORITY_INTER_REQUEST_GAP_MS}" \
      REQUEST_TIMEOUT="${REQUEST_TIMEOUT}" \
      SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
      MODEL_READY_RETRIES="${MODEL_READY_RETRIES}" \
      MODEL_READY_DELAY_SECS="${MODEL_READY_DELAY_SECS}" \
      MODEL_READY_STABLE_HITS="${MODEL_READY_STABLE_HITS}" \
      MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES}" \
      MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS}" \
      MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS}" \
      STOP_DYNAMO_WHEN_DONE="0" \
      WORKER_BASE_ARGS="${WORKER_BASE_ARGS}" \
      IGNORE_EOS="${IGNORE_EOS}" \
      EXPERIMENT_RESET_MODE="${EXPERIMENT_RESET_MODE}" \
      PRIORITY_PROBE_SEED="${run_seed}" \
      AUTO_BUILD_PRECISE_IMAGES="${AUTO_BUILD_PRECISE_IMAGES}" \
      "${sweep_axis}=${value}" \
      "${PRIORITY_SCHEDULING_PROBE_HELPER}" "${MODEL}"
    LAST_SWEEP_RUN_IDS+=("${run_id}")
  done
  if [[ "${#LAST_SWEEP_RUN_IDS[@]}" -gt 0 ]]; then
    printf '%s\n' "${LAST_SWEEP_RUN_IDS[*]}" > "${MICROBENCH_LATEST_PREFIX}_last_sweep_run_ids.txt"
  fi
}

run_plot_mode() {
  local matrix_csv="${PRIORITY_SCHEDULING_PLOT_MATRIX_CSV:-${MICROBENCH_LATEST_PREFIX}_matrix.csv}"
  if [[ ! -f "${matrix_csv}" ]]; then
    echo "Plot mode needs a matrix CSV to read from." >&2
    echo "Set PRIORITY_SCHEDULING_PLOT_MATRIX_CSV or run probe/all first." >&2
    exit 2
  fi
  banner "PRIORITY SCHEDULING MICROBENCH PLOT"
  echo "Building charts from: ${matrix_csv}"
  printf '%s\n' "${matrix_csv}" > "${MICROBENCH_LATEST_PREFIX}_plot_matrix_path.txt"
  build_microbenchmark_charts "${matrix_csv}"
}

print_final_status() {
  banner "PRIORITY SCHEDULING MICROBENCH READY"
  if [[ "${PRIORITY_SCHEDULING_MODE}" = "plot" ]]; then
    cat <<EOF
Run directory: ${MICROBENCH_OUT_DIR}
Run contract: ${MICROBENCH_OUT_DIR}/run_contract.json
Chart source matrix: ${PRIORITY_SCHEDULING_PLOT_MATRIX_CSV:-${MICROBENCH_LATEST_PREFIX}_matrix.csv}
Attach gain chart: ${MICROBENCH_OUT_DIR}/charts/attach_gain.svg
Queue wait chart: ${MICROBENCH_OUT_DIR}/charts/queue_wait.svg
EOF
    return
  fi
  cat <<EOF
Run directory: ${MICROBENCH_OUT_DIR}
Run contract: ${MICROBENCH_OUT_DIR}/run_contract.json
Microbenchmark matrix: ${MICROBENCH_OUT_DIR}/microbenchmark_matrix.csv
Microbenchmark summary: ${MICROBENCH_OUT_DIR}/microbenchmark_summary.csv
Microbenchmark summary md: ${MICROBENCH_OUT_DIR}/microbenchmark_summary.md
Attach gain chart: ${MICROBENCH_OUT_DIR}/charts/attach_gain.svg
Queue wait chart: ${MICROBENCH_OUT_DIR}/charts/queue_wait.svg
Last probe run id: ${LAST_PROBE_RUN_ID:-<none>}
Sweep run ids: ${LAST_SWEEP_RUN_IDS[*]:-<none>}
EOF
}

clear_microbenchmark_latest_pointers
if [[ "${PRIORITY_SCHEDULING_MODE}" = "plot" ]]; then
  reset_microbenchmark_plot_outputs
else
  reset_microbenchmark_outputs
fi

print_contract_summary
write_run_contract

case "${PRIORITY_SCHEDULING_MODE}" in
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
    echo "Unknown PRIORITY_SCHEDULING_MODE: ${PRIORITY_SCHEDULING_MODE}" >&2
    usage >&2
    exit 2
    ;;
esac

update_run_contract_with_helper_ids
if [[ "${PRIORITY_SCHEDULING_MODE}" != "plot" ]]; then
  build_microbenchmark_report
  build_microbenchmark_charts "${MICROBENCH_OUT_DIR}/microbenchmark_matrix.csv"
fi

finalize_runtime_cleanup

print_final_status
