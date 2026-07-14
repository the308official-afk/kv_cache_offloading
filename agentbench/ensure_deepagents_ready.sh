#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
AGENTBENCH_DEEPAGENTS_AUTO_INSTALL="${AGENTBENCH_DEEPAGENTS_AUTO_INSTALL:-1}"
AGENTBENCH_DEEPAGENTS_FORCE_REFRESH="${AGENTBENCH_DEEPAGENTS_FORCE_REFRESH:-0}"
AGENTBENCH_DEEPAGENTS_FORCE_REINSTALL="${AGENTBENCH_DEEPAGENTS_FORCE_REINSTALL:-0}"
AGENTBENCH_DEEPAGENTS_REPO_URL="${AGENTBENCH_DEEPAGENTS_REPO_URL:-https://github.com/langchain-ai/deepagents.git}"
AGENTBENCH_DEEPAGENTS_REF="${AGENTBENCH_DEEPAGENTS_REF:-2cf7e25dbb40e783d9d4d545c29e595800bf314f}"
AGENTBENCH_DEEPAGENTS_DIR="${AGENTBENCH_DEEPAGENTS_DIR:-upstream/deepagents}"
AGENTBENCH_DEEPAGENTS_PACKAGE_DIR="${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR:-${AGENTBENCH_DEEPAGENTS_DIR}/libs/deepagents}"
AGENTBENCH_REQUIREMENTS_FILE="${AGENTBENCH_REQUIREMENTS_FILE:-agentbench/requirements.txt}"
AGENTBENCH_DEEPAGENTS_MARKER="${AGENTBENCH_DEEPAGENTS_MARKER:-experiments/runtime_state/deepagents_ready.marker}"

echo "Checking Deep Agents dependency..."
echo "Deep Agents dir: ${AGENTBENCH_DEEPAGENTS_DIR}"
echo "Deep Agents ref: ${AGENTBENCH_DEEPAGENTS_REF}"
echo "Auto install: ${AGENTBENCH_DEEPAGENTS_AUTO_INSTALL}"
echo "Force refresh: ${AGENTBENCH_DEEPAGENTS_FORCE_REFRESH}"
echo "Force reinstall: ${AGENTBENCH_DEEPAGENTS_FORCE_REINSTALL}"

current_commit() {
  if [[ -d "${AGENTBENCH_DEEPAGENTS_DIR}/.git" ]]; then
    git -C "${AGENTBENCH_DEEPAGENTS_DIR}" rev-parse HEAD 2>/dev/null || true
  fi
}

deepagents_import_path() {
  "${PYTHON_BIN}" - <<'PY' 2>/dev/null || true
try:
    import deepagents
except Exception:
    raise SystemExit(1)
print(getattr(deepagents, "__file__", ""))
PY
}

write_marker() {
  local import_path="$1"
  mkdir -p "$(dirname "${AGENTBENCH_DEEPAGENTS_MARKER}")"
  cat > "${AGENTBENCH_DEEPAGENTS_MARKER}" <<EOF
deepagents_ref=${AGENTBENCH_DEEPAGENTS_REF}
deepagents_commit=$(current_commit)
python_bin=${PYTHON_BIN}
package_dir=${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR}
import_path=${import_path}
EOF
}

marker_matches() {
  [[ -f "${AGENTBENCH_DEEPAGENTS_MARKER}" ]] || return 1
  grep -qx "deepagents_ref=${AGENTBENCH_DEEPAGENTS_REF}" "${AGENTBENCH_DEEPAGENTS_MARKER}" || return 1
  grep -qx "deepagents_commit=$(current_commit)" "${AGENTBENCH_DEEPAGENTS_MARKER}" || return 1
  grep -qx "python_bin=${PYTHON_BIN}" "${AGENTBENCH_DEEPAGENTS_MARKER}" || return 1
  grep -qx "package_dir=${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR}" "${AGENTBENCH_DEEPAGENTS_MARKER}" || return 1
}

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
  echo "Deep Agents git checkout exists."
fi

if [[ "${AGENTBENCH_DEEPAGENTS_FORCE_REFRESH}" = "1" || "$(current_commit)" != "${AGENTBENCH_DEEPAGENTS_REF}" ]]; then
  echo "Refreshing Deep Agents checkout..."
  git -C "${AGENTBENCH_DEEPAGENTS_DIR}" fetch origin
  git -C "${AGENTBENCH_DEEPAGENTS_DIR}" checkout "${AGENTBENCH_DEEPAGENTS_REF}"
else
  echo "Deep Agents checkout already at pinned ref."
fi

if [[ ! -f "${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR}/pyproject.toml" ]]; then
  echo "Deep Agents package pyproject is missing after checkout." >&2
  echo "Expected: ${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR}/pyproject.toml" >&2
  exit 1
fi

import_path="$(deepagents_import_path)"
if [[ "${AGENTBENCH_DEEPAGENTS_FORCE_REINSTALL}" != "1" && -n "${import_path}" ]] && marker_matches; then
  echo "Deep Agents import ok: ${import_path}"
  echo "Deep Agents marker ok: ${AGENTBENCH_DEEPAGENTS_MARKER}"
  echo "Deep Agents already ready; skipping install."
  exit 0
fi

if [[ "${AGENTBENCH_DEEPAGENTS_FORCE_REINSTALL}" = "1" ]]; then
  echo "Deep Agents reinstall requested."
elif [[ -z "${import_path}" ]]; then
  echo "Deep Agents import missing; installing."
else
  echo "Deep Agents marker missing or stale; reinstalling to refresh environment state."
fi

echo "Installing Deep Agents package..."
"${PYTHON_BIN}" -m pip install "${AGENTBENCH_DEEPAGENTS_PACKAGE_DIR}"

if [[ -f "${AGENTBENCH_REQUIREMENTS_FILE}" ]]; then
  echo "Installing AgentBench Python requirements..."
  "${PYTHON_BIN}" -m pip install -r "${AGENTBENCH_REQUIREMENTS_FILE}"
fi

echo "Verifying Deep Agents import..."
import_path="$("${PYTHON_BIN}" - <<'PY'
import deepagents
print("deepagents:", deepagents.__file__)
PY
)"
echo "${import_path}"
write_marker "${import_path#deepagents: }"

echo "Deep Agents ready."
