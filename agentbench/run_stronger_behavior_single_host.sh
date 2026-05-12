#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL="${MODEL:-${AGENTBENCH_MODEL}}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}"

exec "${PYTHON_BIN}" agentbench/deepagents_swebench_single_host.py \
  --json-path agentbench/sample_task_stronger.json \
  --frontend-url "${FRONTEND_URL}" \
  --model "${MODEL}" \
  --step-limit 2 \
  "$@"
