#!/bin/bash

set -euo pipefail

ROOT_DISK="${ROOT_DISK:-/dev/nvme0n1}"
ROOT_PARTITION_NUMBER="${ROOT_PARTITION_NUMBER:-1}"
ROOT_FILESYSTEM_MOUNT="${ROOT_FILESYSTEM_MOUNT:-/}"

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script with sudo."
    exit 1
  fi
}

ensure_growpart() {
  if ! command -v growpart >/dev/null 2>&1; then
    dnf install -y cloud-utils-growpart
  fi
}

show_before() {
  echo "Before expansion:"
  lsblk
  df -h "${ROOT_FILESYSTEM_MOUNT}"
}

expand_partition() {
  local output status
  set +e
  output="$(growpart "${ROOT_DISK}" "${ROOT_PARTITION_NUMBER}" 2>&1)"
  status=$?
  set -e

  echo "${output}"

  if [ "${status}" -eq 0 ]; then
    return 0
  fi

  if echo "${output}" | grep -q "NOCHANGE"; then
    echo "Partition is already using the full root volume."
    return 0
  fi

  echo "growpart failed unexpectedly." >&2
  exit "${status}"
}

expand_xfs() {
  xfs_growfs -d "${ROOT_FILESYSTEM_MOUNT}"
}

show_after() {
  echo
  echo "After expansion:"
  lsblk
  df -h "${ROOT_FILESYSTEM_MOUNT}"
}

main() {
  require_root
  ensure_growpart
  show_before
  expand_partition
  expand_xfs
  show_after
}

main "$@"
