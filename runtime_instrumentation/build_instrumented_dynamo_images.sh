#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-${ROOT_DIR}/upstream/dynamo}"
PROFILE_SCRIPT="${SCRIPT_DIR}/dynamo_machine_profile.sh"
if [[ -f "${PROFILE_SCRIPT}" ]]; then
  # shellcheck disable=SC1090
  source "${PROFILE_SCRIPT}"
fi
FRONTEND_IMAGE_TAG="${FRONTEND_IMAGE_TAG:-local/dynamo-frontend:runtime-json-logs}"
WORKER_IMAGE_TAG="${WORKER_IMAGE_TAG:-local/dynamo-sglang:runtime-json-logs}"
SKIP_FRONTEND="${SKIP_FRONTEND:-0}"
SKIP_WORKER="${SKIP_WORKER:-0}"
LEAN_FRONTEND="${LEAN_FRONTEND:-0}"
DOCKER_BUILD_PLATFORM="${DOCKER_BUILD_PLATFORM:-${TARGET_PLATFORM:-}}"
DOCKER_BUILD_LOAD="${DOCKER_BUILD_LOAD:-1}"

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

build_image() {
  local tag="$1"
  local dockerfile="$2"

  if [[ -n "${DOCKER_BUILD_PLATFORM}" ]]; then
    if docker buildx version >/dev/null 2>&1; then
      local cmd=(docker buildx build)
      if [[ "${DOCKER_BUILD_LOAD}" == "1" ]]; then
        cmd+=(--load)
      fi
      cmd+=(--platform "${DOCKER_BUILD_PLATFORM}" -f "${dockerfile}" -t "${tag}" .)
      echo "Building ${tag} for platform ${DOCKER_BUILD_PLATFORM} via docker buildx"
      "${cmd[@]}"
      return
    fi

    echo "Building ${tag} for platform ${DOCKER_BUILD_PLATFORM} via docker build"
    docker build --platform "${DOCKER_BUILD_PLATFORM}" -f "${dockerfile}" -t "${tag}" .
    return
  fi

  echo "Building ${tag}"
  docker build -f "${dockerfile}" -t "${tag}" .
}

render_platform_args() {
  if [[ -n "${DOCKER_BUILD_PLATFORM}" ]]; then
    printf '%s\n' "--platform" "${DOCKER_BUILD_PLATFORM}"
  fi
}

cd "${SOURCE_DIR}"

if [[ "${SKIP_FRONTEND}" != "1" ]]; then
  echo "Rendering Dynamo frontend Dockerfile"
  mapfile -t _render_platform_args < <(render_platform_args)
  python3 container/render.py "${_render_platform_args[@]}" --framework=dynamo --target=frontend --output-short-filename
  if [[ "${LEAN_FRONTEND}" == "1" ]]; then
    echo "Applying lean frontend Dockerfile adjustment: skip benchmark package install"
    python3 - <<'PY'
from pathlib import Path

path = Path("container/rendered.Dockerfile")
text = path.read_text()
old = """    if [ "$ENABLE_KVBM" = "true" ]; then \\
        KVBM_WHEEL=$(ls /opt/dynamo/wheelhouse/kvbm*.whl 2>/dev/null | head -1); \\
        if [ -z "$KVBM_WHEEL" ]; then \\
            echo "ERROR: ENABLE_KVBM is true but no KVBM wheel found in wheelhouse" >&2; \\
            exit 1; \\
        fi; \\
        uv pip install "$KVBM_WHEEL"; \\
    fi && \\
    cd /workspace/benchmarks && \\
    export UV_GIT_LFS=1 UV_HTTP_TIMEOUT=300 UV_HTTP_RETRIES=5 && \\
    uv pip install .
"""
new = """    if [ "$ENABLE_KVBM" = "true" ]; then \\
        KVBM_WHEEL=$(ls /opt/dynamo/wheelhouse/kvbm*.whl 2>/dev/null | head -1); \\
        if [ -z "$KVBM_WHEEL" ]; then \\
            echo "ERROR: ENABLE_KVBM is true but no KVBM wheel found in wheelhouse" >&2; \\
            exit 1; \\
        fi; \\
        uv pip install "$KVBM_WHEEL"; \\
    fi
"""
if old not in text:
    raise SystemExit("Could not find frontend benchmark install block in rendered Dockerfile")
path.write_text(text.replace(old, new))
PY
  fi
  build_image "${FRONTEND_IMAGE_TAG}" "container/rendered.Dockerfile"
fi

if [[ "${SKIP_WORKER}" != "1" ]]; then
  echo "Rendering Dynamo SGLang runtime Dockerfile"
  mapfile -t _render_platform_args < <(render_platform_args)
  python3 container/render.py "${_render_platform_args[@]}" --framework=sglang --output-short-filename
  build_image "${WORKER_IMAGE_TAG}" "container/rendered.Dockerfile"
fi

cat <<EOF

Instrumented images are ready.

Frontend image: ${FRONTEND_IMAGE_TAG}
Worker image:   ${WORKER_IMAGE_TAG}
Build platform: ${DOCKER_BUILD_PLATFORM:-host default}
Machine profile: ${DYNAMO_MACHINE_PROFILE:-default}

Example single-host run:
  cd ${ROOT_DIR}
  DYN_RUNTIME_JSON_LOGS=1 \\
  FRONTEND_IMAGE=${FRONTEND_IMAGE_TAG} \\
  WORKER_IMAGE=${WORKER_IMAGE_TAG} \\
  ./run_dynamo_single_host.sh start
EOF
