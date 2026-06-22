#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROFILE_SCRIPT="${SCRIPT_DIR}/dynamo_machine_profile.sh"

if [[ -f "${PROFILE_SCRIPT}" ]]; then
  # shellcheck disable=SC1090
  source "${PROFILE_SCRIPT}"
fi

WORKER_IMAGE="${WORKER_IMAGE:-local/dynamo-sglang:runtime-json-logs}"
WORKER_CONTAINER_NAME="${WORKER_CONTAINER_NAME:-dynamo-sglang-worker}"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/experiments/reports/runtime_probe}"
LABEL="${LABEL:-$(hostname -s 2>/dev/null || hostname)}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUT_PATH="${OUT_PATH:-${OUT_DIR}/worker_runtime_probe_${LABEL}_${TIMESTAMP}.txt}"

usage() {
  cat <<EOF
Usage: $0

Captures the effective Dynamo/SGLang worker runtime on the current machine and
writes a plain-text report that you can compare across EC2 and GH200 hosts.

Environment overrides:
  DYNAMO_MACHINE_PROFILE   Default: ${DYNAMO_MACHINE_PROFILE:-<unset>}
  WORKER_IMAGE             Default: ${WORKER_IMAGE}
  WORKER_CONTAINER_NAME    Default: ${WORKER_CONTAINER_NAME}
  OUT_DIR                  Default: ${OUT_DIR}
  OUT_PATH                 Default: ${OUT_PATH}
  LABEL                    Default: ${LABEL}

Examples:
  export DYNAMO_MACHINE_PROFILE=ec2
  source runtime_instrumentation/dynamo_machine_profile.sh
  ./runtime_instrumentation/probe_worker_runtime.sh

  export DYNAMO_MACHINE_PROFILE=gh200
  source runtime_instrumentation/dynamo_machine_profile.sh
  ./runtime_instrumentation/probe_worker_runtime.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for ${0##*/}" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

RUN_MODE="image"
if docker ps --format '{{.Names}}' | grep -Fxq "${WORKER_CONTAINER_NAME}"; then
  RUN_MODE="container"
fi

report() {
  tee -a "${OUT_PATH}"
}

run_in_runtime() {
  if [[ "${RUN_MODE}" == "container" ]]; then
    docker exec "${WORKER_CONTAINER_NAME}" "$@"
  else
    docker run --rm --entrypoint "$1" "${WORKER_IMAGE}" "${@:2}"
  fi
}

run_shell_in_runtime() {
  if [[ "${RUN_MODE}" == "container" ]]; then
    docker exec "${WORKER_CONTAINER_NAME}" bash -lc "$1"
  else
    docker run --rm --entrypoint bash "${WORKER_IMAGE}" -lc "$1"
  fi
}

probe_cli_value() {
  local value="$1"
  local tmp_output
  tmp_output="$(mktemp)"
  set +e
  run_shell_in_runtime "python3 -m dynamo.sglang --radix-eviction-policy ${value} --help" >"${tmp_output}" 2>&1
  local exit_code=$?
  set -e

  {
    echo "probe_value=${value}"
    echo "exit_code=${exit_code}"
    if grep -q "invalid choice" "${tmp_output}"; then
      echo "result=invalid"
      grep -m 1 "invalid choice" "${tmp_output}"
    else
      echo "result=accepted_or_non_choice_failure"
      head -n 5 "${tmp_output}"
    fi
    echo
  } | report

  rm -f "${tmp_output}"
}

{
  echo "=== Worker Runtime Probe ==="
  echo "timestamp=${TIMESTAMP}"
  echo "label=${LABEL}"
  echo "repo_root=${REPO_ROOT}"
  echo
  echo "=== Host ==="
  echo "hostname=$(hostname)"
  echo "uname=$(uname -a)"
  echo "arch=$(uname -m)"
  echo "dynamo_machine_profile=${DYNAMO_MACHINE_PROFILE:-<unset>}"
  echo "frontend_image=${FRONTEND_IMAGE:-<unset>}"
  echo "worker_image=${WORKER_IMAGE}"
  echo "docker_build_platform=${DOCKER_BUILD_PLATFORM:-<unset>}"
  echo "target_platform=${TARGET_PLATFORM:-<unset>}"
  echo "run_mode=${RUN_MODE}"
  echo
  echo "=== Docker Image ==="
  docker image inspect "${WORKER_IMAGE}" \
    --format 'image_id={{.Id}}
repo_tags={{join .RepoTags ", "}}
os={{.Os}}
architecture={{.Architecture}}
created={{.Created}}'
  echo
  echo "=== Container State ==="
  if [[ "${RUN_MODE}" == "container" ]]; then
    docker inspect "${WORKER_CONTAINER_NAME}" \
      --format 'name={{.Name}}
image={{.Config.Image}}
status={{.State.Status}}
started_at={{.State.StartedAt}}
platform={{.Platform}}'
    echo
    echo "--- Selected Worker Env ---"
    docker inspect "${WORKER_CONTAINER_NAME}" --format '{{range .Config.Env}}{{println .}}{{end}}' | \
      grep -E '^(WORKER_|SGLANG_|DYN_|DYNAMO_|FRONTEND_|TARGET_PLATFORM|DOCKER_BUILD_PLATFORM)' || true
  else
    echo "container_not_running=true"
  fi
  echo
  echo "=== Python Package Snapshot ==="
} > "${OUT_PATH}"

run_in_runtime python3 - <<'PY' | report
import importlib
import importlib.metadata as md
import json

interesting = {}
for name in sorted({dist.metadata["Name"] for dist in md.distributions() if dist.metadata.get("Name")}):
    lowered = name.lower()
    if "sglang" in lowered or "dynamo" in lowered:
        try:
            interesting[name] = md.version(name)
        except Exception:
            interesting[name] = "<version lookup failed>"

module_info = {}
for mod_name in ("dynamo", "sglang"):
    try:
        mod = importlib.import_module(mod_name)
        module_info[mod_name] = getattr(mod, "__file__", "<no file>")
    except Exception as exc:
        module_info[mod_name] = f"<import failed: {exc}>"

print(json.dumps({"packages": interesting, "modules": module_info}, indent=2, sort_keys=True))
PY

{
  echo
  echo "=== CLI Capability Probe ==="
} | report

probe_cli_value "lru"
probe_cli_value "lfu"
probe_cli_value "priority"

{
  echo "=== Help Snippet ==="
} | report

run_shell_in_runtime "python3 -m dynamo.sglang --help 2>&1 | grep -n 'radix-eviction-policy\\|enable-priority-scheduling\\|priority' || true" | report

{
  echo
  echo "Saved report: ${OUT_PATH}"
} | report

echo "Saved report: ${OUT_PATH}"
