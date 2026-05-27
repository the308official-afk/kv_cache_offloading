#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SOURCE_PROFILE_DIR="${1:-${SOURCE_PROFILE_DIR:-}}"
if [[ -z "${SOURCE_PROFILE_DIR}" ]]; then
  cat >&2 <<EOF
Usage: $0 <nsys-profile-dir>

Example:
  LATEST_PROFILE="\$(ls -td experiments/deepagents_swebench_profile/profiles/* | head -1)"
  $0 "\${LATEST_PROFILE}"
EOF
  exit 1
fi

SOURCE_PROFILE_DIR="$(cd "${SOURCE_PROFILE_DIR}" && pwd)"
RUN_STAMP="$(date +%Y%m%d_%H%M%S)"
HBM_RUN_DIR="${HBM_RUN_DIR:-${SOURCE_PROFILE_DIR}/hbm_analysis/ncu_${RUN_STAMP}}"
HBM_OUT_DIR="${HBM_OUT_DIR:-${SOURCE_PROFILE_DIR}/kernel_analysis/hbm}"
HBM_BASENAME="${HBM_BASENAME:-hbm-top-kernels_${RUN_STAMP}}"
HBM_TOP_KERNELS_PER_GROUP="${HBM_TOP_KERNELS_PER_GROUP:-2}"
HBM_AGENT_PHASES="${HBM_AGENT_PHASES:-planning,execution,patch_generation,review}"
HBM_INFERENCE_PHASES="${HBM_INFERENCE_PHASES:-decode,prefill}"
HBM_BUCKETS="${HBM_BUCKETS:-ffn_mlp,attention_kv}"
HBM_SKIP_GENERATION_READY="${HBM_SKIP_GENERATION_READY:-1}"
PROFILE_READY_RETRIES="${PROFILE_READY_RETRIES:-30}"
PROFILE_READY_DELAY_SECS="${PROFILE_READY_DELAY_SECS:-5}"
PROFILE_READY_REQUEST_TIMEOUT_SECS="${PROFILE_READY_REQUEST_TIMEOUT_SECS:-180}"
PROFILE_STOP_TIMEOUT_SECS="${PROFILE_STOP_TIMEOUT_SECS:-240}"
MODEL_READY_RETRIES="${MODEL_READY_RETRIES:-600}"
MODEL_READY_DELAY_SECS="${MODEL_READY_DELAY_SECS:-2}"
MODEL="${MODEL:-}"
CONTEXT_LENGTH="${CONTEXT_LENGTH:-65536}"
WORKER_EXTRA_ARGS="${WORKER_EXTRA_ARGS:---enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length ${CONTEXT_LENGTH}}"
WORKER_PROFILE_NCU_METRICS="${WORKER_PROFILE_NCU_METRICS:-dram__bytes_read.sum,dram__bytes_write.sum}"
WORKER_PROFILE_NCU_EXTRA_ARGS="${WORKER_PROFILE_NCU_EXTRA_ARGS:---target-processes all --replay-mode kernel --kernel-name-base demangled}"
WORKER_PROFILE_NCU_DIR="${WORKER_PROFILE_NCU_DIR:-}"

TOP_AGENT_PHASE_KERNELS="${SOURCE_PROFILE_DIR}/kernel_analysis/top_agent_phase_kernels.csv"
AGENTBENCH_COMMAND_FILE="${SOURCE_PROFILE_DIR}/agentbench-command.txt"

mkdir -p "${HBM_RUN_DIR}" "${HBM_OUT_DIR}"
cd "${REPO_ROOT}"

if [[ ! -f "${TOP_AGENT_PHASE_KERNELS}" ]]; then
  echo "ERROR: missing top kernel table: ${TOP_AGENT_PHASE_KERNELS}" >&2
  exit 1
fi

if [[ ! -f "${AGENTBENCH_COMMAND_FILE}" ]]; then
  echo "ERROR: missing source AgentBench command: ${AGENTBENCH_COMMAND_FILE}" >&2
  exit 1
fi

extract_command_arg() {
  local flag="$1"
  python3.11 - "${AGENTBENCH_COMMAND_FILE}" "${flag}" <<'PY'
from __future__ import annotations

import shlex
import sys
from pathlib import Path

command = shlex.split(Path(sys.argv[1]).read_text(encoding="utf-8"))
flag = sys.argv[2]
for index, item in enumerate(command):
    if item == flag and index + 1 < len(command):
        print(command[index + 1])
        raise SystemExit(0)
    if item.startswith(flag + "="):
        print(item.split("=", 1)[1])
        raise SystemExit(0)
PY
}

if [[ -z "${MODEL}" ]]; then
  MODEL="$(extract_command_arg --model || true)"
  MODEL="${MODEL:-Qwen/Qwen2.5-7B-Instruct}"
fi

if [[ -z "${FRONTEND_URL:-}" ]]; then
  FRONTEND_URL="$(extract_command_arg --frontend-url || true)"
fi

DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT:-}"
if [[ -z "${DYNAMO_FRONTEND_PORT}" && -n "${FRONTEND_URL:-}" ]]; then
  DYNAMO_FRONTEND_PORT="$(python3.11 - "${FRONTEND_URL}" <<'PY'
from urllib.parse import urlparse
import sys

parsed = urlparse(sys.argv[1])
print(parsed.port or 80)
PY
)"
fi
DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT:-8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:${DYNAMO_FRONTEND_PORT}/v1/chat/completions}"

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "ERROR: required command not found: ${command_name}" >&2
    exit 1
  fi
}

capture_stack_logs() {
  docker logs --tail 300 dynamo-frontend > "${HBM_RUN_DIR}/dynamo-frontend.log" 2>&1 || true
  docker logs --tail 500 dynamo-sglang-worker > "${HBM_RUN_DIR}/dynamo-sglang-worker.log" 2>&1 || true
  docker logs dynamo-sglang-worker > "${HBM_RUN_DIR}/dynamo-sglang-worker.full.log" 2>&1 || true
  docker ps -a --filter name=dynamo-sglang-worker \
    --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Command}}' \
    > "${HBM_RUN_DIR}/docker-worker-state.txt" 2>&1 || true
  docker inspect dynamo-sglang-worker > "${HBM_RUN_DIR}/docker-worker-inspect.json" 2>&1 || true
}

stop_profiled_stack() {
  docker stop -t "${PROFILE_STOP_TIMEOUT_SECS}" dynamo-sglang-worker >/dev/null 2>&1 || true
  ./run_dynamo_single_host.sh stop
}

cleanup() {
  local status=$?
  if [[ ${status} -ne 0 ]]; then
    capture_stack_logs
    stop_profiled_stack >/dev/null 2>&1 || true
  fi
}

wait_for_generation_ready() {
  local attempt
  local response_file="${HBM_RUN_DIR}/generation-readiness-last-response.txt"
  for ((attempt=1; attempt<=PROFILE_READY_RETRIES; attempt++)); do
    echo "Checking Nsight Compute worker generation readiness (${attempt}/${PROFILE_READY_RETRIES})..."
    if curl -fsS \
      --connect-timeout 3 \
      --max-time "${PROFILE_READY_REQUEST_TIMEOUT_SECS}" \
      "${FRONTEND_URL}" \
      -H 'Content-Type: application/json' \
      -d "{
        \"model\": \"${MODEL}\",
        \"messages\": [
          {\"role\": \"user\", \"content\": \"Reply with exactly: ok\"}
        ],
        \"max_tokens\": 4,
        \"temperature\": 0
      }" > "${response_file}" 2>&1; then
      return 0
    fi
    echo "Nsight Compute worker is not generation-ready yet. Last response:"
    tail -40 "${response_file}" || true
    sleep "${PROFILE_READY_DELAY_SECS}"
  done

  echo "ERROR: Nsight Compute worker did not become generation-ready." >&2
  capture_stack_logs
  return 1
}

run_source_agentbench_command() {
  local command_text
  command_text="$(cat "${AGENTBENCH_COMMAND_FILE}")"
  printf "%s\n" "${command_text}" > "${HBM_RUN_DIR}/agentbench-command.txt"
  AGENTBENCH_WORKFLOW_MODE="${AGENTBENCH_WORKFLOW_MODE:-phased}" bash -lc "${command_text}" \
    2>&1 | tee "${HBM_RUN_DIR}/agentbench-run.log"
}

export_ncu_csv() {
  local report_path="${HBM_RUN_DIR}/${HBM_BASENAME}.ncu-rep"
  local csv_path="${HBM_RUN_DIR}/${HBM_BASENAME}.csv"

  if [[ ! -f "${report_path}" ]]; then
    echo "WARNING: expected Nsight Compute report not found: ${report_path}" >&2
    return 1
  fi

  if command -v ncu >/dev/null 2>&1; then
    ncu --import "${report_path}" --csv --page raw > "${csv_path}"
    printf "%s\n" "${csv_path}"
    return 0
  fi

  cat >&2 <<EOF
Nsight Compute report exists, but host 'ncu' is not on PATH:
  ${report_path}

Export manually on a machine with Nsight Compute CLI:
  ncu --import "${report_path}" --csv --page raw > "${csv_path}"

Then run:
  python3.11 experiments/deepagents_swebench_profile/analyze_ncu_hbm.py \\
    --top-agent-phase-kernels "${HBM_RUN_DIR}/selected_top_kernels.csv" \\
    --ncu-csv "${csv_path}" \\
    --out-dir "${HBM_OUT_DIR}"
EOF
  return 1
}

require_command docker
require_command curl
require_command python3.11

python3.11 "${SCRIPT_DIR}/select_hbm_top_kernels.py" \
  --top-agent-phase-kernels "${TOP_AGENT_PHASE_KERNELS}" \
  --out-dir "${HBM_RUN_DIR}" \
  --top-kernels-per-group "${HBM_TOP_KERNELS_PER_GROUP}" \
  --agent-phases "${HBM_AGENT_PHASES}" \
  --inference-phases "${HBM_INFERENCE_PHASES}" \
  --buckets "${HBM_BUCKETS}"

KERNEL_REGEX="$(cat "${HBM_RUN_DIR}/selected_kernel_regex.txt")"

cat <<EOF
Selected HBM top kernels:
  ${HBM_RUN_DIR}/selected_top_kernels.csv

Nsight Compute kernel filter:
  ${KERNEL_REGEX}

HBM run directory:
  ${HBM_RUN_DIR}
EOF

trap cleanup EXIT

./run_dynamo_single_host.sh stop

WORKER_PROFILE_MODE="ncu" \
WORKER_PROFILE_DIR="${HBM_RUN_DIR}" \
WORKER_PROFILE_BASENAME="${HBM_BASENAME}" \
WORKER_PROFILE_NCU_DIR="${WORKER_PROFILE_NCU_DIR}" \
WORKER_PROFILE_NCU_METRICS="${WORKER_PROFILE_NCU_METRICS}" \
WORKER_PROFILE_NCU_KERNEL_NAME="${KERNEL_REGEX}" \
WORKER_PROFILE_NCU_EXTRA_ARGS="${WORKER_PROFILE_NCU_EXTRA_ARGS}" \
MODEL_READY_RETRIES="${MODEL_READY_RETRIES}" \
MODEL_READY_DELAY_SECS="${MODEL_READY_DELAY_SECS}" \
DYN_RUNTIME_JSON_LOGS="${DYN_RUNTIME_JSON_LOGS:-1}" \
DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER:-hermes}" \
SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN="${SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN:-1}" \
WORKER_EXTRA_ARGS="${WORKER_EXTRA_ARGS}" \
DYNAMO_MODEL_PATH="${MODEL}" \
DYNAMO_SERVED_MODEL_NAME="${MODEL}" \
DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT}" \
FRONTEND_IMAGE="${FRONTEND_IMAGE:-local/dynamo-frontend:runtime-json-logs}" \
WORKER_IMAGE="${WORKER_IMAGE:-local/dynamo-sglang:runtime-json-logs}" \
./run_dynamo_single_host.sh start

if [[ "${HBM_SKIP_GENERATION_READY}" != "1" ]]; then
  wait_for_generation_ready
fi
run_source_agentbench_command

capture_stack_logs
stop_profiled_stack
trap - EXIT

if NCU_CSV_PATH="$(export_ncu_csv)"; then
  python3.11 "${SCRIPT_DIR}/analyze_ncu_hbm.py" \
    --top-agent-phase-kernels "${HBM_RUN_DIR}/selected_top_kernels.csv" \
    --ncu-csv "${NCU_CSV_PATH}" \
    --out-dir "${HBM_OUT_DIR}"
fi

cat <<EOF

HBM run directory:
  ${HBM_RUN_DIR}

HBM analysis directory:
  ${HBM_OUT_DIR}

Key files:
  ${HBM_OUT_DIR}/hbm_phase_bucket_summary.csv
  ${HBM_OUT_DIR}/hbm_summary.md
EOF
