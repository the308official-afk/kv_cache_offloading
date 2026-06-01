#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SGLANG_IMAGE="${SGLANG_IMAGE:-${WORKER_IMAGE:-nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.2}}"
SGLANG_CONTAINER="${SGLANG_CONTAINER:-}"
DEST_ROOT="${DEST_ROOT:-${REPO_ROOT}/upstream/sglang}"
DEST_PACKAGE_DIR="${DEST_PACKAGE_DIR:-${DEST_ROOT}/python/sglang}"

usage() {
  cat <<EOF
Usage: $0

Extract the installed Python sglang package from the worker image into the repo.

Environment:
  SGLANG_IMAGE      Default: ${SGLANG_IMAGE}
  SGLANG_CONTAINER  Default: ${SGLANG_CONTAINER:-<unset>} (optional existing container name)
  DEST_ROOT         Default: ${DEST_ROOT}
  DEST_PACKAGE_DIR  Default: ${DEST_PACKAGE_DIR}

Example:
  SGLANG_IMAGE=nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.2 $0
EOF
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed or not on PATH." >&2
  exit 1
fi

tmp_container=""
cleanup() {
  if [[ -n "${tmp_container}" ]]; then
    docker rm -f "${tmp_container}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

resolve_probe='
import importlib.util
import pathlib
import sys

spec = importlib.util.find_spec("sglang")
if spec is not None and spec.submodule_search_locations:
    print(pathlib.Path(list(spec.submodule_search_locations)[0]).resolve())
    raise SystemExit(0)

for raw_root in sys.path:
    if not raw_root:
        continue
    root = pathlib.Path(raw_root)
    candidate = root / "sglang" / "__init__.py"
    if candidate.exists():
        print(candidate.parent.resolve())
        raise SystemExit(0)

search_roots = [
    pathlib.Path("/workspace"),
    pathlib.Path("/usr/local/lib"),
    pathlib.Path("/usr/lib"),
    pathlib.Path("/opt"),
]
for root in search_roots:
    if not root.exists():
        continue
    for candidate in root.rglob("sglang/__init__.py"):
        print(candidate.parent.resolve())
        raise SystemExit(0)

raise SystemExit("Could not find sglang package via importlib, sys.path, or filesystem fallback")
'

if [[ -n "${SGLANG_CONTAINER}" ]]; then
  echo "Resolving installed sglang package path in container: ${SGLANG_CONTAINER}" >&2
  if ! package_path="$(docker exec -i "${SGLANG_CONTAINER}" python3 -c "${resolve_probe}")"; then
    echo "Could not resolve sglang package path in container ${SGLANG_CONTAINER}." >&2
    exit 1
  fi
else
  echo "Resolving installed sglang package path in image: ${SGLANG_IMAGE}" >&2
  if ! package_path="$(docker run --rm --entrypoint python3 "${SGLANG_IMAGE}" -c "${resolve_probe}")"; then
    echo "Could not resolve sglang package path in image ${SGLANG_IMAGE}." >&2
    exit 1
  fi
fi

if [[ -z "${package_path}" ]]; then
  echo "Could not resolve sglang package path." >&2
  exit 1
fi

echo "Package path: ${package_path}" >&2
echo "Destination: ${DEST_PACKAGE_DIR}" >&2

mkdir -p "${DEST_ROOT}/python"
rm -rf "${DEST_PACKAGE_DIR}"

package_parent="$(dirname "${package_path}")"
package_name="$(basename "${package_path}")"
tar_excludes=(
  "--exclude=${package_name}/srt/mem_cache/cpp_radix_tree/.clang-format"
)

if [[ -n "${SGLANG_CONTAINER}" ]]; then
  docker exec -i "${SGLANG_CONTAINER}" \
    tar -C "${package_parent}" "${tar_excludes[@]}" -cf - "${package_name}" | \
    tar -C "${DEST_ROOT}/python" -xf -
else
  tmp_container="$(docker create --entrypoint sleep "${SGLANG_IMAGE}" infinity)"
  docker start "${tmp_container}" >/dev/null
  docker exec -i "${tmp_container}" \
    tar -C "${package_parent}" "${tar_excludes[@]}" -cf - "${package_name}" | \
    tar -C "${DEST_ROOT}/python" -xf -
fi

if [[ ! -f "${DEST_PACKAGE_DIR}/__init__.py" ]]; then
  echo "Extraction did not create expected package: ${DEST_PACKAGE_DIR}/__init__.py" >&2
  exit 1
fi

cat > "${DEST_ROOT}/SOURCE_IMAGE.txt" <<EOF
image=${SGLANG_IMAGE}
container=${SGLANG_CONTAINER}
EOF

find "${DEST_PACKAGE_DIR}" -name 'memory_pool_host.py' -print > "${DEST_ROOT}/TARGET_FILES.txt" || true
find "${DEST_PACKAGE_DIR}" -name 'cache_controller.py' -print >> "${DEST_ROOT}/TARGET_FILES.txt" || true
find "${DEST_PACKAGE_DIR}" -name 'hicache_storage.py' -print >> "${DEST_ROOT}/TARGET_FILES.txt" || true
find "${DEST_PACKAGE_DIR}" -name 'hiradix_cache.py' -print >> "${DEST_ROOT}/TARGET_FILES.txt" || true
find "${DEST_PACKAGE_DIR}" -name 'bench_serving.py' -print >> "${DEST_ROOT}/TARGET_FILES.txt" || true

echo "Extracted sglang source to ${DEST_PACKAGE_DIR}" >&2
echo "Potential instrumentation targets:" >&2
sed 's/^/  /' "${DEST_ROOT}/TARGET_FILES.txt" >&2
