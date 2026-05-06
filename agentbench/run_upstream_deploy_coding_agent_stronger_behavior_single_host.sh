#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL="${MODEL:-Qwen/Qwen2.5-0.5B}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:8000/v1/chat/completions}"

exec "${PYTHON_BIN}" agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --json-path agentbench/sample_task_stronger.json \
  --frontend-url "${FRONTEND_URL}" \
  --model "${MODEL}" \
  --step-limit 4 \
  "$@"
