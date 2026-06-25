#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

usage() {
  cat <<'EOF'
Usage:
  ./agentbench/run_cache_control_retention_threshold_sweep_single_host.sh [model ...]

This runs a harsher retention threshold sweep focused on:
  control arm:   cache_control=off
  protected arm: cache_control=ephemeral:1h (by default)

Useful tuning knobs:
  DYNAMO_MACHINE_PROFILE              ec2 or gh200
  RETENTION_SWEEP_ID                 run id
  RETENTION_ATTRIBUTION_MODE         precise or light
  RETENTION_REQUEST_CONTEXT_MODE     auto or disable
  KV_TIER_MODES                      gpu_only, gpu_cpu, gpu_cpu_storage
  CONTROL_HINT_PROFILE               usually none
  PROTECTED_HINT_PROFILES            usually none for cache-control experiments
  CONTROL_CACHE_CONTROL_PROFILE      usually off
  PROTECTED_CACHE_CONTROL_PROFILES   e.g. ephemeral:1h
  DISTRACTOR_COUNTS                  e.g. "2 4 6 8 10 12"
  PROTECTED_INPUT_LEN                e.g. 2000
  DISTRACTOR_INPUT_LEN               e.g. 2000
  GPU_ONLY_MEM_FRACTION_STATIC       e.g. 0.62
  RANDOM_OUTPUT_LEN                  usually 1
  MAX_CONTEXT_TOKENS                 worker effective context ceiling
  SGLANG_TRANSFER_LOG_PROFILE        off, light, timing, full
  WORKER_BASE_ARGS                   extra SGLang worker args
EOF
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

RETENTION_SWEEP_ID="${RETENTION_SWEEP_ID:-retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)}"
DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-ec2}"
RETENTION_ATTRIBUTION_MODE="${RETENTION_ATTRIBUTION_MODE:-precise}"
RETENTION_REQUEST_CONTEXT_MODE="${RETENTION_REQUEST_CONTEXT_MODE:-auto}"
KV_TIER_MODES="${KV_TIER_MODES:-gpu_only}"
CONTROL_HINT_PROFILE="${CONTROL_HINT_PROFILE:-none}"
PROTECTED_HINT_PROFILES="${PROTECTED_HINT_PROFILES:-none}"
CONTROL_CACHE_CONTROL_PROFILE="${CONTROL_CACHE_CONTROL_PROFILE:-off}"
PROTECTED_CACHE_CONTROL_PROFILES="${PROTECTED_CACHE_CONTROL_PROFILES:-ephemeral:1h}"
DISTRACTOR_COUNTS="${DISTRACTOR_COUNTS:-2 4 6 8 10 12}"
PROTECTED_INPUT_LEN="${PROTECTED_INPUT_LEN:-2000}"
DISTRACTOR_INPUT_LEN="${DISTRACTOR_INPUT_LEN:-2000}"
GPU_ONLY_MEM_FRACTION_STATIC="${GPU_ONLY_MEM_FRACTION_STATIC:-0.62}"
RANDOM_OUTPUT_LEN="${RANDOM_OUTPUT_LEN:-1}"
MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS:-17146}"
SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-full}"
WORKER_BASE_ARGS="${WORKER_BASE_ARGS:---enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority}"

cat <<EOF
Cache-control retention threshold sweep
  retention_sweep_id: ${RETENTION_SWEEP_ID}
  machine_profile: ${DYNAMO_MACHINE_PROFILE}
  attribution_mode: ${RETENTION_ATTRIBUTION_MODE}
  kv_tier_modes: ${KV_TIER_MODES}
  control_cache_control: ${CONTROL_CACHE_CONTROL_PROFILE}
  protected_cache_control: ${PROTECTED_CACHE_CONTROL_PROFILES}
  distractor_counts: ${DISTRACTOR_COUNTS}
  protected_input_len: ${PROTECTED_INPUT_LEN}
  distractor_input_len: ${DISTRACTOR_INPUT_LEN}
  gpu_only_mem_fraction_static: ${GPU_ONLY_MEM_FRACTION_STATIC}
  request_context_mode: ${RETENTION_REQUEST_CONTEXT_MODE}
  random_output_len: ${RANDOM_OUTPUT_LEN}
  max_context_tokens: ${MAX_CONTEXT_TOKENS}
  transfer_log_profile: ${SGLANG_TRANSFER_LOG_PROFILE}
  worker_base_args: ${WORKER_BASE_ARGS}
EOF

exec env \
  DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE}" \
  RETENTION_SWEEP_ID="${RETENTION_SWEEP_ID}" \
  RETENTION_ATTRIBUTION_MODE="${RETENTION_ATTRIBUTION_MODE}" \
  RETENTION_REQUEST_CONTEXT_MODE="${RETENTION_REQUEST_CONTEXT_MODE}" \
  LATEST_RETENTION_THRESHOLD_PROGRESS="experiments/reports/latest_cache_control_retention_threshold_progress.csv" \
  LATEST_RETENTION_THRESHOLD_MATRIX="experiments/reports/latest_cache_control_retention_threshold_matrix.csv" \
  LATEST_RETENTION_THRESHOLD_COMPARISON="experiments/reports/latest_cache_control_retention_threshold_comparison.csv" \
  LATEST_RETENTION_THRESHOLD_SUMMARY="experiments/reports/latest_cache_control_retention_threshold_summary.md" \
  KV_TIER_MODES="${KV_TIER_MODES}" \
  CONTROL_HINT_PROFILE="${CONTROL_HINT_PROFILE}" \
  PROTECTED_HINT_PROFILES="${PROTECTED_HINT_PROFILES}" \
  CONTROL_CACHE_CONTROL_PROFILE="${CONTROL_CACHE_CONTROL_PROFILE}" \
  PROTECTED_CACHE_CONTROL_PROFILES="${PROTECTED_CACHE_CONTROL_PROFILES}" \
  DISTRACTOR_COUNTS="${DISTRACTOR_COUNTS}" \
  PROTECTED_INPUT_LEN="${PROTECTED_INPUT_LEN}" \
  DISTRACTOR_INPUT_LEN="${DISTRACTOR_INPUT_LEN}" \
  GPU_ONLY_MEM_FRACTION_STATIC="${GPU_ONLY_MEM_FRACTION_STATIC}" \
  RANDOM_OUTPUT_LEN="${RANDOM_OUTPUT_LEN}" \
  MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS}" \
  SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
  WORKER_BASE_ARGS="${WORKER_BASE_ARGS}" \
  ./agentbench/run_kv_retention_threshold_sweep_single_host.sh "$@"
