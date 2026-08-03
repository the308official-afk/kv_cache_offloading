#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL="${1:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}"
NEMO_READY_HELPER="${NEMO_READY_HELPER:-./agentbench/ensure_nemo_agent_toolkit_ready.sh}"
NEMO_DYNAMO_LOG_SINCE="${NEMO_DYNAMO_LOG_SINCE:-5m}"
NEMO_DYNAMO_DEBUG_ID="${NEMO_DYNAMO_DEBUG_ID:-nemo_dynamo_debug_$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="${OUT_DIR:-experiments/reports/nemo_dynamo_debug/${NEMO_DYNAMO_DEBUG_ID}}"

mkdir -p "${OUT_DIR}"

cat <<EOF
========================================
NEMO DYNAMO NVEXT DEBUG
========================================
Model: ${MODEL}
Frontend URL: ${FRONTEND_URL}
Python: ${PYTHON_BIN}
Output dir: ${OUT_DIR}

This script does not start Dynamo.
Run it while the Dynamo runtime you want to inspect is already up.
EOF

echo
echo "========================================"
echo "STEP 0: ENSURE NEMO AGENT TOOLKIT"
echo "========================================"
"${NEMO_READY_HELPER}" 2>&1 | tee "${OUT_DIR}/ensure_nemo_agent_toolkit_ready.log"

echo
echo "========================================"
echo "STEP 1: VERIFY NATIVE NVEXT INJECTION"
echo "========================================"
"${PYTHON_BIN}" agentbench/diagnose_nemo_dynamo_nvext.py \
  --frontend-url "${FRONTEND_URL}" \
  --model "${MODEL}" \
  --output-dir "${OUT_DIR}" \
  2>&1 | tee "${OUT_DIR}/diagnose_nemo_dynamo_nvext.log"

echo
echo "========================================"
echo "STEP 2: CAPTURE RECENT DYNAMO LOG MARKERS"
echo "========================================"
for container in dynamo-frontend dynamo-sglang-worker; do
  log_file="${OUT_DIR}/${container}_recent.log"
  if docker ps --format '{{.Names}}' | grep -qx "${container}"; then
    docker logs --since "${NEMO_DYNAMO_LOG_SINCE}" "${container}" > "${log_file}" 2>&1 || true
    grep -niE 'nvext|agent_hints|latency_sensitivity|priority|worker.decode|RUNTIME_JSON' "${log_file}" > "${OUT_DIR}/${container}_markers.log" 2>&1 || true
    echo "Saved ${container} logs: ${log_file}"
    echo "Saved ${container} markers: ${OUT_DIR}/${container}_markers.log"
  else
    echo "Container not running: ${container}" | tee "${log_file}"
  fi
done

echo
echo "========================================"
echo "DONE"
echo "========================================"
echo "Summary: ${OUT_DIR}/summary.md"
echo "Full debug output: ${OUT_DIR}"
