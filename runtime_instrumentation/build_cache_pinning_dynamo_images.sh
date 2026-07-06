#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROFILE_SCRIPT="${SCRIPT_DIR}/dynamo_machine_profile.sh"
if [[ -f "${PROFILE_SCRIPT}" ]]; then
  # shellcheck disable=SC1090
  source "${PROFILE_SCRIPT}"
fi
PINNING_PROFILE_SCRIPT="${SCRIPT_DIR}/cache_pinning_profile.sh"
if [[ -f "${PINNING_PROFILE_SCRIPT}" ]]; then
  # shellcheck disable=SC1090
  source "${PINNING_PROFILE_SCRIPT}"
fi

SOURCE_DIR="${SOURCE_DIR:-${CACHE_PINNING_DYNAMO_SOURCE_DIR}}"
FRONTEND_IMAGE_TAG="${FRONTEND_IMAGE_TAG:-${CACHE_PINNING_FRONTEND_IMAGE}}"
WORKER_IMAGE_TAG="${WORKER_IMAGE_TAG:-${CACHE_PINNING_WORKER_IMAGE}}"
SKIP_FRONTEND="${SKIP_FRONTEND:-0}"
SKIP_WORKER="${SKIP_WORKER:-0}"
LEAN_FRONTEND="${LEAN_FRONTEND:-1}"
DOCKER_BUILD_PLATFORM="${DOCKER_BUILD_PLATFORM:-${TARGET_PLATFORM:-}}"
DOCKER_BUILD_LOAD="${DOCKER_BUILD_LOAD:-1}"
DOCKER_BUILD_NO_CACHE="${DOCKER_BUILD_NO_CACHE:-0}"
CACHE_PINNING_EPP_IMAGE="${CACHE_PINNING_EPP_IMAGE:-registry.k8s.io/gateway-api-inference-extension/epp:v0.5.1}"

require_valid_source_repo() {
  if [[ ! -d "${SOURCE_DIR}" ]]; then
    echo "Dynamo source directory not found: ${SOURCE_DIR}" >&2
    echo "Run: ${SCRIPT_DIR}/fetch_cache_pinning_dynamo_source.sh" >&2
    exit 1
  fi
  if [[ ! -d "${SOURCE_DIR}/.git" ]]; then
    echo "Dynamo source directory exists but is not a git clone: ${SOURCE_DIR}" >&2
    exit 1
  fi
  local required_files=(
    "pyproject.toml"
    "Cargo.toml"
    "rust-toolchain.toml"
    "container/render.py"
  )
  local relpath=""
  for relpath in "${required_files[@]}"; do
    if [[ ! -e "${SOURCE_DIR}/${relpath}" ]]; then
      echo "Cache-pinning Dynamo source clone is incomplete: missing ${relpath}" >&2
      exit 1
    fi
  done
}

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
Not enough free disk space to safely build cache-pinning Dynamo images.

Docker root:
  ${docker_root}

Available space:
  ${available_gb} GB

Recommended minimum:
  ${min_free_gb} GB
EOF
  exit 1
}

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

repair_rendered_nats_install_block() {
  local path="${1:-container/rendered.Dockerfile}"
  if [[ ! -f "${path}" ]]; then
    echo "Rendered Dockerfile not found for NATS repair: ${path}" >&2
    exit 1
  fi
  python3 - "${path}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
start = text.find("# Install NATS server\n")
end = text.find("# Install etcd\n", start)
if start < 0 or end < 0:
    raise SystemExit(f"Could not find NATS install block in {path}")
replacement = """# Install NATS server
ARG NATS_VERSION
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \\
    NATS_ARCH="${TARGETARCH:-${ARCH:-}}" && \\
    NATS_ARCH="${NATS_ARCH#linux/}" && \\
    if [ "$NATS_ARCH" = "aarch64" ]; then NATS_ARCH="arm64"; fi && \\
    if [ "$NATS_ARCH" != "amd64" ] && [ "$NATS_ARCH" != "arm64" ]; then \\
        echo "Unsupported NATS arch: $NATS_ARCH" >&2; exit 1; \\
    fi && \\
    wget --tries=3 --waitretry=5 https://github.com/nats-io/nats-server/releases/download/${NATS_VERSION}/nats-server-${NATS_VERSION}-${NATS_ARCH}.deb && \\
    dpkg -i nats-server-${NATS_VERSION}-${NATS_ARCH}.deb && rm nats-server-${NATS_VERSION}-${NATS_ARCH}.deb

"""
updated = text[:start] + replacement + text[end:]
if updated != text:
    path.write_text(updated)
PY
}

repair_rendered_etcd_install_block() {
  local path="${1:-container/rendered.Dockerfile}"
  if [[ ! -f "${path}" ]]; then
    echo "Rendered Dockerfile not found for ETCD repair: ${path}" >&2
    exit 1
  fi
  python3 - "${path}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
start = text.find("# Install etcd\n")
end = text.find("ENV PATH=/usr/local/bin/etcd/:$PATH\n", start)
if start < 0 or end < 0:
    raise SystemExit(f"Could not find etcd install block in {path}")
end += len("ENV PATH=/usr/local/bin/etcd/:$PATH\n")
replacement = """# Install etcd
ARG ETCD_VERSION
RUN ETCD_ARCH="${TARGETARCH:-${ARCH:-}}" && \\
    ETCD_ARCH="${ETCD_ARCH#linux/}" && \\
    if [ "$ETCD_ARCH" = "aarch64" ]; then ETCD_ARCH="arm64"; fi && \\
    if [ "$ETCD_ARCH" != "amd64" ] && [ "$ETCD_ARCH" != "arm64" ]; then \\
        echo "Unsupported ETCD arch: $ETCD_ARCH" >&2; exit 1; \\
    fi && \\
    wget --tries=3 --waitretry=5 https://github.com/etcd-io/etcd/releases/download/$ETCD_VERSION/etcd-$ETCD_VERSION-linux-${ETCD_ARCH}.tar.gz -O /tmp/etcd.tar.gz && \\
    mkdir -p /usr/local/bin/etcd && \\
    tar -xvf /tmp/etcd.tar.gz -C /usr/local/bin/etcd --strip-components=1 && \\
    rm /tmp/etcd.tar.gz
ENV PATH=/usr/local/bin/etcd/:$PATH
"""
updated = text[:start] + replacement + text[end:]
if updated != text:
    path.write_text(updated)
PY
}

require_valid_source_repo
check_build_disk_space

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
  echo "Rendering cache-pinning Dynamo frontend Dockerfile"
  mapfile -t _render_platform_args < <(render_platform_args)
  python3 container/render.py "${_render_platform_args[@]}" --framework=dynamo --target=frontend --output-short-filename
  echo "Applying cache-pinning EPP image override: ${CACHE_PINNING_EPP_IMAGE}"
  CACHE_PINNING_EPP_IMAGE="${CACHE_PINNING_EPP_IMAGE}" python3 - <<'PY'
import os
import re
from pathlib import Path

path = Path("container/rendered.Dockerfile")
text = path.read_text()
new_image = os.environ["CACHE_PINNING_EPP_IMAGE"]
updated = re.sub(
    r"FROM\s+us-central1-docker\.pkg\.dev/k8s-staging-images/gateway-api-inference-extension/epp:[^\s]+ AS epp",
    f"FROM {new_image} AS epp",
    text,
)
if updated == text:
    updated = re.sub(
        r"FROM\s+\$\{EPP_IMAGE\} AS epp",
        f"FROM {new_image} AS epp",
        text,
    )
if updated == text:
    raise SystemExit("Could not find EPP image stage to override in rendered Dockerfile")
path.write_text(updated)
PY
  echo "Normalizing rendered NATS install block for amd64/arm64 asset names"
  repair_rendered_nats_install_block "container/rendered.Dockerfile"
  echo "Normalizing rendered ETCD install block for amd64/arm64 asset names"
  repair_rendered_etcd_install_block "container/rendered.Dockerfile"
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
  echo "Rendering cache-pinning Dynamo SGLang runtime Dockerfile"
  mapfile -t _render_platform_args < <(render_platform_args)
  python3 container/render.py "${_render_platform_args[@]}" --framework=sglang --output-short-filename
  echo "Normalizing rendered NATS install block for amd64/arm64 asset names"
  repair_rendered_nats_install_block "container/rendered.Dockerfile"
  echo "Normalizing rendered ETCD install block for amd64/arm64 asset names"
  repair_rendered_etcd_install_block "container/rendered.Dockerfile"
  build_image "${WORKER_IMAGE_TAG}" "container/rendered.Dockerfile"
fi

cat <<EOF

Cache-pinning images are ready.

Frontend image: ${FRONTEND_IMAGE_TAG}
Worker image:   ${WORKER_IMAGE_TAG}
Build platform: ${DOCKER_BUILD_PLATFORM:-host default}
Machine profile: ${DYNAMO_MACHINE_PROFILE:-default}
Source dir: ${SOURCE_DIR}
EPP image: ${CACHE_PINNING_EPP_IMAGE}
EOF
