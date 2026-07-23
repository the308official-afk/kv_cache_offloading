#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3}"

"${PYTHON_BIN}" experiments/scripts/retention_probe/compare_swebench_dataset_vs_trajectory_prompts.py "$@"
