#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-${ROOT_DIR}/upstream/dynamo}"
SOURCE_REPO="${SOURCE_REPO:-https://github.com/ai-dynamo/dynamo.git}"

mkdir -p "$(dirname "${SOURCE_DIR}")"

if [[ -d "${SOURCE_DIR}" && ! -d "${SOURCE_DIR}/.git" ]]; then
  echo "Existing source directory is not a git clone: ${SOURCE_DIR}" >&2
  echo "It is likely a partial copy or failed earlier attempt." >&2
  echo "Remove it and rerun:" >&2
  echo "  rm -rf ${SOURCE_DIR}" >&2
  echo "  ${BASH_SOURCE[0]}" >&2
  exit 1
fi

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
