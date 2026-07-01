#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-}"
BUILD_IF_MISSING="${AUTO_BUILD_PRECISE_IMAGES:-0}"

usage() {
  cat <<EOF
Usage:
  $0 [--machine-profile ec2|gh200] [--build-if-missing]

Ensures the machine-specific instrumented Dynamo images are selected and
available for precise experiments.

Examples:
  DYNAMO_MACHINE_PROFILE=ec2 $0
  $0 --machine-profile gh200 --build-if-missing
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --machine-profile)
      MACHINE_PROFILE="${2:-}"
      shift 2
      ;;
    --build-if-missing)
      BUILD_IF_MISSING=1
      shift
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

if [[ -n "${MACHINE_PROFILE}" ]]; then
  export DYNAMO_MACHINE_PROFILE="${MACHINE_PROFILE}"
fi

if [[ -z "${DYNAMO_MACHINE_PROFILE:-}" ]]; then
  cat >&2 <<EOF
Machine profile is required.

Set one of:
  export DYNAMO_MACHINE_PROFILE=ec2
  export DYNAMO_MACHINE_PROFILE=gh200

or pass:
  $0 --machine-profile ec2
EOF
  exit 1
fi

source runtime_instrumentation/dynamo_machine_profile.sh
source runtime_instrumentation/precise_sglang_helper.sh

SOURCE_READY=0
if [[ "${BUILD_IF_MISSING}" = "1" ]]; then
  DYNAMO_ROOT="$(resolve_precise_dynamo_root || true)"
  if [[ -n "${DYNAMO_ROOT}" ]] && _precise_dynamo_require_markers "${DYNAMO_ROOT}" runtime; then
    SOURCE_READY=1
  else
    echo "Preparing instrumented Dynamo source..."
    ./runtime_instrumentation/prepare_instrumented_dynamo_source.sh
    DYNAMO_ROOT="$(resolve_precise_dynamo_root || true)"
    if [[ -n "${DYNAMO_ROOT}" ]] && _precise_dynamo_require_markers "${DYNAMO_ROOT}" runtime; then
      SOURCE_READY=1
    fi
  fi
fi

if [[ -z "${FRONTEND_IMAGE:-}" || -z "${WORKER_IMAGE:-}" ]]; then
  cat >&2 <<EOF
Could not resolve FRONTEND_IMAGE / WORKER_IMAGE.

Set a machine profile first, for example:
  export DYNAMO_MACHINE_PROFILE=ec2
  source runtime_instrumentation/dynamo_machine_profile.sh

or pass:
  $0 --machine-profile ec2
EOF
  exit 1
fi

echo "Using machine profile: ${DYNAMO_MACHINE_PROFILE:-default}"
echo "FRONTEND_IMAGE=${FRONTEND_IMAGE}"
echo "WORKER_IMAGE=${WORKER_IMAGE}"

frontend_ok=0
worker_ok=0
if docker image inspect "${FRONTEND_IMAGE}" >/dev/null 2>&1; then
  frontend_ok=1
  echo "frontend image ok"
fi
if docker image inspect "${WORKER_IMAGE}" >/dev/null 2>&1; then
  worker_ok=1
  echo "worker image ok"
fi

STAMP_PATH="$(precise_runtime_stamp_path "${DYNAMO_MACHINE_PROFILE:-default}")"
STAMP_OK=0
CURRENT_SOURCE_SIGNATURE=""
STAMP_SOURCE_SIGNATURE=""
if [[ "${SOURCE_READY}" -eq 1 ]]; then
  CURRENT_SOURCE_SIGNATURE="$(precise_dynamo_source_signature "${DYNAMO_ROOT}")"
  if [[ -f "${STAMP_PATH}" ]]; then
    STAMP_SOURCE_SIGNATURE="$(grep '^source_signature=' "${STAMP_PATH}" | head -1 | cut -d= -f2- || true)"
    if [[ -n "${STAMP_SOURCE_SIGNATURE}" && "${STAMP_SOURCE_SIGNATURE}" = "${CURRENT_SOURCE_SIGNATURE}" ]]; then
      STAMP_OK=1
    fi
  fi
fi

if [[ "${frontend_ok}" -eq 1 && "${worker_ok}" -eq 1 && ( "${SOURCE_READY}" -eq 0 || "${STAMP_OK}" -eq 1 ) ]]; then
  precise_banner_numbered 1 6 "PRECISE RUNTIME IMAGE READY (the machine-specific Dynamo images are there)"
  exit 0
fi

if [[ "${BUILD_IF_MISSING}" != "1" ]]; then
  cat >&2 <<EOF
Missing machine-specific instrumented runtime images.

Expected:
  FRONTEND_IMAGE=${FRONTEND_IMAGE}
  WORKER_IMAGE=${WORKER_IMAGE}

Machine profile:
  ${DYNAMO_MACHINE_PROFILE:-default}

Runtime stamp:
  ${STAMP_PATH}

Either build them manually:
  ./runtime_instrumentation/prepare_instrumented_dynamo_source.sh
  LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh

or rerun with automatic build enabled:
  $0 --machine-profile ${DYNAMO_MACHINE_PROFILE:-ec2} --build-if-missing
EOF
  exit 1
fi

if [[ "${SOURCE_READY}" -eq 1 && "${frontend_ok}" -eq 1 && "${worker_ok}" -eq 1 && "${STAMP_OK}" -ne 1 ]]; then
  echo "Existing precise runtime images were not built from the current instrumented Dynamo source."
  echo "Current source signature: ${CURRENT_SOURCE_SIGNATURE}"
  echo "Stamped source signature: ${STAMP_SOURCE_SIGNATURE:-<missing>}"
fi

precise_banner "PRECISE IMAGE BUILD START (building machine-specific Dynamo images; plain Docker logs are expected while output is captured)"
echo "Build reason: precise runtime images are missing or stale for the current instrumented source."
echo "Building machine-specific instrumented Dynamo images..."
LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
  ./runtime_instrumentation/build_instrumented_dynamo_images.sh
precise_banner "PRECISE IMAGE BUILD DONE (machine-specific Dynamo images finished building)"

docker image inspect "${FRONTEND_IMAGE}" >/dev/null 2>&1 || {
  echo "Failed to build frontend image: ${FRONTEND_IMAGE}" >&2
  exit 1
}
docker image inspect "${WORKER_IMAGE}" >/dev/null 2>&1 || {
  echo "Failed to build worker image: ${WORKER_IMAGE}" >&2
  exit 1
}

echo "frontend image ok"
echo "worker image ok"
precise_banner_numbered 1 6 "PRECISE RUNTIME IMAGE READY (the machine-specific Dynamo images are there)"
