#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_NAME="$(basename "${REPO_ROOT}")"

PEM="/Users/oluwolejaiyeoba/Documents/GitHub/secrets/projectonekeypair.pem"
REMOTE_PROJECT_DIR="/home/ec2-user/${REPO_NAME}"

SERVERS=(
  "44.211.175.29"
  "34.238.41.201"
  "44.211.226.196"
)
LABELS=("S0" "S1" "S2")

usage() {
  cat <<'EOF'
Usage:
  ./download.sh
    Download AgentBench results from server 0

  ./download.sh <server-index>
    Download AgentBench results from the given server

Examples:
  ./download.sh
  ./download.sh 1
EOF
}

REMOTE_RESULTS_DIR="${REMOTE_PROJECT_DIR}/agentbench/results"
LOCAL_RESULTS_DIR="${REPO_ROOT}/agentbench/results"
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

ssh "${SSH_OPTS[@]}" "$remote_host" "test -d '${REMOTE_RESULTS_DIR}'" || {
  echo "Remote results directory does not exist: ${REMOTE_RESULTS_DIR}" >&2
  exit 1
}

rsync \
  "${RSYNC_COMMON_OPTS[@]}" \
  -e "$SSH_CMD" \
  "${remote_host}:${REMOTE_RESULTS_DIR}/" \
  "${LOCAL_RESULTS_DIR}/"

echo "Download complete."
