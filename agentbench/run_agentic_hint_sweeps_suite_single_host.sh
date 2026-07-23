#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh
SUITE_CONFIG_PATH="${SUITE_CONFIG_PATH:-agentbench/agentic_hint_sweeps_suite.conf.sh}"
if [[ -f "${SUITE_CONFIG_PATH}" ]]; then
  # shellcheck disable=SC1090
  source "${SUITE_CONFIG_PATH}"
fi
if [[ -f runtime_instrumentation/dynamo_machine_profile.sh ]]; then
  # shellcheck disable=SC1091
  source runtime_instrumentation/dynamo_machine_profile.sh
fi
EXPERIMENT_DIRS_HELPER="${EXPERIMENT_DIRS_HELPER:-./runtime_instrumentation/ensure_experiment_dirs_ready.sh}"

MODEL="${1:-${SUITE_MODEL:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}}"
SUITE_ID="${AGENTIC_HINT_SUITE_ID:-agentic_hint_sweeps_suite_$(date +%Y%m%d_%H%M%S)}"
SUITE_EXPERIMENTS="${SUITE_EXPERIMENTS:-}"
SUITE_RUNS="${SUITE_RUNS:-}"
SUITE_DEFAULT_RUNS="${SUITE_DEFAULT_RUNS:-}"
SUITE_CONTINUE_ON_ERROR="${SUITE_CONTINUE_ON_ERROR:-0}"
SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS="${SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS:-1}"
SUITE_DEFAULT_MODE="${SUITE_DEFAULT_MODE:-sweep}"
SUITE_INTERACTIVE_BUILD_PROGRESS="${SUITE_INTERACTIVE_BUILD_PROGRESS:-1}"
SUITE_ENSURE_PRECISE_RUNTIME="${SUITE_ENSURE_PRECISE_RUNTIME:-auto}"
SUITE_ISOLATION_MODE="${SUITE_ISOLATION_MODE:-per_case}"
SUITE_CHART_GROUP="${SUITE_CHART_GROUP:-}"
EXPERIMENT_RESET_MODE="${EXPERIMENT_RESET_MODE:-flush}"
RETENTION_PROMPT_ISOLATION_MODE="${RETENTION_PROMPT_ISOLATION_MODE:-disjoint}"
SPEC_PREFILL_PROMPT_ISOLATION_MODE="${SPEC_PREFILL_PROMPT_ISOLATION_MODE:-disjoint}"

EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS="1"
EFFECTIVE_EXPERIMENT_RESET_MODE="restart"
EFFECTIVE_KV_RETENTION_RESET_MODE="restart"
EFFECTIVE_RETENTION_SWEEP_SEED_MODE="per_cell"
EFFECTIVE_CACHE_PINNING_SWEEP_SEED_MODE="per_cell"
EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE="per_value"
EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE="per_value"
CASE_EXPERIMENT_RESET_MODE=""
CASE_KV_RETENTION_RESET_MODE=""
WRAPPER_STOP_DYNAMO_WHEN_DONE="1"

SUITE_ROOT_DIR="experiments/reports/agentic_hint_sweeps_suite/${SUITE_ID}"
LATEST_PREFIX="experiments/reports/latest_agentic_hint_sweeps_suite"
SUITE_DRIVER_LOG="${SUITE_DRIVER_LOG:-${SUITE_ROOT_DIR}/suite_driver.log}"
SUITE_MANIFEST_JSON="${SUITE_ROOT_DIR}/suite_manifest.json"
SUITE_SUMMARY_MD="${SUITE_ROOT_DIR}/suite_summary.md"
SUITE_JSONL="${SUITE_ROOT_DIR}/suite_results.jsonl"
SUITE_ENV_SNAPSHOT="${SUITE_ROOT_DIR}/suite_env.sh"
SUITE_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SUITE_CHART_GROUP_RESOLVED=""

LATEST_SUMMARY_MD="${LATEST_PREFIX}_summary.md"
LATEST_MANIFEST_JSON="${LATEST_PREFIX}_manifest.json"
LATEST_DRIVER_LOG="${LATEST_PREFIX}_driver.log"

banner() {
  cat <<EOF
========================================
$1
========================================
EOF
}

suite_run_start_banner() {
  local index="$1"
  local total="$2"
  local experiment_id="$3"
  local label="$4"
  local mode="$5"
  cat <<EOF | tee -a "${SUITE_DRIVER_LOG}"

################################################################################
### SUITE EXPERIMENT ${index}/${total}: EXPERIMENT ${experiment_id} START
### LABEL: ${label}
### MODE: ${mode}
### MODEL: ${MODEL}
################################################################################

EOF
}

suite_run_end_banner() {
  local index="$1"
  local total="$2"
  local experiment_id="$3"
  local label="$4"
  local status="$5"
  cat <<EOF | tee -a "${SUITE_DRIVER_LOG}"

################################################################################
### SUITE EXPERIMENT ${index}/${total}: EXPERIMENT ${experiment_id} END
### LABEL: ${label}
### STATUS: ${status}
################################################################################

EOF
}

usage() {
  cat <<'EOF'
Usage:
  ./agentbench/run_agentic_hint_sweeps_suite_single_host.sh [model]

Recommended flow:
  1. Edit agentbench/agentic_hint_sweeps_suite.conf.sh
  2. Run this script with one model argument

Main knobs:
  SUITE_CONFIG_PATH=path/to/alternate_suite.conf.sh
  DYNAMO_MACHINE_PROFILE=ec2|gh200
  SUITE_RUNS="exp9_synthetic exp11_swebench"
  SUITE_EXPERIMENTS="9 11 12"           # legacy fallback when SUITE_RUNS is unset
  SUITE_ISOLATION_MODE=per_case|clean|flush|fast # per_case uses the known-good reset mode for each selected case
  SUITE_CONTINUE_ON_ERROR=0|1
  SUITE_INTERACTIVE_BUILD_PROGRESS=1
  SUITE_ENSURE_PRECISE_RUNTIME=auto|0|1
EOF
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${MODEL}" ]]; then
  echo "No model specified. Pass it as an argument or set SUITE_MODEL / MODEL / MODEL_NAME." >&2
  exit 1
fi

case "${SUITE_ISOLATION_MODE}" in
  per_case)
    EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS="1"
    EFFECTIVE_EXPERIMENT_RESET_MODE="restart"
    EFFECTIVE_KV_RETENTION_RESET_MODE="restart"
    EFFECTIVE_RETENTION_SWEEP_SEED_MODE="per_cell"
    EFFECTIVE_CACHE_PINNING_SWEEP_SEED_MODE="per_cell"
    EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE="per_value"
    EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE="per_value"
    ;;
  clean)
    EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS="1"
    EFFECTIVE_EXPERIMENT_RESET_MODE="restart"
    EFFECTIVE_KV_RETENTION_RESET_MODE="restart"
    EFFECTIVE_RETENTION_SWEEP_SEED_MODE="per_cell"
    EFFECTIVE_CACHE_PINNING_SWEEP_SEED_MODE="per_cell"
    EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE="per_value"
    EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE="per_value"
    ;;
  flush)
    EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS="1"
    EFFECTIVE_EXPERIMENT_RESET_MODE="flush"
    EFFECTIVE_KV_RETENTION_RESET_MODE="flush"
    EFFECTIVE_RETENTION_SWEEP_SEED_MODE="per_cell"
    EFFECTIVE_CACHE_PINNING_SWEEP_SEED_MODE="per_cell"
    EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE="per_value"
    EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE="per_value"
    ;;
  fast)
    EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS="1"
    EFFECTIVE_EXPERIMENT_RESET_MODE="none"
    EFFECTIVE_KV_RETENTION_RESET_MODE="none"
    EFFECTIVE_RETENTION_SWEEP_SEED_MODE="per_cell"
    EFFECTIVE_CACHE_PINNING_SWEEP_SEED_MODE="per_cell"
    EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE="per_value"
    EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE="per_value"
    ;;
  *)
    echo "Unknown SUITE_ISOLATION_MODE: ${SUITE_ISOLATION_MODE}" >&2
    echo "Valid values: per_case clean flush fast" >&2
    exit 2
    ;;
esac

mkdir -p "${SUITE_ROOT_DIR}"
rm -f "${LATEST_SUMMARY_MD}" "${LATEST_MANIFEST_JSON}" "${LATEST_DRIVER_LOG}"
: > "${SUITE_DRIVER_LOG}"
: > "${SUITE_JSONL}"

cat > "${SUITE_ENV_SNAPSHOT}" <<EOF
AGENTIC_HINT_SUITE_ID='${SUITE_ID}'
SUITE_CONFIG_PATH='${SUITE_CONFIG_PATH}'
DYNAMO_MACHINE_PROFILE='${DYNAMO_MACHINE_PROFILE:-}'
SUITE_MODEL='${MODEL}'
SUITE_DEFAULT_RUNS='${SUITE_DEFAULT_RUNS}'
SUITE_RUNS='${SUITE_RUNS}'
SUITE_EXPERIMENTS='${SUITE_EXPERIMENTS}'
SUITE_ISOLATION_MODE='${SUITE_ISOLATION_MODE}'
SUITE_CONTINUE_ON_ERROR='${SUITE_CONTINUE_ON_ERROR}'
SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS='${EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS}'
SUITE_DEFAULT_MODE='${SUITE_DEFAULT_MODE}'
SUITE_INTERACTIVE_BUILD_PROGRESS='${SUITE_INTERACTIVE_BUILD_PROGRESS}'
SUITE_ENSURE_PRECISE_RUNTIME='${SUITE_ENSURE_PRECISE_RUNTIME}'
SUITE_CHART_GROUP='${SUITE_CHART_GROUP}'
PRECISE_START_MODE='${PRECISE_START_MODE:-}'
EXPERIMENT_RESET_MODE='${EFFECTIVE_EXPERIMENT_RESET_MODE}'
WRAPPER_STOP_DYNAMO_WHEN_DONE='${WRAPPER_STOP_DYNAMO_WHEN_DONE}'
KV_RETENTION_MODE='${KV_RETENTION_MODE:-}'
KV_RETENTION_RESET_MODE='${EFFECTIVE_KV_RETENTION_RESET_MODE}'
RETENTION_SWEEP_SEED_MODE='${EFFECTIVE_RETENTION_SWEEP_SEED_MODE}'
RETENTION_PROMPT_ISOLATION_MODE='${RETENTION_PROMPT_ISOLATION_MODE}'
RETENTION_ATTRIBUTION_MODE='${RETENTION_ATTRIBUTION_MODE:-}'
RETENTION_REQUEST_CONTEXT_MODE='${RETENTION_REQUEST_CONTEXT_MODE:-}'
RETENTION_TOP_LEVEL_PRIORITY_MODE='${RETENTION_TOP_LEVEL_PRIORITY_MODE:-}'
KV_RETENTION_SWEEP_AXIS='${KV_RETENTION_SWEEP_AXIS:-}'
KV_RETENTION_SWEEP_VALUES='${KV_RETENTION_SWEEP_VALUES:-}'
DISTRACTOR_COUNTS='${DISTRACTOR_COUNTS:-}'
PROTECTED_INPUT_LEN='${PROTECTED_INPUT_LEN:-}'
DISTRACTOR_INPUT_LEN='${DISTRACTOR_INPUT_LEN:-}'
PROTECTED_HINT_PROFILES='${PROTECTED_HINT_PROFILES:-}'
SGLANG_TRANSFER_LOG='${SGLANG_TRANSFER_LOG:-}'
SGLANG_TRANSFER_LOG_PROFILE='${SGLANG_TRANSFER_LOG_PROFILE:-}'
CACHE_PINNING_MODE='${CACHE_PINNING_MODE:-}'
CACHE_PINNING_SWEEP_SEED_MODE='${EFFECTIVE_CACHE_PINNING_SWEEP_SEED_MODE}'
CACHE_PINNING_VALIDATE_TTL='${CACHE_PINNING_VALIDATE_TTL:-}'
CACHE_PINNING_SWEEP_VALUES='${CACHE_PINNING_SWEEP_VALUES:-}'
CACHE_PINNING_TTL='${CACHE_PINNING_TTL:-}'
CACHE_PINNING_PINNED_RATIO='${CACHE_PINNING_PINNED_RATIO:-}'
CACHE_PINNING_HICACHE_RATIO='${CACHE_PINNING_HICACHE_RATIO:-}'
PRIORITY_SCHEDULING_MODE='${PRIORITY_SCHEDULING_MODE:-}'
PRIORITY_SCHEDULING_SWEEP_SEED_MODE='${EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE}'
PRIORITY_SCHEDULING_SWEEP_AXIS='${PRIORITY_SCHEDULING_SWEEP_AXIS:-}'
PRIORITY_SCHEDULING_SWEEP_VALUES='${PRIORITY_SCHEDULING_SWEEP_VALUES:-}'
LOW_PRIORITY_COUNT='${LOW_PRIORITY_COUNT:-}'
HIGH_PRIORITY_COUNT='${HIGH_PRIORITY_COUNT:-}'
PRIORITY_INPUT_LEN='${PRIORITY_INPUT_LEN:-}'
PRIORITY_OUTPUT_LEN='${PRIORITY_OUTPUT_LEN:-}'
PRIORITY_INTER_REQUEST_GAP_MS='${PRIORITY_INTER_REQUEST_GAP_MS:-}'
PRIORITY_REQUEST_SOURCE='${PRIORITY_REQUEST_SOURCE:-}'
PRIORITY_SWEBENCH_DATASET='${PRIORITY_SWEBENCH_DATASET:-}'
PRIORITY_SWEBENCH_SPLIT='${PRIORITY_SWEBENCH_SPLIT:-}'
PRIORITY_SWEBENCH_START_INDEX='${PRIORITY_SWEBENCH_START_INDEX:-}'
PRIORITY_SWEBENCH_ALLOW_REUSE='${PRIORITY_SWEBENCH_ALLOW_REUSE:-}'
SPEC_PREFILL_MODE='${SPEC_PREFILL_MODE:-}'
SPEC_PREFILL_PROMPT_ISOLATION_MODE='${SPEC_PREFILL_PROMPT_ISOLATION_MODE}'
SPEC_PREFILL_SWEEP_SEED_MODE='${EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE}'
SPEC_PREFILL_SWEEP_AXIS='${SPEC_PREFILL_SWEEP_AXIS:-}'
SPEC_PREFILL_SWEEP_VALUES='${SPEC_PREFILL_SWEEP_VALUES:-}'
SPEC_PREFILL_TURN_A_WORDS='${SPEC_PREFILL_TURN_A_WORDS:-}'
SPEC_PREFILL_TURN_B_WORDS='${SPEC_PREFILL_TURN_B_WORDS:-}'
SPEC_PREFILL_OUTPUT_TOKENS='${SPEC_PREFILL_OUTPUT_TOKENS:-}'
SPEC_PREFILL_REQUEST_SOURCE='${SPEC_PREFILL_REQUEST_SOURCE:-}'
SPEC_PREFILL_SWEBENCH_DATASET='${SPEC_PREFILL_SWEBENCH_DATASET:-}'
SPEC_PREFILL_SWEBENCH_SPLIT='${SPEC_PREFILL_SWEBENCH_SPLIT:-}'
SPEC_PREFILL_TURN_A_INDEX='${SPEC_PREFILL_TURN_A_INDEX:-}'
SPEC_PREFILL_TURN_B_INDEX='${SPEC_PREFILL_TURN_B_INDEX:-}'
SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET='${SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET:-}'
SPEC_PREFILL_COMPARISON_MODE='${SPEC_PREFILL_COMPARISON_MODE:-}'
EXP9_MODE='${EXP9_MODE:-}'
EXP9_SYNTHETIC_RESET_MODE='${EXP9_SYNTHETIC_RESET_MODE:-}'
EXP9_SWEBENCH_RESET_MODE='${EXP9_SWEBENCH_RESET_MODE:-}'
EXP9_RETENTION_REQUEST_SOURCE='${EXP9_RETENTION_REQUEST_SOURCE:-}'
EXP9_RETENTION_SWEBENCH_DATASET='${EXP9_RETENTION_SWEBENCH_DATASET:-}'
EXP9_RETENTION_SWEBENCH_SPLIT='${EXP9_RETENTION_SWEBENCH_SPLIT:-}'
EXP9_RETENTION_SWEBENCH_INDEX='${EXP9_RETENTION_SWEBENCH_INDEX:-}'
EXP9_RETENTION_SWEBENCH_INSTANCE_ID='${EXP9_RETENTION_SWEBENCH_INSTANCE_ID:-}'
EXP9_RETENTION_SWEBENCH_DISTRACTOR_START_INDEX='${EXP9_RETENTION_SWEBENCH_DISTRACTOR_START_INDEX:-}'
EXP9_RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE='${EXP9_RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE:-}'
EXP9_RETENTION_TRAJECTORY_PROMPT_CATALOG='${EXP9_RETENTION_TRAJECTORY_PROMPT_CATALOG:-}'
EXP9_RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX='${EXP9_RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX:-}'
EXP9_RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID='${EXP9_RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID:-}'
EXP9_RETENTION_TRAJECTORY_PROTECTED_STAGE='${EXP9_RETENTION_TRAJECTORY_PROTECTED_STAGE:-}'
EXP9_RETENTION_TRAJECTORY_STAGES='${EXP9_RETENTION_TRAJECTORY_STAGES:-}'
EXP9_RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE='${EXP9_RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE:-}'
EXP9_RETENTION_TRAJECTORY_REPLAY_HEADER_MODE='${EXP9_RETENTION_TRAJECTORY_REPLAY_HEADER_MODE:-}'
EXP9_RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX='${EXP9_RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX:-}'
EXP9_RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE='${EXP9_RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE:-}'
EXP9_RETENTION_ATTRIBUTION_MODE='${EXP9_RETENTION_ATTRIBUTION_MODE:-}'
EXP9_RETENTION_REQUEST_CONTEXT_MODE='${EXP9_RETENTION_REQUEST_CONTEXT_MODE:-}'
EXP9_RETENTION_TOP_LEVEL_PRIORITY_MODE='${EXP9_RETENTION_TOP_LEVEL_PRIORITY_MODE:-}'
EXP9_STOP_ON_PROBE_FAILURE='${EXP9_STOP_ON_PROBE_FAILURE:-}'
EXP9_DISTRACTOR_COUNTS='${EXP9_DISTRACTOR_COUNTS:-}'
EXP9_PROTECTED_INPUT_LEN='${EXP9_PROTECTED_INPUT_LEN:-}'
EXP9_DISTRACTOR_INPUT_LEN='${EXP9_DISTRACTOR_INPUT_LEN:-}'
EXP9_PROTECTED_HINT_PROFILES='${EXP9_PROTECTED_HINT_PROFILES:-}'
EXP10_MODE='${EXP10_MODE:-}'
EXP10_DISTRACTOR_COUNTS='${EXP10_DISTRACTOR_COUNTS:-}'
EXP10_PROTECTED_INPUT_LEN='${EXP10_PROTECTED_INPUT_LEN:-}'
EXP10_DISTRACTOR_INPUT_LEN='${EXP10_DISTRACTOR_INPUT_LEN:-}'
EXP10_CACHE_PINNING_TTL='${EXP10_CACHE_PINNING_TTL:-}'
EXP10_CACHE_PINNING_PINNED_RATIO='${EXP10_CACHE_PINNING_PINNED_RATIO:-}'
EXP10_CACHE_PINNING_HICACHE_RATIO='${EXP10_CACHE_PINNING_HICACHE_RATIO:-}'
EXP11_MODE='${EXP11_MODE:-}'
EXP11_SYNTHETIC_RESET_MODE='${EXP11_SYNTHETIC_RESET_MODE:-}'
EXP11_SWEBENCH_RESET_MODE='${EXP11_SWEBENCH_RESET_MODE:-}'
EXP11_PRIORITY_REQUEST_SOURCE='${EXP11_PRIORITY_REQUEST_SOURCE:-}'
EXP11_PRIORITY_SWEBENCH_DATASET='${EXP11_PRIORITY_SWEBENCH_DATASET:-}'
EXP11_PRIORITY_SWEBENCH_SPLIT='${EXP11_PRIORITY_SWEBENCH_SPLIT:-}'
EXP11_PRIORITY_SWEBENCH_START_INDEX='${EXP11_PRIORITY_SWEBENCH_START_INDEX:-}'
EXP11_PRIORITY_SWEBENCH_ALLOW_REUSE='${EXP11_PRIORITY_SWEBENCH_ALLOW_REUSE:-}'
EXP11_PRIORITY_SCHEDULING_SWEEP_AXIS='${EXP11_PRIORITY_SCHEDULING_SWEEP_AXIS:-}'
EXP11_PRIORITY_SCHEDULING_SWEEP_VALUES='${EXP11_PRIORITY_SCHEDULING_SWEEP_VALUES:-}'
EXP11_LOW_PRIORITY_COUNT='${EXP11_LOW_PRIORITY_COUNT:-}'
EXP11_HIGH_PRIORITY_COUNT='${EXP11_HIGH_PRIORITY_COUNT:-}'
EXP11_PRIORITY_INPUT_LEN='${EXP11_PRIORITY_INPUT_LEN:-}'
EXP11_PRIORITY_OUTPUT_LEN='${EXP11_PRIORITY_OUTPUT_LEN:-}'
EXP11_PRIORITY_INTER_REQUEST_GAP_MS='${EXP11_PRIORITY_INTER_REQUEST_GAP_MS:-}'
EXP12_MODE='${EXP12_MODE:-}'
EXP12_SYNTHETIC_RESET_MODE='${EXP12_SYNTHETIC_RESET_MODE:-}'
EXP12_SWEBENCH_RESET_MODE='${EXP12_SWEBENCH_RESET_MODE:-}'
EXP12_SPEC_PREFILL_REQUEST_SOURCE='${EXP12_SPEC_PREFILL_REQUEST_SOURCE:-}'
EXP12_SPEC_PREFILL_SWEBENCH_DATASET='${EXP12_SPEC_PREFILL_SWEBENCH_DATASET:-}'
EXP12_SPEC_PREFILL_SWEBENCH_SPLIT='${EXP12_SPEC_PREFILL_SWEBENCH_SPLIT:-}'
EXP12_SPEC_PREFILL_TURN_A_INDEX='${EXP12_SPEC_PREFILL_TURN_A_INDEX:-}'
EXP12_SPEC_PREFILL_TURN_B_INDEX='${EXP12_SPEC_PREFILL_TURN_B_INDEX:-}'
EXP12_SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET='${EXP12_SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET:-}'
EXP12_SPEC_PREFILL_COMPARISON_MODE='${EXP12_SPEC_PREFILL_COMPARISON_MODE:-}'
EXP12_SPEC_PREFILL_ATTRIBUTION_MODE='${EXP12_SPEC_PREFILL_ATTRIBUTION_MODE:-}'
EXP12_SPEC_PREFILL_REQUEST_CONTEXT_MODE='${EXP12_SPEC_PREFILL_REQUEST_CONTEXT_MODE:-}'
EXP12_SPEC_PREFILL_SWEEP_AXIS='${EXP12_SPEC_PREFILL_SWEEP_AXIS:-}'
EXP12_SPEC_PREFILL_SWEEP_VALUES='${EXP12_SPEC_PREFILL_SWEEP_VALUES:-}'
EXP12_SPEC_PREFILL_TURN_A_WORDS='${EXP12_SPEC_PREFILL_TURN_A_WORDS:-}'
EXP12_SPEC_PREFILL_TURN_B_WORDS='${EXP12_SPEC_PREFILL_TURN_B_WORDS:-}'
EXP12_SPEC_PREFILL_OUTPUT_TOKENS='${EXP12_SPEC_PREFILL_OUTPUT_TOKENS:-}'
EXP13_MODE='${EXP13_MODE:-}'
EXP13_SYNTHETIC_RESET_MODE='${EXP13_SYNTHETIC_RESET_MODE:-}'
EXP13_SWEBENCH_RESET_MODE='${EXP13_SWEBENCH_RESET_MODE:-}'
EXP13_PRIORITY_REQUEST_SOURCE='${EXP13_PRIORITY_REQUEST_SOURCE:-}'
EXP13_PRIORITY_SWEBENCH_DATASET='${EXP13_PRIORITY_SWEBENCH_DATASET:-}'
EXP13_PRIORITY_SWEBENCH_SPLIT='${EXP13_PRIORITY_SWEBENCH_SPLIT:-}'
EXP13_PRIORITY_SWEBENCH_START_INDEX='${EXP13_PRIORITY_SWEBENCH_START_INDEX:-}'
EXP13_PRIORITY_SWEBENCH_ALLOW_REUSE='${EXP13_PRIORITY_SWEBENCH_ALLOW_REUSE:-}'
EXP13_PRIORITY_SCHEDULING_SWEEP_AXIS='${EXP13_PRIORITY_SCHEDULING_SWEEP_AXIS:-}'
EXP13_PRIORITY_SCHEDULING_SWEEP_VALUES='${EXP13_PRIORITY_SCHEDULING_SWEEP_VALUES:-}'
EXP13_LOW_PRIORITY_COUNT='${EXP13_LOW_PRIORITY_COUNT:-}'
EXP13_HIGH_PRIORITY_COUNT='${EXP13_HIGH_PRIORITY_COUNT:-}'
EXP13_PRIORITY_INPUT_LEN='${EXP13_PRIORITY_INPUT_LEN:-}'
EXP13_PRIORITY_OUTPUT_LEN='${EXP13_PRIORITY_OUTPUT_LEN:-}'
EXP13_PRIORITY_INTER_REQUEST_GAP_MS='${EXP13_PRIORITY_INTER_REQUEST_GAP_MS:-}'
EOF

log() {
  echo "$@" | tee -a "${SUITE_DRIVER_LOG}"
}

resolve_value() {
  local var_name=""
  for var_name in "$@"; do
    if [[ -n "${!var_name:-}" ]]; then
      printf '%s' "${!var_name}"
      return 0
    fi
  done
  return 0
}

run_and_log() {
  "$@" 2>&1 | tee -a "${SUITE_DRIVER_LOG}"
}

ensure_suite_experiment_dirs_ready() {
  if ! run_and_log "${EXPERIMENT_DIRS_HELPER}"; then
    echo "Suite experiment directory preflight failed." >&2
    exit 1
  fi
  export EXPERIMENT_DIRS_READY_ALREADY=1
}

should_ensure_precise_runtime() {
  case "${SUITE_ENSURE_PRECISE_RUNTIME}" in
    1|true|yes)
      return 0
      ;;
    0|false|no)
      return 1
      ;;
    auto|"")
      [[ "${DYNAMO_MACHINE_PROFILE:-}" = "gh200" ]]
      return
      ;;
    *)
      echo "Unknown SUITE_ENSURE_PRECISE_RUNTIME value: ${SUITE_ENSURE_PRECISE_RUNTIME}" >&2
      echo "Valid values: auto 0 1" >&2
      exit 2
      ;;
  esac
}

ensure_suite_precise_runtime_if_needed() {
  if ! should_ensure_precise_runtime; then
    return 0
  fi

  banner "SUITE PRECISE RUNTIME START (GH200 preflight/build is running once before the suite)" | tee -a "${SUITE_DRIVER_LOG}"
  if ! run_and_log ./runtime_instrumentation/ensure_precise_runtime_ready.sh --machine-profile "${DYNAMO_MACHINE_PROFILE}" --build-if-missing; then
    echo "Suite precise runtime preflight failed." >&2
    exit 1
  fi
  banner "SUITE PRECISE RUNTIME READY (GH200 machine-specific precise images are ready)" | tee -a "${SUITE_DRIVER_LOG}"
}

sync_latest_matrices_to_shared_charts() {
  local charts_dir="experiments/charts"
  mkdir -p "${charts_dir}"
  has_selected_experiment 9 && [[ -f "experiments/reports/latest_kv_retention_microbenchmark_matrix.csv" ]] && cp -f "experiments/reports/latest_kv_retention_microbenchmark_matrix.csv" "${charts_dir}/exp9_kvretention_matrix.csv"
  has_selected_experiment 10 && [[ -f "experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv" ]] && cp -f "experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv" "${charts_dir}/exp10_cachepinning_matrix.csv"
  has_selected_experiment 11 && [[ -f "experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv" ]] && cp -f "experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv" "${charts_dir}/exp11_prioritysched_matrix.csv"
  has_selected_experiment 12 && [[ -f "experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv" ]] && cp -f "experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv" "${charts_dir}/exp12_specprefill_matrix.csv"
  has_selected_experiment 13 && [[ -f "experiments/reports/latest_latency_sensitivity_microbenchmark_matrix.csv" ]] && cp -f "experiments/reports/latest_latency_sensitivity_microbenchmark_matrix.csv" "${charts_dir}/exp13_latencysens_matrix.csv"
}

sanitize_chart_group() {
  local raw="$1"
  printf '%s' "${raw}" | tr -c 'A-Za-z0-9._-' '_'
}

infer_suite_chart_group() {
  if [[ -n "${SUITE_CHART_GROUP:-}" ]]; then
    sanitize_chart_group "${SUITE_CHART_GROUP}"
    return 0
  fi

  local saw_swebench=0
  local saw_synthetic=0
  local saw_other=0
  local run_case=""
  for run_case in "${SUITE_RUN_SELECTION[@]:-}"; do
    case "${run_case}" in
      *_swebench) saw_swebench=1 ;;
      *_synthetic) saw_synthetic=1 ;;
      *) saw_other=1 ;;
    esac
  done

  if [[ "${saw_swebench}" = "1" && "${saw_synthetic}" = "0" && "${saw_other}" = "0" ]]; then
    echo "swebench"
  elif [[ "${saw_synthetic}" = "1" && "${saw_swebench}" = "0" && "${saw_other}" = "0" ]]; then
    echo "synthetic"
  elif [[ "${saw_swebench}${saw_synthetic}${saw_other}" = "001" ]]; then
    echo "other"
  else
    echo "mixed"
  fi
}

copy_chart_asset_to_suite_dirs() {
  local src="$1"
  if [[ ! -f "${src}" || -z "${SUITE_CHART_GROUP_RESOLVED}" ]]; then
    return 0
  fi

  local basename
  basename="$(basename "${src}")"
  local group_dir="experiments/charts/${SUITE_CHART_GROUP_RESOLVED}"
  local archive_dir="experiments/charts/archive/${SUITE_ID}"
  mkdir -p "${group_dir}" "${archive_dir}"
  cp -f "${src}" "${group_dir}/${basename}"
  cp -f "${src}" "${archive_dir}/${basename}"
}

mirror_selected_shared_charts_to_suite_dirs() {
  local charts_dir="experiments/charts"
  local path=""
  for path in "${charts_dir}"/exp9_* "${charts_dir}"/exp10_* "${charts_dir}"/exp11_* "${charts_dir}"/exp12_* "${charts_dir}"/exp13_*; do
    [[ -f "${path}" ]] || continue
    copy_chart_asset_to_suite_dirs "${path}"
  done
}

prune_suite_chart_group_dir() {
  if [[ -z "${SUITE_CHART_GROUP_RESOLVED}" ]]; then
    return 0
  fi
  local group_dir="experiments/charts/${SUITE_CHART_GROUP_RESOLVED}"
  mkdir -p "${group_dir}"
  rm -f \
    "${group_dir}"/exp9_* \
    "${group_dir}"/exp10_* \
    "${group_dir}"/exp11_* \
    "${group_dir}"/exp12_* \
    "${group_dir}"/exp13_* 2>/dev/null || true
}

prune_shared_chart_dir_for_suite_selection() {
  local charts_dir="experiments/charts"
  mkdir -p "${charts_dir}"

  prune_one_experiment() {
    local experiment_id="$1"
    shift
    if has_selected_experiment "${experiment_id}"; then
      return 0
    fi
    rm -f "$@"
  }

  prune_one_experiment 9 \
    "${charts_dir}/exp9_kvretention_matrix.csv" \
    "${charts_dir}/exp9_kvretention_latency_vs_distractors.svg" \
    "${charts_dir}/exp9_kvretention_cache_vs_distractors.svg" \
    "${charts_dir}/exp9_kvretention_latency_gain_vs_distractors.svg" \
    "${charts_dir}/exp9_kvretention_cache_gain_vs_distractors.svg" \
    "${charts_dir}/exp9_kvretention_survival_vs_distractors.svg" \
    "${charts_dir}/latest_kv_retention_microbenchmark_matrix.csv"

  prune_one_experiment 10 \
    "${charts_dir}/exp10_cachepinning_matrix.csv" \
    "${charts_dir}/exp10_cachepinning_validation_latency.svg" \
    "${charts_dir}/exp10_cachepinning_validation_cache.svg" \
    "${charts_dir}/exp10_cachepinning_latency_vs_distractors.svg" \
    "${charts_dir}/exp10_cachepinning_cache_vs_distractors.svg" \
    "${charts_dir}/exp10_cachepinning_latency_gain_vs_distractors.svg" \
    "${charts_dir}/exp10_cachepinning_cache_gain_vs_distractors.svg" \
    "${charts_dir}/latest_cache_pinning_microbenchmark_matrix.csv" \
    "${charts_dir}/latest_cache_pinning_microbenchmark_validation_latency.svg" \
    "${charts_dir}/latest_cache_pinning_microbenchmark_validation_cached_tokens.svg" \
    "${charts_dir}/latest_cache_pinning_microbenchmark_sweep_replay_latency.svg" \
    "${charts_dir}/latest_cache_pinning_microbenchmark_sweep_replay_cached_tokens.svg"

  prune_one_experiment 11 \
    "${charts_dir}/exp11_prioritysched_matrix.csv" \
    "${charts_dir}/exp11_prioritysched_jump_ahead_vs_arrival_gap.svg" \
    "${charts_dir}/exp11_prioritysched_queue_wait_vs_arrival_gap.svg" \
    "${charts_dir}/exp11_prioritysched_priority_wins_vs_arrival_gap.svg" \
    "${charts_dir}/exp11_prioritysched_wait_vs_arrival_gap.svg" \
    "${charts_dir}/exp11_prioritysched_wait_gain_vs_arrival_gap.svg" \
    "${charts_dir}/exp11_prioritysched_latency_vs_arrival_gap.svg" \
    "${charts_dir}/exp11_prioritysched_latency_gain_vs_arrival_gap.svg" \
    "${charts_dir}/latest_priority_scheduling_microbenchmark_matrix.csv"

  prune_one_experiment 12 \
    "${charts_dir}/exp12_specprefill_matrix.csv" \
    "${charts_dir}/exp12_specprefill_latency_vs_warmup_wait.svg" \
    "${charts_dir}/exp12_specprefill_cache_vs_warmup_wait.svg" \
    "${charts_dir}/exp12_specprefill_latency_gain_vs_warmup_wait.svg" \
    "${charts_dir}/exp12_specprefill_cache_gain_vs_warmup_wait.svg" \
    "${charts_dir}/exp12_specprefill_turna_latency_vs_warmup_wait.svg" \
    "${charts_dir}/latest_speculative_prefill_microbenchmark_matrix.csv"

  prune_one_experiment 13 \
    "${charts_dir}/exp13_latencysens_matrix.csv" \
    "${charts_dir}/exp13_latencysens_jump_ahead_vs_arrival_gap.svg" \
    "${charts_dir}/latest_latency_sensitivity_microbenchmark_matrix.csv"
}

sync_shared_assets_for_experiment() {
  local experiment_id="$1"
  local published_any=0
  local charts_dir="experiments/charts"
  mkdir -p "${charts_dir}"

  sync_one() {
    local src="$1"
    local dest="$2"
    if [[ -f "${src}" ]]; then
      cp -f "${src}" "${dest}"
      copy_chart_asset_to_suite_dirs "${dest}"
      published_any=1
    fi
  }

  case "${experiment_id}" in
    9)
      sync_one "experiments/reports/latest_kv_retention_microbenchmark_matrix.csv" "${charts_dir}/exp9_kvretention_matrix.csv"
      sync_one "experiments/reports/latest_kv_retention_microbenchmark_replay_latency.svg" "${charts_dir}/exp9_kvretention_latency_vs_distractors.svg"
      sync_one "experiments/reports/latest_kv_retention_microbenchmark_replay_cached_tokens.svg" "${charts_dir}/exp9_kvretention_cache_vs_distractors.svg"
      ;;
    10)
      sync_one "experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv" "${charts_dir}/exp10_cachepinning_matrix.csv"
      sync_one "experiments/reports/latest_cache_pinning_microbenchmark_validation_latency.svg" "${charts_dir}/exp10_cachepinning_validation_latency.svg"
      sync_one "experiments/reports/latest_cache_pinning_microbenchmark_validation_cached_tokens.svg" "${charts_dir}/exp10_cachepinning_validation_cache.svg"
      sync_one "experiments/reports/latest_cache_pinning_microbenchmark_sweep_replay_latency.svg" "${charts_dir}/exp10_cachepinning_latency_vs_distractors.svg"
      sync_one "experiments/reports/latest_cache_pinning_microbenchmark_sweep_replay_cached_tokens.svg" "${charts_dir}/exp10_cachepinning_cache_vs_distractors.svg"
      sync_one "experiments/reports/latest_cache_pinning_microbenchmark_sweep_latency_gain.svg" "${charts_dir}/exp10_cachepinning_latency_gain_vs_distractors.svg"
      sync_one "experiments/reports/latest_cache_pinning_microbenchmark_sweep_cache_gain.svg" "${charts_dir}/exp10_cachepinning_cache_gain_vs_distractors.svg"
      ;;
    11)
      sync_one "experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv" "${charts_dir}/exp11_prioritysched_matrix.csv"
      sync_one "experiments/reports/latest_priority_scheduling_microbenchmark_jump_ahead.svg" "${charts_dir}/exp11_prioritysched_jump_ahead_vs_arrival_gap.svg"
      ;;
    12)
      sync_one "experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv" "${charts_dir}/exp12_specprefill_matrix.csv"
      sync_one "experiments/reports/latest_speculative_prefill_microbenchmark_turnb_latency.svg" "${charts_dir}/exp12_specprefill_latency_vs_warmup_wait.svg"
      ;;
    13)
      sync_one "experiments/reports/latest_latency_sensitivity_microbenchmark_matrix.csv" "${charts_dir}/exp13_latencysens_matrix.csv"
      sync_one "experiments/reports/latest_latency_sensitivity_microbenchmark_jump_ahead.svg" "${charts_dir}/exp13_latencysens_jump_ahead_vs_arrival_gap.svg"
      ;;
  esac

  if [[ "${published_any}" = "1" ]]; then
    log "Published Experiment ${experiment_id} charts to ${charts_dir}"
  else
    log "No publishable chart outputs were found yet for Experiment ${experiment_id}"
  fi
}

resolved_mode_display() {
  local experiment_id="$1"
  local mode="$2"
  case "${experiment_id}:${mode}" in
    9:all|11:all|12:all|13:all)
      echo "all (resolved to sweep + plot)"
      ;;
    10:all)
      echo "all (resolved to validate + sweep + plot)"
      ;;
    *)
      echo "${mode}"
      ;;
  esac
}

canonical_experiment() {
  case "$1" in
    9|retention|kv_retention) echo "9" ;;
    10|cache_pinning|pinning) echo "10" ;;
    11|priority|priority_scheduling) echo "11" ;;
    12|spec_prefill|speculative_prefill) echo "12" ;;
    13|latency_sensitivity|latency) echo "13" ;;
    *) return 1 ;;
  esac
}

canonical_suite_run() {
  case "$1" in
    exp9_synthetic|9_synthetic|kv_retention_synthetic) echo "exp9_synthetic" ;;
    exp9_swebench|9_swebench|kv_retention_swebench) echo "exp9_swebench" ;;
    exp9_trajectory|9_trajectory|kv_retention_trajectory|trajectory_retention) echo "exp9_trajectory" ;;
    exp10|exp10_cache_pinning|cache_pinning) echo "exp10" ;;
    exp11_synthetic|11_synthetic|priority_synthetic|priority_scheduling_synthetic) echo "exp11_synthetic" ;;
    exp11_swebench|11_swebench|priority_swebench|priority_scheduling_swebench) echo "exp11_swebench" ;;
    exp12_synthetic|12_synthetic|spec_prefill_synthetic|speculative_prefill_synthetic) echo "exp12_synthetic" ;;
    exp12_swebench|12_swebench|spec_prefill_swebench|speculative_prefill_swebench) echo "exp12_swebench" ;;
    exp13_synthetic|13_synthetic|latency_sensitivity_synthetic) echo "exp13_synthetic" ;;
    exp13_swebench|13_swebench|latency_sensitivity_swebench) echo "exp13_swebench" ;;
    *) return 1 ;;
  esac
}

suite_run_experiment_id() {
  case "$1" in
    exp9_*) echo "9" ;;
    exp10*) echo "10" ;;
    exp11_*) echo "11" ;;
    exp12_*) echo "12" ;;
    exp13_*) echo "13" ;;
    *) return 1 ;;
  esac
}

build_suite_run_selection() {
  SUITE_RUN_SELECTION=()
  local token=""
  local exp=""
  if [[ -n "${SUITE_RUNS:-}" ]]; then
    for token in ${SUITE_RUNS}; do
      if exp="$(canonical_suite_run "${token}")"; then
        SUITE_RUN_SELECTION+=("${exp}")
      else
        SUITE_RUN_SELECTION+=("UNKNOWN:${token}")
      fi
    done
    return
  fi

  if [[ -z "${SUITE_EXPERIMENTS:-}" && -n "${SUITE_DEFAULT_RUNS:-}" ]]; then
    for token in ${SUITE_DEFAULT_RUNS}; do
      if exp="$(canonical_suite_run "${token}")"; then
        SUITE_RUN_SELECTION+=("${exp}")
      else
        SUITE_RUN_SELECTION+=("UNKNOWN:${token}")
      fi
    done
    return
  fi

  for token in ${SUITE_EXPERIMENTS}; do
    if ! exp="$(canonical_experiment "${token}")"; then
      SUITE_RUN_SELECTION+=("UNKNOWN:${token}")
      continue
    fi
    case "${exp}" in
      9) SUITE_RUN_SELECTION+=("exp9_synthetic") ;;
      10) SUITE_RUN_SELECTION+=("exp10") ;;
      11) SUITE_RUN_SELECTION+=("exp11_synthetic") ;;
      12) SUITE_RUN_SELECTION+=("exp12_synthetic") ;;
    esac
  done
}

has_selected_experiment() {
  local target
  target="$(canonical_experiment "$1")" || return 1
  local exp=""
  local run_case=""
  for run_case in "${SUITE_RUN_SELECTION[@]:-}"; do
    exp="$(suite_run_experiment_id "${run_case}")" || continue
    if [[ "${exp}" = "${target}" ]]; then
      return 0
    fi
  done
  return 1
}

append_result_json() {
  python3 - <<'PY' \
    "${SUITE_JSONL}" \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" "$9" "${10}" "${11}" "${12}" "${13}" "${14}"
import json
import sys

path = sys.argv[1]
payload = {
    "experiment_id": sys.argv[2],
    "label": sys.argv[3],
    "status": sys.argv[4],
    "mode": sys.argv[5],
    "wrapper": sys.argv[6],
    "latest_matrix": sys.argv[7],
    "latest_summary_csv": sys.argv[8],
    "latest_summary_md": sys.argv[9],
    "latest_run_contract": sys.argv[10],
    "latest_chart_manifest": sys.argv[11],
    "latest_charts": [item for item in sys.argv[12].split("|") if item],
    "error_message": sys.argv[13],
    "started_at_utc": sys.argv[14],
    "finished_at_utc": sys.argv[15],
}
with open(path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(payload, sort_keys=True) + "\n")
PY
}

build_suite_outputs() {
  python3 - <<'PY' \
    "${SUITE_JSONL}" \
    "${SUITE_MANIFEST_JSON}" \
    "${SUITE_SUMMARY_MD}" \
    "${SUITE_ID}" \
    "${MODEL}" \
    "${DYNAMO_MACHINE_PROFILE:-}" \
    "${SUITE_RUNS}" \
    "${SUITE_RUN_SELECTION[*]}" \
    "${SUITE_EXPERIMENTS}" \
    "${SUITE_CONTINUE_ON_ERROR}" \
    "${SUITE_ENV_SNAPSHOT}" \
    "${SUITE_DRIVER_LOG}" \
    "${SUITE_STARTED_AT}" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "${SUITE_CHART_GROUP_RESOLVED}" \
    "experiments/charts/${SUITE_CHART_GROUP_RESOLVED}" \
    "experiments/charts/archive/${SUITE_ID}"
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

jsonl_path = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
summary_path = Path(sys.argv[3])
suite_id = sys.argv[4]
model = sys.argv[5]
machine_profile = sys.argv[6]
suite_runs = sys.argv[7]
resolved_suite_runs = sys.argv[8]
suite_experiments = sys.argv[9]
continue_on_error = sys.argv[10]
env_snapshot = sys.argv[11]
driver_log = sys.argv[12]
suite_started_at = sys.argv[13]
suite_finished_at = sys.argv[14]
suite_chart_group = sys.argv[15]
suite_chart_group_dir = sys.argv[16]
suite_chart_archive_dir = sys.argv[17]

results = []
if jsonl_path.exists():
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            results.append(json.loads(line))

manifest = {
    "suite_id": suite_id,
    "model": model,
    "machine_profile": machine_profile,
    "suite_runs": suite_runs,
    "resolved_suite_runs": resolved_suite_runs,
    "suite_experiments": suite_experiments,
    "continue_on_error": continue_on_error,
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "started_at_utc": suite_started_at,
    "finished_at_utc": suite_finished_at,
    "suite_chart_group": suite_chart_group,
    "suite_chart_group_dir": str(Path(suite_chart_group_dir).resolve()),
    "suite_chart_archive_dir": str(Path(suite_chart_archive_dir).resolve()),
    "suite_env_snapshot": str(Path(env_snapshot).resolve()),
    "suite_driver_log": str(Path(driver_log).resolve()),
    "results": results,
}
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

lines = [
    "# Agentic Hint Sweeps Suite",
    "",
    f"- suite_id: `{suite_id}`",
    f"- model: `{model}`",
    f"- machine_profile: `{machine_profile}`",
    f"- suite_runs: `{suite_runs}`",
    f"- resolved_suite_runs: `{resolved_suite_runs}`",
    f"- legacy_experiments: `{suite_experiments}`",
    f"- continue_on_error: `{continue_on_error}`",
    f"- started_at_utc: `{suite_started_at}`",
    f"- finished_at_utc: `{suite_finished_at}`",
    f"- chart_group: `{suite_chart_group}`",
    f"- chart_group_dir: `{suite_chart_group_dir}`",
    f"- chart_archive_dir: `{suite_chart_archive_dir}`",
    f"- env_snapshot: `{env_snapshot}`",
    f"- driver_log: `{driver_log}`",
    "",
    "| Experiment | Status | Mode | Matrix | Charts |",
    "| --- | --- | --- | --- | --- |",
]
for result in results:
    chart_text = "<br>".join(result["latest_charts"]) if result["latest_charts"] else "-"
    matrix_text = result["latest_matrix"] or "-"
    lines.append(
        f"| {result['experiment_id']} ({result['label']}) | {result['status']} | {result['mode']} | {matrix_text} | {chart_text} |"
    )
    if result["error_message"]:
        lines.append(f"|  | error |  |  | `{result['error_message']}` |")
summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

  cp -f "${SUITE_MANIFEST_JSON}" "${LATEST_MANIFEST_JSON}"
  cp -f "${SUITE_SUMMARY_MD}" "${LATEST_SUMMARY_MD}"
  cp -f "${SUITE_DRIVER_LOG}" "${LATEST_DRIVER_LOG}"
}

stop_dynamo_if_requested() {
  if [[ "${EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS}" = "1" ]]; then
    log "Stopping Dynamo between experiments..."
    ./run_dynamo_single_host.sh stop >> "${SUITE_DRIVER_LOG}" 2>&1 || true
    env EXPERIMENT_RESET_STATE_FILE="experiments/runtime_state/active_runtime_signature.txt" \
      ./runtime_instrumentation/reset_experiment_state.sh clear-active >> "${SUITE_DRIVER_LOG}" 2>&1 || true
  fi
}

prepare_fresh_runtime_for_experiment() {
  if [[ "${EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS}" != "1" ]]; then
    return 0
  fi
  log "Preparing a clean Dynamo state for the next experiment..."
  ./run_dynamo_single_host.sh stop >> "${SUITE_DRIVER_LOG}" 2>&1 || true
  env EXPERIMENT_RESET_STATE_FILE="experiments/runtime_state/active_runtime_signature.txt" \
    ./runtime_instrumentation/reset_experiment_state.sh clear-active >> "${SUITE_DRIVER_LOG}" 2>&1 || true
}

set_case_reset_modes() {
  if [[ "${SUITE_ISOLATION_MODE}" != "per_case" ]]; then
    CASE_EXPERIMENT_RESET_MODE=""
    CASE_KV_RETENTION_RESET_MODE=""
    return 0
  fi
  CASE_EXPERIMENT_RESET_MODE="$1"
  CASE_KV_RETENTION_RESET_MODE="${2:-$1}"
}

case_experiment_reset_mode() {
  printf '%s' "${CASE_EXPERIMENT_RESET_MODE:-${EFFECTIVE_EXPERIMENT_RESET_MODE}}"
}

case_kv_retention_reset_mode() {
  printf '%s' "${CASE_KV_RETENTION_RESET_MODE:-${CASE_EXPERIMENT_RESET_MODE:-${EFFECTIVE_KV_RETENTION_RESET_MODE}}}"
}

run_experiment_9() {
  local index="$1"
  local total="$2"
  local mode="${EXP9_MODE:-${KV_RETENTION_MODE:-${SUITE_DEFAULT_MODE}}}"
  local display_mode
  display_mode="$(resolved_mode_display "9" "${mode}")"
  local wrapper="./agentbench/run_kv_retention_microbenchmark_single_host.sh"
  local started_at
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local status="passed"
  local error_message=""
  local exp9_retention_attribution_mode
  local exp9_retention_request_source
  local exp9_retention_swebench_dataset
  local exp9_retention_swebench_split
  local exp9_retention_swebench_index
  local exp9_retention_swebench_instance_id
  local exp9_retention_swebench_distractor_start_index
  local exp9_retention_swebench_allow_distractor_reuse
  local exp9_retention_trajectory_prompt_catalog
  local exp9_retention_trajectory_protected_task_index
  local exp9_retention_trajectory_protected_instance_id
  local exp9_retention_trajectory_protected_stage
  local exp9_retention_trajectory_stages
  local exp9_retention_trajectory_distractor_start_task_index
  local exp9_retention_trajectory_allow_distractor_reuse
  local exp9_retention_request_context_mode
  local exp9_retention_top_level_priority_mode
  local exp9_distractor_counts
  local exp9_protected_input_len
  local exp9_distractor_input_len
  local exp9_protected_hint_profiles
  local exp9_stop_on_probe_failure
  local exp9_experiment_reset_mode
  local exp9_kv_retention_reset_mode
  exp9_retention_request_source="$(resolve_value EXP9_RETENTION_REQUEST_SOURCE RETENTION_REQUEST_SOURCE)"
  exp9_retention_swebench_dataset="$(resolve_value EXP9_RETENTION_SWEBENCH_DATASET RETENTION_SWEBENCH_DATASET)"
  exp9_retention_swebench_split="$(resolve_value EXP9_RETENTION_SWEBENCH_SPLIT RETENTION_SWEBENCH_SPLIT)"
  exp9_retention_swebench_index="$(resolve_value EXP9_RETENTION_SWEBENCH_INDEX RETENTION_SWEBENCH_INDEX)"
  exp9_retention_swebench_instance_id="$(resolve_value EXP9_RETENTION_SWEBENCH_INSTANCE_ID RETENTION_SWEBENCH_INSTANCE_ID)"
  exp9_retention_swebench_distractor_start_index="$(resolve_value EXP9_RETENTION_SWEBENCH_DISTRACTOR_START_INDEX RETENTION_SWEBENCH_DISTRACTOR_START_INDEX)"
  exp9_retention_swebench_allow_distractor_reuse="$(resolve_value EXP9_RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE)"
  exp9_retention_trajectory_prompt_catalog="$(resolve_value EXP9_RETENTION_TRAJECTORY_PROMPT_CATALOG RETENTION_TRAJECTORY_PROMPT_CATALOG)"
  exp9_retention_trajectory_protected_task_index="$(resolve_value EXP9_RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX)"
  exp9_retention_trajectory_protected_instance_id="$(resolve_value EXP9_RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID)"
  exp9_retention_trajectory_protected_stage="$(resolve_value EXP9_RETENTION_TRAJECTORY_PROTECTED_STAGE RETENTION_TRAJECTORY_PROTECTED_STAGE)"
  exp9_retention_trajectory_stages="$(resolve_value EXP9_RETENTION_TRAJECTORY_STAGES RETENTION_TRAJECTORY_STAGES)"
  exp9_retention_trajectory_prompt_prefix_mode="$(resolve_value EXP9_RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE)"
  if [[ -z "${exp9_retention_trajectory_prompt_prefix_mode}" ]]; then
    exp9_retention_trajectory_prompt_prefix_mode="$(resolve_value EXP9_RETENTION_TRAJECTORY_REPLAY_HEADER_MODE RETENTION_TRAJECTORY_REPLAY_HEADER_MODE)"
  fi
  exp9_retention_trajectory_distractor_start_task_index="$(resolve_value EXP9_RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX)"
  exp9_retention_trajectory_allow_distractor_reuse="$(resolve_value EXP9_RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE)"
  exp9_retention_attribution_mode="$(resolve_value EXP9_RETENTION_ATTRIBUTION_MODE RETENTION_ATTRIBUTION_MODE)"
  exp9_retention_request_context_mode="$(resolve_value EXP9_RETENTION_REQUEST_CONTEXT_MODE RETENTION_REQUEST_CONTEXT_MODE)"
  exp9_retention_top_level_priority_mode="$(resolve_value EXP9_RETENTION_TOP_LEVEL_PRIORITY_MODE RETENTION_TOP_LEVEL_PRIORITY_MODE)"
  exp9_stop_on_probe_failure="$(resolve_value EXP9_STOP_ON_PROBE_FAILURE STOP_ON_PROBE_FAILURE)"
  exp9_distractor_counts="$(resolve_value EXP9_DISTRACTOR_COUNTS DISTRACTOR_COUNTS)"
  exp9_protected_input_len="$(resolve_value EXP9_PROTECTED_INPUT_LEN PROTECTED_INPUT_LEN)"
  exp9_distractor_input_len="$(resolve_value EXP9_DISTRACTOR_INPUT_LEN DISTRACTOR_INPUT_LEN)"
  exp9_protected_hint_profiles="$(resolve_value EXP9_PROTECTED_HINT_PROFILES PROTECTED_HINT_PROFILES)"
  exp9_experiment_reset_mode="$(case_experiment_reset_mode)"
  exp9_kv_retention_reset_mode="$(case_kv_retention_reset_mode)"
  log
  prepare_fresh_runtime_for_experiment
  suite_run_start_banner "${index}" "${total}" "9" "kv_retention" "${display_mode}"
  cat <<EOF | tee -a "${SUITE_DRIVER_LOG}"
--- Experiment 9 parameters ---
wrapper=${wrapper}
mode=${display_mode}
request_source=${exp9_retention_request_source}
swebench_dataset=${exp9_retention_swebench_dataset}
swebench_split=${exp9_retention_swebench_split}
swebench_index=${exp9_retention_swebench_index}
swebench_instance_id=${exp9_retention_swebench_instance_id}
swebench_distractor_start_index=${exp9_retention_swebench_distractor_start_index}
swebench_allow_distractor_reuse=${exp9_retention_swebench_allow_distractor_reuse}
trajectory_prompt_catalog=${exp9_retention_trajectory_prompt_catalog}
trajectory_protected_task_index=${exp9_retention_trajectory_protected_task_index}
trajectory_protected_instance_id=${exp9_retention_trajectory_protected_instance_id}
trajectory_protected_stage=${exp9_retention_trajectory_protected_stage}
trajectory_stages=${exp9_retention_trajectory_stages}
trajectory_prompt_prefix_mode=${exp9_retention_trajectory_prompt_prefix_mode}
trajectory_distractor_start_task_index=${exp9_retention_trajectory_distractor_start_task_index}
trajectory_allow_distractor_reuse=${exp9_retention_trajectory_allow_distractor_reuse}
retention_attribution_mode=${exp9_retention_attribution_mode}
retention_request_context_mode=${exp9_retention_request_context_mode}
retention_top_level_priority_mode=${exp9_retention_top_level_priority_mode}
retention_reset_mode=${exp9_kv_retention_reset_mode}
retention_sweep_seed_mode=${EFFECTIVE_RETENTION_SWEEP_SEED_MODE}
retention_prompt_isolation_mode=${RETENTION_PROMPT_ISOLATION_MODE}
precise_start_mode=${PRECISE_START_MODE:-clean}
sglang_transfer_log=${SGLANG_TRANSFER_LOG}
sglang_transfer_log_profile=${SGLANG_TRANSFER_LOG_PROFILE}
stop_on_probe_failure=${exp9_stop_on_probe_failure}
distractor_counts=${exp9_distractor_counts}
protected_input_len=${exp9_protected_input_len}
distractor_input_len=${exp9_distractor_input_len}
protected_hint_profiles=${exp9_protected_hint_profiles}
EOF
  local -a env_args=(
    env
    DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}"
    EXPERIMENT_DIRS_READY_ALREADY="${EXPERIMENT_DIRS_READY_ALREADY:-0}"
    INTERACTIVE_BUILD_PROGRESS="${SUITE_INTERACTIVE_BUILD_PROGRESS}"
    PRECISE_START_MODE="${PRECISE_START_MODE:-clean}"
    SGLANG_TRANSFER_LOG="${SGLANG_TRANSFER_LOG:-1}"
    SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-full}"
    EXPERIMENT_RESET_MODE="${exp9_experiment_reset_mode}"
    KV_RETENTION_RESET_MODE="${exp9_kv_retention_reset_mode}"
    RETENTION_SWEEP_SEED_MODE="${EFFECTIVE_RETENTION_SWEEP_SEED_MODE}"
    RETENTION_PROMPT_ISOLATION_MODE="${RETENTION_PROMPT_ISOLATION_MODE}"
    STOP_DYNAMO_WHEN_DONE="${WRAPPER_STOP_DYNAMO_WHEN_DONE}"
    KV_RETENTION_MODE="${mode}"
  )
  [[ -n "${exp9_retention_attribution_mode}" ]] && env_args+=(RETENTION_ATTRIBUTION_MODE="${exp9_retention_attribution_mode}")
  [[ -n "${exp9_retention_request_source}" ]] && env_args+=(RETENTION_REQUEST_SOURCE="${exp9_retention_request_source}")
  [[ -n "${exp9_retention_swebench_dataset}" ]] && env_args+=(RETENTION_SWEBENCH_DATASET="${exp9_retention_swebench_dataset}")
  [[ -n "${exp9_retention_swebench_split}" ]] && env_args+=(RETENTION_SWEBENCH_SPLIT="${exp9_retention_swebench_split}")
  [[ -n "${exp9_retention_swebench_index}" ]] && env_args+=(RETENTION_SWEBENCH_INDEX="${exp9_retention_swebench_index}")
  [[ -n "${exp9_retention_swebench_instance_id}" ]] && env_args+=(RETENTION_SWEBENCH_INSTANCE_ID="${exp9_retention_swebench_instance_id}")
  [[ -n "${exp9_retention_swebench_distractor_start_index}" ]] && env_args+=(RETENTION_SWEBENCH_DISTRACTOR_START_INDEX="${exp9_retention_swebench_distractor_start_index}")
  [[ -n "${exp9_retention_swebench_allow_distractor_reuse}" ]] && env_args+=(RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE="${exp9_retention_swebench_allow_distractor_reuse}")
  [[ -n "${exp9_retention_trajectory_prompt_catalog}" ]] && env_args+=(RETENTION_TRAJECTORY_PROMPT_CATALOG="${exp9_retention_trajectory_prompt_catalog}")
  [[ -n "${exp9_retention_trajectory_protected_task_index}" ]] && env_args+=(RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX="${exp9_retention_trajectory_protected_task_index}")
  [[ -n "${exp9_retention_trajectory_protected_instance_id}" ]] && env_args+=(RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID="${exp9_retention_trajectory_protected_instance_id}")
  [[ -n "${exp9_retention_trajectory_protected_stage}" ]] && env_args+=(RETENTION_TRAJECTORY_PROTECTED_STAGE="${exp9_retention_trajectory_protected_stage}")
  [[ -n "${exp9_retention_trajectory_stages}" ]] && env_args+=(RETENTION_TRAJECTORY_STAGES="${exp9_retention_trajectory_stages}")
  [[ -n "${exp9_retention_trajectory_prompt_prefix_mode}" ]] && env_args+=(RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE="${exp9_retention_trajectory_prompt_prefix_mode}")
  [[ -n "${exp9_retention_trajectory_distractor_start_task_index}" ]] && env_args+=(RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX="${exp9_retention_trajectory_distractor_start_task_index}")
  [[ -n "${exp9_retention_trajectory_allow_distractor_reuse}" ]] && env_args+=(RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE="${exp9_retention_trajectory_allow_distractor_reuse}")
  [[ -n "${exp9_retention_request_context_mode}" ]] && env_args+=(RETENTION_REQUEST_CONTEXT_MODE="${exp9_retention_request_context_mode}")
  [[ -n "${exp9_retention_top_level_priority_mode}" ]] && env_args+=(RETENTION_TOP_LEVEL_PRIORITY_MODE="${exp9_retention_top_level_priority_mode}")
  [[ -n "${exp9_stop_on_probe_failure}" ]] && env_args+=(STOP_ON_PROBE_FAILURE="${exp9_stop_on_probe_failure}")
  [[ -n "${exp9_distractor_counts}" ]] && env_args+=(DISTRACTOR_COUNTS="${exp9_distractor_counts}")
  [[ -n "${exp9_protected_input_len}" ]] && env_args+=(PROTECTED_INPUT_LEN="${exp9_protected_input_len}")
  [[ -n "${exp9_distractor_input_len}" ]] && env_args+=(DISTRACTOR_INPUT_LEN="${exp9_distractor_input_len}")
  [[ -n "${exp9_protected_hint_profiles}" ]] && env_args+=(PROTECTED_HINT_PROFILES="${exp9_protected_hint_profiles}")
  if ! run_and_log "${env_args[@]}" "${wrapper}" "${MODEL}"; then
    status="failed"
    error_message="Experiment 9 wrapper failed"
  fi
  if [[ "${status}" = "passed" ]]; then
    sync_shared_assets_for_experiment "9"
  fi
  stop_dynamo_if_requested
  suite_run_end_banner "${index}" "${total}" "9" "kv_retention" "${status}"
  append_result_json \
    "9" "kv_retention" "${status}" "${mode}" "${wrapper}" \
    "experiments/reports/latest_kv_retention_microbenchmark_matrix.csv" \
    "" \
    "experiments/reports/latest_kv_retention_microbenchmark_summary.md" \
    "experiments/reports/latest_kv_retention_microbenchmark_run_contract.json" \
    "" \
    "experiments/reports/latest_kv_retention_microbenchmark_replay_latency.svg|experiments/reports/latest_kv_retention_microbenchmark_replay_cached_tokens.svg" \
    "${error_message}" "${started_at}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  [[ "${status}" = "passed" || "${SUITE_CONTINUE_ON_ERROR}" = "1" ]]
}

run_experiment_10() {
  local index="$1"
  local total="$2"
  local mode="${EXP10_MODE:-${CACHE_PINNING_MODE:-${SUITE_DEFAULT_MODE}}}"
  local display_mode
  display_mode="$(resolved_mode_display "10" "${mode}")"
  local wrapper="./agentbench/run_cache_pinning_microbenchmark_single_host.sh"
  local started_at
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local status="passed"
  local error_message=""
  local exp10_distractor_counts
  local exp10_protected_input_len
  local exp10_distractor_input_len
  local exp10_cache_pinning_ttl
  local exp10_cache_pinning_pinned_ratio
  local exp10_cache_pinning_hicache_ratio
  exp10_distractor_counts="$(resolve_value EXP10_DISTRACTOR_COUNTS DISTRACTOR_COUNTS)"
  exp10_protected_input_len="$(resolve_value EXP10_PROTECTED_INPUT_LEN PROTECTED_INPUT_LEN)"
  exp10_distractor_input_len="$(resolve_value EXP10_DISTRACTOR_INPUT_LEN DISTRACTOR_INPUT_LEN)"
  exp10_cache_pinning_ttl="$(resolve_value EXP10_CACHE_PINNING_TTL CACHE_PINNING_TTL)"
  exp10_cache_pinning_pinned_ratio="$(resolve_value EXP10_CACHE_PINNING_PINNED_RATIO CACHE_PINNING_PINNED_RATIO)"
  exp10_cache_pinning_hicache_ratio="$(resolve_value EXP10_CACHE_PINNING_HICACHE_RATIO CACHE_PINNING_HICACHE_RATIO)"
  log
  prepare_fresh_runtime_for_experiment
  suite_run_start_banner "${index}" "${total}" "10" "cache_pinning" "${display_mode}"
  cat <<EOF | tee -a "${SUITE_DRIVER_LOG}"
--- Experiment 10 parameters ---
wrapper=${wrapper}
mode=${display_mode}
experiment_reset_mode=${EFFECTIVE_EXPERIMENT_RESET_MODE}
retention_sweep_seed_mode=${EFFECTIVE_CACHE_PINNING_SWEEP_SEED_MODE}
retention_prompt_isolation_mode=${RETENTION_PROMPT_ISOLATION_MODE}
precise_start_mode=${PRECISE_START_MODE:-clean}
sglang_transfer_log=${SGLANG_TRANSFER_LOG}
sglang_transfer_log_profile=${SGLANG_TRANSFER_LOG_PROFILE}
distractor_counts=${exp10_distractor_counts}
protected_input_len=${exp10_protected_input_len}
distractor_input_len=${exp10_distractor_input_len}
cache_pinning_ttl=${exp10_cache_pinning_ttl}
cache_pinning_pinned_ratio=${exp10_cache_pinning_pinned_ratio}
cache_pinning_hicache_ratio=${exp10_cache_pinning_hicache_ratio}
EOF
  local -a env_args=(
    env
    DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}"
    EXPERIMENT_DIRS_READY_ALREADY="${EXPERIMENT_DIRS_READY_ALREADY:-0}"
    INTERACTIVE_BUILD_PROGRESS="${SUITE_INTERACTIVE_BUILD_PROGRESS}"
    PRECISE_START_MODE="${PRECISE_START_MODE:-clean}"
    SGLANG_TRANSFER_LOG="${SGLANG_TRANSFER_LOG:-1}"
    SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-full}"
    EXPERIMENT_RESET_MODE="${EFFECTIVE_EXPERIMENT_RESET_MODE}"
    RETENTION_SWEEP_SEED_MODE="${EFFECTIVE_CACHE_PINNING_SWEEP_SEED_MODE}"
    RETENTION_PROMPT_ISOLATION_MODE="${RETENTION_PROMPT_ISOLATION_MODE}"
    STOP_DYNAMO_WHEN_DONE="${WRAPPER_STOP_DYNAMO_WHEN_DONE}"
    CACHE_PINNING_MODE="${mode}"
  )
  [[ -n "${exp10_distractor_counts}" ]] && env_args+=(DISTRACTOR_COUNTS="${exp10_distractor_counts}")
  [[ -n "${exp10_protected_input_len}" ]] && env_args+=(PROTECTED_INPUT_LEN="${exp10_protected_input_len}")
  [[ -n "${exp10_distractor_input_len}" ]] && env_args+=(DISTRACTOR_INPUT_LEN="${exp10_distractor_input_len}")
  [[ -n "${exp10_cache_pinning_ttl}" ]] && env_args+=(CACHE_PINNING_TTL="${exp10_cache_pinning_ttl}")
  [[ -n "${exp10_cache_pinning_pinned_ratio}" ]] && env_args+=(CACHE_PINNING_PINNED_RATIO="${exp10_cache_pinning_pinned_ratio}")
  [[ -n "${exp10_cache_pinning_hicache_ratio}" ]] && env_args+=(CACHE_PINNING_HICACHE_RATIO="${exp10_cache_pinning_hicache_ratio}")
  if ! run_and_log "${env_args[@]}" "${wrapper}" "${MODEL}"; then
    status="failed"
    error_message="Experiment 10 wrapper failed"
  fi
  if [[ "${status}" = "passed" ]]; then
    sync_shared_assets_for_experiment "10"
  fi
  stop_dynamo_if_requested
  suite_run_end_banner "${index}" "${total}" "10" "cache_pinning" "${status}"
  append_result_json \
    "10" "cache_pinning" "${status}" "${mode}" "${wrapper}" \
    "experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv" \
    "experiments/reports/latest_cache_pinning_microbenchmark_summary.csv" \
    "experiments/reports/latest_cache_pinning_microbenchmark_summary.md" \
    "experiments/reports/latest_cache_pinning_microbenchmark_run_contract.json" \
    "experiments/reports/latest_cache_pinning_microbenchmark_chart_manifest.json" \
    "experiments/reports/latest_cache_pinning_microbenchmark_validation_latency.svg|experiments/reports/latest_cache_pinning_microbenchmark_validation_cached_tokens.svg|experiments/reports/latest_cache_pinning_microbenchmark_sweep_replay_latency.svg|experiments/reports/latest_cache_pinning_microbenchmark_sweep_replay_cached_tokens.svg" \
    "${error_message}" "${started_at}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  [[ "${status}" = "passed" || "${SUITE_CONTINUE_ON_ERROR}" = "1" ]]
}

run_experiment_11() {
  local index="$1"
  local total="$2"
  local mode="${EXP11_MODE:-${PRIORITY_SCHEDULING_MODE:-${SUITE_DEFAULT_MODE}}}"
  local display_mode
  display_mode="$(resolved_mode_display "11" "${mode}")"
  local wrapper="./agentbench/run_priority_scheduling_microbenchmark_single_host.sh"
  local started_at
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local status="passed"
  local error_message=""
  local exp11_sweep_axis
  local exp11_sweep_values
  local exp11_low_priority_count
  local exp11_high_priority_count
  local exp11_priority_input_len
  local exp11_priority_output_len
  local exp11_priority_inter_request_gap_ms
  local exp11_request_source
  local exp11_swebench_dataset
  local exp11_swebench_split
  local exp11_swebench_start_index
  local exp11_swebench_allow_reuse
  local exp11_experiment_reset_mode
  exp11_sweep_axis="$(resolve_value EXP11_PRIORITY_SCHEDULING_SWEEP_AXIS PRIORITY_SCHEDULING_SWEEP_AXIS)"
  exp11_sweep_values="$(resolve_value EXP11_PRIORITY_SCHEDULING_SWEEP_VALUES PRIORITY_SCHEDULING_SWEEP_VALUES)"
  exp11_low_priority_count="$(resolve_value EXP11_LOW_PRIORITY_COUNT LOW_PRIORITY_COUNT)"
  exp11_high_priority_count="$(resolve_value EXP11_HIGH_PRIORITY_COUNT HIGH_PRIORITY_COUNT)"
  exp11_priority_input_len="$(resolve_value EXP11_PRIORITY_INPUT_LEN PRIORITY_INPUT_LEN)"
  exp11_priority_output_len="$(resolve_value EXP11_PRIORITY_OUTPUT_LEN PRIORITY_OUTPUT_LEN)"
  exp11_priority_inter_request_gap_ms="$(resolve_value EXP11_PRIORITY_INTER_REQUEST_GAP_MS PRIORITY_INTER_REQUEST_GAP_MS)"
  exp11_request_source="$(resolve_value EXP11_PRIORITY_REQUEST_SOURCE PRIORITY_REQUEST_SOURCE)"
  exp11_swebench_dataset="$(resolve_value EXP11_PRIORITY_SWEBENCH_DATASET PRIORITY_SWEBENCH_DATASET)"
  exp11_swebench_split="$(resolve_value EXP11_PRIORITY_SWEBENCH_SPLIT PRIORITY_SWEBENCH_SPLIT)"
  exp11_swebench_start_index="$(resolve_value EXP11_PRIORITY_SWEBENCH_START_INDEX PRIORITY_SWEBENCH_START_INDEX)"
  exp11_swebench_allow_reuse="$(resolve_value EXP11_PRIORITY_SWEBENCH_ALLOW_REUSE PRIORITY_SWEBENCH_ALLOW_REUSE)"
  exp11_experiment_reset_mode="$(case_experiment_reset_mode)"
  log
  prepare_fresh_runtime_for_experiment
  suite_run_start_banner "${index}" "${total}" "11" "priority_scheduling" "${display_mode}"
  cat <<EOF | tee -a "${SUITE_DRIVER_LOG}"
--- Experiment 11 parameters ---
wrapper=${wrapper}
mode=${display_mode}
experiment_reset_mode=${exp11_experiment_reset_mode}
priority_scheduling_sweep_seed_mode=${EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE}
retention_prompt_isolation_mode=${RETENTION_PROMPT_ISOLATION_MODE}
precise_start_mode=${PRECISE_START_MODE:-clean}
sglang_transfer_log=${SGLANG_TRANSFER_LOG}
sglang_transfer_log_profile=${SGLANG_TRANSFER_LOG_PROFILE}
priority_scheduling_sweep_axis=${exp11_sweep_axis}
priority_scheduling_sweep_values=${exp11_sweep_values}
low_priority_count=${exp11_low_priority_count}
high_priority_count=${exp11_high_priority_count}
priority_input_len=${exp11_priority_input_len}
priority_output_len=${exp11_priority_output_len}
priority_inter_request_gap_ms=${exp11_priority_inter_request_gap_ms}
priority_request_source=${exp11_request_source}
priority_swebench_dataset=${exp11_swebench_dataset}
priority_swebench_split=${exp11_swebench_split}
priority_swebench_start_index=${exp11_swebench_start_index}
priority_swebench_allow_reuse=${exp11_swebench_allow_reuse}
EOF
  local -a env_args=(
    env
    DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}"
    EXPERIMENT_DIRS_READY_ALREADY="${EXPERIMENT_DIRS_READY_ALREADY:-0}"
    INTERACTIVE_BUILD_PROGRESS="${SUITE_INTERACTIVE_BUILD_PROGRESS}"
    PRECISE_START_MODE="${PRECISE_START_MODE:-clean}"
    SGLANG_TRANSFER_LOG="${SGLANG_TRANSFER_LOG:-1}"
    SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-full}"
    EXPERIMENT_RESET_MODE="${exp11_experiment_reset_mode}"
    RETENTION_PROMPT_ISOLATION_MODE="${RETENTION_PROMPT_ISOLATION_MODE}"
    PRIORITY_SCHEDULING_SWEEP_SEED_MODE="${EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE}"
    STOP_DYNAMO_WHEN_DONE="${WRAPPER_STOP_DYNAMO_WHEN_DONE}"
    PRIORITY_SCHEDULING_MODE="${mode}"
  )
  [[ -n "${exp11_sweep_axis}" ]] && env_args+=(PRIORITY_SCHEDULING_SWEEP_AXIS="${exp11_sweep_axis}")
  [[ -n "${exp11_sweep_values}" ]] && env_args+=(PRIORITY_SCHEDULING_SWEEP_VALUES="${exp11_sweep_values}")
  [[ -n "${exp11_low_priority_count}" ]] && env_args+=(LOW_PRIORITY_COUNT="${exp11_low_priority_count}")
  [[ -n "${exp11_high_priority_count}" ]] && env_args+=(HIGH_PRIORITY_COUNT="${exp11_high_priority_count}")
  [[ -n "${exp11_priority_input_len}" ]] && env_args+=(PRIORITY_INPUT_LEN="${exp11_priority_input_len}")
  [[ -n "${exp11_priority_output_len}" ]] && env_args+=(PRIORITY_OUTPUT_LEN="${exp11_priority_output_len}")
  [[ -n "${exp11_priority_inter_request_gap_ms}" ]] && env_args+=(PRIORITY_INTER_REQUEST_GAP_MS="${exp11_priority_inter_request_gap_ms}")
  [[ -n "${exp11_request_source}" ]] && env_args+=(PRIORITY_REQUEST_SOURCE="${exp11_request_source}")
  [[ -n "${exp11_swebench_dataset}" ]] && env_args+=(PRIORITY_SWEBENCH_DATASET="${exp11_swebench_dataset}")
  [[ -n "${exp11_swebench_split}" ]] && env_args+=(PRIORITY_SWEBENCH_SPLIT="${exp11_swebench_split}")
  [[ -n "${exp11_swebench_start_index}" ]] && env_args+=(PRIORITY_SWEBENCH_START_INDEX="${exp11_swebench_start_index}")
  [[ -n "${exp11_swebench_allow_reuse}" ]] && env_args+=(PRIORITY_SWEBENCH_ALLOW_REUSE="${exp11_swebench_allow_reuse}")
  if ! run_and_log "${env_args[@]}" "${wrapper}" "${MODEL}"; then
    status="failed"
    error_message="Experiment 11 wrapper failed"
  fi
  if [[ "${status}" = "passed" ]]; then
    sync_shared_assets_for_experiment "11"
  fi
  stop_dynamo_if_requested
  suite_run_end_banner "${index}" "${total}" "11" "priority_scheduling" "${status}"
  append_result_json \
    "11" "priority_scheduling" "${status}" "${mode}" "${wrapper}" \
    "experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv" \
    "" \
    "experiments/reports/latest_priority_scheduling_microbenchmark_summary.md" \
    "experiments/reports/latest_priority_scheduling_microbenchmark_run_contract.json" \
    "" \
    "experiments/reports/latest_priority_scheduling_microbenchmark_jump_ahead.svg" \
    "${error_message}" "${started_at}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  [[ "${status}" = "passed" || "${SUITE_CONTINUE_ON_ERROR}" = "1" ]]
}

run_experiment_12() {
  local index="$1"
  local total="$2"
  local mode="${EXP12_MODE:-${SPEC_PREFILL_MODE:-${SUITE_DEFAULT_MODE}}}"
  local display_mode
  display_mode="$(resolved_mode_display "12" "${mode}")"
  local wrapper="./agentbench/run_speculative_prefill_microbenchmark_single_host.sh"
  local started_at
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local status="passed"
  local error_message=""
  local exp12_sweep_axis
  local exp12_sweep_values
  local exp12_turn_a_words
  local exp12_turn_b_words
  local exp12_output_tokens
  local exp12_attribution_mode
  local exp12_request_context_mode
  local exp12_request_source
  local exp12_swebench_dataset
  local exp12_swebench_split
  local exp12_turn_a_index
  local exp12_turn_b_index
  local exp12_swebench_protected_offset
  local exp12_comparison_mode
  local exp12_experiment_reset_mode
  exp12_sweep_axis="$(resolve_value EXP12_SPEC_PREFILL_SWEEP_AXIS SPEC_PREFILL_SWEEP_AXIS)"
  exp12_sweep_values="$(resolve_value EXP12_SPEC_PREFILL_SWEEP_VALUES SPEC_PREFILL_SWEEP_VALUES)"
  exp12_turn_a_words="$(resolve_value EXP12_SPEC_PREFILL_TURN_A_WORDS SPEC_PREFILL_TURN_A_WORDS)"
  exp12_turn_b_words="$(resolve_value EXP12_SPEC_PREFILL_TURN_B_WORDS SPEC_PREFILL_TURN_B_WORDS)"
  exp12_output_tokens="$(resolve_value EXP12_SPEC_PREFILL_OUTPUT_TOKENS SPEC_PREFILL_OUTPUT_TOKENS)"
  exp12_attribution_mode="$(resolve_value EXP12_SPEC_PREFILL_ATTRIBUTION_MODE SPEC_PREFILL_ATTRIBUTION_MODE)"
  exp12_request_context_mode="$(resolve_value EXP12_SPEC_PREFILL_REQUEST_CONTEXT_MODE SPEC_PREFILL_REQUEST_CONTEXT_MODE)"
  exp12_request_source="$(resolve_value EXP12_SPEC_PREFILL_REQUEST_SOURCE SPEC_PREFILL_REQUEST_SOURCE)"
  exp12_swebench_dataset="$(resolve_value EXP12_SPEC_PREFILL_SWEBENCH_DATASET SPEC_PREFILL_SWEBENCH_DATASET)"
  exp12_swebench_split="$(resolve_value EXP12_SPEC_PREFILL_SWEBENCH_SPLIT SPEC_PREFILL_SWEBENCH_SPLIT)"
  exp12_turn_a_index="$(resolve_value EXP12_SPEC_PREFILL_TURN_A_INDEX SPEC_PREFILL_TURN_A_INDEX)"
  exp12_turn_b_index="$(resolve_value EXP12_SPEC_PREFILL_TURN_B_INDEX SPEC_PREFILL_TURN_B_INDEX)"
  exp12_swebench_protected_offset="$(resolve_value EXP12_SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET)"
  exp12_comparison_mode="$(resolve_value EXP12_SPEC_PREFILL_COMPARISON_MODE SPEC_PREFILL_COMPARISON_MODE)"
  exp12_experiment_reset_mode="$(case_experiment_reset_mode)"
  log
  prepare_fresh_runtime_for_experiment
  suite_run_start_banner "${index}" "${total}" "12" "speculative_prefill" "${display_mode}"
  cat <<EOF | tee -a "${SUITE_DRIVER_LOG}"
--- Experiment 12 parameters ---
wrapper=${wrapper}
mode=${display_mode}
spec_prefill_attribution_mode=${exp12_attribution_mode}
spec_prefill_request_context_mode=${exp12_request_context_mode}
experiment_reset_mode=${exp12_experiment_reset_mode}
spec_prefill_prompt_isolation_mode=${SPEC_PREFILL_PROMPT_ISOLATION_MODE}
spec_prefill_sweep_seed_mode=${EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE}
precise_start_mode=${PRECISE_START_MODE:-clean}
sglang_transfer_log=${SGLANG_TRANSFER_LOG}
sglang_transfer_log_profile=${SGLANG_TRANSFER_LOG_PROFILE}
spec_prefill_sweep_axis=${exp12_sweep_axis}
spec_prefill_sweep_values=${exp12_sweep_values}
spec_prefill_turn_a_words=${exp12_turn_a_words}
spec_prefill_turn_b_words=${exp12_turn_b_words}
spec_prefill_output_tokens=${exp12_output_tokens}
spec_prefill_request_source=${exp12_request_source}
spec_prefill_swebench_dataset=${exp12_swebench_dataset}
spec_prefill_swebench_split=${exp12_swebench_split}
spec_prefill_turn_a_index=${exp12_turn_a_index}
spec_prefill_turn_b_index=${exp12_turn_b_index}
spec_prefill_swebench_protected_offset=${exp12_swebench_protected_offset}
spec_prefill_comparison_mode=${exp12_comparison_mode}
EOF
  local -a env_args=(
    env
    DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}"
    EXPERIMENT_DIRS_READY_ALREADY="${EXPERIMENT_DIRS_READY_ALREADY:-0}"
    INTERACTIVE_BUILD_PROGRESS="${SUITE_INTERACTIVE_BUILD_PROGRESS}"
    PRECISE_START_MODE="${PRECISE_START_MODE:-clean}"
    SGLANG_TRANSFER_LOG="${SGLANG_TRANSFER_LOG:-1}"
    SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-full}"
    EXPERIMENT_RESET_MODE="${exp12_experiment_reset_mode}"
    RETENTION_PROMPT_ISOLATION_MODE="${SPEC_PREFILL_PROMPT_ISOLATION_MODE}"
    SPEC_PREFILL_SWEEP_SEED_MODE="${EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE}"
    STOP_DYNAMO_WHEN_DONE="${WRAPPER_STOP_DYNAMO_WHEN_DONE}"
    SPEC_PREFILL_MODE="${mode}"
  )
  [[ -n "${exp12_attribution_mode}" ]] && env_args+=(SPEC_PREFILL_ATTRIBUTION_MODE="${exp12_attribution_mode}")
  [[ -n "${exp12_request_context_mode}" ]] && env_args+=(SPEC_PREFILL_REQUEST_CONTEXT_MODE="${exp12_request_context_mode}")
  [[ -n "${exp12_sweep_axis}" ]] && env_args+=(SPEC_PREFILL_SWEEP_AXIS="${exp12_sweep_axis}")
  [[ -n "${exp12_sweep_values}" ]] && env_args+=(SPEC_PREFILL_SWEEP_VALUES="${exp12_sweep_values}")
  [[ -n "${exp12_turn_a_words}" ]] && env_args+=(SPEC_PREFILL_TURN_A_WORDS="${exp12_turn_a_words}")
  [[ -n "${exp12_turn_b_words}" ]] && env_args+=(SPEC_PREFILL_TURN_B_WORDS="${exp12_turn_b_words}")
  [[ -n "${exp12_output_tokens}" ]] && env_args+=(SPEC_PREFILL_OUTPUT_TOKENS="${exp12_output_tokens}")
  [[ -n "${exp12_request_source}" ]] && env_args+=(SPEC_PREFILL_REQUEST_SOURCE="${exp12_request_source}")
  [[ -n "${exp12_swebench_dataset}" ]] && env_args+=(SPEC_PREFILL_SWEBENCH_DATASET="${exp12_swebench_dataset}")
  [[ -n "${exp12_swebench_split}" ]] && env_args+=(SPEC_PREFILL_SWEBENCH_SPLIT="${exp12_swebench_split}")
  [[ -n "${exp12_turn_a_index}" ]] && env_args+=(SPEC_PREFILL_TURN_A_INDEX="${exp12_turn_a_index}")
  [[ -n "${exp12_turn_b_index}" ]] && env_args+=(SPEC_PREFILL_TURN_B_INDEX="${exp12_turn_b_index}")
  [[ -n "${exp12_swebench_protected_offset}" ]] && env_args+=(SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET="${exp12_swebench_protected_offset}")
  [[ -n "${exp12_comparison_mode}" ]] && env_args+=(SPEC_PREFILL_COMPARISON_MODE="${exp12_comparison_mode}")
  if ! run_and_log "${env_args[@]}" "${wrapper}" "${MODEL}"; then
    status="failed"
    error_message="Experiment 12 wrapper failed"
  fi
  if [[ "${status}" = "passed" ]]; then
    sync_shared_assets_for_experiment "12"
  fi
  stop_dynamo_if_requested
  suite_run_end_banner "${index}" "${total}" "12" "speculative_prefill" "${status}"
  append_result_json \
    "12" "speculative_prefill" "${status}" "${mode}" "${wrapper}" \
    "experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv" \
    "" \
    "experiments/reports/latest_speculative_prefill_microbenchmark_summary.md" \
    "experiments/reports/latest_speculative_prefill_microbenchmark_run_contract.json" \
    "" \
    "experiments/reports/latest_speculative_prefill_microbenchmark_turnb_latency.svg" \
    "${error_message}" "${started_at}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  [[ "${status}" = "passed" || "${SUITE_CONTINUE_ON_ERROR}" = "1" ]]
}

run_experiment_13() {
  local index="$1"
  local total="$2"
  local mode="${EXP13_MODE:-${LATENCY_SENSITIVITY_MODE:-${SUITE_DEFAULT_MODE}}}"
  local display_mode
  display_mode="$(resolved_mode_display "13" "${mode}")"
  local wrapper="./agentbench/run_latency_sensitivity_microbenchmark_single_host.sh"
  local started_at
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local status="passed"
  local error_message=""
  local exp13_sweep_axis
  local exp13_sweep_values
  local exp13_low_priority_count
  local exp13_high_priority_count
  local exp13_priority_input_len
  local exp13_priority_output_len
  local exp13_priority_inter_request_gap_ms
  local exp13_request_source
  local exp13_swebench_dataset
  local exp13_swebench_split
  local exp13_swebench_start_index
  local exp13_swebench_allow_reuse
  local exp13_experiment_reset_mode
  exp13_sweep_axis="$(resolve_value EXP13_PRIORITY_SCHEDULING_SWEEP_AXIS PRIORITY_SCHEDULING_SWEEP_AXIS)"
  exp13_sweep_values="$(resolve_value EXP13_PRIORITY_SCHEDULING_SWEEP_VALUES PRIORITY_SCHEDULING_SWEEP_VALUES)"
  exp13_low_priority_count="$(resolve_value EXP13_LOW_PRIORITY_COUNT LOW_PRIORITY_COUNT)"
  exp13_high_priority_count="$(resolve_value EXP13_HIGH_PRIORITY_COUNT HIGH_PRIORITY_COUNT)"
  exp13_priority_input_len="$(resolve_value EXP13_PRIORITY_INPUT_LEN PRIORITY_INPUT_LEN)"
  exp13_priority_output_len="$(resolve_value EXP13_PRIORITY_OUTPUT_LEN PRIORITY_OUTPUT_LEN)"
  exp13_priority_inter_request_gap_ms="$(resolve_value EXP13_PRIORITY_INTER_REQUEST_GAP_MS PRIORITY_INTER_REQUEST_GAP_MS)"
  exp13_request_source="$(resolve_value EXP13_PRIORITY_REQUEST_SOURCE PRIORITY_REQUEST_SOURCE)"
  exp13_swebench_dataset="$(resolve_value EXP13_PRIORITY_SWEBENCH_DATASET PRIORITY_SWEBENCH_DATASET)"
  exp13_swebench_split="$(resolve_value EXP13_PRIORITY_SWEBENCH_SPLIT PRIORITY_SWEBENCH_SPLIT)"
  exp13_swebench_start_index="$(resolve_value EXP13_PRIORITY_SWEBENCH_START_INDEX PRIORITY_SWEBENCH_START_INDEX)"
  exp13_swebench_allow_reuse="$(resolve_value EXP13_PRIORITY_SWEBENCH_ALLOW_REUSE PRIORITY_SWEBENCH_ALLOW_REUSE)"
  exp13_experiment_reset_mode="$(case_experiment_reset_mode)"
  log
  prepare_fresh_runtime_for_experiment
  suite_run_start_banner "${index}" "${total}" "13" "latency_sensitivity" "${display_mode}"
  cat <<EOF | tee -a "${SUITE_DRIVER_LOG}"
--- Experiment 13 parameters ---
wrapper=${wrapper}
mode=${display_mode}
experiment_reset_mode=${exp13_experiment_reset_mode}
latency_sensitivity_sweep_seed_mode=${EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE}
retention_prompt_isolation_mode=${RETENTION_PROMPT_ISOLATION_MODE}
precise_start_mode=${PRECISE_START_MODE:-clean}
sglang_transfer_log=${SGLANG_TRANSFER_LOG}
sglang_transfer_log_profile=${SGLANG_TRANSFER_LOG_PROFILE}
latency_sensitivity_sweep_axis=${exp13_sweep_axis}
latency_sensitivity_sweep_values=${exp13_sweep_values}
low_priority_count=${exp13_low_priority_count}
high_priority_count=${exp13_high_priority_count}
priority_input_len=${exp13_priority_input_len}
priority_output_len=${exp13_priority_output_len}
priority_inter_request_gap_ms=${exp13_priority_inter_request_gap_ms}
priority_request_source=${exp13_request_source}
priority_swebench_dataset=${exp13_swebench_dataset}
priority_swebench_split=${exp13_swebench_split}
priority_swebench_start_index=${exp13_swebench_start_index}
priority_swebench_allow_reuse=${exp13_swebench_allow_reuse}
EOF
  local -a env_args=(
    env
    DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}"
    EXPERIMENT_DIRS_READY_ALREADY="${EXPERIMENT_DIRS_READY_ALREADY:-0}"
    INTERACTIVE_BUILD_PROGRESS="${SUITE_INTERACTIVE_BUILD_PROGRESS}"
    PRECISE_START_MODE="${PRECISE_START_MODE:-clean}"
    SGLANG_TRANSFER_LOG="${SGLANG_TRANSFER_LOG:-1}"
    SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-full}"
    EXPERIMENT_RESET_MODE="${exp13_experiment_reset_mode}"
    RETENTION_PROMPT_ISOLATION_MODE="${RETENTION_PROMPT_ISOLATION_MODE}"
    PRIORITY_SCHEDULING_SWEEP_SEED_MODE="${EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE}"
    STOP_DYNAMO_WHEN_DONE="${WRAPPER_STOP_DYNAMO_WHEN_DONE}"
    LATENCY_SENSITIVITY_MODE="${mode}"
  )
  [[ -n "${exp13_sweep_axis}" ]] && env_args+=(PRIORITY_SCHEDULING_SWEEP_AXIS="${exp13_sweep_axis}")
  [[ -n "${exp13_sweep_values}" ]] && env_args+=(PRIORITY_SCHEDULING_SWEEP_VALUES="${exp13_sweep_values}")
  [[ -n "${exp13_low_priority_count}" ]] && env_args+=(LOW_PRIORITY_COUNT="${exp13_low_priority_count}")
  [[ -n "${exp13_high_priority_count}" ]] && env_args+=(HIGH_PRIORITY_COUNT="${exp13_high_priority_count}")
  [[ -n "${exp13_priority_input_len}" ]] && env_args+=(PRIORITY_INPUT_LEN="${exp13_priority_input_len}")
  [[ -n "${exp13_priority_output_len}" ]] && env_args+=(PRIORITY_OUTPUT_LEN="${exp13_priority_output_len}")
  [[ -n "${exp13_priority_inter_request_gap_ms}" ]] && env_args+=(PRIORITY_INTER_REQUEST_GAP_MS="${exp13_priority_inter_request_gap_ms}")
  [[ -n "${exp13_request_source}" ]] && env_args+=(PRIORITY_REQUEST_SOURCE="${exp13_request_source}")
  [[ -n "${exp13_swebench_dataset}" ]] && env_args+=(PRIORITY_SWEBENCH_DATASET="${exp13_swebench_dataset}")
  [[ -n "${exp13_swebench_split}" ]] && env_args+=(PRIORITY_SWEBENCH_SPLIT="${exp13_swebench_split}")
  [[ -n "${exp13_swebench_start_index}" ]] && env_args+=(PRIORITY_SWEBENCH_START_INDEX="${exp13_swebench_start_index}")
  [[ -n "${exp13_swebench_allow_reuse}" ]] && env_args+=(PRIORITY_SWEBENCH_ALLOW_REUSE="${exp13_swebench_allow_reuse}")
  if ! run_and_log "${env_args[@]}" "${wrapper}" "${MODEL}"; then
    status="failed"
    error_message="Experiment 13 wrapper failed"
  fi
  if [[ "${status}" = "passed" ]]; then
    sync_shared_assets_for_experiment "13"
  fi
  stop_dynamo_if_requested
  suite_run_end_banner "${index}" "${total}" "13" "latency_sensitivity" "${status}"
  append_result_json \
    "13" "latency_sensitivity" "${status}" "${mode}" "${wrapper}" \
    "experiments/reports/latest_latency_sensitivity_microbenchmark_matrix.csv" \
    "" \
    "experiments/reports/latest_latency_sensitivity_microbenchmark_summary.md" \
    "experiments/reports/latest_latency_sensitivity_microbenchmark_run_contract.json" \
    "" \
    "experiments/reports/latest_latency_sensitivity_microbenchmark_jump_ahead.svg" \
    "${error_message}" "${started_at}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  [[ "${status}" = "passed" || "${SUITE_CONTINUE_ON_ERROR}" = "1" ]]
}

suite_case_banner() {
  local index="$1"
  local total="$2"
  local run_case="$3"
  cat <<EOF | tee -a "${SUITE_DRIVER_LOG}"

################################################################################
### SUITE RUN CASE ${index}/${total}: ${run_case}
################################################################################

EOF
}

configure_suite_case() {
  local run_case="$1"
  CASE_EXPERIMENT_RESET_MODE=""
  CASE_KV_RETENTION_RESET_MODE=""
  case "${run_case}" in
    exp9_synthetic)
      set_case_reset_modes "${EXP9_SYNTHETIC_RESET_MODE}" "${EXP9_SYNTHETIC_RESET_MODE}"
      EXP9_MODE="${EXP9_SYNTHETIC_MODE}"
      EXP9_RETENTION_REQUEST_SOURCE="${EXP9_SYNTHETIC_RETENTION_REQUEST_SOURCE}"
      EXP9_RETENTION_ATTRIBUTION_MODE="${EXP9_SYNTHETIC_RETENTION_ATTRIBUTION_MODE}"
      EXP9_RETENTION_REQUEST_CONTEXT_MODE="${EXP9_SYNTHETIC_RETENTION_REQUEST_CONTEXT_MODE}"
      EXP9_RETENTION_TOP_LEVEL_PRIORITY_MODE="${EXP9_SYNTHETIC_RETENTION_TOP_LEVEL_PRIORITY_MODE}"
      EXP9_STOP_ON_PROBE_FAILURE="${EXP9_SYNTHETIC_STOP_ON_PROBE_FAILURE}"
      EXP9_DISTRACTOR_COUNTS="${EXP9_SYNTHETIC_DISTRACTOR_COUNTS}"
      EXP9_PROTECTED_INPUT_LEN="${EXP9_SYNTHETIC_PROTECTED_INPUT_LEN}"
      EXP9_DISTRACTOR_INPUT_LEN="${EXP9_SYNTHETIC_DISTRACTOR_INPUT_LEN}"
      EXP9_PROTECTED_HINT_PROFILES="${EXP9_SYNTHETIC_PROTECTED_HINT_PROFILES}"
      EXP9_RETENTION_SWEBENCH_INSTANCE_ID=""
      EXP9_RETENTION_SWEBENCH_DISTRACTOR_START_INDEX=""
      EXP9_RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE=""
      ;;
    exp9_swebench)
      set_case_reset_modes "${EXP9_SWEBENCH_RESET_MODE}" "${EXP9_SWEBENCH_RESET_MODE}"
      EXP9_MODE="${EXP9_SWEBENCH_MODE}"
      EXP9_RETENTION_REQUEST_SOURCE="${EXP9_SWEBENCH_RETENTION_REQUEST_SOURCE}"
      EXP9_RETENTION_SWEBENCH_DATASET="${EXP9_SWEBENCH_RETENTION_SWEBENCH_DATASET}"
      EXP9_RETENTION_SWEBENCH_SPLIT="${EXP9_SWEBENCH_RETENTION_SWEBENCH_SPLIT}"
      EXP9_RETENTION_SWEBENCH_INDEX="${EXP9_SWEBENCH_RETENTION_SWEBENCH_INDEX}"
      EXP9_RETENTION_ATTRIBUTION_MODE=""
      EXP9_RETENTION_REQUEST_CONTEXT_MODE=""
      EXP9_RETENTION_TOP_LEVEL_PRIORITY_MODE=""
      EXP9_STOP_ON_PROBE_FAILURE=""
      EXP9_DISTRACTOR_COUNTS="${EXP9_SWEBENCH_DISTRACTOR_COUNTS}"
      EXP9_PROTECTED_INPUT_LEN=""
      EXP9_DISTRACTOR_INPUT_LEN=""
      EXP9_PROTECTED_HINT_PROFILES="${EXP9_SWEBENCH_PROTECTED_HINT_PROFILES}"
      EXP9_RETENTION_SWEBENCH_INSTANCE_ID=""
      EXP9_RETENTION_SWEBENCH_DISTRACTOR_START_INDEX=""
      EXP9_RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE=""
      ;;
    exp9_trajectory)
      set_case_reset_modes "${EXP9_TRAJECTORY_RESET_MODE}" "${EXP9_TRAJECTORY_RESET_MODE}"
      EXP9_MODE="${EXP9_TRAJECTORY_MODE}"
      EXP9_RETENTION_REQUEST_SOURCE="${EXP9_TRAJECTORY_RETENTION_REQUEST_SOURCE}"
      EXP9_RETENTION_SWEBENCH_DATASET=""
      EXP9_RETENTION_SWEBENCH_SPLIT=""
      EXP9_RETENTION_SWEBENCH_INDEX=""
      EXP9_RETENTION_ATTRIBUTION_MODE=""
      EXP9_RETENTION_REQUEST_CONTEXT_MODE=""
      EXP9_RETENTION_TOP_LEVEL_PRIORITY_MODE=""
      EXP9_STOP_ON_PROBE_FAILURE=""
      EXP9_DISTRACTOR_COUNTS="${EXP9_TRAJECTORY_DISTRACTOR_COUNTS}"
      EXP9_PROTECTED_INPUT_LEN=""
      EXP9_DISTRACTOR_INPUT_LEN=""
      EXP9_PROTECTED_HINT_PROFILES="${EXP9_TRAJECTORY_PROTECTED_HINT_PROFILES}"
      EXP9_RETENTION_SWEBENCH_INSTANCE_ID=""
      EXP9_RETENTION_SWEBENCH_DISTRACTOR_START_INDEX=""
      EXP9_RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE=""
      ;;
    exp11_synthetic)
      set_case_reset_modes "${EXP11_SYNTHETIC_RESET_MODE}"
      EXP11_MODE="${EXP11_SYNTHETIC_MODE}"
      EXP11_PRIORITY_REQUEST_SOURCE="${EXP11_SYNTHETIC_PRIORITY_REQUEST_SOURCE}"
      EXP11_PRIORITY_SCHEDULING_SWEEP_AXIS="${EXP11_SYNTHETIC_PRIORITY_SCHEDULING_SWEEP_AXIS}"
      EXP11_PRIORITY_SCHEDULING_SWEEP_VALUES="${EXP11_SYNTHETIC_PRIORITY_SCHEDULING_SWEEP_VALUES}"
      EXP11_LOW_PRIORITY_COUNT="${EXP11_SYNTHETIC_LOW_PRIORITY_COUNT}"
      EXP11_HIGH_PRIORITY_COUNT="${EXP11_SYNTHETIC_HIGH_PRIORITY_COUNT}"
      EXP11_PRIORITY_INPUT_LEN="${EXP11_SYNTHETIC_PRIORITY_INPUT_LEN}"
      EXP11_PRIORITY_OUTPUT_LEN="${EXP11_SYNTHETIC_PRIORITY_OUTPUT_LEN}"
      EXP11_PRIORITY_INTER_REQUEST_GAP_MS="${EXP11_SYNTHETIC_PRIORITY_INTER_REQUEST_GAP_MS}"
      EXP11_PRIORITY_SWEBENCH_DATASET=""
      EXP11_PRIORITY_SWEBENCH_SPLIT=""
      EXP11_PRIORITY_SWEBENCH_START_INDEX=""
      EXP11_PRIORITY_SWEBENCH_ALLOW_REUSE=""
      ;;
    exp11_swebench)
      set_case_reset_modes "${EXP11_SWEBENCH_RESET_MODE}"
      EXP11_MODE="${EXP11_SWEBENCH_MODE}"
      EXP11_PRIORITY_REQUEST_SOURCE="${EXP11_SWEBENCH_PRIORITY_REQUEST_SOURCE}"
      EXP11_PRIORITY_SWEBENCH_DATASET="${EXP11_SWEBENCH_PRIORITY_SWEBENCH_DATASET}"
      EXP11_PRIORITY_SWEBENCH_SPLIT="${EXP11_SWEBENCH_PRIORITY_SWEBENCH_SPLIT}"
      EXP11_PRIORITY_SWEBENCH_START_INDEX="${EXP11_SWEBENCH_PRIORITY_SWEBENCH_START_INDEX}"
      EXP11_PRIORITY_SCHEDULING_SWEEP_AXIS="${EXP11_SWEBENCH_PRIORITY_SCHEDULING_SWEEP_AXIS}"
      EXP11_PRIORITY_SCHEDULING_SWEEP_VALUES="${EXP11_SWEBENCH_PRIORITY_SCHEDULING_SWEEP_VALUES}"
      EXP11_LOW_PRIORITY_COUNT="${EXP11_SWEBENCH_LOW_PRIORITY_COUNT}"
      EXP11_HIGH_PRIORITY_COUNT="${EXP11_SWEBENCH_HIGH_PRIORITY_COUNT}"
      EXP11_PRIORITY_INPUT_LEN=""
      EXP11_PRIORITY_OUTPUT_LEN="${EXP11_SWEBENCH_PRIORITY_OUTPUT_LEN}"
      EXP11_PRIORITY_INTER_REQUEST_GAP_MS="${EXP11_SWEBENCH_PRIORITY_INTER_REQUEST_GAP_MS}"
      EXP11_PRIORITY_SWEBENCH_ALLOW_REUSE=""
      ;;
    exp12_synthetic)
      set_case_reset_modes "${EXP12_SYNTHETIC_RESET_MODE}"
      EXP12_MODE="${EXP12_SYNTHETIC_MODE}"
      EXP12_SPEC_PREFILL_REQUEST_SOURCE="${EXP12_SYNTHETIC_SPEC_PREFILL_REQUEST_SOURCE}"
      EXP12_SPEC_PREFILL_ATTRIBUTION_MODE="${EXP12_SYNTHETIC_SPEC_PREFILL_ATTRIBUTION_MODE}"
      EXP12_SPEC_PREFILL_REQUEST_CONTEXT_MODE="${EXP12_SYNTHETIC_SPEC_PREFILL_REQUEST_CONTEXT_MODE}"
      EXP12_SPEC_PREFILL_SWEEP_AXIS="${EXP12_SYNTHETIC_SPEC_PREFILL_SWEEP_AXIS}"
      EXP12_SPEC_PREFILL_SWEEP_VALUES="${EXP12_SYNTHETIC_SPEC_PREFILL_SWEEP_VALUES}"
      EXP12_SPEC_PREFILL_TURN_A_WORDS="${EXP12_SYNTHETIC_SPEC_PREFILL_TURN_A_WORDS}"
      EXP12_SPEC_PREFILL_TURN_B_WORDS="${EXP12_SYNTHETIC_SPEC_PREFILL_TURN_B_WORDS}"
      EXP12_SPEC_PREFILL_OUTPUT_TOKENS="${EXP12_SYNTHETIC_SPEC_PREFILL_OUTPUT_TOKENS}"
      EXP12_SPEC_PREFILL_SWEBENCH_DATASET=""
      EXP12_SPEC_PREFILL_SWEBENCH_SPLIT=""
      EXP12_SPEC_PREFILL_TURN_A_INDEX=""
      EXP12_SPEC_PREFILL_TURN_B_INDEX=""
      EXP12_SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET=""
      EXP12_SPEC_PREFILL_COMPARISON_MODE=""
      ;;
    exp12_swebench)
      set_case_reset_modes "${EXP12_SWEBENCH_RESET_MODE}"
      EXP12_MODE="${EXP12_SWEBENCH_MODE}"
      EXP12_SPEC_PREFILL_REQUEST_SOURCE="${EXP12_SWEBENCH_SPEC_PREFILL_REQUEST_SOURCE}"
      EXP12_SPEC_PREFILL_SWEBENCH_DATASET="${EXP12_SWEBENCH_SPEC_PREFILL_SWEBENCH_DATASET}"
      EXP12_SPEC_PREFILL_SWEBENCH_SPLIT="${EXP12_SWEBENCH_SPEC_PREFILL_SWEBENCH_SPLIT}"
      EXP12_SPEC_PREFILL_TURN_A_INDEX="${EXP12_SWEBENCH_SPEC_PREFILL_TURN_A_INDEX}"
      EXP12_SPEC_PREFILL_TURN_B_INDEX="${EXP12_SWEBENCH_SPEC_PREFILL_TURN_B_INDEX}"
      EXP12_SPEC_PREFILL_COMPARISON_MODE="${EXP12_SWEBENCH_SPEC_PREFILL_COMPARISON_MODE}"
      EXP12_SPEC_PREFILL_ATTRIBUTION_MODE=""
      EXP12_SPEC_PREFILL_REQUEST_CONTEXT_MODE=""
      EXP12_SPEC_PREFILL_SWEEP_AXIS="${EXP12_SWEBENCH_SPEC_PREFILL_SWEEP_AXIS}"
      EXP12_SPEC_PREFILL_SWEEP_VALUES="${EXP12_SWEBENCH_SPEC_PREFILL_SWEEP_VALUES}"
      EXP12_SPEC_PREFILL_TURN_A_WORDS=""
      EXP12_SPEC_PREFILL_TURN_B_WORDS=""
      EXP12_SPEC_PREFILL_OUTPUT_TOKENS="${EXP12_SWEBENCH_SPEC_PREFILL_OUTPUT_TOKENS}"
      EXP12_SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET=""
      ;;
    exp13_synthetic)
      set_case_reset_modes "${EXP13_SYNTHETIC_RESET_MODE}"
      EXP13_MODE="${EXP13_SYNTHETIC_MODE}"
      EXP13_PRIORITY_REQUEST_SOURCE="${EXP13_SYNTHETIC_PRIORITY_REQUEST_SOURCE}"
      EXP13_PRIORITY_SCHEDULING_SWEEP_AXIS="${EXP13_SYNTHETIC_PRIORITY_SCHEDULING_SWEEP_AXIS}"
      EXP13_PRIORITY_SCHEDULING_SWEEP_VALUES="${EXP13_SYNTHETIC_PRIORITY_SCHEDULING_SWEEP_VALUES}"
      EXP13_LOW_PRIORITY_COUNT="${EXP13_SYNTHETIC_LOW_PRIORITY_COUNT}"
      EXP13_HIGH_PRIORITY_COUNT="${EXP13_SYNTHETIC_HIGH_PRIORITY_COUNT}"
      EXP13_PRIORITY_INPUT_LEN="${EXP13_SYNTHETIC_PRIORITY_INPUT_LEN}"
      EXP13_PRIORITY_OUTPUT_LEN="${EXP13_SYNTHETIC_PRIORITY_OUTPUT_LEN}"
      EXP13_PRIORITY_INTER_REQUEST_GAP_MS="${EXP13_SYNTHETIC_PRIORITY_INTER_REQUEST_GAP_MS}"
      EXP13_PRIORITY_SWEBENCH_DATASET=""
      EXP13_PRIORITY_SWEBENCH_SPLIT=""
      EXP13_PRIORITY_SWEBENCH_START_INDEX=""
      EXP13_PRIORITY_SWEBENCH_ALLOW_REUSE=""
      ;;
    exp13_swebench)
      set_case_reset_modes "${EXP13_SWEBENCH_RESET_MODE}"
      EXP13_MODE="${EXP13_SWEBENCH_MODE}"
      EXP13_PRIORITY_REQUEST_SOURCE="${EXP13_SWEBENCH_PRIORITY_REQUEST_SOURCE}"
      EXP13_PRIORITY_SWEBENCH_DATASET="${EXP13_SWEBENCH_PRIORITY_SWEBENCH_DATASET}"
      EXP13_PRIORITY_SWEBENCH_SPLIT="${EXP13_SWEBENCH_PRIORITY_SWEBENCH_SPLIT}"
      EXP13_PRIORITY_SWEBENCH_START_INDEX="${EXP13_SWEBENCH_PRIORITY_SWEBENCH_START_INDEX}"
      EXP13_PRIORITY_SCHEDULING_SWEEP_AXIS="${EXP13_SWEBENCH_PRIORITY_SCHEDULING_SWEEP_AXIS}"
      EXP13_PRIORITY_SCHEDULING_SWEEP_VALUES="${EXP13_SWEBENCH_PRIORITY_SCHEDULING_SWEEP_VALUES}"
      EXP13_LOW_PRIORITY_COUNT="${EXP13_SWEBENCH_LOW_PRIORITY_COUNT}"
      EXP13_HIGH_PRIORITY_COUNT="${EXP13_SWEBENCH_HIGH_PRIORITY_COUNT}"
      EXP13_PRIORITY_INPUT_LEN=""
      EXP13_PRIORITY_OUTPUT_LEN="${EXP13_SWEBENCH_PRIORITY_OUTPUT_LEN}"
      EXP13_PRIORITY_INTER_REQUEST_GAP_MS="${EXP13_SWEBENCH_PRIORITY_INTER_REQUEST_GAP_MS}"
      EXP13_PRIORITY_SWEBENCH_ALLOW_REUSE=""
      ;;
    exp10)
      ;;
    *)
      return 1
      ;;
  esac
}

run_suite_case() {
  local run_case="$1"
  local index="$2"
  local total="$3"
  local exp
  exp="$(suite_run_experiment_id "${run_case}")" || return 1
  suite_case_banner "${index}" "${total}" "${run_case}"
  configure_suite_case "${run_case}" || return 1
  log "Resolved case reset mode: experiment_reset_mode=$(case_experiment_reset_mode) kv_retention_reset_mode=$(case_kv_retention_reset_mode)"
  case "${exp}" in
    9) run_experiment_9 "${index}" "${total}" ;;
    10) run_experiment_10 "${index}" "${total}" ;;
    11) run_experiment_11 "${index}" "${total}" ;;
    12) run_experiment_12 "${index}" "${total}" ;;
    13) run_experiment_13 "${index}" "${total}" ;;
    *) return 1 ;;
  esac
}

declare -a SUITE_RUN_SELECTION=()
build_suite_run_selection
SUITE_CHART_GROUP_RESOLVED="$(infer_suite_chart_group)"
cat >> "${SUITE_ENV_SNAPSHOT}" <<EOF
SUITE_CHART_GROUP_RESOLVED='${SUITE_CHART_GROUP_RESOLVED}'
SUITE_CHART_GROUP_DIR='experiments/charts/${SUITE_CHART_GROUP_RESOLVED}'
SUITE_CHART_ARCHIVE_DIR='experiments/charts/archive/${SUITE_ID}'
EOF

banner "AGENTIC HINT SWEEPS SUITE" | tee -a "${SUITE_DRIVER_LOG}"
log "Suite id: ${SUITE_ID}"
log "Suite config path: ${SUITE_CONFIG_PATH}"
log "Model: ${MODEL}"
log "Machine profile: ${DYNAMO_MACHINE_PROFILE:-default}"
log "Suite runs: ${SUITE_RUN_SELECTION[*]}"
log "Legacy experiments: ${SUITE_EXPERIMENTS:-<unset>}"
log "Suite isolation mode: ${SUITE_ISOLATION_MODE}"
log "Suite chart group: ${SUITE_CHART_GROUP_RESOLVED}"
log "Suite chart group dir: experiments/charts/${SUITE_CHART_GROUP_RESOLVED}"
log "Suite chart archive dir: experiments/charts/archive/${SUITE_ID}"
log "Continue on error: ${SUITE_CONTINUE_ON_ERROR}"
log "Stop Dynamo between experiments: ${EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS}"
log "Default mode: ${SUITE_DEFAULT_MODE}"
log "Interactive build progress: ${SUITE_INTERACTIVE_BUILD_PROGRESS}"
log "Suite ensure precise runtime: ${SUITE_ENSURE_PRECISE_RUNTIME}"
log "Retention prompt isolation mode: ${RETENTION_PROMPT_ISOLATION_MODE}"
log "Speculative-prefill prompt isolation mode: ${SPEC_PREFILL_PROMPT_ISOLATION_MODE}"
log "Default experiment reset mode: ${EFFECTIVE_EXPERIMENT_RESET_MODE}"
log "Wrapper stop Dynamo when done: ${WRAPPER_STOP_DYNAMO_WHEN_DONE}"
case "${SUITE_ISOLATION_MODE}" in
  per_case)
    log "Suite runtime policy: restart between experiments, use each selected case's known-good reset mode"
    log "Case reset policy: synthetic cases use flush; SWE-bench cases use restart"
    log "Sweep prompt policy: different prompts across sweep values where supported"
    ;;
  clean)
    log "Suite runtime policy: restart between experiments, restart between sweep values"
    log "Sweep prompt policy: fixed prompts across sweep values"
    ;;
  flush)
    log "Suite runtime policy: restart between experiments, flush between sweep values"
    log "Sweep prompt policy: different prompts across sweep values"
    ;;
  fast)
    log "Suite runtime policy: restart between experiments, no restart between sweep values"
    log "Sweep prompt policy: different prompts across sweep values"
    ;;
esac
log "Suite env snapshot: ${SUITE_ENV_SNAPSHOT}"
log "Driver log: ${SUITE_DRIVER_LOG}"

ensure_suite_experiment_dirs_ready
prune_suite_chart_group_dir
prune_shared_chart_dir_for_suite_selection
ensure_suite_precise_runtime_if_needed

suite_ok=1
selected_experiment_total=0
for run_case in "${SUITE_RUN_SELECTION[@]}"; do
  if [[ "${run_case}" != UNKNOWN:* ]]; then
    selected_experiment_total=$((selected_experiment_total + 1))
  fi
done
log "Resolved selected run count: ${selected_experiment_total}"

selected_experiment_index=0
for run_case in "${SUITE_RUN_SELECTION[@]}"; do
  if [[ "${run_case}" = UNKNOWN:* ]]; then
    log "Unknown suite run token: ${run_case#UNKNOWN:}"
    suite_ok=0
    if [[ "${SUITE_CONTINUE_ON_ERROR}" != "1" ]]; then
      break
    fi
    continue
  fi

  selected_experiment_index=$((selected_experiment_index + 1))
  run_suite_case "${run_case}" "${selected_experiment_index}" "${selected_experiment_total}" || suite_ok=0

  if [[ "${suite_ok}" != "1" && "${SUITE_CONTINUE_ON_ERROR}" != "1" ]]; then
    break
  fi
done

build_suite_outputs

prune_shared_chart_dir_for_suite_selection
sync_latest_matrices_to_shared_charts
mirror_selected_shared_charts_to_suite_dirs

banner "AGENTIC HINT SWEEPS SUITE READY" | tee -a "${SUITE_DRIVER_LOG}"
log "Suite run dir: ${SUITE_ROOT_DIR}"
log "Suite summary: ${SUITE_SUMMARY_MD}"
log "Suite manifest: ${SUITE_MANIFEST_JSON}"
log "Latest summary: ${LATEST_SUMMARY_MD}"
log "Latest manifest: ${LATEST_MANIFEST_JSON}"
log "Latest driver log: ${LATEST_DRIVER_LOG}"
log "Grouped charts: experiments/charts/${SUITE_CHART_GROUP_RESOLVED}"
log "Archived charts: experiments/charts/archive/${SUITE_ID}"

if [[ "${suite_ok}" != "1" ]]; then
  exit 1
fi
