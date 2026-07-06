#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

PRECISE_START_MODE="${PRECISE_START_MODE:-clean}"
LABEL="precise experiment"
WORKER_CONTAINER_NAME="${WORKER_CONTAINER_NAME:-dynamo-sglang-worker}"
FRONTEND_CONTAINER_NAME="${FRONTEND_CONTAINER_NAME:-dynamo-frontend}"
ETCD_CONTAINER_NAME="${ETCD_CONTAINER_NAME:-dynamo-etcd}"
NATS_CONTAINER_NAME="${NATS_CONTAINER_NAME:-dynamo-nats}"

usage() {
  cat <<EOF
Usage:
  $0 [--label TEXT] [--mode clean|reuse]

Environment:
  PRECISE_START_MODE   Default: clean

Behavior:
  clean  stop and remove any old Dynamo runtime before the experiment begins
  reuse  skip the automatic clean-start step
EOF
}

banner() {
  cat <<EOF
========================================
$1
========================================
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --label)
      LABEL="${2:-}"
      shift 2
      ;;
    --mode)
      PRECISE_START_MODE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "${PRECISE_START_MODE}" in
  clean)
    ;;
  reuse|none|skip)
    echo "Skipping automatic clean-start for ${LABEL} (PRECISE_START_MODE=${PRECISE_START_MODE})."
    exit 0
    ;;
  *)
    echo "Unknown PRECISE_START_MODE: ${PRECISE_START_MODE}" >&2
    echo "Valid values: clean reuse none skip" >&2
    exit 2
    ;;
esac

banner "PRECISE CLEAN START ACTIVE (clearing any old runtime before ${LABEL})"

./run_dynamo_single_host.sh stop >/dev/null 2>&1 || true

if command -v docker >/dev/null 2>&1; then
  docker rm -f \
    "${WORKER_CONTAINER_NAME}" \
    "${FRONTEND_CONTAINER_NAME}" \
    "${ETCD_CONTAINER_NAME}" \
    "${NATS_CONTAINER_NAME}" \
    >/dev/null 2>&1 || true
fi

./runtime_instrumentation/reset_experiment_state.sh clear-active >/dev/null 2>&1 || true

banner "PRECISE CLEAN START READY (old runtime cleared before ${LABEL})"
