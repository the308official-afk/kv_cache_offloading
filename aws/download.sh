#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_NAME="$(basename "${REPO_ROOT}")"

PEM="/Users/oluwolejaiyeoba/Documents/GitHub/secrets/projectonekeypair.pem"
REMOTE_PROJECT_DIR="/home/ec2-user/${REPO_NAME}"
REMOTE_RESULTS_DIR="${REMOTE_PROJECT_DIR}/hintbench/results"
LOCAL_RESULTS_DIR="${REPO_ROOT}/hintbench/results"

SERVERS=(
  "44.211.175.29"
  "3.82.232.236"
  "44.211.226.196"
)
LABELS=("S0" "S1" "S2")

DEFAULT_INDEX=0
INDEX="${1:-$DEFAULT_INDEX}"

if [[ "${INDEX}" -lt 0 ]] || [[ "${INDEX}" -ge ${#SERVERS[@]} ]]; then
  echo "Usage: $0 [server-index]" >&2
  echo "Example: $0 0" >&2
  echo "Valid server indexes: 0..$((${#SERVERS[@]} - 1))" >&2
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

echo "==== Downloading HintBench results from ${label} (${ip}) ===="
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
