#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh
if [[ -f runtime_instrumentation/dynamo_machine_profile.sh ]]; then
  # shellcheck disable=SC1091
  source runtime_instrumentation/dynamo_machine_profile.sh
fi

MODEL="${1:-${SUITE_MODEL:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}}"
SUITE_ID="${AGENTIC_HINT_SUITE_ID:-agentic_hint_sweeps_suite_$(date +%Y%m%d_%H%M%S)}"
SUITE_EXPERIMENTS="${SUITE_EXPERIMENTS:-9 10 11 12}"
SUITE_CONTINUE_ON_ERROR="${SUITE_CONTINUE_ON_ERROR:-0}"
SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS="${SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS:-1}"
SUITE_DEFAULT_MODE="${SUITE_DEFAULT_MODE:-sweep}"
SUITE_INTERACTIVE_BUILD_PROGRESS="${SUITE_INTERACTIVE_BUILD_PROGRESS:-1}"
SUITE_ENSURE_PRECISE_RUNTIME="${SUITE_ENSURE_PRECISE_RUNTIME:-auto}"
SUITE_ISOLATION_MODE="${SUITE_ISOLATION_MODE:-clean}"
EXPERIMENT_RESET_MODE="${EXPERIMENT_RESET_MODE:-flush}"

EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS="1"
EFFECTIVE_EXPERIMENT_RESET_MODE="restart"
EFFECTIVE_KV_RETENTION_RESET_MODE="restart"
EFFECTIVE_RETENTION_SWEEP_SEED_MODE="fixed"
EFFECTIVE_CACHE_PINNING_SWEEP_SEED_MODE="fixed"
EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE="fixed"
EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE="fixed"
WRAPPER_STOP_DYNAMO_WHEN_DONE="1"

SUITE_ROOT_DIR="experiments/reports/agentic_hint_sweeps_suite/${SUITE_ID}"
LATEST_PREFIX="experiments/reports/latest_agentic_hint_sweeps_suite"
SUITE_DRIVER_LOG="${SUITE_DRIVER_LOG:-${SUITE_ROOT_DIR}/suite_driver.log}"
SUITE_MANIFEST_JSON="${SUITE_ROOT_DIR}/suite_manifest.json"
SUITE_SUMMARY_MD="${SUITE_ROOT_DIR}/suite_summary.md"
SUITE_JSONL="${SUITE_ROOT_DIR}/suite_results.jsonl"
SUITE_ENV_SNAPSHOT="${SUITE_ROOT_DIR}/suite_env.sh"
SUITE_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

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

Environment:
  DYNAMO_MACHINE_PROFILE=ec2|gh200
  SUITE_EXPERIMENTS="9 10 11 12"        # or "retention cache_pinning priority spec_prefill"
  SUITE_ISOLATION_MODE=clean|fast       # clean=restarts sweep values, fast=reuses runtime within experiments without flush
  SUITE_CONTINUE_ON_ERROR=0|1
  SUITE_DEFAULT_MODE=sweep
  SUITE_INTERACTIVE_BUILD_PROGRESS=1    # keep live Docker progress UI for foreground runs
  SUITE_ENSURE_PRECISE_RUNTIME=auto|0|1 # auto => run once only for gh200

This suite calls the public wrappers for:
  9  = KV retention microbenchmark
  10 = Cache-pinning microbenchmark
  11 = Priority scheduling microbenchmark
  12 = Speculative prefill microbenchmark
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
  clean)
    EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS="1"
    EFFECTIVE_EXPERIMENT_RESET_MODE="restart"
    EFFECTIVE_KV_RETENTION_RESET_MODE="restart"
    EFFECTIVE_RETENTION_SWEEP_SEED_MODE="fixed"
    EFFECTIVE_CACHE_PINNING_SWEEP_SEED_MODE="fixed"
    EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE="fixed"
    EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE="fixed"
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
    echo "Valid values: clean fast" >&2
    exit 2
    ;;
esac

mkdir -p "${SUITE_ROOT_DIR}"
rm -f "${LATEST_SUMMARY_MD}" "${LATEST_MANIFEST_JSON}" "${LATEST_DRIVER_LOG}"
: > "${SUITE_DRIVER_LOG}"
: > "${SUITE_JSONL}"

cat > "${SUITE_ENV_SNAPSHOT}" <<EOF
AGENTIC_HINT_SUITE_ID='${SUITE_ID}'
DYNAMO_MACHINE_PROFILE='${DYNAMO_MACHINE_PROFILE:-}'
SUITE_MODEL='${MODEL}'
SUITE_EXPERIMENTS='${SUITE_EXPERIMENTS}'
SUITE_ISOLATION_MODE='${SUITE_ISOLATION_MODE}'
SUITE_CONTINUE_ON_ERROR='${SUITE_CONTINUE_ON_ERROR}'
SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS='${EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS}'
SUITE_DEFAULT_MODE='${SUITE_DEFAULT_MODE}'
SUITE_INTERACTIVE_BUILD_PROGRESS='${SUITE_INTERACTIVE_BUILD_PROGRESS}'
SUITE_ENSURE_PRECISE_RUNTIME='${SUITE_ENSURE_PRECISE_RUNTIME}'
EXPERIMENT_RESET_MODE='${EFFECTIVE_EXPERIMENT_RESET_MODE}'
WRAPPER_STOP_DYNAMO_WHEN_DONE='${WRAPPER_STOP_DYNAMO_WHEN_DONE}'
KV_RETENTION_MODE='${KV_RETENTION_MODE:-}'
KV_RETENTION_RESET_MODE='${EFFECTIVE_KV_RETENTION_RESET_MODE}'
RETENTION_SWEEP_SEED_MODE='${EFFECTIVE_RETENTION_SWEEP_SEED_MODE}'
KV_RETENTION_SWEEP_AXIS='${KV_RETENTION_SWEEP_AXIS:-}'
KV_RETENTION_SWEEP_VALUES='${KV_RETENTION_SWEEP_VALUES:-}'
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
SPEC_PREFILL_MODE='${SPEC_PREFILL_MODE:-}'
SPEC_PREFILL_SWEEP_SEED_MODE='${EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE}'
SPEC_PREFILL_SWEEP_AXIS='${SPEC_PREFILL_SWEEP_AXIS:-}'
SPEC_PREFILL_SWEEP_VALUES='${SPEC_PREFILL_SWEEP_VALUES:-}'
EOF

log() {
  echo "$@" | tee -a "${SUITE_DRIVER_LOG}"
}

run_and_log() {
  "$@" 2>&1 | tee -a "${SUITE_DRIVER_LOG}"
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
  [[ -f "experiments/reports/latest_kv_retention_microbenchmark_matrix.csv" ]] && cp -f "experiments/reports/latest_kv_retention_microbenchmark_matrix.csv" "${charts_dir}/exp9_kvretention_matrix.csv"
  [[ -f "experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv" ]] && cp -f "experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv" "${charts_dir}/exp10_cachepinning_matrix.csv"
  [[ -f "experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv" ]] && cp -f "experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv" "${charts_dir}/exp11_prioritysched_matrix.csv"
  [[ -f "experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv" ]] && cp -f "experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv" "${charts_dir}/exp12_specprefill_matrix.csv"
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
      sync_one "experiments/reports/latest_priority_scheduling_microbenchmark_queue_wait.svg" "${charts_dir}/exp11_prioritysched_queue_wait_vs_arrival_gap.svg"
      ;;
    12)
      sync_one "experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv" "${charts_dir}/exp12_specprefill_matrix.csv"
      sync_one "experiments/reports/latest_speculative_prefill_microbenchmark_turnb_latency.svg" "${charts_dir}/exp12_specprefill_latency_vs_warmup_wait.svg"
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
    9:all|11:all|12:all)
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
    *) return 1 ;;
  esac
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
    "${SUITE_EXPERIMENTS}" \
    "${SUITE_CONTINUE_ON_ERROR}" \
    "${SUITE_ENV_SNAPSHOT}" \
    "${SUITE_DRIVER_LOG}" \
    "${SUITE_STARTED_AT}" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
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
suite_experiments = sys.argv[7]
continue_on_error = sys.argv[8]
env_snapshot = sys.argv[9]
driver_log = sys.argv[10]
suite_started_at = sys.argv[11]
suite_finished_at = sys.argv[12]

results = []
if jsonl_path.exists():
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            results.append(json.loads(line))

manifest = {
    "suite_id": suite_id,
    "model": model,
    "machine_profile": machine_profile,
    "suite_experiments": suite_experiments,
    "continue_on_error": continue_on_error,
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "started_at_utc": suite_started_at,
    "finished_at_utc": suite_finished_at,
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
    f"- experiments: `{suite_experiments}`",
    f"- continue_on_error: `{continue_on_error}`",
    f"- started_at_utc: `{suite_started_at}`",
    f"- finished_at_utc: `{suite_finished_at}`",
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

run_experiment_9() {
  local index="$1"
  local total="$2"
  local mode="${KV_RETENTION_MODE:-${SUITE_DEFAULT_MODE}}"
  local display_mode
  display_mode="$(resolved_mode_display "9" "${mode}")"
  local wrapper="./agentbench/run_kv_retention_microbenchmark_single_host.sh"
  local started_at
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local status="passed"
  local error_message=""
  log
  prepare_fresh_runtime_for_experiment
  suite_run_start_banner "${index}" "${total}" "9" "kv_retention" "${display_mode}"
  log "Wrapper: ${wrapper}"
  log "Mode: ${display_mode}"
  log "KV retention reset mode: ${EFFECTIVE_KV_RETENTION_RESET_MODE}"
  if ! run_and_log env DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}" INTERACTIVE_BUILD_PROGRESS="${SUITE_INTERACTIVE_BUILD_PROGRESS}" EXPERIMENT_RESET_MODE="${EFFECTIVE_EXPERIMENT_RESET_MODE}" KV_RETENTION_RESET_MODE="${EFFECTIVE_KV_RETENTION_RESET_MODE}" RETENTION_SWEEP_SEED_MODE="${EFFECTIVE_RETENTION_SWEEP_SEED_MODE}" STOP_DYNAMO_WHEN_DONE="${WRAPPER_STOP_DYNAMO_WHEN_DONE}" KV_RETENTION_MODE="${mode}" "${wrapper}" "${MODEL}"; then
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
    "experiments/reports/latest_kv_retention_microbenchmark_summary.csv" \
    "experiments/reports/latest_kv_retention_microbenchmark_summary.md" \
    "experiments/reports/latest_kv_retention_microbenchmark_run_contract.json" \
    "experiments/reports/latest_kv_retention_microbenchmark_chart_manifest.json" \
    "experiments/reports/latest_kv_retention_microbenchmark_replay_latency.svg|experiments/reports/latest_kv_retention_microbenchmark_replay_cached_tokens.svg|experiments/reports/latest_kv_retention_microbenchmark_survival_curve.svg" \
    "${error_message}" "${started_at}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  [[ "${status}" = "passed" || "${SUITE_CONTINUE_ON_ERROR}" = "1" ]]
}

run_experiment_10() {
  local index="$1"
  local total="$2"
  local mode="${CACHE_PINNING_MODE:-${SUITE_DEFAULT_MODE}}"
  local display_mode
  display_mode="$(resolved_mode_display "10" "${mode}")"
  local wrapper="./agentbench/run_cache_pinning_microbenchmark_single_host.sh"
  local started_at
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local status="passed"
  local error_message=""
  log
  prepare_fresh_runtime_for_experiment
  suite_run_start_banner "${index}" "${total}" "10" "cache_pinning" "${display_mode}"
  log "Wrapper: ${wrapper}"
  log "Mode: ${display_mode}"
  if ! run_and_log env DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}" INTERACTIVE_BUILD_PROGRESS="${SUITE_INTERACTIVE_BUILD_PROGRESS}" EXPERIMENT_RESET_MODE="${EFFECTIVE_EXPERIMENT_RESET_MODE}" RETENTION_SWEEP_SEED_MODE="${EFFECTIVE_CACHE_PINNING_SWEEP_SEED_MODE}" STOP_DYNAMO_WHEN_DONE="${WRAPPER_STOP_DYNAMO_WHEN_DONE}" CACHE_PINNING_MODE="${mode}" "${wrapper}" "${MODEL}"; then
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
  local mode="${PRIORITY_SCHEDULING_MODE:-${SUITE_DEFAULT_MODE}}"
  local display_mode
  display_mode="$(resolved_mode_display "11" "${mode}")"
  local wrapper="./agentbench/run_priority_scheduling_microbenchmark_single_host.sh"
  local started_at
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local status="passed"
  local error_message=""
  log
  prepare_fresh_runtime_for_experiment
  suite_run_start_banner "${index}" "${total}" "11" "priority_scheduling" "${display_mode}"
  log "Wrapper: ${wrapper}"
  log "Mode: ${display_mode}"
  if ! run_and_log env DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}" INTERACTIVE_BUILD_PROGRESS="${SUITE_INTERACTIVE_BUILD_PROGRESS}" EXPERIMENT_RESET_MODE="${EFFECTIVE_EXPERIMENT_RESET_MODE}" PRIORITY_SCHEDULING_SWEEP_SEED_MODE="${EFFECTIVE_PRIORITY_SCHEDULING_SWEEP_SEED_MODE}" STOP_DYNAMO_WHEN_DONE="${WRAPPER_STOP_DYNAMO_WHEN_DONE}" PRIORITY_SCHEDULING_MODE="${mode}" "${wrapper}" "${MODEL}"; then
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
    "experiments/reports/latest_priority_scheduling_microbenchmark_summary.csv" \
    "experiments/reports/latest_priority_scheduling_microbenchmark_summary.md" \
    "experiments/reports/latest_priority_scheduling_microbenchmark_run_contract.json" \
    "experiments/reports/latest_priority_scheduling_microbenchmark_chart_manifest.json" \
    "experiments/reports/latest_priority_scheduling_microbenchmark_attach_gain.svg|experiments/reports/latest_priority_scheduling_microbenchmark_queue_wait.svg" \
    "${error_message}" "${started_at}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  [[ "${status}" = "passed" || "${SUITE_CONTINUE_ON_ERROR}" = "1" ]]
}

run_experiment_12() {
  local index="$1"
  local total="$2"
  local mode="${SPEC_PREFILL_MODE:-${SUITE_DEFAULT_MODE}}"
  local display_mode
  display_mode="$(resolved_mode_display "12" "${mode}")"
  local wrapper="./agentbench/run_speculative_prefill_microbenchmark_single_host.sh"
  local started_at
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local status="passed"
  local error_message=""
  log
  prepare_fresh_runtime_for_experiment
  suite_run_start_banner "${index}" "${total}" "12" "speculative_prefill" "${display_mode}"
  log "Wrapper: ${wrapper}"
  log "Mode: ${display_mode}"
  if ! run_and_log env DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}" INTERACTIVE_BUILD_PROGRESS="${SUITE_INTERACTIVE_BUILD_PROGRESS}" EXPERIMENT_RESET_MODE="${EFFECTIVE_EXPERIMENT_RESET_MODE}" SPEC_PREFILL_SWEEP_SEED_MODE="${EFFECTIVE_SPEC_PREFILL_SWEEP_SEED_MODE}" STOP_DYNAMO_WHEN_DONE="${WRAPPER_STOP_DYNAMO_WHEN_DONE}" SPEC_PREFILL_MODE="${mode}" "${wrapper}" "${MODEL}"; then
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
    "experiments/reports/latest_speculative_prefill_microbenchmark_summary.csv" \
    "experiments/reports/latest_speculative_prefill_microbenchmark_summary.md" \
    "experiments/reports/latest_speculative_prefill_microbenchmark_run_contract.json" \
    "experiments/reports/latest_speculative_prefill_microbenchmark_chart_manifest.json" \
    "experiments/reports/latest_speculative_prefill_microbenchmark_turnb_latency.svg|experiments/reports/latest_speculative_prefill_microbenchmark_turnb_cached.svg" \
    "${error_message}" "${started_at}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  [[ "${status}" = "passed" || "${SUITE_CONTINUE_ON_ERROR}" = "1" ]]
}

banner "AGENTIC HINT SWEEPS SUITE" | tee -a "${SUITE_DRIVER_LOG}"
log "Suite id: ${SUITE_ID}"
log "Model: ${MODEL}"
log "Machine profile: ${DYNAMO_MACHINE_PROFILE:-default}"
log "Experiments: ${SUITE_EXPERIMENTS}"
log "Suite isolation mode: ${SUITE_ISOLATION_MODE}"
log "Continue on error: ${SUITE_CONTINUE_ON_ERROR}"
log "Stop Dynamo between experiments: ${EFFECTIVE_SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS}"
log "Default mode: ${SUITE_DEFAULT_MODE}"
log "Interactive build progress: ${SUITE_INTERACTIVE_BUILD_PROGRESS}"
log "Suite ensure precise runtime: ${SUITE_ENSURE_PRECISE_RUNTIME}"
log "Experiment reset mode: ${EFFECTIVE_EXPERIMENT_RESET_MODE}"
log "Wrapper stop Dynamo when done: ${WRAPPER_STOP_DYNAMO_WHEN_DONE}"
if [[ "${SUITE_ISOLATION_MODE}" = "clean" ]]; then
  log "Suite runtime policy: restart between experiments, restart between sweep values"
  log "Sweep prompt policy: fixed prompts across sweep values"
else
  log "Suite runtime policy: restart between experiments, no restart between sweep values"
  log "Sweep prompt policy: different prompts across sweep values"
fi
log "Suite env snapshot: ${SUITE_ENV_SNAPSHOT}"
log "Driver log: ${SUITE_DRIVER_LOG}"

ensure_suite_precise_runtime_if_needed

suite_ok=1
selected_experiment_total=0
for token in ${SUITE_EXPERIMENTS}; do
  if exp="$(canonical_experiment "${token}")"; then
    selected_experiment_total=$((selected_experiment_total + 1))
  fi
done
log "Resolved selected experiment count: ${selected_experiment_total}"

selected_experiment_index=0
for token in ${SUITE_EXPERIMENTS}; do
  if ! exp="$(canonical_experiment "${token}")"; then
    log "Unknown suite experiment token: ${token}"
    suite_ok=0
    if [[ "${SUITE_CONTINUE_ON_ERROR}" != "1" ]]; then
      break
    fi
    continue
  fi

  selected_experiment_index=$((selected_experiment_index + 1))
  case "${exp}" in
    9) run_experiment_9 "${selected_experiment_index}" "${selected_experiment_total}" || suite_ok=0 ;;
    10) run_experiment_10 "${selected_experiment_index}" "${selected_experiment_total}" || suite_ok=0 ;;
    11) run_experiment_11 "${selected_experiment_index}" "${selected_experiment_total}" || suite_ok=0 ;;
    12) run_experiment_12 "${selected_experiment_index}" "${selected_experiment_total}" || suite_ok=0 ;;
  esac

  if [[ "${suite_ok}" != "1" && "${SUITE_CONTINUE_ON_ERROR}" != "1" ]]; then
    break
  fi
done

build_suite_outputs

sync_latest_matrices_to_shared_charts

banner "AGENTIC HINT SWEEPS SUITE READY" | tee -a "${SUITE_DRIVER_LOG}"
log "Suite run dir: ${SUITE_ROOT_DIR}"
log "Suite summary: ${SUITE_SUMMARY_MD}"
log "Suite manifest: ${SUITE_MANIFEST_JSON}"
log "Latest summary: ${LATEST_SUMMARY_MD}"
log "Latest manifest: ${LATEST_MANIFEST_JSON}"
log "Latest driver log: ${LATEST_DRIVER_LOG}"

if [[ "${suite_ok}" != "1" ]]; then
  exit 1
fi
