#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

SUITE_ID="${AGENTIC_HINT_SUITE_ID:-agentic_hint_sweeps_suite_$(date +%Y%m%d_%H%M%S)}"
SUITE_DIR="experiments/reports/agentic_hint_sweeps_suite/${SUITE_ID}"
NOHUP_LOG="${SUITE_DIR}/suite_nohup.log"
PID_FILE="${SUITE_DIR}/suite_nohup.pid"
LAUNCH_ENV_FILE="${SUITE_DIR}/suite_launch_env.sh"
LATEST_NOHUP_LINK="experiments/reports/latest_agentic_hint_sweeps_suite_nohup.log"

mkdir -p "${SUITE_DIR}"

cat > "${LAUNCH_ENV_FILE}" <<EOF
AGENTIC_HINT_SUITE_ID='${SUITE_ID}'
DYNAMO_MACHINE_PROFILE='${DYNAMO_MACHINE_PROFILE:-}'
SUITE_MODEL='${SUITE_MODEL:-}'
SUITE_EXPERIMENTS='${SUITE_EXPERIMENTS:-}'
SUITE_CONTINUE_ON_ERROR='${SUITE_CONTINUE_ON_ERROR:-}'
SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS='${SUITE_STOP_DYNAMO_BETWEEN_EXPERIMENTS:-}'
SUITE_DEFAULT_MODE='${SUITE_DEFAULT_MODE:-}'
KV_RETENTION_MODE='${KV_RETENTION_MODE:-}'
KV_RETENTION_SWEEP_AXIS='${KV_RETENTION_SWEEP_AXIS:-}'
KV_RETENTION_SWEEP_VALUES='${KV_RETENTION_SWEEP_VALUES:-}'
CACHE_PINNING_MODE='${CACHE_PINNING_MODE:-}'
CACHE_PINNING_VALIDATE_TTL='${CACHE_PINNING_VALIDATE_TTL:-}'
CACHE_PINNING_SWEEP_VALUES='${CACHE_PINNING_SWEEP_VALUES:-}'
CACHE_PINNING_TTL='${CACHE_PINNING_TTL:-}'
CACHE_PINNING_PINNED_RATIO='${CACHE_PINNING_PINNED_RATIO:-}'
CACHE_PINNING_HICACHE_RATIO='${CACHE_PINNING_HICACHE_RATIO:-}'
PRIORITY_SCHEDULING_MODE='${PRIORITY_SCHEDULING_MODE:-}'
PRIORITY_SCHEDULING_SWEEP_AXIS='${PRIORITY_SCHEDULING_SWEEP_AXIS:-}'
PRIORITY_SCHEDULING_SWEEP_VALUES='${PRIORITY_SCHEDULING_SWEEP_VALUES:-}'
SPEC_PREFILL_MODE='${SPEC_PREFILL_MODE:-}'
SPEC_PREFILL_SWEEP_AXIS='${SPEC_PREFILL_SWEEP_AXIS:-}'
SPEC_PREFILL_SWEEP_VALUES='${SPEC_PREFILL_SWEEP_VALUES:-}'
EOF

nohup env AGENTIC_HINT_SUITE_ID="${SUITE_ID}" \
  ./agentbench/run_agentic_hint_sweeps_suite_single_host.sh "$@" \
  > "${NOHUP_LOG}" 2>&1 < /dev/null &

PID=$!
printf '%s\n' "${PID}" > "${PID_FILE}"
ln -sfn "agentic_hint_sweeps_suite/${SUITE_ID}/suite_nohup.log" "${LATEST_NOHUP_LINK}"

cat <<EOF
Started agentic hint sweeps suite in the background.

suite_id: ${SUITE_ID}
pid: ${PID}
nohup_log: ${NOHUP_LOG}
latest_nohup_log: ${LATEST_NOHUP_LINK}
pid_file: ${PID_FILE}
launch_env: ${LAUNCH_ENV_FILE}

Watch the run:
  tail -f ${NOHUP_LOG}
  tail -f ${LATEST_NOHUP_LINK}

Check final outputs:
  cat ${SUITE_DIR}/suite_summary.md
  cat ${SUITE_DIR}/suite_manifest.json
  cat experiments/reports/latest_agentic_hint_sweeps_suite_summary.md
  cat experiments/reports/latest_agentic_hint_sweeps_suite_manifest.json

Stop it if needed:
  kill ${PID}
EOF
