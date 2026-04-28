#!/bin/bash

set -euo pipefail

DOCKER_DATA_DEVICE="${DOCKER_DATA_DEVICE:-/dev/nvme1n1}"
DOCKER_DATA_MOUNT="${DOCKER_DATA_MOUNT:-/mnt/docker-data}"
DOCKER_DAEMON_JSON="${DOCKER_DAEMON_JSON:-/etc/docker/daemon.json}"
DOCKER_DROPIN_DIR="/etc/systemd/system/docker.service.d"
DOCKER_DROPIN_FILE="${DOCKER_DROPIN_DIR}/mount.conf"

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script with sudo."
    exit 1
  fi
}

stop_docker() {
  systemctl stop docker.service || true
  systemctl stop docker.socket || true
}

ensure_mount_dir() {
  mkdir -p "$DOCKER_DATA_MOUNT"
}

ensure_fstab_entry() {
  local uuid
  uuid="$(blkid -s UUID -o value "$DOCKER_DATA_DEVICE")"
  if [ -z "$uuid" ]; then
    echo "Could not determine UUID for $DOCKER_DATA_DEVICE"
    exit 1
  fi

  if grep -qE "[[:space:]]${DOCKER_DATA_MOUNT}[[:space:]]" /etc/fstab; then
    sed -i.bak "\|[[:space:]]${DOCKER_DATA_MOUNT}[[:space:]]|d" /etc/fstab
  fi
  echo "UUID=${uuid} ${DOCKER_DATA_MOUNT} xfs defaults 0 2" >> /etc/fstab
}

mount_disk() {
  if mountpoint -q "$DOCKER_DATA_MOUNT"; then
    umount "$DOCKER_DATA_MOUNT"
  fi
  mount "$DOCKER_DATA_DEVICE" "$DOCKER_DATA_MOUNT"
}

ensure_docker_dropin() {
  mkdir -p "$DOCKER_DROPIN_DIR"
  cat > "$DOCKER_DROPIN_FILE" <<EOF
[Unit]
RequiresMountsFor=${DOCKER_DATA_MOUNT}
EOF
}

ensure_docker_daemon_json() {
  printf '{"data-root": "%s"}\n' "$DOCKER_DATA_MOUNT" > "$DOCKER_DAEMON_JSON"
}

restart_docker() {
  systemctl daemon-reload
  systemctl start docker.socket
  systemctl restart docker
}

verify_mount() {
  local backing_fs
  backing_fs="$(df -P "$DOCKER_DATA_MOUNT" | awk 'NR==2 {print $1}')"
  if [ "$backing_fs" != "$DOCKER_DATA_DEVICE" ]; then
    echo "Mount verification failed: $DOCKER_DATA_MOUNT is backed by $backing_fs, expected $DOCKER_DATA_DEVICE"
    exit 1
  fi
}

print_status() {
  echo
  echo "Recovery complete. Verify with:"
  echo "  df -h ${DOCKER_DATA_MOUNT}"
  echo "  docker info | grep \"Docker Root Dir\""
}

main() {
  require_root
  stop_docker
  ensure_mount_dir
  ensure_fstab_entry
  mount_disk
  verify_mount
  ensure_docker_dropin
  ensure_docker_daemon_json
  restart_docker
  print_status
}

main "$@"
