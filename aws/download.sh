#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_NAME="$(basename "${REPO_ROOT}")"

PEM="/Users/oluwolejaiyeoba/Documents/GitHub/secrets/projectonekeypair.pem"
REMOTE_PROJECT_DIR="/home/ec2-user/${REPO_NAME}"

SERVERS=(
  "44.211.175.29"
  "18.206.118.59"
  "44.211.226.196"
)
LABELS=("S0" "S1" "S2")

usage() {
  cat <<'EOF'
Usage:
  ./download.sh
    Download AgentBench results, reports, and SGLang transfer logs from server 0

  ./download.sh <server-index>
    Download AgentBench results, reports, and SGLang transfer logs from the given server

Examples:
  ./download.sh
  ./download.sh 1
EOF
}

REMOTE_RESULTS_DIR="${REMOTE_PROJECT_DIR}/experiments/raw/agentbench/results"
REMOTE_RESULTS_DIR_LEGACY="${REMOTE_PROJECT_DIR}/agentbench/results"
LOCAL_RESULTS_DIR="${REPO_ROOT}/experiments/raw/agentbench/results"
REMOTE_TRANSFER_LOG_DIR="${REMOTE_PROJECT_DIR}/experiments/raw/sglang_transfer_logs"
REMOTE_TRANSFER_REPORT_LEGACY="${REMOTE_PROJECT_DIR}/experiments/sglang_transfer_logs/sglang_transfer_events.jsonl"
LOCAL_TRANSFER_LOG_DIR="${REPO_ROOT}/experiments/raw/sglang_transfer_logs"
REMOTE_RUN_REPORTS_DIR="${REMOTE_PROJECT_DIR}/experiments/reports/runs"
LOCAL_RUN_REPORTS_DIR="${REPO_ROOT}/experiments/reports/runs"
INDEX="0"

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 1
fi

if [[ $# -eq 1 ]]; then
  INDEX="$1"
fi

if ! [[ "${INDEX}" =~ ^[0-9]+$ ]]; then
  echo "Server index must be numeric: ${INDEX}" >&2
  usage >&2
  exit 1
fi

if (( INDEX < 0 || INDEX >= ${#SERVERS[@]} )); then
  echo "Server index out of range: ${INDEX}" >&2
  echo "Valid indices: 0..$(( ${#SERVERS[@]} - 1 ))" >&2
  exit 1
fi

chmod 400 "$PEM"
mkdir -p "$LOCAL_RESULTS_DIR"
mkdir -p "$LOCAL_TRANSFER_LOG_DIR"
mkdir -p "$LOCAL_RUN_REPORTS_DIR"

SSH_OPTS=(
  -i "$PEM"
  -o ControlMaster=auto
  -o ControlPersist=10m
  -o ControlPath=/tmp/kv-cache-offloading-download-%r@%h:%p
  -o StrictHostKeyChecking=accept-new
)
SSH_CMD="ssh ${SSH_OPTS[*]}"

RSYNC_COMMON_OPTS=(
  -az
  --itemize-changes
  --omit-dir-times
  --no-perms
  --no-owner
  --no-group
)

ip="${SERVERS[$INDEX]}"
label="${LABELS[$INDEX]}"
remote_host="ec2-user@${ip}"

echo "==== Downloading agentbench results from ${label} (${ip}) ===="
echo "Remote source: ${REMOTE_RESULTS_DIR}/"
echo "Local dest:    ${LOCAL_RESULTS_DIR}/"

if ! ssh "${SSH_OPTS[@]}" "$remote_host" "test -d '${REMOTE_RESULTS_DIR}'"; then
  echo "New AgentBench results path not found, checking legacy path..." >&2
  if ssh "${SSH_OPTS[@]}" "$remote_host" "test -d '${REMOTE_RESULTS_DIR_LEGACY}'"; then
    REMOTE_RESULTS_DIR="${REMOTE_RESULTS_DIR_LEGACY}"
    echo "Remote source: ${REMOTE_RESULTS_DIR}/"
  else
    echo "Remote results directory does not exist:" >&2
    echo "  ${REMOTE_RESULTS_DIR}" >&2
    echo "  ${REMOTE_RESULTS_DIR_LEGACY}" >&2
    exit 1
  fi
fi

rsync \
  "${RSYNC_COMMON_OPTS[@]}" \
  -e "$SSH_CMD" \
  "${remote_host}:${REMOTE_RESULTS_DIR}/" \
  "${LOCAL_RESULTS_DIR}/"

echo "==== Downloading SGLang transfer reports from ${label} (${ip}) ===="
echo "Remote source: ${REMOTE_TRANSFER_LOG_DIR}/sglang_transfer_events*.jsonl"
echo "Local dest:    ${LOCAL_TRANSFER_LOG_DIR}/"

if ssh "${SSH_OPTS[@]}" "$remote_host" "find '${REMOTE_TRANSFER_LOG_DIR}' -maxdepth 1 -type f -name 'sglang_transfer_events*.jsonl' | grep -q ."; then
  rsync \
    "${RSYNC_COMMON_OPTS[@]}" \
    --include='sglang_transfer_events*.jsonl' \
    --include='latest_sglang_transfer_events.jsonl' \
    --exclude='*' \
    -e "$SSH_CMD" \
    "${remote_host}:${REMOTE_TRANSFER_LOG_DIR}/" \
    "${LOCAL_TRANSFER_LOG_DIR}/"
else
  echo "Timestamped transfer reports not found, checking legacy path..." >&2
  if ssh "${SSH_OPTS[@]}" "$remote_host" "test -f '${REMOTE_TRANSFER_REPORT_LEGACY}'"; then
    echo "Remote source: ${REMOTE_TRANSFER_REPORT_LEGACY}"
    rsync \
      "${RSYNC_COMMON_OPTS[@]}" \
      -e "$SSH_CMD" \
      "${remote_host}:${REMOTE_TRANSFER_REPORT_LEGACY}" \
      "${LOCAL_TRANSFER_LOG_DIR}/"
  else
    echo "Remote SGLang transfer reports do not exist:" >&2
    echo "  ${REMOTE_TRANSFER_LOG_DIR}/sglang_transfer_events*.jsonl" >&2
    echo "  ${REMOTE_TRANSFER_REPORT_LEGACY}" >&2
    exit 1
  fi
fi

echo "==== Downloading run-level reports from ${label} (${ip}) ===="
echo "Remote source: ${REMOTE_RUN_REPORTS_DIR}/"
echo "Local dest:    ${LOCAL_RUN_REPORTS_DIR}/"

if ssh "${SSH_OPTS[@]}" "$remote_host" "test -d '${REMOTE_RUN_REPORTS_DIR}'"; then
  rsync \
    "${RSYNC_COMMON_OPTS[@]}" \
    -e "$SSH_CMD" \
    "${remote_host}:${REMOTE_RUN_REPORTS_DIR}/" \
    "${LOCAL_RUN_REPORTS_DIR}/"
else
  echo "Remote run-level reports directory not found; local report builder can regenerate it." >&2
fi

if [[ -x "${REPO_ROOT}/experiments/scripts/agentbench_report/build_run_report.py" ]]; then
  echo "==== Building local latest run report ===="
  if ! python3 "${REPO_ROOT}/experiments/scripts/agentbench_report/build_run_report.py"; then
    echo "Warning: local report builder failed; raw downloads are still present." >&2
  fi
fi

echo "Download complete."
