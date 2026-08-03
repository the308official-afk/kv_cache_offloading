#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
AGENTBENCH_NEMO_AUTO_INSTALL="${AGENTBENCH_NEMO_AUTO_INSTALL:-1}"
AGENTBENCH_NEMO_INSTALL_MODE="${AGENTBENCH_NEMO_INSTALL_MODE:-source}"
AGENTBENCH_NEMO_FORCE_REFRESH="${AGENTBENCH_NEMO_FORCE_REFRESH:-0}"
AGENTBENCH_NEMO_FORCE_REINSTALL="${AGENTBENCH_NEMO_FORCE_REINSTALL:-0}"
AGENTBENCH_NEMO_REPO_URL="${AGENTBENCH_NEMO_REPO_URL:-https://github.com/NVIDIA/NeMo-Agent-Toolkit.git}"
AGENTBENCH_NEMO_REF="${AGENTBENCH_NEMO_REF:-develop}"
AGENTBENCH_NEMO_DIR="${AGENTBENCH_NEMO_DIR:-upstream/nemo-agent-toolkit}"
AGENTBENCH_NEMO_EXTRAS="${AGENTBENCH_NEMO_EXTRAS:-langchain}"
AGENTBENCH_NEMO_MARKER="${AGENTBENCH_NEMO_MARKER:-experiments/runtime_state/nemo_agent_toolkit_ready.marker}"

echo "Checking NeMo Agent Toolkit dependency..."
echo "NeMo Agent Toolkit install mode: ${AGENTBENCH_NEMO_INSTALL_MODE}"
echo "NeMo Agent Toolkit dir: ${AGENTBENCH_NEMO_DIR}"
echo "NeMo Agent Toolkit ref: ${AGENTBENCH_NEMO_REF}"
echo "NeMo Agent Toolkit extras: ${AGENTBENCH_NEMO_EXTRAS}"
echo "Auto install: ${AGENTBENCH_NEMO_AUTO_INSTALL}"
echo "Force refresh: ${AGENTBENCH_NEMO_FORCE_REFRESH}"
echo "Force reinstall: ${AGENTBENCH_NEMO_FORCE_REINSTALL}"

current_commit() {
  if [[ -d "${AGENTBENCH_NEMO_DIR}/.git" ]]; then
    git -C "${AGENTBENCH_NEMO_DIR}" rev-parse HEAD 2>/dev/null || true
  fi
}

nemo_import_summary() {
  "${PYTHON_BIN}" - <<'PY' 2>/dev/null || true
try:
    import nat
    from nat.llm import dynamo_llm
except Exception:
    raise SystemExit(1)

required = [
    "DynamoModelConfig",
    "_DynamoTransport",
    "DynamoPrefixContext",
]
missing = [name for name in required if not hasattr(dynamo_llm, name)]
if missing:
    raise SystemExit(2)

print(f"nat={getattr(nat, '__file__', '')}")
print(f"dynamo_llm={getattr(dynamo_llm, '__file__', '')}")
PY
}

write_marker() {
  local import_summary="$1"
  mkdir -p "$(dirname "${AGENTBENCH_NEMO_MARKER}")"
  {
    echo "nemo_install_mode=${AGENTBENCH_NEMO_INSTALL_MODE}"
    echo "nemo_ref=${AGENTBENCH_NEMO_REF}"
    echo "nemo_commit=$(current_commit)"
    echo "python_bin=${PYTHON_BIN}"
    echo "nemo_dir=${AGENTBENCH_NEMO_DIR}"
    echo "nemo_extras=${AGENTBENCH_NEMO_EXTRAS}"
    printf '%s\n' "${import_summary}"
  } > "${AGENTBENCH_NEMO_MARKER}"
}

marker_matches() {
  [[ -f "${AGENTBENCH_NEMO_MARKER}" ]] || return 1
  grep -qx "nemo_install_mode=${AGENTBENCH_NEMO_INSTALL_MODE}" "${AGENTBENCH_NEMO_MARKER}" || return 1
  grep -qx "nemo_ref=${AGENTBENCH_NEMO_REF}" "${AGENTBENCH_NEMO_MARKER}" || return 1
  grep -qx "python_bin=${PYTHON_BIN}" "${AGENTBENCH_NEMO_MARKER}" || return 1
  grep -qx "nemo_dir=${AGENTBENCH_NEMO_DIR}" "${AGENTBENCH_NEMO_MARKER}" || return 1
  grep -qx "nemo_extras=${AGENTBENCH_NEMO_EXTRAS}" "${AGENTBENCH_NEMO_MARKER}" || return 1
  if [[ "${AGENTBENCH_NEMO_INSTALL_MODE}" = "source" ]]; then
    grep -qx "nemo_commit=$(current_commit)" "${AGENTBENCH_NEMO_MARKER}" || return 1
  fi
}

package_spec() {
  if [[ -n "${AGENTBENCH_NEMO_EXTRAS}" ]]; then
    printf 'nvidia-nat[%s]\n' "${AGENTBENCH_NEMO_EXTRAS}"
  else
    printf 'nvidia-nat\n'
  fi
}

source_spec() {
  if [[ -n "${AGENTBENCH_NEMO_EXTRAS}" ]]; then
    printf '%s[%s]\n' "${AGENTBENCH_NEMO_DIR}" "${AGENTBENCH_NEMO_EXTRAS}"
  else
    printf '%s\n' "${AGENTBENCH_NEMO_DIR}"
  fi
}

if [[ "${AGENTBENCH_NEMO_INSTALL_MODE}" != "source" && "${AGENTBENCH_NEMO_INSTALL_MODE}" != "package" ]]; then
  echo "Unsupported AGENTBENCH_NEMO_INSTALL_MODE=${AGENTBENCH_NEMO_INSTALL_MODE}. Use source or package." >&2
  exit 2
fi

import_summary="$(nemo_import_summary)"
if [[ "${AGENTBENCH_NEMO_FORCE_REINSTALL}" != "1" && -n "${import_summary}" ]] && marker_matches; then
  echo "NeMo Agent Toolkit import ok:"
  echo "${import_summary}"
  echo "NeMo Agent Toolkit marker ok: ${AGENTBENCH_NEMO_MARKER}"
  echo "NeMo Agent Toolkit already ready; skipping install."
  exit 0
fi

if [[ "${AGENTBENCH_NEMO_AUTO_INSTALL}" != "1" ]]; then
  echo "NeMo Agent Toolkit is missing or marker is stale, and AGENTBENCH_NEMO_AUTO_INSTALL=0." >&2
  exit 1
fi

if [[ "${AGENTBENCH_NEMO_INSTALL_MODE}" = "source" ]]; then
  mkdir -p "$(dirname "${AGENTBENCH_NEMO_DIR}")"

  if [[ ! -d "${AGENTBENCH_NEMO_DIR}/.git" ]]; then
    if [[ -e "${AGENTBENCH_NEMO_DIR}" ]]; then
      echo "NeMo Agent Toolkit path exists but is not a git checkout: ${AGENTBENCH_NEMO_DIR}" >&2
      echo "Move or remove it, then retry." >&2
      exit 1
    fi
    echo "NeMo Agent Toolkit source missing; cloning..."
    git clone "${AGENTBENCH_NEMO_REPO_URL}" "${AGENTBENCH_NEMO_DIR}"
  else
    echo "NeMo Agent Toolkit git checkout exists."
  fi

  if [[ "${AGENTBENCH_NEMO_FORCE_REFRESH}" = "1" || "$(current_commit)" != "${AGENTBENCH_NEMO_REF}" ]]; then
    echo "Refreshing NeMo Agent Toolkit checkout..."
    git -C "${AGENTBENCH_NEMO_DIR}" fetch origin
    git -C "${AGENTBENCH_NEMO_DIR}" checkout "${AGENTBENCH_NEMO_REF}"
  else
    echo "NeMo Agent Toolkit checkout already at requested ref."
  fi

  if [[ ! -f "${AGENTBENCH_NEMO_DIR}/pyproject.toml" ]]; then
    echo "NeMo Agent Toolkit pyproject is missing after checkout." >&2
    echo "Expected: ${AGENTBENCH_NEMO_DIR}/pyproject.toml" >&2
    exit 1
  fi

  echo "Installing NeMo Agent Toolkit from source..."
  "${PYTHON_BIN}" -m pip install -e "$(source_spec)"
else
  echo "Installing NeMo Agent Toolkit package..."
  "${PYTHON_BIN}" -m pip install "$(package_spec)"
fi

echo "Verifying NeMo Agent Toolkit import..."
import_summary="$(nemo_import_summary)"
if [[ -z "${import_summary}" ]]; then
  echo "NeMo Agent Toolkit import verification failed." >&2
  exit 1
fi

echo "${import_summary}"
write_marker "${import_summary}"

echo "NeMo Agent Toolkit ready."
