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
source "${SCRIPT_DIR}/precise_sglang_helper.sh"
FRONTEND_IMAGE_TAG="${FRONTEND_IMAGE_TAG:-local/dynamo-frontend:runtime-json-logs}"
WORKER_IMAGE_TAG="${WORKER_IMAGE_TAG:-local/dynamo-sglang:runtime-json-logs}"
SKIP_FRONTEND="${SKIP_FRONTEND:-0}"
SKIP_WORKER="${SKIP_WORKER:-0}"
LEAN_FRONTEND="${LEAN_FRONTEND:-0}"
DOCKER_BUILD_PLATFORM="${DOCKER_BUILD_PLATFORM:-${TARGET_PLATFORM:-}}"
DOCKER_BUILD_LOAD="${DOCKER_BUILD_LOAD:-1}"
DOCKER_BUILD_NO_CACHE="${DOCKER_BUILD_NO_CACHE:-0}"

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

require_instrumentation_markers() {
  local required_markers=(
    "components/src/dynamo/common/runtime_logging.py:agent_hint_log_fields"
    "components/src/dynamo/common/runtime_logging.py:_maybe_register_transfer_runtime_event"
    "components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:agent_hint_log_fields"
    "components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:worker.decode.request_received"
    "components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:worker.decode.request_attached"
    "components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:worker.decode.request_completed"
    "components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py:agent_hint_log_fields"
    "components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py:worker.prefill.request_received"
    "components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py:worker.prefill.request_attached"
    "components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py:worker.prefill.request_completed"
    "lib/llm/src/preprocessor.rs:runtime_observability_extra_args_from_nvext"
    "lib/llm/src/preprocessor.rs:cache_control_source"
    "components/src/dynamo/common/runtime_logging.py:cache_control_source"
    "lib/llm/src/protocols/openai/nvext.rs:expected_output_tokens"
    "components/src/dynamo/sglang/init_llm.py:clear_kv_blocks_endpoint = runtime.endpoint("
    "components/src/dynamo/sglang/init_llm.py:clear_kv_blocks_endpoint.serve_endpoint("
    "components/src/dynamo/sglang/request_handlers/handler_base.py:async def clear_kv_blocks"
    "components/src/dynamo/sglang/request_handlers/handler_base.py:flush_cache"
    "components/src/dynamo/sglang/request_handlers/handler_base.py:runtime.register_engine_route(\"clear_kv_blocks\""
  )

  local missing=0
  local file=""
  local pattern=""
  for marker in "${required_markers[@]}"; do
    file="${marker%%:*}"
    pattern="${marker#*:}"
    if ! grep -q "${pattern}" "${SOURCE_DIR}/${file}"; then
      if [[ "${missing}" -eq 0 ]]; then
        echo "Dynamo source is present but not instrumented for runtime JSON logging: ${SOURCE_DIR}" >&2
        echo "Missing required instrumentation markers:" >&2
      fi
      echo "  ${file}: ${pattern}" >&2
      missing=1
    fi
  done

  if [[ "${missing}" -eq 1 ]]; then
    cat >&2 <<EOF

Before building runtime-json-logs images, prepare the Dynamo source:

  cd ${ROOT_DIR}
  ./runtime_instrumentation/prepare_instrumented_dynamo_source.sh

Then rebuild:

  DYN_RUNTIME_JSON_LOGS=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh
EOF
    exit 1
  fi
}

require_valid_source_repo
require_instrumentation_markers

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required but not available on PATH" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not available on PATH" >&2
  exit 1
fi

check_build_disk_space() {
  local docker_root
  docker_root="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
  if [[ -z "${docker_root}" ]]; then
    docker_root="/var/lib/docker"
  fi

  if [[ ! -d "${docker_root}" ]]; then
    return 0
  fi

  local min_free_gb="${MIN_FREE_GB_FOR_DYNAMO_BUILD:-80}"
  local available_kb
  available_kb="$(df -Pk "${docker_root}" | awk 'NR==2 {print $4}')"
  if [[ -z "${available_kb}" || ! "${available_kb}" =~ ^[0-9]+$ ]]; then
    return 0
  fi

  local available_gb=$(( available_kb / 1024 / 1024 ))
  if (( available_gb >= min_free_gb )); then
    return 0
  fi

  cat >&2 <<EOF
Not enough free disk space to safely build instrumented Dynamo images.

Docker root:
  ${docker_root}

Available space:
  ${available_gb} GB

Recommended minimum:
  ${min_free_gb} GB

This build can fail with:
  failed to solve: ... no space left on device

Suggested recovery:

  cd ${ROOT_DIR}
  ./run_dynamo_single_host.sh stop || true
  df -h ${docker_root}
  docker system df
  docker container prune -f
  docker image prune -f
  docker builder prune -f

If you still do not have enough space and do not need old Docker state:

  docker system prune -af
  docker builder prune -af

Then retry the build.
EOF
  exit 1
}

check_build_disk_space

build_image() {
  local tag="$1"
  local dockerfile="$2"

  if [[ -n "${DOCKER_BUILD_PLATFORM}" ]]; then
    if docker buildx version >/dev/null 2>&1; then
      local cmd=(docker buildx build)
      if [[ "${DOCKER_BUILD_LOAD}" == "1" ]]; then
        cmd+=(--load)
      fi
      if [[ "${DOCKER_BUILD_NO_CACHE}" == "1" ]]; then
        cmd+=(--no-cache)
      fi
      cmd+=(--platform "${DOCKER_BUILD_PLATFORM}" -f "${dockerfile}" -t "${tag}" .)
      echo "Building ${tag} for platform ${DOCKER_BUILD_PLATFORM} via docker buildx"
      "${cmd[@]}"
      return
    fi

    echo "Building ${tag} for platform ${DOCKER_BUILD_PLATFORM} via docker build"
    if [[ "${DOCKER_BUILD_NO_CACHE}" == "1" ]]; then
      docker build --no-cache --platform "${DOCKER_BUILD_PLATFORM}" -f "${dockerfile}" -t "${tag}" .
    else
      docker build --platform "${DOCKER_BUILD_PLATFORM}" -f "${dockerfile}" -t "${tag}" .
    fi
    return
  fi

  echo "Building ${tag}"
  if [[ "${DOCKER_BUILD_NO_CACHE}" == "1" ]]; then
    docker build --no-cache -f "${dockerfile}" -t "${tag}" .
  else
    docker build -f "${dockerfile}" -t "${tag}" .
  fi
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

STAMP_PATH="$(precise_runtime_stamp_path "${DYNAMO_MACHINE_PROFILE:-default}")"
mkdir -p "$(dirname "${STAMP_PATH}")"
{
  echo "machine_profile=${DYNAMO_MACHINE_PROFILE:-default}"
  echo "frontend_image=${FRONTEND_IMAGE_TAG}"
  echo "worker_image=${WORKER_IMAGE_TAG}"
  echo "source_dir=${SOURCE_DIR}"
  echo "source_signature=$(precise_dynamo_source_signature "${SOURCE_DIR}")"
  echo "built_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "${STAMP_PATH}"

cat <<EOF

Instrumented images are ready.

Frontend image: ${FRONTEND_IMAGE_TAG}
Worker image:   ${WORKER_IMAGE_TAG}
Build platform: ${DOCKER_BUILD_PLATFORM:-host default}
Machine profile: ${DYNAMO_MACHINE_PROFILE:-default}
Runtime stamp:  ${STAMP_PATH}

Example single-host run:
  cd ${ROOT_DIR}
  DYN_RUNTIME_JSON_LOGS=1 \\
  FRONTEND_IMAGE=${FRONTEND_IMAGE_TAG} \\
  WORKER_IMAGE=${WORKER_IMAGE_TAG} \\
  ./run_dynamo_single_host.sh start
EOF
