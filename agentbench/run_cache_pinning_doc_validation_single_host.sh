#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh
if [[ -f runtime_instrumentation/dynamo_machine_profile.sh ]]; then
  # shellcheck disable=SC1091
  source runtime_instrumentation/dynamo_machine_profile.sh
fi
source runtime_instrumentation/cache_pinning_runtime_helper.sh

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL="${1:-${MODEL:-${MODEL_NAME:-${AGENTBENCH_MODEL}}}}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}"
CACHE_PINNING_DOC_ID="${CACHE_PINNING_DOC_ID:-cache_pinning_doc_$(date +%Y%m%d_%H%M%S)}"
CACHE_PINNING_TTL="${CACHE_PINNING_TTL:-1h}"
CACHE_PINNING_TURN1_MAX_TOKENS="${CACHE_PINNING_TURN1_MAX_TOKENS:-128}"
CACHE_PINNING_TURN2_MAX_TOKENS="${CACHE_PINNING_TURN2_MAX_TOKENS:-128}"
CACHE_PINNING_HICACHE_RATIO="${CACHE_PINNING_HICACHE_RATIO:-1}"
CACHE_PINNING_HICACHE_WRITE_POLICY="${CACHE_PINNING_HICACHE_WRITE_POLICY:-write_through}"
CACHE_PINNING_PINNED_RATIO="${CACHE_PINNING_PINNED_RATIO:-0.1}"
CACHE_PINNING_MEM_FRACTION_STATIC="${CACHE_PINNING_MEM_FRACTION_STATIC:-0.7}"
AUTO_BUILD_CACHE_PINNING_IMAGES="${AUTO_BUILD_CACHE_PINNING_IMAGES:-1}"
CACHE_PINNING_REBUILD_IMAGES="${CACHE_PINNING_REBUILD_IMAGES:-0}"
STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE:-0}"
MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES:-${AGENTBENCH_MODEL_SMOKE_RETRIES}}"
MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS:-${AGENTBENCH_MODEL_SMOKE_DELAY_SECS}}"
MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS:-${AGENTBENCH_MODEL_COOLDOWN_SECS}}"

RUN_DIR="experiments/reports/cache_pinning_doc_validation/${CACHE_PINNING_DOC_ID}"
DRIVER_LOG="${RUN_DIR}/cache_pinning_doc_driver.log"
SMOKE_LOG="${RUN_DIR}/cache_pinning_doc_smoke_test.log"
WORKER_LOG="${RUN_DIR}/cache_pinning_doc_worker.log"
FRONTEND_LOG="${RUN_DIR}/cache_pinning_doc_frontend.log"
LATEST_SUMMARY_CSV="experiments/reports/latest_cache_pinning_doc_validation_summary.csv"
LATEST_REQUESTS_CSV="experiments/reports/latest_cache_pinning_doc_validation_requests.csv"
LATEST_SUMMARY_MD="experiments/reports/latest_cache_pinning_doc_validation_summary.md"
mkdir -p "${RUN_DIR}"
print_local_ready() {
  local frontend_flag="$1"
  cache_pinning_banner_numbered 2 6 "CACHE PINNING LOCAL READY (the isolated Dynamo and SGLang PR sources are selected)" | tee -a "${DRIVER_LOG}"
  cat <<EOF | tee -a "${DRIVER_LOG}"
Machine profile: ${DYNAMO_MACHINE_PROFILE:-default}
Dynamo source dir: ${CACHE_PINNING_DYNAMO_SOURCE_DIR}
Dynamo source ref: ${CACHE_PINNING_DYNAMO_SOURCE_REF}
SGLang source dir: ${CACHE_PINNING_SGLANG_SOURCE_DIR}
SGLang source ref: ${CACHE_PINNING_SGLANG_SOURCE_REF}
Frontend image: ${CACHE_PINNING_FRONTEND_IMAGE}
Worker image: ${CACHE_PINNING_WORKER_IMAGE}
Frontend flag: ${frontend_flag}
EOF
}

worker_stopped() {
  local running
  running="$(docker inspect dynamo-sglang-worker --format '{{.State.Running}}' 2>/dev/null || true)"
  [[ "${running}" = "false" ]]
}

append_worker_debug_to_log() {
  {
    echo
    echo "==== dynamo-sglang-worker docker state ===="
    docker ps -a --filter "name=dynamo-sglang-worker" || true
    echo
    echo "==== dynamo-sglang-worker inspect state ===="
    docker inspect dynamo-sglang-worker \
      --format 'running={{.State.Running}} status={{.State.Status}} exit_code={{.State.ExitCode}} error={{.State.Error}} oom_killed={{.State.OOMKilled}}' \
      2>/dev/null || true
    echo
    echo "==== dynamo-sglang-worker logs tail ===="
    docker logs --tail 240 dynamo-sglang-worker 2>&1 || true
  } >> "${SMOKE_LOG}" 2>&1
}

smoke_test_model() {
  local model="$1"
  local frontend_port="${DYNAMO_FRONTEND_PORT:-8000}"
  local chat_url="http://127.0.0.1:${frontend_port}/v1/chat/completions"
  local models_url="http://127.0.0.1:${frontend_port}/v1/models"
  local registered_models
  local model_listed
  local payload
  local response_file
  local http_code

  for ((attempt=1; attempt<=MODEL_SMOKE_RETRIES; attempt++)); do
    echo "Smoke test ${attempt}/${MODEL_SMOKE_RETRIES} for ${model}" | tee -a "${DRIVER_LOG}"
    registered_models="$(curl -fsS "${models_url}" 2>/dev/null || true)"
    model_listed="$(
      REGISTERED_MODELS="${registered_models}" EXPECTED_MODEL="${model}" "${PYTHON_BIN}" - <<'PY'
import json, os
try:
    payload = json.loads(os.environ.get("REGISTERED_MODELS", "") or "{}")
except json.JSONDecodeError:
    print("0")
    raise SystemExit
expected = os.environ["EXPECTED_MODEL"]
print("1" if any(item.get("id") == expected for item in payload.get("data", [])) else "0")
PY
    )"
    if [[ "${model_listed}" != "1" ]]; then
      if worker_stopped; then
        append_worker_debug_to_log
        return 1
      fi
      sleep "${MODEL_SMOKE_DELAY_SECS}"
      continue
    fi

    payload="$("${PYTHON_BIN}" -c 'import json, sys; print(json.dumps({"model": sys.argv[1], "messages": [{"role": "user", "content": "Reply with exactly: OK"}], "max_tokens": 10}))' "${model}")"
    response_file="$(mktemp)"
    http_code="$(curl -sS -o "${response_file}" -w "%{http_code}" "${chat_url}" -H "Content-Type: application/json" -d "${payload}" 2>> "${SMOKE_LOG}" || true)"
    rm -f "${response_file}"
    if [[ "${http_code}" =~ ^2[0-9][0-9]$ ]]; then
      echo "Smoke test passed for ${model}" | tee -a "${DRIVER_LOG}"
      return 0
    fi
    if worker_stopped; then
      append_worker_debug_to_log
      return 1
    fi
    sleep "${MODEL_SMOKE_DELAY_SECS}"
  done

  append_worker_debug_to_log
  echo "Smoke test failed for ${model}. See ${SMOKE_LOG}" | tee -a "${DRIVER_LOG}" >&2
  return 1
}

check_live_ready() {
  local overlay_status
  overlay_status="$(docker exec -i dynamo-sglang-worker python3 - <<'PY'
from pathlib import Path
overlay = Path("/workspace/sglang_transfer_overlay/sglang/srt/mem_cache/hiradix_cache.py")
print("1" if overlay.exists() else "0")
print("1" if overlay.exists() and "pin_expiry" in overlay.read_text() else "0")
PY
)"
  local exists
  local pin_expiry
  exists="$(printf '%s\n' "${overlay_status}" | sed -n '1p')"
  pin_expiry="$(printf '%s\n' "${overlay_status}" | sed -n '2p')"
  if [[ "${exists}" != "1" || "${pin_expiry}" != "1" ]]; then
    echo "Live worker does not appear to be using the isolated cache-pinning SGLang overlay." | tee -a "${DRIVER_LOG}" >&2
    exit 1
  fi
  cache_pinning_banner_numbered 5 6 "CACHE PINNING LIVE READY (the live worker is using the isolated cache-pinning stack)" | tee -a "${DRIVER_LOG}"
}

print_model_readiness_go() {
  cache_pinning_banner_numbered 4 6 "MODEL READINESS GO (model registration and smoke test both passed)" | tee -a "${DRIVER_LOG}"
}

copy_latest_reports() {
  cp -f "${RUN_DIR}/doc_validation_summary.csv" "${LATEST_SUMMARY_CSV}"
  cp -f "${RUN_DIR}/doc_validation_requests.csv" "${LATEST_REQUESTS_CSV}"
  cp -f "${RUN_DIR}/doc_validation_summary.md" "${LATEST_SUMMARY_MD}"
}

usage() {
  cat <<EOF
Usage:
  $0 [model]

Example:
  DYNAMO_MACHINE_PROFILE=ec2 \\
  CACHE_PINNING_DOC_ID="cache_pinning_doc_\$(date +%Y%m%d_%H%M%S)" \\
  CACHE_PINNING_TTL=1h \\
  CACHE_PINNING_PINNED_RATIO=0.1 \\
  CACHE_PINNING_HICACHE_RATIO=1 \\
  ./agentbench/run_cache_pinning_doc_validation_single_host.sh \\
    Qwen/Qwen2.5-Coder-7B-Instruct
EOF
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${MODEL}" ]]; then
  echo "No model specified. Pass it as an argument or set MODEL / MODEL_NAME." >&2
  exit 1
fi

ensure_cache_pinning_runtime_images "${DRIVER_LOG}" "CACHE PINNING IMAGE READY (isolated cache-pinning images are there)" 6 1
prepare_cache_pinning_sources "${DRIVER_LOG}"

FRONTEND_FLAG="$(detect_cache_pinning_frontend_flag "${CACHE_PINNING_DYNAMO_SOURCE_DIR}" || true)"
if [[ -z "${FRONTEND_FLAG}" ]]; then
  echo "Could not find either --enable-agentic-cache-control or --enable-cache-control in isolated Dynamo source." | tee -a "${DRIVER_LOG}" >&2
  exit 1
fi

print_local_ready "${FRONTEND_FLAG}"

echo "Cache-pinning doc validation run ID: ${CACHE_PINNING_DOC_ID}" | tee -a "${DRIVER_LOG}"
echo "Model: ${MODEL}" | tee -a "${DRIVER_LOG}"
echo "TTL: ${CACHE_PINNING_TTL}" | tee -a "${DRIVER_LOG}"
echo "EPP image: ${CACHE_PINNING_EPP_IMAGE}" | tee -a "${DRIVER_LOG}"
echo "Driver log: ${DRIVER_LOG}" | tee -a "${DRIVER_LOG}"
echo "Smoke log: ${SMOKE_LOG}" | tee -a "${DRIVER_LOG}"
echo "Frontend log: ${FRONTEND_LOG}" | tee -a "${DRIVER_LOG}"
echo "Worker log: ${WORKER_LOG}" | tee -a "${DRIVER_LOG}"

echo "Stopping Dynamo..." | tee -a "${DRIVER_LOG}"
./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true

agentbench_print_model_readiness_active_banner | tee -a "${DRIVER_LOG}"

echo "Starting Dynamo for ${MODEL}..." | tee -a "${DRIVER_LOG}"
ROUTER_EXTRA_ARGS="--no-router-kv-events --router-queue-threshold 4.0 ${FRONTEND_FLAG}" \
WORKER_EXTRA_ARGS="--enable-cache-report --enable-hierarchical-cache --hicache-ratio ${CACHE_PINNING_HICACHE_RATIO} --hicache-write-policy ${CACHE_PINNING_HICACHE_WRITE_POLICY} --mem-fraction-static ${CACHE_PINNING_MEM_FRACTION_STATIC}" \
WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="${CACHE_PINNING_SGLANG_ROOT}" \
SGLANG_HICACHE_MAX_PINNED_RATIO="${CACHE_PINNING_PINNED_RATIO}" \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="${MODEL}" \
DYNAMO_SERVED_MODEL_NAME="${MODEL}" \
FRONTEND_IMAGE="${CACHE_PINNING_FRONTEND_IMAGE}" \
WORKER_IMAGE="${CACHE_PINNING_WORKER_IMAGE}" \
./run_dynamo_single_host.sh start >> "${DRIVER_LOG}" 2>&1

sleep "${MODEL_COOLDOWN_SECS}"

if ! smoke_test_model "${MODEL}"; then
  exit 1
fi

print_model_readiness_go
check_live_ready

cache_pinning_banner_numbered 6 6 "CACHE PINNING EXPERIMENT GO (doc-style validation requests are about to start)" | tee -a "${DRIVER_LOG}"

"${PYTHON_BIN}" experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py \
  --run-id "${CACHE_PINNING_DOC_ID}" \
  --frontend-url "${FRONTEND_URL}" \
  --model "${MODEL}" \
  --ttl "${CACHE_PINNING_TTL}" \
  --turn1-max-tokens "${CACHE_PINNING_TURN1_MAX_TOKENS}" \
  --turn2-max-tokens "${CACHE_PINNING_TURN2_MAX_TOKENS}" \
  --frontend-flag="${FRONTEND_FLAG}" \
  --out-dir "${RUN_DIR}" >> "${DRIVER_LOG}" 2>&1

docker logs dynamo-sglang-worker > "${WORKER_LOG}" 2>&1 || true
docker logs dynamo-frontend > "${FRONTEND_LOG}" 2>&1 || true

"${PYTHON_BIN}" experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py \
  --run-id "${CACHE_PINNING_DOC_ID}" \
  --frontend-url "${FRONTEND_URL}" \
  --model "${MODEL}" \
  --ttl "${CACHE_PINNING_TTL}" \
  --turn1-max-tokens "${CACHE_PINNING_TURN1_MAX_TOKENS}" \
  --turn2-max-tokens "${CACHE_PINNING_TURN2_MAX_TOKENS}" \
  --frontend-flag="${FRONTEND_FLAG}" \
  --frontend-log "${FRONTEND_LOG}" \
  --worker-log "${WORKER_LOG}" \
  --out-dir "${RUN_DIR}" \
  --postprocess-only >> "${DRIVER_LOG}" 2>&1

copy_latest_reports

echo "Run directory: ${RUN_DIR}"
echo "Summary CSV: ${RUN_DIR}/doc_validation_summary.csv"
echo "Requests CSV: ${RUN_DIR}/doc_validation_requests.csv"
echo "Summary MD: ${RUN_DIR}/doc_validation_summary.md"

if [[ "${STOP_DYNAMO_WHEN_DONE}" = "1" ]]; then
  echo "Stopping Dynamo..." | tee -a "${DRIVER_LOG}"
  ./run_dynamo_single_host.sh stop >> "${DRIVER_LOG}" 2>&1 || true
fi
