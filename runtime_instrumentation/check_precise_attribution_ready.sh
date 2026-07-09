#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

source runtime_instrumentation/precise_sglang_helper.sh

MODE="${1:-transfer}"
WORKER_CONTAINER_NAME="${WORKER_CONTAINER_NAME:-dynamo-sglang-worker}"
LOG_FILE="${LOG_FILE:-}"

usage() {
  cat <<EOF
Usage:
  $0 [transfer|priority|specprefill]

Checks whether the live Dynamo/SGLang worker container is actually running the
expected precise-attribution patches.

Modes:
  transfer   Validate precise KV/transfer attribution markers.
  priority   Validate precise priority-attribution markers in addition to
             transfer markers.
  specprefill  Validate speculative-prefill decision-path markers plus
               transfer/runtime attribution markers.

Examples:
  $0 transfer
  LOG_FILE=experiments/reports/debug/preflight.log $0 priority
EOF
}

if [[ "${MODE}" = "-h" || "${MODE}" = "--help" ]]; then
  usage
  exit 0
fi

case "${MODE}" in
  transfer|priority|specprefill) ;;
  *)
    echo "Unknown mode: ${MODE}" >&2
    usage >&2
    exit 2
    ;;
esac

log() {
  local message="$1"
  if [[ -n "${LOG_FILE}" ]]; then
    printf '%s\n' "${message}" | tee -a "${LOG_FILE}"
  else
    printf '%s\n' "${message}"
  fi
}

fail() {
  log "========================================"
  log "(4/6) PRECISE ATTRIBUTION CHECK FAILED (the live running worker is missing required instrumentation)"
  log "========================================"
  log "FAIL: $1"
  exit 1
}

if ! command -v docker >/dev/null 2>&1; then
  fail "docker is required"
fi

ROOT="$(resolve_precise_sglang_root || true)"
[[ -n "${ROOT}" ]] || fail "could not resolve extracted SGLang source root"
[[ -f "${ROOT}/__init__.py" ]] || fail "resolved SGLang root is invalid: ${ROOT}"

if ! _precise_sglang_require_markers "${ROOT}" transfer; then
  fail "local extracted SGLang source is missing transfer markers: ${ROOT}"
fi
log "Local SGLang transfer markers: ok (${ROOT})"

if [[ "${MODE}" = "priority" ]]; then
  if ! _precise_sglang_require_markers "${ROOT}" priority; then
    if [[ "${PREPARED_SGLANG_PRIORITY_MARKERS_PRESENT:-1}" = "0" ]]; then
      log "Local SGLang priority markers: unavailable on pinned/extracted SGLang source (${ROOT})"
      log "Continuing with precise worker/runtime attribution only."
    else
      fail "local extracted SGLang source is missing priority markers: ${ROOT}"
    fi
  else
    log "Local SGLang priority markers: ok (${ROOT})"
  fi
elif [[ "${MODE}" = "specprefill" ]]; then
  DYNAMO_ROOT="${SOURCE_DIR:-$(resolve_precise_dynamo_root || true)}"
  [[ -n "${DYNAMO_ROOT}" ]] || fail "could not resolve local Dynamo source root"
  if ! _precise_dynamo_require_markers "${DYNAMO_ROOT}" specprefill; then
    fail "local Dynamo source is missing speculative-prefill markers: ${DYNAMO_ROOT}"
  fi
  log "Local Dynamo speculative-prefill markers: ok (${DYNAMO_ROOT})"
fi

RUNNING="$(docker inspect "${WORKER_CONTAINER_NAME}" --format '{{.State.Running}}' 2>/dev/null || true)"
[[ "${RUNNING}" = "true" ]] || fail "worker container is not running: ${WORKER_CONTAINER_NAME}"
log "Worker container running: ${WORKER_CONTAINER_NAME}"

MOUNT_OK="$(
  docker inspect "${WORKER_CONTAINER_NAME}" \
    --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}' 2>/dev/null |
    grep -c '/workspace/sglang_transfer_overlay/sglang' || true
)"
if [[ "${MOUNT_OK}" -eq 0 ]]; then
  fail "worker container does not have the patched SGLang overlay mounted"
fi
log "Worker overlay mount: ok"

WORKER_ENV="$(
  docker inspect "${WORKER_CONTAINER_NAME}" \
    --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null |
    grep -E '^(SGLANG_TRANSFER_LOG|SGLANG_TRANSFER_LOG_PROFILE|SGLANG_TRANSFER_LOG_OVERHEAD_TIMING|DYN_RUNTIME_JSON_LOGS)=' || true
)"
if [[ -z "${WORKER_ENV}" ]]; then
  fail "worker env does not expose precise-attribution settings"
fi
log "Worker env markers:"
while IFS= read -r line; do
  [[ -n "${line}" ]] && log "  ${line}"
done <<< "${WORKER_ENV}"

DECODE_CHECK="$(
  docker exec -i "${WORKER_CONTAINER_NAME}" python3 - <<'PY'
import importlib.util
import json
from pathlib import Path

spec = importlib.util.find_spec("dynamo.sglang.request_handlers.llm.decode_handler")
if spec is None or not spec.origin:
    raise SystemExit("could not locate decode_handler.py inside worker")
path = Path(spec.origin)
text = path.read_text(encoding="utf-8")
checks = {
    "path": str(path),
    "attach_logged = False": "attach_logged = False" in text,
    "worker.decode.request_attached": "worker.decode.request_attached" in text,
    "request: Dict[str, Any]": "request: Dict[str, Any]" in text,
}
print(json.dumps(checks, sort_keys=True))
missing = [key for key, value in checks.items() if key != "path" and not value]
if missing:
    raise SystemExit(11)
PY
)" || fail "worker decode handler is missing one or more Dynamo precise-attribution markers"
log "Dynamo decode handler markers: ${DECODE_CHECK}"

if [[ "${MODE}" = "transfer" ]]; then
  TRANSFER_CHECK="$(
    docker exec -i "${WORKER_CONTAINER_NAME}" python3 - <<'PY'
import importlib.util
import json
from pathlib import Path

spec = importlib.util.find_spec("sglang.srt.mem_cache.memory_pool_host")
if spec is None or not spec.origin:
    raise SystemExit("could not locate memory_pool_host.py inside worker")
path = Path(spec.origin)
text = path.read_text(encoding="utf-8")
checks = {
    "path": str(path),
    "_sgl_log_transfer_event": "_sgl_log_transfer_event" in text,
}
print(json.dumps(checks, sort_keys=True))
if not checks["_sgl_log_transfer_event"]:
    raise SystemExit(12)
PY
  )" || fail "worker SGLang transfer markers are missing"
  log "SGLang transfer markers: ${TRANSFER_CHECK}"
elif [[ "${MODE}" = "priority" ]]; then
  if [[ "${PREPARED_SGLANG_PRIORITY_MARKERS_PRESENT:-1}" = "0" ]]; then
    log "SGLang priority markers: unavailable on pinned/extracted SGLang source; skipping direct priority-path proof."
  else
    PRIORITY_CHECK="$(
      docker exec -i "${WORKER_CONTAINER_NAME}" python3 - <<'PY'
import importlib.util
import json
from pathlib import Path

root_spec = importlib.util.find_spec("sglang")
if root_spec is None or not root_spec.origin:
    raise SystemExit("could not locate sglang package inside worker")
root = Path(root_spec.origin).resolve().parent
targets = [
    root / "srt" / "mem_cache",
    root / "srt" / "managers",
]
combined = ""
present_files = []
for target in targets:
    if target.is_file() and target.suffix == ".py":
        combined += target.read_text(encoding="utf-8") + "\n"
        present_files.append(str(target))
        continue
    if not target.is_dir():
        continue
    for path in sorted(target.rglob("*.py")):
        try:
            combined += path.read_text(encoding="utf-8") + "\n"
            present_files.append(str(path))
        except Exception:
            continue
checks = {
    "files": present_files,
    "_sgl_log_priority_event": "_sgl_log_priority_event" in combined,
    "priority_hint_seen": "priority_hint_seen" in combined,
    "scheduler_priority_applied": "scheduler_priority_applied" in combined,
}
print(json.dumps(checks, sort_keys=True))
missing = [key for key, value in checks.items() if key != "files" and not value]
if missing:
    raise SystemExit(13)
PY
    )" || fail "worker SGLang priority markers are missing"
    log "SGLang priority markers: ${PRIORITY_CHECK}"
  fi
else
  log "Speculative-prefill decision-path proof will be validated from runtime events during the experiment."
fi

precise_banner_numbered 4 6 "PRECISE ATTRIBUTION READY (the live running worker really has the instrumentation)" "${LOG_FILE}"
log "PASS: precise ${MODE} attribution is ready"
