#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-${ROOT_DIR}/runtime_upstream/dynamo}"
FRONTEND_IMAGE_TAG="${FRONTEND_IMAGE_TAG:-local/dynamo-frontend:runtime-json-logs}"
WORKER_IMAGE_TAG="${WORKER_IMAGE_TAG:-local/dynamo-sglang:runtime-json-logs}"
SKIP_FRONTEND="${SKIP_FRONTEND:-0}"
SKIP_WORKER="${SKIP_WORKER:-0}"

require_valid_source_repo() {
  if [[ ! -d "${SOURCE_DIR}" ]]; then
    echo "Dynamo source directory not found: ${SOURCE_DIR}" >&2
    echo "Run: ${SCRIPT_DIR}/fetch_dynamo_source.sh" >&2
    exit 1
  fi

  if [[ ! -d "${SOURCE_DIR}/.git" ]]; then
    echo "Dynamo source directory exists but is not a git clone: ${SOURCE_DIR}" >&2
    echo "It is likely a partial copy or failed earlier attempt." >&2
    echo "Remove it and rerun:" >&2
    echo "  rm -rf ${SOURCE_DIR}" >&2
    echo "  ${SCRIPT_DIR}/fetch_dynamo_source.sh" >&2
    exit 1
  fi

  local required_files=(
    "pyproject.toml"
    "Cargo.toml"
    "rust-toolchain.toml"
    "container/render.py"
  )

  local missing=0
  for relpath in "${required_files[@]}"; do
    if [[ ! -e "${SOURCE_DIR}/${relpath}" ]]; then
      if [[ "${missing}" -eq 0 ]]; then
        echo "Dynamo source clone is incomplete: ${SOURCE_DIR}" >&2
        echo "Missing required files:" >&2
      fi
      echo "  ${relpath}" >&2
      missing=1
    fi
  done

  if [[ "${missing}" -eq 1 ]]; then
    echo "Recreate the source clone and rerun:" >&2
    echo "  rm -rf ${SOURCE_DIR}" >&2
    echo "  ${SCRIPT_DIR}/fetch_dynamo_source.sh" >&2
    exit 1
  fi
}

require_valid_source_repo

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required but not available on PATH" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not available on PATH" >&2
  exit 1
fi

cd "${SOURCE_DIR}"

if [[ "${SKIP_FRONTEND}" != "1" ]]; then
  echo "Rendering Dynamo frontend Dockerfile"
  python3 container/render.py --framework=dynamo --target=frontend --output-short-filename
  echo "Building ${FRONTEND_IMAGE_TAG}"
  docker build -f container/rendered.Dockerfile -t "${FRONTEND_IMAGE_TAG}" .
fi

if [[ "${SKIP_WORKER}" != "1" ]]; then
  echo "Rendering Dynamo SGLang runtime Dockerfile"
  python3 container/render.py --framework=sglang --output-short-filename
  echo "Building ${WORKER_IMAGE_TAG}"
  docker build -f container/rendered.Dockerfile -t "${WORKER_IMAGE_TAG}" .
fi

cat <<EOF

Instrumented images are ready.

Frontend image: ${FRONTEND_IMAGE_TAG}
Worker image:   ${WORKER_IMAGE_TAG}

Example single-host run:
  cd ${ROOT_DIR}
  DYN_RUNTIME_JSON_LOGS=1 \\
  FRONTEND_IMAGE=${FRONTEND_IMAGE_TAG} \\
  WORKER_IMAGE=${WORKER_IMAGE_TAG} \\
  ./run_dynamo_single_host.sh start
EOF
