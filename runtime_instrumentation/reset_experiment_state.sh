#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

ACTION="${1:-}"
FRONTEND_URL="${FRONTEND_URL:-${AGENTBENCH_FRONTEND_URL:-http://127.0.0.1:8000/v1/chat/completions}}"
RUNTIME_SIGNATURE="${EXPERIMENT_RUNTIME_SIGNATURE:-}"
STATE_FILE="${EXPERIMENT_RESET_STATE_FILE:-experiments/runtime_state/active_runtime_signature.txt}"
EXPECTED_MODEL="${EXPERIMENT_EXPECTED_MODEL:-${MODEL:-${MODEL_NAME:-}}}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

usage() {
  cat <<EOF
Usage:
  $0 reuse-ready|flush|mark-active|clear-active

Environment:
  FRONTEND_URL
  EXPERIMENT_RUNTIME_SIGNATURE
  EXPERIMENT_RESET_STATE_FILE
  EXPERIMENT_EXPECTED_MODEL
EOF
}

log() {
  printf '%s\n' "$*"
}

fail() {
  printf '%s\n' "$*" >&2
  exit 1
}

frontend_base_url() {
  "${PYTHON_BIN}" - <<'PY' "${FRONTEND_URL}"
import sys

url = sys.argv[1].rstrip("/")
suffixes = (
    "/v1/chat/completions",
    "/v1/completions",
    "/v1/responses",
    "/v1",
)
for suffix in suffixes:
    if url.endswith(suffix):
        print(url[: -len(suffix)])
        break
else:
    print(url)
PY
}

models_url() {
  printf '%s/v1/models\n' "$(frontend_base_url)"
}

clear_url() {
  printf '%s/clear_kv_blocks\n' "$(frontend_base_url)"
}

require_signature() {
  [[ -n "${RUNTIME_SIGNATURE}" ]] || fail "EXPERIMENT_RUNTIME_SIGNATURE is required for ${ACTION}"
}

state_dir() {
  dirname "${STATE_FILE}"
}

models_contains_expected() {
  local payload
  payload="$(curl -fsS "$(models_url)" 2>/dev/null || true)"
  [[ -n "${payload}" ]] || return 1
  EXPECTED_MODEL_ENV="${EXPECTED_MODEL}" MODELS_PAYLOAD="${payload}" "${PYTHON_BIN}" - <<'PY'
import json
import os
import sys

expected = os.environ.get("EXPECTED_MODEL_ENV", "")
payload = os.environ.get("MODELS_PAYLOAD", "")
if not expected:
    raise SystemExit(2)

try:
    doc = json.loads(payload)
except json.JSONDecodeError:
    raise SystemExit(1)

for item in doc.get("data", []):
    if item.get("id") == expected:
        raise SystemExit(0)

raise SystemExit(1)
PY
}

do_reuse_ready() {
  require_signature
  [[ -f "${STATE_FILE}" ]] || exit 1
  [[ "$(cat "${STATE_FILE}")" = "${RUNTIME_SIGNATURE}" ]] || exit 1
  [[ -n "${EXPECTED_MODEL}" ]] || exit 1
  models_contains_expected
}

do_mark_active() {
  require_signature
  mkdir -p "$(state_dir)"
  printf '%s\n' "${RUNTIME_SIGNATURE}" > "${STATE_FILE}"
  log "Marked active runtime signature: ${STATE_FILE}"
}

do_clear_active() {
  rm -f "${STATE_FILE}"
  log "Cleared active runtime signature: ${STATE_FILE}"
}

do_flush() {
  local url http_code response_file
  url="$(clear_url)"
  response_file="$(mktemp)"
  http_code="$(curl -sS -o "${response_file}" -w "%{http_code}" -X POST "${url}" || true)"
  if [[ ! "${http_code}" =~ ^2[0-9][0-9]$ ]]; then
    cat "${response_file}" >&2 || true
    rm -f "${response_file}"
    if [[ "${http_code}" = "404" || "${http_code}" = "400" ]]; then
      fail "KV cache flush endpoint is not usable at ${url} (http ${http_code}). Rebuild/restart the instrumented Dynamo/SGLang images so the SGLang worker serves clear_kv_blocks."
    fi
    fail "KV cache flush failed at ${url} (http ${http_code:-<none>})"
  fi
  RESPONSE_FILE="${response_file}" "${PYTHON_BIN}" - <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(os.environ["RESPONSE_FILE"])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"Could not parse clear_kv_blocks response: {exc}")

cleared = payload.get("cleared_workers") or []
failed = payload.get("failed_workers") or []
if failed:
    raise SystemExit(
        "clear_kv_blocks reported failed workers: "
        + json.dumps(failed, sort_keys=True)
    )
if not cleared:
    raise SystemExit(
        "clear_kv_blocks did not report any cleared workers: "
        + json.dumps(payload, sort_keys=True)
    )
print(
    "KV cache flush succeeded: "
    + json.dumps(
        {
            "cleared_workers": len(cleared),
            "failed_workers": len(failed),
        },
        sort_keys=True,
    )
)
PY
  rm -f "${response_file}"
}

case "${ACTION}" in
  reuse-ready)
    do_reuse_ready
    ;;
  flush)
    do_flush
    ;;
  mark-active)
    do_mark_active
    ;;
  clear-active)
    do_clear_active
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
