#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-${ROOT_DIR}/runtime_upstream/dynamo}"
SOURCE_REPO="${SOURCE_REPO:-https://github.com/ai-dynamo/dynamo.git}"

mkdir -p "$(dirname "${SOURCE_DIR}")"

if [[ -d "${SOURCE_DIR}/.git" ]]; then
  if ! git -C "${SOURCE_DIR}" diff --quiet --ignore-submodules=all; then
    echo "Existing Dynamo source clone is dirty: ${SOURCE_DIR}" >&2
    echo "Refusing to pull on top of local changes." >&2
    echo "If this clone already has the runtime instrumentation patch, keep it as-is or reset it intentionally." >&2
    exit 1
  fi

  echo "Updating existing Dynamo source clone at ${SOURCE_DIR}"
  git -C "${SOURCE_DIR}" fetch --all --tags
  git -C "${SOURCE_DIR}" pull --ff-only
else
  echo "Cloning ${SOURCE_REPO} into ${SOURCE_DIR}"
  GIT_LFS_SKIP_SMUDGE=1 git clone "${SOURCE_REPO}" "${SOURCE_DIR}"
fi

echo
echo "Dynamo source is ready at:"
echo "  ${SOURCE_DIR}"
