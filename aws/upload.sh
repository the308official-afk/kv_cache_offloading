#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_NAME="$(basename "${REPO_ROOT}")"

# === CONFIG ===
PEM="/Users/oluwolejaiyeoba/Documents/GitHub/secrets/projectonekeypair.pem"
LOCAL_BASE="${REPO_ROOT}"
REMOTE_PROJECT_DIR="/home/ec2-user/${REPO_NAME}"

# SERVERS=("44.201.229.234" "44.202.2.239" "3.88.7.135")
SERVERS=(
  ""   
  "3.92.188.47"
  ""
)
LABELS=("S0" "S1" "S2")

usage() {
  cat <<'EOF'
Usage:
  ./upload.sh        Upload to all configured servers
  ./upload.sh <idx>  Upload only to server index <idx> (for example: ./upload.sh 1)
EOF
}

# Ensure key permissions
chmod 400 "$PEM"

SSH_OPTS=(
  -i "$PEM"
  -o ControlMaster=auto
  -o ControlPersist=10m
  -o ControlPath=/tmp/kv-cache-offloading-upload-%r@%h:%p
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

RSYNC_EXCLUDES=(
  --exclude '.git/'
  --exclude '.DS_Store'
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '.pytest_cache/'
  --exclude '.mypy_cache/'
  --exclude '.ruff_cache/'
  --exclude '.coverage'
  --exclude 'htmlcov/'
  --exclude '.venv/'
  --exclude 'venv/'
  --exclude 'agentbench/results/'
  --include 'experiments/'
  --include 'experiments/scripts/'
  --include 'experiments/scripts/***'
  --exclude 'experiments/*'
)

rsync_upload_repo() {
  local source_path="$1"
  local remote_path="$2"

  rsync \
    "${RSYNC_COMMON_OPTS[@]}" \
    "${RSYNC_EXCLUDES[@]}" \
    -e "$SSH_CMD" \
    "$source_path" \
    "$remote_path"
}

if [[ ! -d "${LOCAL_BASE}" ]]; then
  echo "Local repo root not found: ${LOCAL_BASE}" >&2
  exit 1
fi

if [[ ! -d "${LOCAL_BASE}/hintbench" ]]; then
  echo "Warning: ${LOCAL_BASE}/hintbench was not found locally." >&2
fi

TARGET_INDICES=()

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 1
fi

if [[ $# -eq 1 ]]; then
  if ! [[ "$1" =~ ^[0-9]+$ ]]; then
    echo "Server index must be numeric: $1" >&2
    usage >&2
    exit 1
  fi
  if (( "$1" < 0 || "$1" >= ${#SERVERS[@]} )); then
    echo "Server index out of range: $1" >&2
    echo "Valid indices: 0..$(( ${#SERVERS[@]} - 1 ))" >&2
    exit 1
  fi
  TARGET_INDICES=("$1")
else
  TARGET_INDICES=("${!SERVERS[@]}")
fi

for i in "${TARGET_INDICES[@]}"; do
  ip="${SERVERS[$i]}"
  label="${LABELS[$i]}"
  remote_host="ec2-user@${ip}"
  remote_base="${remote_host}:${REMOTE_PROJECT_DIR}/"

  echo "==== Uploading ${REPO_NAME} to ${label} (${ip}) ===="
  echo "Local source: ${LOCAL_BASE}/"
  echo "Remote dest:  ${REMOTE_PROJECT_DIR}/"

  ssh "${SSH_OPTS[@]}" "$remote_host" "mkdir -p '${REMOTE_PROJECT_DIR}'"

  # Trailing slash uploads the full repo contents into REMOTE_PROJECT_DIR.
  rsync_upload_repo "${LOCAL_BASE}/" "$remote_base"
done
