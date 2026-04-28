#!/bin/bash

set -euo pipefail

DOCKER_DATA_DEVICE="${DOCKER_DATA_DEVICE:-/dev/nvme1n1}"
DOCKER_DATA_MOUNT="${DOCKER_DATA_MOUNT:-/mnt/docker-data}"
FILESYSTEM_TYPE="${FILESYSTEM_TYPE:-xfs}"
DOCKER_DAEMON_JSON="${DOCKER_DAEMON_JSON:-/etc/docker/daemon.json}"

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script with sudo."
    exit 1
  fi
}

ensure_device_exists() {
  if [ ! -b "$DOCKER_DATA_DEVICE" ]; then
    echo "Block device $DOCKER_DATA_DEVICE does not exist."
    exit 1
  fi
}

ensure_mount_dir() {
  mkdir -p "$DOCKER_DATA_MOUNT"
}

format_if_needed() {
  if ! blkid "$DOCKER_DATA_DEVICE" >/dev/null 2>&1; then
    echo "Formatting $DOCKER_DATA_DEVICE as $FILESYSTEM_TYPE..."
    mkfs -t "$FILESYSTEM_TYPE" "$DOCKER_DATA_DEVICE"
  fi
}

write_fstab_entry() {
  local uuid
  uuid="$(blkid -s UUID -o value "$DOCKER_DATA_DEVICE")"
  if [ -z "$uuid" ]; then
    echo "Could not determine UUID for $DOCKER_DATA_DEVICE after formatting."
    exit 1
  fi

  if grep -qE "[[:space:]]${DOCKER_DATA_MOUNT}[[:space:]]" /etc/fstab; then
    sed -i.bak "\|[[:space:]]${DOCKER_DATA_MOUNT}[[:space:]]|d" /etc/fstab
  fi
  echo "UUID=${uuid} ${DOCKER_DATA_MOUNT} ${FILESYSTEM_TYPE} defaults 0 2" >> /etc/fstab
}

mount_disk() {
  mount "$DOCKER_DATA_DEVICE" "$DOCKER_DATA_MOUNT"
}

configure_docker() {
  systemctl stop docker.service || true
  systemctl stop docker.socket || true

  printf '{"data-root": "%s"}\n' "$DOCKER_DATA_MOUNT" > "$DOCKER_DAEMON_JSON"

  mkdir -p /etc/systemd/system/docker.service.d
  cat > /etc/systemd/system/docker.service.d/mount.conf <<EOF
[Unit]
RequiresMountsFor=${DOCKER_DATA_MOUNT}
EOF

  systemctl daemon-reload
  systemctl start docker.socket
  systemctl restart docker
}

print_status() {
  echo
  echo "Persistent Docker EBS setup complete."
  echo "Verify with:"
  echo "  df -h ${DOCKER_DATA_MOUNT}"
  echo "  docker info | grep \"Docker Root Dir\""
}

main() {
  require_root
  ensure_device_exists
  ensure_mount_dir
  format_if_needed
  write_fstab_entry
  mount_disk
  configure_docker
  print_status
}

main "$@"
