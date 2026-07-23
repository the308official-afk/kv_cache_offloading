#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh
if [[ -f runtime_instrumentation/dynamo_machine_profile.sh ]]; then
  # shellcheck disable=SC1091
  source runtime_instrumentation/dynamo_machine_profile.sh
fi
EXPERIMENT_DIRS_HELPER="${EXPERIMENT_DIRS_HELPER:-./runtime_instrumentation/ensure_experiment_dirs_ready.sh}"
PRECISE_CLEAN_START_HELPER="${PRECISE_CLEAN_START_HELPER:-./runtime_instrumentation/ensure_precise_clean_start.sh}"

CONTRACT_PATH="${CONTRACT_PATH:-contracts/kv_retention_microbenchmark.contract.sh}"
CONTRACT_DOC_PATH="${CONTRACT_DOC_PATH:-contracts/kv_retention_microbenchmark.contract.md}"
if [[ ! -f "${CONTRACT_PATH}" ]]; then
  echo "Missing machine-readable contract: ${CONTRACT_PATH}" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "${CONTRACT_PATH}"

MODEL="${1:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}"
BASE_ID="${KV_RETENTION_ID:-kv_retention_microbenchmark_$(date +%Y%m%d_%H%M%S)}"
PYTHON_BIN="${PYTHON_BIN:-}"
PRECISE_START_MODE="${PRECISE_START_MODE:-clean}"

MICROBENCH_LATEST_PREFIX="experiments/reports/latest_kv_retention_microbenchmark"
MICROBENCH_OUT_DIR="experiments/reports/kv_retention_microbenchmark/${BASE_ID}"
SHARED_CHART_DIR="experiments/charts"
LATEST_POINTERS=(
  "${MICROBENCH_LATEST_PREFIX}_contract_sh_path.txt"
  "${MICROBENCH_LATEST_PREFIX}_contract_doc_path.txt"
  "${MICROBENCH_LATEST_PREFIX}_last_mode.txt"
  "${MICROBENCH_LATEST_PREFIX}_last_probe_run_id.txt"
  "${MICROBENCH_LATEST_PREFIX}_last_sweep_run_id.txt"
  "${MICROBENCH_LATEST_PREFIX}_plot_matrix_path.txt"
)
LATEST_REPORT_OUTPUTS=(
  "${MICROBENCH_LATEST_PREFIX}_matrix.csv"
  "${MICROBENCH_LATEST_PREFIX}_summary.csv"
  "${MICROBENCH_LATEST_PREFIX}_summary.md"
  "${MICROBENCH_LATEST_PREFIX}_run_contract.json"
  "${MICROBENCH_LATEST_PREFIX}_replay_latency.svg"
  "${MICROBENCH_LATEST_PREFIX}_replay_cached_tokens.svg"
  "${MICROBENCH_LATEST_PREFIX}_survival_curve.svg"
  "${MICROBENCH_LATEST_PREFIX}_latency_gain.svg"
  "${MICROBENCH_LATEST_PREFIX}_cache_gain.svg"
  "${MICROBENCH_LATEST_PREFIX}_chart_manifest.json"
  "experiments/reports/latest_exp9_decision_proof.csv"
  "experiments/reports/latest_exp9_decision_proof.md"
)

LAST_PROBE_RUN_ID=""
LAST_SWEEP_RUN_ID=""

banner() {
  cat <<EOF
========================================
$1
========================================
EOF
}

ensure_experiment_dirs_ready() {
  if [[ "${EXPERIMENT_DIRS_READY_ALREADY:-0}" = "1" ]]; then
    return 0
  fi
  "${EXPERIMENT_DIRS_HELPER}"
}

prepare_shared_chart_dir() {
  mkdir -p "${SHARED_CHART_DIR}"
  find "${SHARED_CHART_DIR}" -maxdepth 1 -type f ! \( -name '*.svg' -o -name '*.csv' -o -name '*.md' \) -delete
  rm -f \
    "${SHARED_CHART_DIR}/latest_kv_retention_microbenchmark_matrix.csv" \
    "${SHARED_CHART_DIR}/latest_kv_retention_microbenchmark_replay_latency.svg" \
    "${SHARED_CHART_DIR}/latest_kv_retention_microbenchmark_replay_cached_tokens.svg" \
    "${SHARED_CHART_DIR}/latest_kv_retention_microbenchmark_survival_curve.svg" \
    "${SHARED_CHART_DIR}/exp9_kvretention_matrix.csv" \
    "${SHARED_CHART_DIR}/exp9_kvretention_latency_vs_distractors.svg" \
    "${SHARED_CHART_DIR}/exp9_kvretention_cache_vs_distractors.svg" \
    "${SHARED_CHART_DIR}/exp9_kvretention_latency_gain_vs_distractors.svg" \
    "${SHARED_CHART_DIR}/exp9_kvretention_cache_gain_vs_distractors.svg" \
    "${SHARED_CHART_DIR}/exp9_kvretention_survival_vs_distractors.svg" \
    "${SHARED_CHART_DIR}/exp9_decision_proof.csv" \
    "${SHARED_CHART_DIR}/exp9_decision_proof.md"
}

usage() {
  cat <<EOF
Usage:
  ./agentbench/run_kv_retention_microbenchmark_single_host.sh [model]

Modes:
  KV_RETENTION_MODE=probe   one retention-probe run
  KV_RETENTION_MODE=sweep   threshold sweep across distractor counts
  KV_RETENTION_MODE=all     sweep, then plot (default)
  KV_RETENTION_MODE=plot    rebuild charts from one existing matrix CSV

Examples:
  KV_RETENTION_MODE=probe \\
  DYNAMO_MACHINE_PROFILE=ec2 \\
  ./agentbench/run_kv_retention_microbenchmark_single_host.sh \\
    Qwen/Qwen2.5-Coder-7B-Instruct

  KV_RETENTION_MODE=sweep \\
  DYNAMO_MACHINE_PROFILE=ec2 \\
  DISTRACTOR_COUNTS="25 50 75 100" \\
  ./agentbench/run_kv_retention_microbenchmark_single_host.sh \\
    Qwen/Qwen2.5-Coder-7B-Instruct
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

ensure_experiment_dirs_ready

ensure_clean_start_if_requested() {
  if [[ "${KV_RETENTION_MODE}" = "plot" ]]; then
    return 0
  fi
  if [[ "${RETENTION_ATTRIBUTION_MODE}" != "precise" ]]; then
    return 0
  fi
  "${PRECISE_CLEAN_START_HELPER}" \
    --label "KV retention microbenchmark" \
    --mode "${PRECISE_START_MODE}"
}

require_contract_vars() {
  local missing=0
  local required_vars=(
    KV_RETENTION_SCHEMA_VERSION
    KV_RETENTION_PUBLIC_WRAPPER
    KV_RETENTION_PROBE_HELPER
    KV_RETENTION_SWEEP_HELPER
    KV_RETENTION_SUPPORTED_MODES
    RETENTION_REQUEST_SOURCE
    RETENTION_SWEBENCH_DATASET
    RETENTION_SWEBENCH_SPLIT
    RETENTION_SWEBENCH_INDEX
    RETENTION_SWEBENCH_DISTRACTOR_START_INDEX
    RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE
    RETENTION_TRAJECTORY_PROMPT_CATALOG
    RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX
    RETENTION_TRAJECTORY_PROTECTED_STAGE
    RETENTION_TRAJECTORY_STAGES
    RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE
    RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX
    RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE
    RETENTION_ATTRIBUTION_MODE
    RETENTION_REQUEST_CONTEXT_MODE
    RETENTION_TOP_LEVEL_PRIORITY_MODE
    KV_RETENTION_RESET_MODE
    KV_TIER_MODES
    DISTRACTOR_COUNT
    DISTRACTOR_COUNTS
    PROTECTED_INPUT_LEN
    DISTRACTOR_INPUT_LEN
    RANDOM_OUTPUT_LEN
    RETENTION_PROMPT_ISOLATION_MODE
    MAX_CONTEXT_TOKENS
    CONTROL_HINT_PROFILE
    PROTECTED_HINT_PROFILES
    CONTROL_CACHE_CONTROL_PROFILE
    PROTECTED_CACHE_CONTROL_PROFILES
    SGLANG_TRANSFER_LOG_PROFILE
    WORKER_BASE_ARGS
    MODEL_READY_RETRIES
    MODEL_READY_DELAY_SECS
    MODEL_READY_STABLE_HITS
    MODEL_SMOKE_RETRIES
    MODEL_SMOKE_DELAY_SECS
    MODEL_COOLDOWN_SECS
    KV_RETENTION_REPORT_DIR
  )
  for var_name in "${required_vars[@]}"; do
    if [[ -z "${!var_name:-}" ]]; then
      echo "Missing required contract variable: ${var_name}" >&2
      missing=1
    fi
  done
  if [[ "${missing}" != "0" ]]; then
    exit 1
  fi
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

require_contract_vars

if [[ -z "${MODEL}" ]]; then
  echo "No model specified. Pass it as an argument or set MODEL / MODEL_NAME." >&2
  exit 1
fi

if [[ ! -x "${KV_RETENTION_PROBE_HELPER}" ]]; then
  echo "Retention probe helper is missing or not executable: ${KV_RETENTION_PROBE_HELPER}" >&2
  exit 1
fi
if [[ ! -x "${KV_RETENTION_SWEEP_HELPER}" ]]; then
  echo "Retention sweep helper is missing or not executable: ${KV_RETENTION_SWEEP_HELPER}" >&2
  exit 1
fi

print_contract_summary() {
  banner "KV RETENTION MICROBENCH CONTRACT"
  cat <<EOF
Contract file: ${CONTRACT_PATH}
Contract doc: ${CONTRACT_DOC_PATH}
Mode: ${KV_RETENTION_MODE}
Model: ${MODEL}
Machine profile: ${DYNAMO_MACHINE_PROFILE:-default}
Schema version: ${KV_RETENTION_SCHEMA_VERSION}

Public wrapper:
  ${KV_RETENTION_PUBLIC_WRAPPER}

Internal helpers:
  probe=${KV_RETENTION_PROBE_HELPER}
  sweep=${KV_RETENTION_SWEEP_HELPER}

Runtime stack:
  dynamo_source_dir=${KV_RETENTION_DYNAMO_SOURCE_DIR}
  sglang_source_image=${KV_RETENTION_SGLANG_SOURCE_IMAGE}
  sglang_source_dir=${KV_RETENTION_SGLANG_SOURCE_DIR}
  frontend_image=${KV_RETENTION_FRONTEND_IMAGE}
  worker_image=${KV_RETENTION_WORKER_IMAGE}

Control defaults:
  control_hint=${CONTROL_HINT_PROFILE}
  protected_hints=${PROTECTED_HINT_PROFILES}
  control_cache_control=${CONTROL_CACHE_CONTROL_PROFILE}
  protected_cache_control=${PROTECTED_CACHE_CONTROL_PROFILES}

Workload defaults:
  request_source=${RETENTION_REQUEST_SOURCE}
EOF
  if [[ "${RETENTION_REQUEST_SOURCE}" = "swebench_dataset" ]]; then
    cat <<EOF
  swebench_dataset=${RETENTION_SWEBENCH_DATASET}
  swebench_split=${RETENTION_SWEBENCH_SPLIT}
  swebench_index=${RETENTION_SWEBENCH_INDEX}
  swebench_instance_id=${RETENTION_SWEBENCH_INSTANCE_ID}
  swebench_distractor_start_index=${RETENTION_SWEBENCH_DISTRACTOR_START_INDEX}
  swebench_allow_distractor_reuse=${RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE}
EOF
  elif [[ "${RETENTION_REQUEST_SOURCE}" = "swebench_trajectory" ]]; then
    cat <<EOF
  trajectory_prompt_catalog=${RETENTION_TRAJECTORY_PROMPT_CATALOG}
  trajectory_protected_task_index=${RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX}
  trajectory_protected_instance_id=${RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID}
  trajectory_protected_stage=${RETENTION_TRAJECTORY_PROTECTED_STAGE}
  trajectory_stages=${RETENTION_TRAJECTORY_STAGES}
  trajectory_prompt_prefix_mode=${RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE}
  trajectory_distractor_start_task_index=${RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX}
  trajectory_allow_distractor_reuse=${RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE}
EOF
  fi
  cat <<EOF
  kv_tier_modes=${KV_TIER_MODES}
  distractor_count=${DISTRACTOR_COUNT}
  distractor_counts=${DISTRACTOR_COUNTS}
  protected_input_len=${PROTECTED_INPUT_LEN}
  distractor_input_len=${DISTRACTOR_INPUT_LEN}
  random_output_len=${RANDOM_OUTPUT_LEN}
  prompt_isolation_mode=${RETENTION_PROMPT_ISOLATION_MODE}
  max_context_tokens=${MAX_CONTEXT_TOKENS}

Runtime defaults:
  attribution_mode=${RETENTION_ATTRIBUTION_MODE}
  request_context_mode=${RETENTION_REQUEST_CONTEXT_MODE}
  top_level_priority_mode=${RETENTION_TOP_LEVEL_PRIORITY_MODE}
  experiment_reset_mode=${KV_RETENTION_RESET_MODE}
  transfer_log_profile=${SGLANG_TRANSFER_LOG_PROFILE}
  worker_base_args=${WORKER_BASE_ARGS}

Readiness defaults:
  MODEL_READY_RETRIES=${MODEL_READY_RETRIES}
  MODEL_READY_DELAY_SECS=${MODEL_READY_DELAY_SECS}
  MODEL_READY_STABLE_HITS=${MODEL_READY_STABLE_HITS}
  MODEL_SMOKE_RETRIES=${MODEL_SMOKE_RETRIES}
  MODEL_SMOKE_DELAY_SECS=${MODEL_SMOKE_DELAY_SECS}
  MODEL_COOLDOWN_SECS=${MODEL_COOLDOWN_SECS}
EOF
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
    "${MICROBENCH_LATEST_PREFIX}_replay_latency.svg" \
    "${MICROBENCH_LATEST_PREFIX}_replay_cached_tokens.svg" \
    "${MICROBENCH_LATEST_PREFIX}_survival_curve.svg" \
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
    "${KV_RETENTION_MODE}"
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
    "KV_RETENTION_SCHEMA_VERSION",
    "KV_RETENTION_MODE",
    "KV_RETENTION_ID",
    "KV_RETENTION_PUBLIC_WRAPPER",
    "KV_RETENTION_PROBE_HELPER",
    "KV_RETENTION_SWEEP_HELPER",
    "KV_RETENTION_DYNAMO_SOURCE_DIR",
    "KV_RETENTION_SGLANG_SOURCE_IMAGE",
    "KV_RETENTION_SGLANG_SOURCE_DIR",
    "KV_RETENTION_SGLANG_ROOT",
    "KV_RETENTION_FRONTEND_IMAGE",
    "KV_RETENTION_WORKER_IMAGE",
    "RETENTION_REQUEST_SOURCE",
    "RETENTION_SWEBENCH_DATASET",
    "RETENTION_SWEBENCH_SPLIT",
    "RETENTION_SWEBENCH_INDEX",
    "RETENTION_SWEBENCH_INSTANCE_ID",
    "RETENTION_SWEBENCH_DISTRACTOR_START_INDEX",
    "RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE",
    "RETENTION_TRAJECTORY_PROMPT_CATALOG",
    "RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX",
    "RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID",
    "RETENTION_TRAJECTORY_PROTECTED_STAGE",
    "RETENTION_TRAJECTORY_STAGES",
    "RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE",
    "RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX",
    "RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE",
    "RETENTION_ATTRIBUTION_MODE",
    "RETENTION_REQUEST_CONTEXT_MODE",
    "RETENTION_TOP_LEVEL_PRIORITY_MODE",
    "KV_RETENTION_RESET_MODE",
    "EXPERIMENT_RESET_MODE",
    "KV_TIER_MODES",
    "DISTRACTOR_COUNT",
    "DISTRACTOR_COUNTS",
    "PROTECTED_INPUT_LEN",
    "DISTRACTOR_INPUT_LEN",
    "RANDOM_OUTPUT_LEN",
    "MAX_CONTEXT_TOKENS",
    "CONTROL_HINT_PROFILE",
    "PROTECTED_HINT_PROFILES",
    "CONTROL_CACHE_CONTROL_PROFILE",
    "PROTECTED_CACHE_CONTROL_PROFILES",
    "DISTRACTOR_CACHE_CONTROL_PROFILE",
    "CACHE_CONTROL_EPHEMERAL_TTL",
    "GPU_ONLY_MEM_FRACTION_STATIC",
    "GPU_CPU_MEM_FRACTION_STATIC",
    "GPU_CPU_STORAGE_MEM_FRACTION_STATIC",
    "HICACHE_RATIO",
    "HICACHE_STORAGE_BACKEND",
    "HICACHE_STORAGE_PREFETCH_POLICY",
    "WORKER_BASE_ARGS",
    "WORKER_EXTRA_ARGS_SUFFIX",
    "SGLANG_TRANSFER_LOG_PROFILE",
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
payload["phase"] = "phase2_single_wrapper"

with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
  cp -f "${MICROBENCH_OUT_DIR}/run_contract.json" "${MICROBENCH_LATEST_PREFIX}_run_contract.json"
}

update_run_contract_with_helper_ids() {
  "${PYTHON_BIN}" - <<'PY' "${MICROBENCH_OUT_DIR}/run_contract.json" "${LAST_PROBE_RUN_ID}" "${LAST_SWEEP_RUN_ID}"
import json
import sys

path = sys.argv[1]
probe_run_id = sys.argv[2]
sweep_run_id = sys.argv[3]

with open(path, encoding="utf-8") as fh:
    payload = json.load(fh)

payload["probe_run_id"] = probe_run_id
payload["sweep_run_id"] = sweep_run_id

with open(path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY
  cp -f "${MICROBENCH_OUT_DIR}/run_contract.json" "${MICROBENCH_LATEST_PREFIX}_run_contract.json"
}

build_microbenchmark_report() {
  "${PYTHON_BIN}" experiments/scripts/retention_probe/build_kv_retention_microbenchmark_report.py \
    --run-id "${BASE_ID}" \
    --mode "${KV_RETENTION_MODE}" \
    --model "${MODEL}" \
    --out-dir "${MICROBENCH_OUT_DIR}" \
    --contract-sh "${CONTRACT_PATH}" \
    --contract-md "${CONTRACT_DOC_PATH}" \
    --probe-run-id "${LAST_PROBE_RUN_ID}" \
    --sweep-run-id "${LAST_SWEEP_RUN_ID}"

  cp -f "${MICROBENCH_OUT_DIR}/microbenchmark_matrix.csv" "${MICROBENCH_LATEST_PREFIX}_matrix.csv"
  cp -f "${MICROBENCH_OUT_DIR}/microbenchmark_summary.md" "${MICROBENCH_LATEST_PREFIX}_summary.md"
  cp -f "${MICROBENCH_OUT_DIR}/run_contract.json" "${MICROBENCH_LATEST_PREFIX}_run_contract.json"
}

build_microbenchmark_charts() {
  local matrix_csv="${1}"
  prepare_shared_chart_dir
  if [[ -f "${matrix_csv}" ]]; then
    cp -f "${matrix_csv}" "${SHARED_CHART_DIR}/exp9_kvretention_matrix.csv"
  fi
  "${PYTHON_BIN}" experiments/scripts/retention_probe/plot_kv_retention_microbenchmark.py \
    --matrix-csv "${matrix_csv}" \
    --out-dir "${MICROBENCH_OUT_DIR}/charts"

  if [[ -f "${MICROBENCH_OUT_DIR}/charts/replay_latency.svg" ]]; then
    cp -f "${MICROBENCH_OUT_DIR}/charts/replay_latency.svg" "${MICROBENCH_LATEST_PREFIX}_replay_latency.svg"
    cp -f "${MICROBENCH_OUT_DIR}/charts/replay_latency.svg" "${SHARED_CHART_DIR}/exp9_kvretention_latency_vs_distractors.svg"
  fi
  if [[ -f "${MICROBENCH_OUT_DIR}/charts/replay_cached_tokens.svg" ]]; then
    cp -f "${MICROBENCH_OUT_DIR}/charts/replay_cached_tokens.svg" "${MICROBENCH_LATEST_PREFIX}_replay_cached_tokens.svg"
    cp -f "${MICROBENCH_OUT_DIR}/charts/replay_cached_tokens.svg" "${SHARED_CHART_DIR}/exp9_kvretention_cache_vs_distractors.svg"
  fi
}

build_decision_proof() {
  local matrix_csv="${1}"
  "${PYTHON_BIN}" experiments/scripts/retention_probe/build_kv_retention_decision_proof.py \
    --matrix-csv "${matrix_csv}" \
    --run-contract-json "${MICROBENCH_OUT_DIR}/run_contract.json" \
    --reports-csv "experiments/reports/latest_exp9_decision_proof.csv" \
    --reports-md "experiments/reports/latest_exp9_decision_proof.md" \
    --charts-csv "${SHARED_CHART_DIR}/exp9_decision_proof.csv" \
    --charts-md "${SHARED_CHART_DIR}/exp9_decision_proof.md"
}

finalize_runtime_cleanup() {
  if [[ "${STOP_DYNAMO_WHEN_DONE}" != "1" || "${KV_RETENTION_MODE}" = "plot" ]]; then
    return 0
  fi
  echo "Final cleanup: stopping Dynamo once after KV retention microbenchmark."
  ./run_dynamo_single_host.sh stop >/dev/null 2>&1 || true
  env EXPERIMENT_RESET_STATE_FILE="${EXPERIMENT_RESET_STATE_FILE:-experiments/runtime_state/active_runtime_signature.txt}" \
    ./runtime_instrumentation/reset_experiment_state.sh clear-active >/dev/null 2>&1 || true
}

print_final_status() {
  banner "KV RETENTION MICROBENCH PHASE 4 READY"
  if [[ "${KV_RETENTION_MODE}" = "plot" ]]; then
    cat <<EOF
Run directory: ${MICROBENCH_OUT_DIR}
Run contract: ${MICROBENCH_OUT_DIR}/run_contract.json
Chart source matrix: ${KV_RETENTION_PLOT_MATRIX_CSV:-${MICROBENCH_LATEST_PREFIX}_matrix.csv}
Replay latency chart: ${MICROBENCH_OUT_DIR}/charts/replay_latency.svg
Replay cached chart: ${MICROBENCH_OUT_DIR}/charts/replay_cached_tokens.svg
Decision proof: experiments/reports/latest_exp9_decision_proof.md
Shared charts: ${SHARED_CHART_DIR}/exp9_kvretention_latency_vs_distractors.svg
               ${SHARED_CHART_DIR}/exp9_kvretention_cache_vs_distractors.svg
Shared proof: ${SHARED_CHART_DIR}/exp9_decision_proof.md

Current status:
  - public wrapper: ready
  - contract-driven defaults: ready
  - helper orchestration: ready
  - consolidated microbenchmark report: ready
  - plotting: ready
EOF
    return
  fi

  cat <<EOF
Run directory: ${MICROBENCH_OUT_DIR}
Run contract: ${MICROBENCH_OUT_DIR}/run_contract.json
Microbenchmark matrix: ${MICROBENCH_OUT_DIR}/microbenchmark_matrix.csv
Microbenchmark summary md: ${MICROBENCH_OUT_DIR}/microbenchmark_summary.md
Replay latency chart: ${MICROBENCH_OUT_DIR}/charts/replay_latency.svg
Replay cached chart: ${MICROBENCH_OUT_DIR}/charts/replay_cached_tokens.svg
Decision proof: experiments/reports/latest_exp9_decision_proof.md
Shared charts: ${SHARED_CHART_DIR}/exp9_kvretention_latency_vs_distractors.svg
               ${SHARED_CHART_DIR}/exp9_kvretention_cache_vs_distractors.svg
Shared proof: ${SHARED_CHART_DIR}/exp9_decision_proof.md
Last probe run id: ${LAST_PROBE_RUN_ID:-<none>}
Last sweep run id: ${LAST_SWEEP_RUN_ID:-<none>}

Current status:
  - public wrapper: ready
  - contract-driven defaults: ready
  - helper orchestration: ready
  - consolidated microbenchmark report: ready
  - plotting: ready
EOF
}

run_probe_mode() {
  local run_id="${BASE_ID}__probe"
  banner "KV RETENTION MICROBENCH PROBE"
  env \
    DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}" \
    FRONTEND_IMAGE="${KV_RETENTION_FRONTEND_IMAGE}" \
    WORKER_IMAGE="${KV_RETENTION_WORKER_IMAGE}" \
    RETENTION_PROBE_ID="${run_id}" \
    RETENTION_REQUEST_SOURCE="${RETENTION_REQUEST_SOURCE}" \
    RETENTION_SWEBENCH_DATASET="${RETENTION_SWEBENCH_DATASET}" \
    RETENTION_SWEBENCH_SPLIT="${RETENTION_SWEBENCH_SPLIT}" \
    RETENTION_SWEBENCH_INDEX="${RETENTION_SWEBENCH_INDEX}" \
    RETENTION_SWEBENCH_INSTANCE_ID="${RETENTION_SWEBENCH_INSTANCE_ID}" \
    RETENTION_SWEBENCH_DISTRACTOR_START_INDEX="${RETENTION_SWEBENCH_DISTRACTOR_START_INDEX}" \
    RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE="${RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE}" \
    RETENTION_TRAJECTORY_PROMPT_CATALOG="${RETENTION_TRAJECTORY_PROMPT_CATALOG}" \
    RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX="${RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX}" \
    RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID="${RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID}" \
    RETENTION_TRAJECTORY_PROTECTED_STAGE="${RETENTION_TRAJECTORY_PROTECTED_STAGE}" \
    RETENTION_TRAJECTORY_STAGES="${RETENTION_TRAJECTORY_STAGES}" \
    RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE="${RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE}" \
    RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX="${RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX}" \
    RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE="${RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE}" \
    RETENTION_ATTRIBUTION_MODE="${RETENTION_ATTRIBUTION_MODE}" \
    RETENTION_REQUEST_CONTEXT_MODE="${RETENTION_REQUEST_CONTEXT_MODE}" \
    RETENTION_TOP_LEVEL_PRIORITY_MODE="${RETENTION_TOP_LEVEL_PRIORITY_MODE}" \
    KV_TIER_MODES="${KV_TIER_MODES}" \
    CONTROL_HINT_PROFILE="${CONTROL_HINT_PROFILE}" \
    PROTECTED_HINT_PROFILES="${PROTECTED_HINT_PROFILES}" \
    CONTROL_CACHE_CONTROL_PROFILE="${CONTROL_CACHE_CONTROL_PROFILE}" \
    PROTECTED_CACHE_CONTROL_PROFILES="${PROTECTED_CACHE_CONTROL_PROFILES}" \
    DISTRACTOR_CACHE_CONTROL_PROFILE="${DISTRACTOR_CACHE_CONTROL_PROFILE}" \
    PROTECTED_INPUT_LEN="${PROTECTED_INPUT_LEN}" \
    DISTRACTOR_INPUT_LEN="${DISTRACTOR_INPUT_LEN}" \
    DISTRACTOR_COUNT="${DISTRACTOR_COUNT}" \
    RANDOM_OUTPUT_LEN="${RANDOM_OUTPUT_LEN}" \
    MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS}" \
    CONTEXT_RESERVE_TOKENS="${CONTEXT_RESERVE_TOKENS}" \
    CACHE_CONTROL_EPHEMERAL_TTL="${CACHE_CONTROL_EPHEMERAL_TTL}" \
    SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
    GPU_ONLY_MEM_FRACTION_STATIC="${GPU_ONLY_MEM_FRACTION_STATIC}" \
    GPU_CPU_MEM_FRACTION_STATIC="${GPU_CPU_MEM_FRACTION_STATIC}" \
    GPU_CPU_STORAGE_MEM_FRACTION_STATIC="${GPU_CPU_STORAGE_MEM_FRACTION_STATIC}" \
    HICACHE_RATIO="${HICACHE_RATIO}" \
    HICACHE_STORAGE_BACKEND="${HICACHE_STORAGE_BACKEND}" \
    HICACHE_STORAGE_PREFETCH_POLICY="${HICACHE_STORAGE_PREFETCH_POLICY}" \
    HICACHE_WRITE_POLICY="${HICACHE_WRITE_POLICY}" \
    HICACHE_EXTRA_ARGS="${HICACHE_EXTRA_ARGS}" \
    FILE_STORAGE_PATH="${FILE_STORAGE_PATH}" \
    HOST_FILE_STORAGE_PATH="${HOST_FILE_STORAGE_PATH}" \
    WORKER_BASE_ARGS="${WORKER_BASE_ARGS}" \
    WORKER_EXTRA_ARGS_SUFFIX="${WORKER_EXTRA_ARGS_SUFFIX}" \
    MODEL_READY_RETRIES="${MODEL_READY_RETRIES}" \
    MODEL_READY_DELAY_SECS="${MODEL_READY_DELAY_SECS}" \
    MODEL_READY_STABLE_HITS="${MODEL_READY_STABLE_HITS}" \
    MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES}" \
    MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS}" \
    MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS}" \
    EXPERIMENT_RESET_MODE="${KV_RETENTION_RESET_MODE}" \
    AUTO_BUILD_PRECISE_IMAGES="${AUTO_BUILD_PRECISE_IMAGES}" \
    REQUIRE_PRECISE_KV="${REQUIRE_PRECISE_KV}" \
    STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE}" \
    "${KV_RETENTION_PROBE_HELPER}" "${MODEL}"
  LAST_PROBE_RUN_ID="${run_id}"
}

run_sweep_mode() {
  local run_id="${BASE_ID}__sweep"
  banner "KV RETENTION MICROBENCH SWEEP"
  env \
    DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}" \
    FRONTEND_IMAGE="${KV_RETENTION_FRONTEND_IMAGE}" \
    WORKER_IMAGE="${KV_RETENTION_WORKER_IMAGE}" \
    RETENTION_SWEEP_ID="${run_id}" \
    RETENTION_REQUEST_SOURCE="${RETENTION_REQUEST_SOURCE}" \
    RETENTION_SWEBENCH_DATASET="${RETENTION_SWEBENCH_DATASET}" \
    RETENTION_SWEBENCH_SPLIT="${RETENTION_SWEBENCH_SPLIT}" \
    RETENTION_SWEBENCH_INDEX="${RETENTION_SWEBENCH_INDEX}" \
    RETENTION_SWEBENCH_INSTANCE_ID="${RETENTION_SWEBENCH_INSTANCE_ID}" \
    RETENTION_SWEBENCH_DISTRACTOR_START_INDEX="${RETENTION_SWEBENCH_DISTRACTOR_START_INDEX}" \
    RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE="${RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE}" \
    RETENTION_TRAJECTORY_PROMPT_CATALOG="${RETENTION_TRAJECTORY_PROMPT_CATALOG}" \
    RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX="${RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX}" \
    RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID="${RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID}" \
    RETENTION_TRAJECTORY_PROTECTED_STAGE="${RETENTION_TRAJECTORY_PROTECTED_STAGE}" \
    RETENTION_TRAJECTORY_STAGES="${RETENTION_TRAJECTORY_STAGES}" \
    RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE="${RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE}" \
    RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX="${RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX}" \
    RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE="${RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE}" \
    RETENTION_ATTRIBUTION_MODE="${RETENTION_ATTRIBUTION_MODE}" \
    RETENTION_REQUEST_CONTEXT_MODE="${RETENTION_REQUEST_CONTEXT_MODE}" \
    RETENTION_TOP_LEVEL_PRIORITY_MODE="${RETENTION_TOP_LEVEL_PRIORITY_MODE}" \
    KV_TIER_MODES="${KV_TIER_MODES}" \
    CONTROL_HINT_PROFILE="${CONTROL_HINT_PROFILE}" \
    PROTECTED_HINT_PROFILES="${PROTECTED_HINT_PROFILES}" \
    CONTROL_CACHE_CONTROL_PROFILE="${CONTROL_CACHE_CONTROL_PROFILE}" \
    PROTECTED_CACHE_CONTROL_PROFILES="${PROTECTED_CACHE_CONTROL_PROFILES}" \
    PROTECTED_INPUT_LEN="${PROTECTED_INPUT_LEN}" \
    DISTRACTOR_INPUT_LEN="${DISTRACTOR_INPUT_LEN}" \
    DISTRACTOR_COUNTS="${DISTRACTOR_COUNTS}" \
    RANDOM_OUTPUT_LEN="${RANDOM_OUTPUT_LEN}" \
    MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS}" \
    CONTEXT_RESERVE_TOKENS="${CONTEXT_RESERVE_TOKENS}" \
    CACHE_CONTROL_EPHEMERAL_TTL="${CACHE_CONTROL_EPHEMERAL_TTL}" \
    SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
    GPU_ONLY_MEM_FRACTION_STATIC="${GPU_ONLY_MEM_FRACTION_STATIC}" \
    RETENTION_MATCH_EVENT_MIN="${RETENTION_MATCH_EVENT_MIN}" \
    RETENTION_MIN_SPEEDUP_RATIO="${RETENTION_MIN_SPEEDUP_RATIO}" \
    RETENTION_MIN_LATENCY_GAIN_MS="${RETENTION_MIN_LATENCY_GAIN_MS}" \
    STOP_ON_PROBE_FAILURE="${STOP_ON_PROBE_FAILURE}" \
    STOP_DYNAMO_WHEN_DONE="0" \
    EXPERIMENT_RESET_MODE="${KV_RETENTION_RESET_MODE}" \
    "${KV_RETENTION_SWEEP_HELPER}" "${MODEL}"
  LAST_SWEEP_RUN_ID="${run_id}"
}

run_plot_mode() {
  local matrix_csv="${KV_RETENTION_PLOT_MATRIX_CSV:-${MICROBENCH_LATEST_PREFIX}_matrix.csv}"
  if [[ ! -f "${matrix_csv}" ]]; then
    echo "Plot mode needs a matrix CSV to read from." >&2
    echo "Set KV_RETENTION_PLOT_MATRIX_CSV or run probe/sweep/all first." >&2
    exit 2
  fi
  banner "KV RETENTION MICROBENCH PLOT"
  echo "Building charts from: ${matrix_csv}"
  build_microbenchmark_charts "${matrix_csv}"
  build_decision_proof "${matrix_csv}"
}

clear_microbenchmark_latest_pointers
if [[ "${KV_RETENTION_MODE}" = "plot" ]]; then
  reset_microbenchmark_plot_outputs
else
  reset_microbenchmark_outputs
fi
print_contract_summary
ensure_clean_start_if_requested
write_run_contract

case "${KV_RETENTION_MODE}" in
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
    echo "Unknown KV_RETENTION_MODE: ${KV_RETENTION_MODE}" >&2
    usage >&2
    exit 2
    ;;
esac

update_run_contract_with_helper_ids
if [[ "${KV_RETENTION_MODE}" != "plot" ]]; then
  build_microbenchmark_report
  build_microbenchmark_charts "${MICROBENCH_OUT_DIR}/microbenchmark_matrix.csv"
  build_decision_proof "${MICROBENCH_OUT_DIR}/microbenchmark_matrix.csv"
fi

finalize_runtime_cleanup

print_final_status
