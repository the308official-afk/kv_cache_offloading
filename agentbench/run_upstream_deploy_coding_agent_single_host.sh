#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL="${MODEL:-${AGENTBENCH_MODEL}}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL}}"
JSON_PATH="${JSON_PATH:-agentbench/sample_task.json}"

USE_DEFAULT_JSON_PATH=1
for arg in "$@"; do
  case "$arg" in
    --json-path|--csv-path|--dataset)
      USE_DEFAULT_JSON_PATH=0
      break
      ;;
  esac
done

ARGS=(
  agentbench/deepagents_swebench_single_host.py
  --app-variant upstream_deploy_coding_agent
  --frontend-url "${FRONTEND_URL}"
  --model "${MODEL}"
)

if [[ "${USE_DEFAULT_JSON_PATH}" -eq 1 ]]; then
  ARGS+=(--json-path "${JSON_PATH}")
fi

ARGS+=("$@")

exec "${PYTHON_BIN}" "${ARGS[@]}"
