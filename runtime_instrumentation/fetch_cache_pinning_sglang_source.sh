#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE_SCRIPT="${ROOT_DIR}/runtime_instrumentation/cache_pinning_profile.sh"
if [[ -f "${PROFILE_SCRIPT}" ]]; then
  # shellcheck disable=SC1090
  source "${PROFILE_SCRIPT}"
fi

SOURCE_DIR="${SOURCE_DIR:-${CACHE_PINNING_SGLANG_SOURCE_DIR}}"
SOURCE_REPO="${SOURCE_REPO:-${CACHE_PINNING_SGLANG_SOURCE_REPO}}"
SOURCE_REF="${SOURCE_REF:-${CACHE_PINNING_SGLANG_SOURCE_REF}}"
PULL_REF="${PULL_REF:-${CACHE_PINNING_SGLANG_PULL_REF}}"

mkdir -p "$(dirname "${SOURCE_DIR}")"

if [[ -d "${SOURCE_DIR}" && ! -d "${SOURCE_DIR}/.git" ]]; then
  echo "Existing source directory is not a git clone: ${SOURCE_DIR}" >&2
  echo "Remove it and rerun." >&2
  exit 1
fi

if [[ -d "${SOURCE_DIR}/.git" ]]; then
  if ! git -C "${SOURCE_DIR}" diff --quiet --ignore-submodules=all; then
    echo "Existing cache-pinning SGLang clone is dirty: ${SOURCE_DIR}" >&2
    exit 1
  fi
  echo "Updating cache-pinning SGLang source clone at ${SOURCE_DIR}"
  git -C "${SOURCE_DIR}" fetch --all --tags
else
  echo "Cloning ${SOURCE_REPO} into ${SOURCE_DIR}"
  GIT_LFS_SKIP_SMUDGE=1 git clone "${SOURCE_REPO}" "${SOURCE_DIR}"
fi

echo "Fetching pull/${PULL_REF}/head for cache-pinning validation"
git -C "${SOURCE_DIR}" fetch origin "pull/${PULL_REF}/head:refs/remotes/origin/cache_pinning_pr_${PULL_REF}"
git -C "${SOURCE_DIR}" checkout --detach "${SOURCE_REF}"

if [[ ! -f "${SOURCE_DIR}/python/sglang/__init__.py" ]]; then
  echo "Expected Python package not found: ${SOURCE_DIR}/python/sglang/__init__.py" >&2
  exit 1
fi

cat > "${SOURCE_DIR}/CACHE_PINNING_SOURCE_REF.txt" <<EOF
repo=${SOURCE_REPO}
pull_ref=${PULL_REF}
ref=${SOURCE_REF}
checked_out_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

echo
echo "Cache-pinning SGLang source is ready at:"
echo "  ${SOURCE_DIR}"
echo "Pinned ref:"
echo "  ${SOURCE_REF}"
