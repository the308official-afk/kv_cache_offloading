#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-${ROOT_DIR}/runtime_upstream/dynamo}"
PATCH_FILE="${PATCH_FILE:-${SCRIPT_DIR}/patches/dynamo_preserve_agent_hints_to_worker.patch}"

if [[ ! -d "${SOURCE_DIR}/.git" ]]; then
  echo "Dynamo source repo not found at ${SOURCE_DIR}" >&2
  echo "Run: ${SCRIPT_DIR}/fetch_dynamo_source.sh" >&2
  exit 1
fi

if [[ ! -f "${PATCH_FILE}" ]]; then
  echo "Patch file not found: ${PATCH_FILE}" >&2
  exit 1
fi

if git -C "${SOURCE_DIR}" apply --check "${PATCH_FILE}" >/dev/null 2>&1; then
  git -C "${SOURCE_DIR}" apply "${PATCH_FILE}"
  echo "Applied Dynamo agent-hint preservation patch to ${SOURCE_DIR}"
  exit 0
fi

if git -C "${SOURCE_DIR}" apply --reverse --check "${PATCH_FILE}" >/dev/null 2>&1; then
  echo "Dynamo agent-hint preservation patch is already applied in ${SOURCE_DIR}"
  exit 0
fi

echo "Patch could not be applied cleanly to ${SOURCE_DIR}" >&2
echo "Check whether the upstream source version drifted from the patch target." >&2
exit 1
