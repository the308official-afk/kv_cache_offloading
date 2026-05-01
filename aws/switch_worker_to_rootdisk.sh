#!/bin/bash

set -euo pipefail

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

require_nvidia_ctk() {
  if ! command -v nvidia-ctk >/dev/null 2>&1; then
    echo "nvidia-ctk is not installed. Run: sudo ./aws/bootstrap_ec2_gpu.sh rootdisk" >&2
    exit 1
  fi
}

stop_docker() {
  systemctl stop docker.service || true
  systemctl stop docker.socket || true
}

remove_mount_dependency() {
  rm -f "$DOCKER_DAEMON_JSON"
  rm -f "$DOCKER_DROPIN_FILE"
  rmdir "$DOCKER_DROPIN_DIR" 2>/dev/null || true

  if grep -qE "[[:space:]]${DOCKER_DATA_MOUNT}[[:space:]]" /etc/fstab; then
    sed -i.bak "\|[[:space:]]${DOCKER_DATA_MOUNT}[[:space:]]|d" /etc/fstab
  fi

  if mountpoint -q "$DOCKER_DATA_MOUNT"; then
    umount "$DOCKER_DATA_MOUNT" || true
  fi
}

reconfigure_docker_runtime() {
  nvidia-ctk runtime configure --runtime=docker
  systemctl daemon-reload
  systemctl start docker.socket
  systemctl restart docker
}

print_next_steps() {
  cat <<EOF
Worker Docker configuration has been switched to root-disk mode.

Verify with:
  docker info | grep "Docker Root Dir"
  MIN_ROOT_FREE_GB=40 ./aws/check_ec2_rootdisk_worker_ready.sh

Expected:
  Docker Root Dir: /var/lib/docker
EOF
}

main() {
  require_root
  require_nvidia_ctk
  stop_docker
  remove_mount_dependency
  reconfigure_docker_runtime
  print_next_steps
}

main "$@"
