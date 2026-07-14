#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
AGENTBENCH_DEEPAGENTS_AUTO_INSTALL="${AGENTBENCH_DEEPAGENTS_AUTO_INSTALL:-1}"
AGENTBENCH_DEEPAGENTS_REPO_URL="${AGENTBENCH_DEEPAGENTS_REPO_URL:-https://github.com/langchain-ai/deepagents.git}"
AGENTBENCH_DEEPAGENTS_REF="${AGENTBENCH_DEEPAGENTS_REF:-2cf7e25dbb40e783d9d4d545c29e595800bf314f}"
AGENTBENCH_DEEPAGENTS_DIR="${AGENTBENCH_DEEPAGENTS_DIR:-upstream/deepagents}"
AGENTBENCH_DEEPAGENTS_PACKAGE_DIR="${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR:-${AGENTBENCH_DEEPAGENTS_DIR}/libs/deepagents}"
AGENTBENCH_REQUIREMENTS_FILE="${AGENTBENCH_REQUIREMENTS_FILE:-agentbench/requirements.txt}"

echo "Checking Deep Agents dependency..."
echo "Deep Agents dir: ${AGENTBENCH_DEEPAGENTS_DIR}"
echo "Deep Agents ref: ${AGENTBENCH_DEEPAGENTS_REF}"
echo "Auto install: ${AGENTBENCH_DEEPAGENTS_AUTO_INSTALL}"

if [[ "${AGENTBENCH_DEEPAGENTS_AUTO_INSTALL}" != "1" ]]; then
  if [[ ! -f "${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR}/pyproject.toml" ]]; then
    echo "Deep Agents source is missing and AGENTBENCH_DEEPAGENTS_AUTO_INSTALL=0." >&2
    echo "Missing: ${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR}/pyproject.toml" >&2
    exit 1
  fi
  echo "Deep Agents source exists."
  exit 0
fi

mkdir -p "$(dirname "${AGENTBENCH_DEEPAGENTS_DIR}")"

if [[ ! -d "${AGENTBENCH_DEEPAGENTS_DIR}/.git" ]]; then
  if [[ -e "${AGENTBENCH_DEEPAGENTS_DIR}" ]]; then
    echo "Deep Agents path exists but is not a git checkout: ${AGENTBENCH_DEEPAGENTS_DIR}" >&2
    echo "Move or remove it, then retry." >&2
    exit 1
  fi
  echo "Deep Agents source missing; cloning..."
  git clone "${AGENTBENCH_DEEPAGENTS_REPO_URL}" "${AGENTBENCH_DEEPAGENTS_DIR}"
else
  echo "Deep Agents git checkout exists; refreshing refs..."
fi

git -C "${AGENTBENCH_DEEPAGENTS_DIR}" fetch origin
git -C "${AGENTBENCH_DEEPAGENTS_DIR}" checkout "${AGENTBENCH_DEEPAGENTS_REF}"

if [[ ! -f "${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR}/pyproject.toml" ]]; then
  echo "Deep Agents package pyproject is missing after checkout." >&2
  echo "Expected: ${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR}/pyproject.toml" >&2
  exit 1
fi

echo "Installing Deep Agents package..."
"${PYTHON_BIN}" -m pip install "${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR}"

if [[ -f "${AGENTBENCH_REQUIREMENTS_FILE}" ]]; then
  echo "Installing AgentBench Python requirements..."
  "${PYTHON_BIN}" -m pip install -r "${AGENTBENCH_REQUIREMENTS_FILE}"
fi

echo "Verifying Deep Agents import..."
"${PYTHON_BIN}" - <<'PY'
import deepagents
print("deepagents:", deepagents.__file__)
PY

echo "Deep Agents ready."
