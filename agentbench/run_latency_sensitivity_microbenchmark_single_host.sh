#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export CONTRACT_PATH="${CONTRACT_PATH:-contracts/latency_sensitivity_microbenchmark.contract.sh}"
export CONTRACT_DOC_PATH="${CONTRACT_DOC_PATH:-contracts/latency_sensitivity_microbenchmark.contract.md}"
export PRIORITY_HINT_KIND="${PRIORITY_HINT_KIND:-latency_sensitivity}"
export PRIORITY_TOP_LEVEL_PRIORITY_MODE="${PRIORITY_TOP_LEVEL_PRIORITY_MODE:-disable}"

if [[ -n "${LATENCY_SENSITIVITY_MODE:-}" ]]; then
  export PRIORITY_SCHEDULING_MODE="${LATENCY_SENSITIVITY_MODE}"
fi
if [[ -n "${LATENCY_SENSITIVITY_ID:-}" ]]; then
  export PRIORITY_SCHEDULING_ID="${LATENCY_SENSITIVITY_ID}"
fi
if [[ -n "${LATENCY_SENSITIVITY_LOW_VALUE:-}" ]]; then
  export LOW_LATENCY_SENSITIVITY_VALUE="${LATENCY_SENSITIVITY_LOW_VALUE}"
fi
if [[ -n "${LATENCY_SENSITIVITY_HIGH_VALUE:-}" ]]; then
  export HIGH_LATENCY_SENSITIVITY_VALUE="${LATENCY_SENSITIVITY_HIGH_VALUE}"
fi

exec ./agentbench/run_priority_scheduling_microbenchmark_single_host.sh "$@"
