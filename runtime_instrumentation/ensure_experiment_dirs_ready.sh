#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

ROOT_DIR="$(pwd)"

banner() {
  cat <<EOF
========================================
$1
========================================
EOF
}

DEFAULT_DIRS=(
  "experiments/raw/sglang_transfer_logs"
  "experiments/raw/lpx_decode_split/profiles"
  "experiments/raw/agentbench/results"
  "experiments/raw/agentbench/diagnostics"
  "experiments/reports"
  "experiments/charts"
  "experiments/runtime_state"
)

DIRS=("${DEFAULT_DIRS[@]}")
if [[ "$#" -gt 0 ]]; then
  DIRS+=("$@")
fi

ensure_one_dir() {
  local rel_path="$1"
  local abs_path="${ROOT_DIR}/${rel_path}"
  local probe_file
  probe_file="${abs_path}/.dir_ready_probe_$$"

  if ! mkdir -p "${abs_path}"; then
    echo "ERROR: could not create required experiment directory:" >&2
    echo "  ${abs_path}" >&2
    return 1
  fi

  if ! : > "${probe_file}"; then
    echo "ERROR: directory exists but is not writable:" >&2
    echo "  ${abs_path}" >&2
    return 1
  fi

  rm -f "${probe_file}"
}

for rel_path in "${DIRS[@]}"; do
  ensure_one_dir "${rel_path}"
done

banner "EXPERIMENT DIRS READY (raw/report/chart/runtime directories exist and are writable)"
for rel_path in "${DIRS[@]}"; do
  printf '%s\n' "  ${ROOT_DIR}/${rel_path}"
done
