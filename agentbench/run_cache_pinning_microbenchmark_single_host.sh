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
CONTRACT_PATH="${CONTRACT_PATH:-contracts/cache_pinning_microbenchmark.contract.sh}"
CONTRACT_DOC_PATH="${CONTRACT_DOC_PATH:-contracts/cache_pinning_microbenchmark.contract.md}"
if [[ ! -f "${CONTRACT_PATH}" ]]; then
  echo "Missing machine-readable contract: ${CONTRACT_PATH}" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "${CONTRACT_PATH}"
source runtime_instrumentation/cache_pinning_profile.sh

MODEL="${1:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}"
BASE_ID="${CACHE_PINNING_ID:-cache_pinning_microbenchmark_$(date +%Y%m%d_%H%M%S)}"
EXPERIMENT_RESET_MODE="${EXPERIMENT_RESET_MODE:-restart}"
RETENTION_PROBE_SEED="${RETENTION_PROBE_SEED:-42}"
RETENTION_SWEEP_SEED_MODE="${RETENTION_SWEEP_SEED_MODE:-fixed}"
RETENTION_PROMPT_ISOLATION_MODE="${RETENTION_PROMPT_ISOLATION_MODE:-strict}"
PRECISE_START_MODE="${PRECISE_START_MODE:-clean}"

MICROBENCH_LATEST_PREFIX="experiments/reports/latest_cache_pinning_microbenchmark"
MICROBENCH_OUT_DIR="experiments/reports/cache_pinning_microbenchmark/${BASE_ID}"
MICROBENCH_CHART_DIR="${MICROBENCH_OUT_DIR}/charts"
MICROBENCH_MATRIX_PATH="${MICROBENCH_OUT_DIR}/microbenchmark_matrix.csv"
SHARED_CHART_DIR="experiments/charts"
LATEST_POINTERS=(
  "${MICROBENCH_LATEST_PREFIX}_contract_sh_path.txt"
  "${MICROBENCH_LATEST_PREFIX}_contract_doc_path.txt"
  "${MICROBENCH_LATEST_PREFIX}_last_mode.txt"
  "${MICROBENCH_LATEST_PREFIX}_last_validate_run_id.txt"
  "${MICROBENCH_LATEST_PREFIX}_last_sweep_run_id.txt"
)
LATEST_REPORT_OUTPUTS=(
  "${MICROBENCH_LATEST_PREFIX}_matrix.csv"
  "${MICROBENCH_LATEST_PREFIX}_summary.csv"
  "${MICROBENCH_LATEST_PREFIX}_summary.md"
  "${MICROBENCH_LATEST_PREFIX}_run_contract.json"
)
LATEST_CHART_OUTPUTS=(
  "${MICROBENCH_LATEST_PREFIX}_validation_latency.svg"
  "${MICROBENCH_LATEST_PREFIX}_validation_cached_tokens.svg"
  "${MICROBENCH_LATEST_PREFIX}_sweep_replay_latency.svg"
  "${MICROBENCH_LATEST_PREFIX}_sweep_replay_cached_tokens.svg"
  "${MICROBENCH_LATEST_PREFIX}_chart_manifest.json"
)

LAST_VALIDATE_RUN_ID=""
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
  find "${SHARED_CHART_DIR}" -maxdepth 1 -type f ! \( -name '*.svg' -o -name '*.csv' -o -name 'README.md' \) -delete
  rm -f \
    "${SHARED_CHART_DIR}/latest_cache_pinning_microbenchmark_matrix.csv" \
    "${SHARED_CHART_DIR}/latest_cache_pinning_microbenchmark_validation_latency.svg" \
    "${SHARED_CHART_DIR}/latest_cache_pinning_microbenchmark_validation_cached_tokens.svg" \
    "${SHARED_CHART_DIR}/latest_cache_pinning_microbenchmark_sweep_replay_latency.svg" \
    "${SHARED_CHART_DIR}/latest_cache_pinning_microbenchmark_sweep_replay_cached_tokens.svg" \
    "${SHARED_CHART_DIR}/exp10_cachepinning_matrix.csv" \
    "${SHARED_CHART_DIR}/exp10_cachepinning_validation_latency.svg" \
    "${SHARED_CHART_DIR}/exp10_cachepinning_validation_cache.svg" \
    "${SHARED_CHART_DIR}/exp10_cachepinning_latency_vs_distractors.svg" \
    "${SHARED_CHART_DIR}/exp10_cachepinning_cache_vs_distractors.svg" \
    "${SHARED_CHART_DIR}/exp10_cachepinning_latency_gain_vs_distractors.svg" \
    "${SHARED_CHART_DIR}/exp10_cachepinning_cache_gain_vs_distractors.svg"
}

usage() {
  cat <<EOF
Usage:
  ./agentbench/run_cache_pinning_microbenchmark_single_host.sh [model]

Modes:
  CACHE_PINNING_MODE=validate   quick doc-style pin-path validation
  CACHE_PINNING_MODE=sweep      retention threshold sweep
  CACHE_PINNING_MODE=all        validation, then sweep (default)
  CACHE_PINNING_MODE=plot       reserved for a later phase

Examples:
  CACHE_PINNING_MODE=validate \\
  DYNAMO_MACHINE_PROFILE=ec2 \\
  ./agentbench/run_cache_pinning_microbenchmark_single_host.sh \\
    Qwen/Qwen2.5-Coder-7B-Instruct

  CACHE_PINNING_MODE=sweep \\
  DYNAMO_MACHINE_PROFILE=ec2 \\
  DISTRACTOR_COUNTS="40 80 120 160" \\
  ./agentbench/run_cache_pinning_microbenchmark_single_host.sh \\
    Qwen/Qwen2.5-Coder-7B-Instruct
EOF
}

ensure_experiment_dirs_ready

ensure_clean_start_if_requested() {
  if [[ "${CACHE_PINNING_MODE}" = "plot" ]]; then
    return 0
  fi
  "${PRECISE_CLEAN_START_HELPER}" \
    --label "Cache-pinning microbenchmark" \
    --mode "${PRECISE_START_MODE}"
}

require_contract_vars() {
  local missing=0
  local required_vars=(
    CACHE_PINNING_DYNAMO_SOURCE_REPO
    CACHE_PINNING_DYNAMO_PULL_REF
    CACHE_PINNING_DYNAMO_SOURCE_REF
    CACHE_PINNING_DYNAMO_SOURCE_DIR
    CACHE_PINNING_SGLANG_SOURCE_REPO
    CACHE_PINNING_SGLANG_PULL_REF
    CACHE_PINNING_SGLANG_SOURCE_REF
    CACHE_PINNING_SGLANG_SOURCE_DIR
    CACHE_PINNING_SGLANG_ROOT
    CACHE_PINNING_FRONTEND_IMAGE
    CACHE_PINNING_WORKER_IMAGE
    CACHE_PINNING_EPP_IMAGE
    CACHE_PINNING_FRONTEND_FLAG_MODE
    CACHE_PINNING_FRONTEND_FLAG_VALUE
    CACHE_PINNING_ENABLE_CACHE_CONTROL
    CACHE_PINNING_ROUTER_MODE
    CACHE_PINNING_REQUEST_TYPE
    CACHE_PINNING_TTL
    CACHE_PINNING_TTL_MIN_SECONDS
    CACHE_PINNING_TTL_MAX_SECONDS
    CACHE_PINNING_PINNED_RATIO
    SGLANG_HICACHE_MAX_PINNED_RATIO
    CACHE_PINNING_HICACHE_RATIO
    CACHE_PINNING_HICACHE_WRITE_POLICY
    CACHE_PINNING_MEM_FRACTION_STATIC
    CACHE_PINNING_ENABLE_CACHE_REPORT
    CACHE_PINNING_ENABLE_HIERARCHICAL_CACHE
    CACHE_PINNING_REQUIRE_HIERARCHICAL_CACHE
    CACHE_PINNING_DEVELOPMENT_BRANCH_STACK
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

if [[ "${CACHE_PINNING_PINNED_RATIO}" != "${SGLANG_HICACHE_MAX_PINNED_RATIO}" ]]; then
  echo "Contract mismatch: CACHE_PINNING_PINNED_RATIO (${CACHE_PINNING_PINNED_RATIO}) != SGLANG_HICACHE_MAX_PINNED_RATIO (${SGLANG_HICACHE_MAX_PINNED_RATIO})" >&2
  exit 1
fi

if [[ -z "${MODEL}" ]]; then
  echo "No model specified. Pass it as an argument or set MODEL / MODEL_NAME." >&2
  exit 1
fi

print_contract_summary() {
  banner "CACHE PINNING MICROBENCH CONTRACT"
  cat <<EOF
Contract file: ${CONTRACT_PATH}
Contract doc: ${CONTRACT_DOC_PATH}
Mode: ${CACHE_PINNING_MODE}
Model: ${MODEL}
Machine profile: ${DYNAMO_MACHINE_PROFILE:-default}

Pinned Dynamo:
  repo=${CACHE_PINNING_DYNAMO_SOURCE_REPO}
  pull_ref=${CACHE_PINNING_DYNAMO_PULL_REF}
  ref=${CACHE_PINNING_DYNAMO_SOURCE_REF}

Pinned SGLang:
  repo=${CACHE_PINNING_SGLANG_SOURCE_REPO}
  pull_ref=${CACHE_PINNING_SGLANG_PULL_REF}
  ref=${CACHE_PINNING_SGLANG_SOURCE_REF}

Images:
  frontend=${CACHE_PINNING_FRONTEND_IMAGE}
  worker=${CACHE_PINNING_WORKER_IMAGE}

Frontend cache-control contract:
  flag_mode=${CACHE_PINNING_FRONTEND_FLAG_MODE}
  flag_value=${CACHE_PINNING_FRONTEND_FLAG_VALUE}
  enable_cache_control=${CACHE_PINNING_ENABLE_CACHE_CONTROL}
  router_mode=${CACHE_PINNING_ROUTER_MODE}

Shared pinning knobs:
  request_type=${CACHE_PINNING_REQUEST_TYPE}
  ttl=${CACHE_PINNING_TTL}
  ttl_min_seconds=${CACHE_PINNING_TTL_MIN_SECONDS}
  ttl_max_seconds=${CACHE_PINNING_TTL_MAX_SECONDS}
  pinned_ratio=${CACHE_PINNING_PINNED_RATIO}
  sglang_hicache_max_pinned_ratio=${SGLANG_HICACHE_MAX_PINNED_RATIO}
  hicache_ratio=${CACHE_PINNING_HICACHE_RATIO}
  hicache_write_policy=${CACHE_PINNING_HICACHE_WRITE_POLICY}
  mem_fraction_static=${CACHE_PINNING_MEM_FRACTION_STATIC}
  enable_cache_report=${CACHE_PINNING_ENABLE_CACHE_REPORT}
  enable_hierarchical_cache=${CACHE_PINNING_ENABLE_HIERARCHICAL_CACHE}
  require_hierarchical_cache=${CACHE_PINNING_REQUIRE_HIERARCHICAL_CACHE}
  development_branch_stack=${CACHE_PINNING_DEVELOPMENT_BRANCH_STACK}
  retention_probe_seed=${RETENTION_PROBE_SEED}
  retention_sweep_seed_mode=${RETENTION_SWEEP_SEED_MODE}
  retention_prompt_isolation_mode=${RETENTION_PROMPT_ISOLATION_MODE}
EOF
  if [[ -f "${CONTRACT_PATH}" ]]; then
    printf '%s\n' "${CONTRACT_PATH}" > "${MICROBENCH_LATEST_PREFIX}_contract_sh_path.txt"
  fi
  if [[ -f "${CONTRACT_DOC_PATH}" ]]; then
    printf '%s\n' "${CONTRACT_DOC_PATH}" > "${MICROBENCH_LATEST_PREFIX}_contract_doc_path.txt"
  fi
  printf '%s\n' "${CACHE_PINNING_MODE}" > "${MICROBENCH_LATEST_PREFIX}_last_mode.txt"
}

clear_microbenchmark_latest_pointers() {
  rm -f "${LATEST_POINTERS[@]}"
}

reset_microbenchmark_report_outputs() {
  rm -f "${LATEST_REPORT_OUTPUTS[@]}" "${LATEST_CHART_OUTPUTS[@]}"
  rm -rf "${MICROBENCH_OUT_DIR}"
  mkdir -p "${MICROBENCH_OUT_DIR}"
}

reset_microbenchmark_plot_outputs() {
  rm -f "${LATEST_CHART_OUTPUTS[@]}"
  rm -rf "${MICROBENCH_OUT_DIR}"
  mkdir -p "${MICROBENCH_OUT_DIR}"
}

run_validate_mode() {
  local run_id="${BASE_ID}__validate"
  banner "CACHE PINNING MICROBENCH VALIDATE"
  env \
    DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE}" \
    FRONTEND_URL="${FRONTEND_URL}" \
    CACHE_PINNING_DOC_ID="${run_id}" \
    CACHE_PINNING_REQUEST_TYPE="${CACHE_PINNING_REQUEST_TYPE}" \
    CACHE_PINNING_TTL="${CACHE_PINNING_TTL}" \
    CACHE_PINNING_TURN1_MAX_TOKENS="${CACHE_PINNING_TURN1_MAX_TOKENS}" \
    CACHE_PINNING_TURN2_MAX_TOKENS="${CACHE_PINNING_TURN2_MAX_TOKENS}" \
    CACHE_PINNING_PINNED_RATIO="${CACHE_PINNING_PINNED_RATIO}" \
    SGLANG_HICACHE_MAX_PINNED_RATIO="${SGLANG_HICACHE_MAX_PINNED_RATIO}" \
    CACHE_PINNING_HICACHE_RATIO="${CACHE_PINNING_HICACHE_RATIO}" \
    CACHE_PINNING_HICACHE_WRITE_POLICY="${CACHE_PINNING_HICACHE_WRITE_POLICY}" \
    CACHE_PINNING_MEM_FRACTION_STATIC="${CACHE_PINNING_MEM_FRACTION_STATIC}" \
    CACHE_PINNING_ENABLE_CACHE_REPORT="${CACHE_PINNING_ENABLE_CACHE_REPORT}" \
    CACHE_PINNING_ROUTER_MODE="${CACHE_PINNING_ROUTER_MODE}" \
    AUTO_BUILD_CACHE_PINNING_IMAGES="${AUTO_BUILD_CACHE_PINNING_IMAGES}" \
    CACHE_PINNING_REBUILD_IMAGES="${CACHE_PINNING_REBUILD_IMAGES}" \
    ./agentbench/run_cache_pinning_doc_validation_single_host.sh "${MODEL}"
  printf '%s\n' "${run_id}" > "${MICROBENCH_LATEST_PREFIX}_last_validate_run_id.txt"
  LAST_VALIDATE_RUN_ID="${run_id}"
}

run_sweep_mode() {
  local run_id="${BASE_ID}__sweep"
  banner "CACHE PINNING MICROBENCH SWEEP"
  env \
    DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE}" \
    RETENTION_SWEEP_ID="${run_id}" \
    RETENTION_ATTRIBUTION_MODE="${RETENTION_ATTRIBUTION_MODE}" \
    RETENTION_REQUEST_CONTEXT_MODE="${RETENTION_REQUEST_CONTEXT_MODE}" \
    RETENTION_TOP_LEVEL_PRIORITY_MODE="${RETENTION_TOP_LEVEL_PRIORITY_MODE}" \
    KV_TIER_MODES="${KV_TIER_MODES}" \
    CONTROL_HINT_PROFILE="${CONTROL_HINT_PROFILE}" \
    PROTECTED_HINT_PROFILES="${PROTECTED_HINT_PROFILES}" \
    CONTROL_CACHE_CONTROL_PROFILE="${CONTROL_CACHE_CONTROL_PROFILE}" \
    PROTECTED_CACHE_CONTROL_PROFILES="${PROTECTED_CACHE_CONTROL_PROFILES}" \
    DISTRACTOR_CACHE_CONTROL_PROFILE="${DISTRACTOR_CACHE_CONTROL_PROFILE}" \
    DISTRACTOR_COUNTS="${DISTRACTOR_COUNTS}" \
    PROTECTED_INPUT_LEN="${PROTECTED_INPUT_LEN}" \
    DISTRACTOR_INPUT_LEN="${DISTRACTOR_INPUT_LEN}" \
    RANDOM_OUTPUT_LEN="${RANDOM_OUTPUT_LEN}" \
    MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS}" \
    CACHE_PINNING_TTL="${CACHE_PINNING_TTL}" \
    CACHE_PINNING_PINNED_RATIO="${CACHE_PINNING_PINNED_RATIO}" \
    SGLANG_HICACHE_MAX_PINNED_RATIO="${SGLANG_HICACHE_MAX_PINNED_RATIO}" \
    CACHE_PINNING_HICACHE_RATIO="${CACHE_PINNING_HICACHE_RATIO}" \
    CACHE_PINNING_HICACHE_WRITE_POLICY="${CACHE_PINNING_HICACHE_WRITE_POLICY}" \
    CACHE_PINNING_MEM_FRACTION_STATIC="${CACHE_PINNING_MEM_FRACTION_STATIC}" \
    CACHE_PINNING_ENABLE_CACHE_REPORT="${CACHE_PINNING_ENABLE_CACHE_REPORT}" \
    CACHE_PINNING_ROUTER_MODE="${CACHE_PINNING_ROUTER_MODE}" \
    AUTO_BUILD_CACHE_PINNING_IMAGES="${AUTO_BUILD_CACHE_PINNING_IMAGES}" \
    CACHE_PINNING_REBUILD_IMAGES="${CACHE_PINNING_REBUILD_IMAGES}" \
    EXPERIMENT_RESET_MODE="${EXPERIMENT_RESET_MODE}" \
    RETENTION_PROBE_SEED="${RETENTION_PROBE_SEED}" \
    RETENTION_SWEEP_SEED_MODE="${RETENTION_SWEEP_SEED_MODE}" \
    RETENTION_PROMPT_ISOLATION_MODE="${RETENTION_PROMPT_ISOLATION_MODE}" \
    SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
    WORKER_BASE_ARGS="${WORKER_BASE_ARGS}" \
    ./agentbench/run_cache_pinning_retention_threshold_sweep_single_host.sh "${MODEL}"
  printf '%s\n' "${run_id}" > "${MICROBENCH_LATEST_PREFIX}_last_sweep_run_id.txt"
  LAST_SWEEP_RUN_ID="${run_id}"
}

run_plot_mode() {
  local matrix_csv="${CACHE_PINNING_PLOT_MATRIX_CSV:-${MICROBENCH_LATEST_PREFIX}_matrix.csv}"
  if [[ ! -f "${matrix_csv}" ]]; then
    echo "Plot mode needs a matrix CSV to read from." >&2
    echo "Set CACHE_PINNING_PLOT_MATRIX_CSV or run validate/sweep/all first." >&2
    exit 2
  fi
  python3 experiments/scripts/cache_pinning/plot_cache_pinning_microbenchmark.py \
    --matrix-csv "${matrix_csv}" \
    --out-dir "${MICROBENCH_CHART_DIR}"
}

build_microbenchmark_report() {
  python3 experiments/scripts/cache_pinning/build_cache_pinning_microbenchmark_report.py \
    --run-id "${BASE_ID}" \
    --mode "${CACHE_PINNING_MODE}" \
    --model "${MODEL}" \
    --out-dir "${MICROBENCH_OUT_DIR}" \
    --contract-sh "${CONTRACT_PATH}" \
    --contract-md "${CONTRACT_DOC_PATH}" \
    --validate-run-id "${LAST_VALIDATE_RUN_ID}" \
    --sweep-run-id "${LAST_SWEEP_RUN_ID}"

  cp -f "${MICROBENCH_MATRIX_PATH}" "${MICROBENCH_LATEST_PREFIX}_matrix.csv"
  cp -f "${MICROBENCH_OUT_DIR}/microbenchmark_summary.csv" "${MICROBENCH_LATEST_PREFIX}_summary.csv"
  cp -f "${MICROBENCH_OUT_DIR}/microbenchmark_summary.md" "${MICROBENCH_LATEST_PREFIX}_summary.md"
  cp -f "${MICROBENCH_OUT_DIR}/run_contract.json" "${MICROBENCH_LATEST_PREFIX}_run_contract.json"
}

build_microbenchmark_charts() {
  prepare_shared_chart_dir
  if [[ -f "${MICROBENCH_MATRIX_PATH}" ]]; then
    cp -f "${MICROBENCH_MATRIX_PATH}" "${SHARED_CHART_DIR}/exp10_cachepinning_matrix.csv"
  fi
  python3 experiments/scripts/cache_pinning/plot_cache_pinning_microbenchmark.py \
    --matrix-csv "${MICROBENCH_MATRIX_PATH}" \
    --out-dir "${MICROBENCH_CHART_DIR}"

  local chart_names=(
    validation_latency
    validation_cached_tokens
    sweep_replay_latency
    sweep_replay_cached_tokens
    sweep_latency_gain
    sweep_cache_gain
  )
  local chart_name=""
  for chart_name in "${chart_names[@]}"; do
    if [[ -f "${MICROBENCH_CHART_DIR}/${chart_name}.svg" ]]; then
      cp -f "${MICROBENCH_CHART_DIR}/${chart_name}.svg" "${MICROBENCH_LATEST_PREFIX}_${chart_name}.svg"
    fi
  done
  [[ -f "${MICROBENCH_CHART_DIR}/sweep_replay_latency.svg" ]] && cp -f "${MICROBENCH_CHART_DIR}/sweep_replay_latency.svg" "${SHARED_CHART_DIR}/exp10_cachepinning_latency_vs_distractors.svg"
  if [[ -f "${MICROBENCH_CHART_DIR}/chart_manifest.json" ]]; then
    cp -f "${MICROBENCH_CHART_DIR}/chart_manifest.json" "${MICROBENCH_LATEST_PREFIX}_chart_manifest.json"
  fi
}

clear_microbenchmark_latest_pointers
if [[ "${CACHE_PINNING_MODE}" = "plot" ]]; then
  reset_microbenchmark_plot_outputs
else
  reset_microbenchmark_report_outputs
fi
print_contract_summary
ensure_clean_start_if_requested

case "${CACHE_PINNING_MODE}" in
  validate)
    run_validate_mode
    ;;
  sweep)
    run_sweep_mode
    ;;
  all)
    run_validate_mode
    run_sweep_mode
    ;;
  plot)
    run_plot_mode
    ;;
  *)
    echo "Unknown CACHE_PINNING_MODE: ${CACHE_PINNING_MODE}" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ "${CACHE_PINNING_MODE}" = "plot" ]]; then
  prepare_shared_chart_dir
  plot_matrix_csv="${CACHE_PINNING_PLOT_MATRIX_CSV:-${MICROBENCH_LATEST_PREFIX}_matrix.csv}"
  if [[ -f "${plot_matrix_csv}" ]]; then
    cp -f "${plot_matrix_csv}" "${SHARED_CHART_DIR}/exp10_cachepinning_matrix.csv"
  fi
  cp -f "${MICROBENCH_CHART_DIR}/validation_latency.svg" "${MICROBENCH_LATEST_PREFIX}_validation_latency.svg" 2>/dev/null || true
  cp -f "${MICROBENCH_CHART_DIR}/validation_cached_tokens.svg" "${MICROBENCH_LATEST_PREFIX}_validation_cached_tokens.svg" 2>/dev/null || true
  cp -f "${MICROBENCH_CHART_DIR}/sweep_replay_latency.svg" "${MICROBENCH_LATEST_PREFIX}_sweep_replay_latency.svg" 2>/dev/null || true
  cp -f "${MICROBENCH_CHART_DIR}/sweep_replay_cached_tokens.svg" "${MICROBENCH_LATEST_PREFIX}_sweep_replay_cached_tokens.svg" 2>/dev/null || true
  cp -f "${MICROBENCH_CHART_DIR}/sweep_latency_gain.svg" "${MICROBENCH_LATEST_PREFIX}_sweep_latency_gain.svg" 2>/dev/null || true
  cp -f "${MICROBENCH_CHART_DIR}/sweep_cache_gain.svg" "${MICROBENCH_LATEST_PREFIX}_sweep_cache_gain.svg" 2>/dev/null || true
  cp -f "${MICROBENCH_CHART_DIR}/chart_manifest.json" "${MICROBENCH_LATEST_PREFIX}_chart_manifest.json" 2>/dev/null || true
  cp -f "${MICROBENCH_CHART_DIR}/sweep_replay_latency.svg" "${SHARED_CHART_DIR}/exp10_cachepinning_latency_vs_distractors.svg" 2>/dev/null || true
else
  build_microbenchmark_report
  build_microbenchmark_charts
fi

banner "CACHE PINNING MICROBENCH DONE"
echo "Mode completed: ${CACHE_PINNING_MODE}"
echo "Contract file: ${CONTRACT_PATH}"
echo "Microbenchmark report dir: ${MICROBENCH_OUT_DIR}"
echo "Latest matrix: ${MICROBENCH_LATEST_PREFIX}_matrix.csv"
echo "Latest summary CSV: ${MICROBENCH_LATEST_PREFIX}_summary.csv"
echo "Latest summary MD: ${MICROBENCH_LATEST_PREFIX}_summary.md"
echo "Latest run contract: ${MICROBENCH_LATEST_PREFIX}_run_contract.json"
echo "Latest validation latency chart: ${MICROBENCH_LATEST_PREFIX}_validation_latency.svg"
echo "Latest validation cached chart: ${MICROBENCH_LATEST_PREFIX}_validation_cached_tokens.svg"
echo "Latest sweep latency chart: ${MICROBENCH_LATEST_PREFIX}_sweep_replay_latency.svg"
echo "Latest sweep cached chart: ${MICROBENCH_LATEST_PREFIX}_sweep_replay_cached_tokens.svg"
