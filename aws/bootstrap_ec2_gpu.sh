#!/bin/bash

set -euo pipefail

GPU_WORKER_STORAGE_MODE="${GPU_WORKER_STORAGE_MODE:-}"
if [ "${1:-}" = "rootdisk" ] || [ "${1:-}" = "ebs" ]; then
  GPU_WORKER_STORAGE_MODE="$1"
  shift
fi

DOCKER_DATA_DEVICE="${DOCKER_DATA_DEVICE:-/dev/nvme1n1}"
DOCKER_DATA_MOUNT="${DOCKER_DATA_MOUNT:-/mnt/docker-data}"
DOCKER_DAEMON_JSON="${DOCKER_DAEMON_JSON:-/etc/docker/daemon.json}"
GPU_WORKER_STORAGE_MODE="${GPU_WORKER_STORAGE_MODE:-ebs}"

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

restart_docker() {
  systemctl daemon-reload
  systemctl start docker.socket
  systemctl restart docker
}

install_docker() {
  dnf install -y docker
  systemctl enable docker
  systemctl start docker
  usermod -aG docker ec2-user || true
}

install_nvidia_driver() {
  dnf install -y nvidia-release
  dnf install -y "kernel-devel-$(uname -r)" "kernel-headers-$(uname -r)"
  dnf install -y nvidia-driver-cuda
}

install_nvidia_container_toolkit() {
  curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo \
    -o /etc/yum.repos.d/nvidia-container-toolkit.repo
  dnf install -y nvidia-container-toolkit
  nvidia-ctk runtime configure --runtime=docker
  restart_docker
}

mount_docker_disk() {
  local uuid

  mkdir -p "$DOCKER_DATA_MOUNT"

  if ! blkid "$DOCKER_DATA_DEVICE" >/dev/null 2>&1; then
    mkfs -t xfs "$DOCKER_DATA_DEVICE"
  fi

  if ! mountpoint -q "$DOCKER_DATA_MOUNT"; then
    mount "$DOCKER_DATA_DEVICE" "$DOCKER_DATA_MOUNT"
  fi

  uuid="$(blkid -s UUID -o value "$DOCKER_DATA_DEVICE")"
  if grep -qE "[[:space:]]${DOCKER_DATA_MOUNT}[[:space:]]" /etc/fstab; then
    sed -i.bak "\|[[:space:]]${DOCKER_DATA_MOUNT}[[:space:]]|d" /etc/fstab
  fi
  echo "UUID=${uuid} ${DOCKER_DATA_MOUNT} xfs defaults 0 2" >> /etc/fstab
}

configure_docker_mount_dependency() {
  mkdir -p /etc/systemd/system/docker.service.d
  cat > /etc/systemd/system/docker.service.d/mount.conf <<EOF
[Unit]
RequiresMountsFor=${DOCKER_DATA_MOUNT}
EOF
  systemctl daemon-reload
}

configure_docker_data_root() {
  stop_docker
  printf '{"data-root": "%s"}\n' "$DOCKER_DATA_MOUNT" > "$DOCKER_DAEMON_JSON"
  restart_docker
}

configure_rootdisk_docker() {
  stop_docker
  rm -f "$DOCKER_DAEMON_JSON"
  rm -f /etc/systemd/system/docker.service.d/mount.conf
  rmdir /etc/systemd/system/docker.service.d 2>/dev/null || true
  if grep -qE "[[:space:]]${DOCKER_DATA_MOUNT}[[:space:]]" /etc/fstab; then
    sed -i.bak "\|[[:space:]]${DOCKER_DATA_MOUNT}[[:space:]]|d" /etc/fstab
  fi
  if mountpoint -q "$DOCKER_DATA_MOUNT"; then
    umount "$DOCKER_DATA_MOUNT" || true
  fi
  systemctl daemon-reload
  systemctl start docker
}

print_next_steps() {
  cat <<EOF
Bootstrap completed.

Recommended next checks:
  nvidia-smi
  docker info | grep -i runtime
  docker info | grep "Docker Root Dir"
  docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

If the NVIDIA driver was installed for the first time, reboot before running GPU containers:
  reboot

If Docker access fails as ec2-user in the current shell, reconnect or run:
  newgrp docker
EOF

  if [ "$GPU_WORKER_STORAGE_MODE" = "rootdisk" ]; then
    cat <<EOF

Root-disk worker mode is active.
Optional root-disk readiness check:
  MIN_ROOT_FREE_GB=40 ./aws/check_ec2_rootdisk_worker_ready.sh
EOF
  else
    cat <<EOF

EBS-backed worker mode is active.
Also verify:
  df -h ${DOCKER_DATA_MOUNT}
  EXPECTED_DOCKER_DEVICE=${DOCKER_DATA_DEVICE} ./aws/check_ec2_ready.sh
EOF
  fi
}

main() {
  require_root
  install_docker
  if [ "$GPU_WORKER_STORAGE_MODE" = "rootdisk" ]; then
    configure_rootdisk_docker
  else
    mount_docker_disk
    configure_docker_mount_dependency
    configure_docker_data_root
  fi
  install_nvidia_driver
  install_nvidia_container_toolkit
  print_next_steps
}

main "$@"
