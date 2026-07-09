#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh
if [[ -f runtime_instrumentation/dynamo_machine_profile.sh ]]; then
  # shellcheck disable=SC1091
  source runtime_instrumentation/dynamo_machine_profile.sh
fi
source runtime_instrumentation/cache_pinning_runtime_helper.sh

RETENTION_SWEEP_ID="${RETENTION_SWEEP_ID:-cache_pinning_retention_sweep_$(date +%Y%m%d_%H%M%S)}"
DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-ec2}"
RETENTION_ATTRIBUTION_MODE="${RETENTION_ATTRIBUTION_MODE:-light}"
RETENTION_REQUEST_CONTEXT_MODE="${RETENTION_REQUEST_CONTEXT_MODE:-disable}"
RETENTION_TOP_LEVEL_PRIORITY_MODE="${RETENTION_TOP_LEVEL_PRIORITY_MODE:-disable}"
KV_TIER_MODES="${KV_TIER_MODES:-gpu_cpu}"
CONTROL_HINT_PROFILE="${CONTROL_HINT_PROFILE:-none}"
PROTECTED_HINT_PROFILES="${PROTECTED_HINT_PROFILES:-none}"
CONTROL_CACHE_CONTROL_PROFILE="${CONTROL_CACHE_CONTROL_PROFILE:-off}"
PROTECTED_CACHE_CONTROL_PROFILES="${PROTECTED_CACHE_CONTROL_PROFILES:-ephemeral:1h}"
DISTRACTOR_CACHE_CONTROL_PROFILE="${DISTRACTOR_CACHE_CONTROL_PROFILE:-off}"
DISTRACTOR_COUNTS="${DISTRACTOR_COUNTS:-20 40 60 80}"
PROTECTED_INPUT_LEN="${PROTECTED_INPUT_LEN:-500}"
DISTRACTOR_INPUT_LEN="${DISTRACTOR_INPUT_LEN:-200}"
RANDOM_OUTPUT_LEN="${RANDOM_OUTPUT_LEN:-1}"
MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS:-17146}"
CACHE_PINNING_TTL="${CACHE_PINNING_TTL:-1h}"
CACHE_PINNING_PINNED_RATIO="${CACHE_PINNING_PINNED_RATIO:-0.1}"
CACHE_PINNING_ENABLE_CACHE_REPORT="${CACHE_PINNING_ENABLE_CACHE_REPORT:-1}"
CACHE_PINNING_ROUTER_MODE="${CACHE_PINNING_ROUTER_MODE:-kv}"
SGLANG_HICACHE_MAX_PINNED_RATIO="${SGLANG_HICACHE_MAX_PINNED_RATIO:-${CACHE_PINNING_PINNED_RATIO}}"
CACHE_PINNING_HICACHE_RATIO="${CACHE_PINNING_HICACHE_RATIO:-1}"
CACHE_PINNING_HICACHE_WRITE_POLICY="${CACHE_PINNING_HICACHE_WRITE_POLICY:-write_through}"
CACHE_PINNING_MEM_FRACTION_STATIC="${CACHE_PINNING_MEM_FRACTION_STATIC:-0.7}"
AUTO_BUILD_CACHE_PINNING_IMAGES="${AUTO_BUILD_CACHE_PINNING_IMAGES:-1}"
CACHE_PINNING_REBUILD_IMAGES="${CACHE_PINNING_REBUILD_IMAGES:-0}"
SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-off}"
WORKER_BASE_ARGS="${WORKER_BASE_ARGS:---enable-cache-report --radix-eviction-policy lru}"
EXPERIMENT_RESET_MODE="${EXPERIMENT_RESET_MODE:-restart}"
RETENTION_PROBE_SEED="${RETENTION_PROBE_SEED:-42}"
RETENTION_SWEEP_SEED_MODE="${RETENTION_SWEEP_SEED_MODE:-fixed}"
RETENTION_PROMPT_ISOLATION_MODE="${RETENTION_PROMPT_ISOLATION_MODE:-strict}"

usage() {
  cat <<EOF
Usage:
  ./agentbench/run_cache_pinning_retention_threshold_sweep_single_host.sh [model ...]

Example:
  DYNAMO_MACHINE_PROFILE=ec2 \\
  RETENTION_SWEEP_ID="cache_pinning_retention_sweep_\$(date +%Y%m%d_%H%M%S)" \\
  DISTRACTOR_COUNTS="40 80 120 160" \\
  PROTECTED_INPUT_LEN=500 \\
  DISTRACTOR_INPUT_LEN=200 \\
  ./agentbench/run_cache_pinning_retention_threshold_sweep_single_host.sh \\
    Qwen/Qwen2.5-Coder-7B-Instruct

This runs the existing retention-threshold report flow on the isolated
cache-pinning PR stack, comparing:
  control arm:   cache_control=off
  protected arm: cache_control=ephemeral:1h
EOF
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

if [[ "${RETENTION_ATTRIBUTION_MODE}" != "light" ]]; then
  echo "This isolated cache-pinning retention sweep currently supports RETENTION_ATTRIBUTION_MODE=light only." >&2
  echo "Use the default light mode here; the goal is behavioral proof on the cache-pinning PR stack." >&2
  exit 2
fi

LOG_DIR="experiments/reports/cache_pinning_retention_threshold_sweeps/${RETENTION_SWEEP_ID}"
LOG_PATH="${LOG_DIR}/cache_pinning_retention_threshold_driver.log"
mkdir -p "${LOG_DIR}"

if [[ " ${WORKER_BASE_ARGS} " == *" --radix-eviction-policy priority "* ]]; then
  echo "Cache-pinning note: this isolated SGLang stack does not accept --radix-eviction-policy priority." | tee -a "${LOG_PATH}"
  echo "Cache-pinning note: rewriting eviction policy to lru for this experiment." | tee -a "${LOG_PATH}"
  WORKER_BASE_ARGS="$(printf '%s' "${WORKER_BASE_ARGS}" | sed 's/--radix-eviction-policy[[:space:]]\+priority/--radix-eviction-policy lru/g')"
fi

echo "Ensuring isolated cache-pinning images..." | tee -a "${LOG_PATH}"
echo "Using machine profile: ${DYNAMO_MACHINE_PROFILE}" | tee -a "${LOG_PATH}"
echo "FRONTEND_IMAGE=${CACHE_PINNING_FRONTEND_IMAGE}" | tee -a "${LOG_PATH}"
echo "WORKER_IMAGE=${CACHE_PINNING_WORKER_IMAGE}" | tee -a "${LOG_PATH}"
ensure_cache_pinning_runtime_images \
  "${LOG_PATH}" \
  "CACHE PINNING IMAGE READY (isolated cache-pinning images are there)" \
  4 \
  1

prepare_cache_pinning_sources "${LOG_PATH}"
FRONTEND_FLAG="$(detect_cache_pinning_frontend_flag "${CACHE_PINNING_DYNAMO_SOURCE_DIR}" || true)"
if [[ -z "${FRONTEND_FLAG}" ]]; then
  echo "Could not find the cache-pinning frontend flag in isolated Dynamo source." | tee -a "${LOG_PATH}" >&2
  exit 1
fi

cache_pinning_banner_numbered 2 4 "CACHE PINNING LOCAL READY (the isolated Dynamo and SGLang PR sources are selected)" | tee -a "${LOG_PATH}"
cat <<EOF | tee -a "${LOG_PATH}"
Machine profile: ${DYNAMO_MACHINE_PROFILE}
Dynamo source dir: ${CACHE_PINNING_DYNAMO_SOURCE_DIR}
Dynamo source ref: ${CACHE_PINNING_DYNAMO_SOURCE_REF}
SGLang source dir: ${CACHE_PINNING_SGLANG_SOURCE_DIR}
SGLang source ref: ${CACHE_PINNING_SGLANG_SOURCE_REF}
Frontend image: ${CACHE_PINNING_FRONTEND_IMAGE}
Worker image: ${CACHE_PINNING_WORKER_IMAGE}
Frontend flag: ${FRONTEND_FLAG}
EOF

cache_pinning_banner_numbered 3 4 "CACHE PINNING RETENTION SETUP READY (control vs ephemeral pressure sweep is configured)" | tee -a "${LOG_PATH}"
cat <<EOF | tee -a "${LOG_PATH}"
retention_sweep_id: ${RETENTION_SWEEP_ID}
attribution_mode: ${RETENTION_ATTRIBUTION_MODE}
kv_tier_modes: ${KV_TIER_MODES}
control_cache_control: ${CONTROL_CACHE_CONTROL_PROFILE}
protected_cache_control: ${PROTECTED_CACHE_CONTROL_PROFILES}
distractor_counts: ${DISTRACTOR_COUNTS}
protected_input_len: ${PROTECTED_INPUT_LEN}
distractor_input_len: ${DISTRACTOR_INPUT_LEN}
ttl: ${CACHE_PINNING_TTL}
pinned_ratio: ${CACHE_PINNING_PINNED_RATIO}
hicache_ratio: ${CACHE_PINNING_HICACHE_RATIO}
hicache_write_policy: ${CACHE_PINNING_HICACHE_WRITE_POLICY}
mem_fraction_static: ${CACHE_PINNING_MEM_FRACTION_STATIC}
experiment_reset_mode: ${EXPERIMENT_RESET_MODE}
retention_probe_seed: ${RETENTION_PROBE_SEED}
retention_sweep_seed_mode: ${RETENTION_SWEEP_SEED_MODE}
retention_prompt_isolation_mode: ${RETENTION_PROMPT_ISOLATION_MODE}
EOF

cache_pinning_banner_numbered 4 4 "CACHE PINNING RETENTION EXPERIMENT GO (threshold sweep is about to start)" | tee -a "${LOG_PATH}"

env \
  DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE}" \
  RETENTION_SWEEP_ID="${RETENTION_SWEEP_ID}" \
  RETENTION_ATTRIBUTION_MODE="${RETENTION_ATTRIBUTION_MODE}" \
  RETENTION_REQUEST_CONTEXT_MODE="${RETENTION_REQUEST_CONTEXT_MODE}" \
  RETENTION_TOP_LEVEL_PRIORITY_MODE="${RETENTION_TOP_LEVEL_PRIORITY_MODE}" \
  KV_TIER_MODES="${KV_TIER_MODES}" \
  CONTROL_HINT_PROFILE="${CONTROL_HINT_PROFILE}" \
  PROTECTED_HINT_PROFILES="${PROTECTED_HINT_PROFILES}" \
  CONTROL_CACHE_CONTROL_PROFILE="${CONTROL_CACHE_CONTROL_PROFILE}" \
  PROTECTED_CACHE_CONTROL_PROFILES="${PROTECTED_CACHE_CONTROL_PROFILES}" \
  DISTRACTOR_CACHE_CONTROL_PROFILE="${DISTRACTOR_CACHE_CONTROL_PROFILE}" \
  CACHE_CONTROL_REQUIRE_HIERARCHICAL_CACHE=1 \
  CACHE_CONTROL_DOC_MODE=0 \
  CACHE_CONTROL_FRONTEND_FLAG_MODE=disable \
  CACHE_CONTROL_EPHEMERAL_TTL="${CACHE_PINNING_TTL}" \
  HICACHE_RATIO="${CACHE_PINNING_HICACHE_RATIO}" \
  HICACHE_WRITE_POLICY="${CACHE_PINNING_HICACHE_WRITE_POLICY}" \
  SGLANG_HICACHE_MAX_PINNED_RATIO="${SGLANG_HICACHE_MAX_PINNED_RATIO}" \
  MEM_FRACTION_STATIC="${CACHE_PINNING_MEM_FRACTION_STATIC}" \
  GPU_ONLY_MEM_FRACTION_STATIC="${CACHE_PINNING_MEM_FRACTION_STATIC}" \
  GPU_CPU_MEM_FRACTION_STATIC="${CACHE_PINNING_MEM_FRACTION_STATIC}" \
  GPU_CPU_STORAGE_MEM_FRACTION_STATIC="${CACHE_PINNING_MEM_FRACTION_STATIC}" \
  DISTRACTOR_COUNTS="${DISTRACTOR_COUNTS}" \
  PROTECTED_INPUT_LEN="${PROTECTED_INPUT_LEN}" \
  DISTRACTOR_INPUT_LEN="${DISTRACTOR_INPUT_LEN}" \
  RANDOM_OUTPUT_LEN="${RANDOM_OUTPUT_LEN}" \
  MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS}" \
  RETENTION_PROMPT_ISOLATION_MODE="${RETENTION_PROMPT_ISOLATION_MODE}" \
  SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
  FRONTEND_IMAGE="${CACHE_PINNING_FRONTEND_IMAGE}" \
  WORKER_IMAGE="${CACHE_PINNING_WORKER_IMAGE}" \
  CUSTOM_RUNTIME_IMAGES_MODE=1 \
  CUSTOM_RUNTIME_SGLANG_ROOT="${CACHE_PINNING_SGLANG_ROOT}" \
  ROUTER_EXTRA_ARGS="--router-mode ${CACHE_PINNING_ROUTER_MODE} --no-router-kv-events --router-queue-threshold 4.0 ${FRONTEND_FLAG}" \
  WORKER_BASE_ARGS="$( [[ "${CACHE_PINNING_ENABLE_CACHE_REPORT}" = "1" && "${WORKER_BASE_ARGS}" != *"--enable-cache-report"* ]] && printf '%s ' '--enable-cache-report' )${WORKER_BASE_ARGS}" \
  LATEST_RETENTION_THRESHOLD_PROGRESS="experiments/reports/latest_cache_pinning_retention_threshold_progress.csv" \
  LATEST_RETENTION_THRESHOLD_MATRIX="experiments/reports/latest_cache_pinning_retention_threshold_matrix.csv" \
  LATEST_RETENTION_THRESHOLD_COMPARISON="experiments/reports/latest_cache_pinning_retention_threshold_comparison.csv" \
  LATEST_RETENTION_THRESHOLD_SUMMARY="experiments/reports/latest_cache_pinning_retention_threshold_summary.md" \
  AUTO_BUILD_CACHE_PINNING_IMAGES="${AUTO_BUILD_CACHE_PINNING_IMAGES}" \
  CACHE_PINNING_REBUILD_IMAGES="${CACHE_PINNING_REBUILD_IMAGES}" \
  EXPERIMENT_RESET_MODE="${EXPERIMENT_RESET_MODE}" \
  RETENTION_PROBE_SEED="${RETENTION_PROBE_SEED}" \
  RETENTION_SWEEP_SEED_MODE="${RETENTION_SWEEP_SEED_MODE}" \
  ./agentbench/run_kv_retention_threshold_sweep_single_host.sh "$@"

sweep_exit_code=$?
if [[ "${sweep_exit_code}" -ne 0 ]]; then
  exit "${sweep_exit_code}"
fi

python3 experiments/scripts/cache_pinning/compact_cache_pinning_retention_reports.py \
  --matrix "${LOG_DIR}/retention_threshold_matrix.csv" \
  --comparison "${LOG_DIR}/retention_threshold_comparison.csv"

python3 experiments/scripts/cache_pinning/compact_cache_pinning_retention_reports.py \
  --matrix "experiments/reports/latest_cache_pinning_retention_threshold_matrix.csv" \
  --comparison "experiments/reports/latest_cache_pinning_retention_threshold_comparison.csv"
