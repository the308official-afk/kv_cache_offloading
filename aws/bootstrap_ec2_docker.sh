#!/bin/bash

set -euo pipefail

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script with sudo."
    exit 1
  fi
}

install_docker() {
  dnf install -y docker
  systemctl enable docker
  systemctl start docker
}

enable_ec2_user_docker_access() {
  usermod -aG docker ec2-user || true
}

print_next_steps() {
  cat <<EOF
Docker bootstrap completed.

Recommended next steps:
  newgrp docker
  docker info

If docker access still fails in the current shell, log out and SSH back in.
EOF
}

main() {
  require_root
  install_docker
  enable_ec2_user_docker_access
  print_next_steps
}

main "$@"
