#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

RETENTION_SWEEP_ID="${RETENTION_SWEEP_ID:-cache_control_retention_sweep_$(date +%Y%m%d_%H%M%S)}"
SWEEP_DIR="experiments/reports/retention_threshold_sweeps/${RETENTION_SWEEP_ID}"
NOHUP_LOG="${SWEEP_DIR}/nohup.log"
PID_FILE="${SWEEP_DIR}/nohup.pid"
LAUNCH_ENV_FILE="${SWEEP_DIR}/launch_env.sh"
LATEST_NOHUP_LINK="experiments/reports/latest_cache_control_retention_nohup.log"

mkdir -p "${SWEEP_DIR}"

cat > "${LAUNCH_ENV_FILE}" <<EOF
RETENTION_SWEEP_ID='${RETENTION_SWEEP_ID}'
DYNAMO_MACHINE_PROFILE='${DYNAMO_MACHINE_PROFILE:-}'
RETENTION_ATTRIBUTION_MODE='${RETENTION_ATTRIBUTION_MODE:-}'
RETENTION_REQUEST_CONTEXT_MODE='${RETENTION_REQUEST_CONTEXT_MODE:-}'
DISTRACTOR_COUNTS='${DISTRACTOR_COUNTS:-}'
KV_TIER_MODES='${KV_TIER_MODES:-}'
CONTROL_HINT_PROFILE='${CONTROL_HINT_PROFILE:-}'
PROTECTED_HINT_PROFILES='${PROTECTED_HINT_PROFILES:-}'
CONTROL_CACHE_CONTROL_PROFILE='${CONTROL_CACHE_CONTROL_PROFILE:-}'
PROTECTED_CACHE_CONTROL_PROFILES='${PROTECTED_CACHE_CONTROL_PROFILES:-}'
PROTECTED_INPUT_LEN='${PROTECTED_INPUT_LEN:-}'
DISTRACTOR_INPUT_LEN='${DISTRACTOR_INPUT_LEN:-}'
GPU_ONLY_MEM_FRACTION_STATIC='${GPU_ONLY_MEM_FRACTION_STATIC:-}'
RANDOM_OUTPUT_LEN='${RANDOM_OUTPUT_LEN:-}'
MAX_CONTEXT_TOKENS='${MAX_CONTEXT_TOKENS:-}'
SGLANG_TRANSFER_LOG_PROFILE='${SGLANG_TRANSFER_LOG_PROFILE:-}'
WORKER_BASE_ARGS='${WORKER_BASE_ARGS:-}'
EOF

nohup ./agentbench/run_cache_control_retention_threshold_sweep_single_host.sh "$@" \
  > "${NOHUP_LOG}" 2>&1 < /dev/null &

PID=$!
printf '%s\n' "${PID}" > "${PID_FILE}"
ln -sfn "retention_threshold_sweeps/${RETENTION_SWEEP_ID}/nohup.log" "${LATEST_NOHUP_LINK}"

cat <<EOF
Started cache-control retention threshold sweep in the background.

retention_sweep_id: ${RETENTION_SWEEP_ID}
pid: ${PID}
nohup_log: ${NOHUP_LOG}
latest_nohup_log: ${LATEST_NOHUP_LINK}
pid_file: ${PID_FILE}
launch_env: ${LAUNCH_ENV_FILE}

Watch the run:
  tail -f ${NOHUP_LOG}
  tail -f ${LATEST_NOHUP_LINK}

Check progress:
  cat ${SWEEP_DIR}/retention_threshold_sweep_progress.csv
  cat ${SWEEP_DIR}/retention_threshold_matrix.csv
  cat ${SWEEP_DIR}/retention_threshold_comparison.csv
  cat ${SWEEP_DIR}/retention_threshold_summary.md

Top-level latest reports:
  cat experiments/reports/latest_retention_probe_matrix.csv
  cat experiments/reports/latest_retention_probe_requests.csv
  cat experiments/reports/latest_retention_probe_summary.md

Stop it if needed:
  kill ${PID}
EOF
