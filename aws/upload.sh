#!/bin/bash

set -euo pipefail

# === CONFIG ===
PEM="/Users/oluwolejaiyeoba/Documents/GitHub/secrets/projectonekeypair.pem"
LOCAL_BASE="/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading"
REMOTE_PROJECT_DIR="/home/ec2-user/kv_cache_offloading"

SERVERS=("44.201.229.234" "44.202.2.239" "3.88.7.135")
LABELS=("S0" "S1" "S2")

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

for i in "${!SERVERS[@]}"; do
  ip="${SERVERS[$i]}"
  label="${LABELS[$i]}"
  remote_host="ec2-user@${ip}"
  remote_base="${remote_host}:${REMOTE_PROJECT_DIR}/"

  echo "==== Uploading kv_cache_offloading to ${label} (${ip}) ===="

  ssh "${SSH_OPTS[@]}" "$remote_host" "mkdir -p '${REMOTE_PROJECT_DIR}'"

  # Trailing slash uploads the contents of the repo root into REMOTE_PROJECT_DIR.
  rsync_upload_repo "${LOCAL_BASE}/" "$remote_base"
done
