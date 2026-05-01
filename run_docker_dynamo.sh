#!/bin/bash

set -euo pipefail

ACTION="${1:-start}"

HOST_HOME_DIR="${HOST_HOME_DIR:-$HOME}"
PERSISTENT_DATA_ROOT="${PERSISTENT_DATA_ROOT:-/mnt/docker-data}"
DYNAMO_CACHE_DIR="${DYNAMO_CACHE_DIR:-${PERSISTENT_DATA_ROOT}/dynamo_cache}"
DYNAMO_CONTAINER_NAME="${DYNAMO_CONTAINER_NAME:-docker-dynamo-sglang}"
DYNAMO_IMAGE="${DYNAMO_IMAGE:-nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.2}"
DYNAMO_PRIORITY_IMAGE="${DYNAMO_PRIORITY_IMAGE:-nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.1.0-dev.1}"
DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH:-Qwen/Qwen2.5-0.5B}"
DYNAMO_DISCOVERY_BACKEND="${DYNAMO_DISCOVERY_BACKEND:-file}"
DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT:-8000}"
DYNAMO_SGLANG_PORT="${DYNAMO_SGLANG_PORT:-30000}"
DYNAMO_EVICTION_POLICY="${DYNAMO_EVICTION_POLICY:-lru}"
RUN_IMAGE="${DYNAMO_IMAGE}"
RUN_EVICTION_POLICY="${DYNAMO_EVICTION_POLICY}"
RUN_FRONTEND_EXTRA_ARGS=""
RUN_WORKER_EXTRA_ARGS=""

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  start          Start the Dynamo container, frontend, and SGLang worker
  start-kv       Start the stable stack with KV-router mode and cache reporting
  start-priority Start the experimental priority-eviction attempt
  test           Send a simple smoke-test request to the frontend
  test-priority  Send a request with agent_hints.priority metadata
  test-specprefill-control  Run a 2-turn control test without speculative prefill
  test-specprefill          Run a 2-turn test with speculative prefill enabled
  test-specprefill-ab       Run both tests and print a side-by-side summary
  logs           Stream frontend and worker logs from the container
  shell          Open an interactive shell inside the running container
  status         Show container/process status
  stop           Stop and remove the Dynamo container

Environment overrides:
  DYNAMO_IMAGE             Default: ${DYNAMO_IMAGE}
  DYNAMO_PRIORITY_IMAGE    Default: ${DYNAMO_PRIORITY_IMAGE}
  DYNAMO_MODEL_PATH        Default: ${DYNAMO_MODEL_PATH}
  DYNAMO_CACHE_DIR         Default: ${DYNAMO_CACHE_DIR}
  DYNAMO_CONTAINER_NAME    Default: ${DYNAMO_CONTAINER_NAME}
  DYNAMO_FRONTEND_PORT     Default: ${DYNAMO_FRONTEND_PORT}
  DYNAMO_SGLANG_PORT       Default: ${DYNAMO_SGLANG_PORT}
  DYNAMO_DISCOVERY_BACKEND Default: ${DYNAMO_DISCOVERY_BACKEND}
  DYNAMO_EVICTION_POLICY   Default: ${DYNAMO_EVICTION_POLICY}

Note:
  The released SGLang runtime images currently accept `lru` and `lfu`.
  If a future image supports `priority`, you can override:
    DYNAMO_EVICTION_POLICY=priority
  The experimental `start-priority` command uses:
    image=${DYNAMO_PRIORITY_IMAGE}
    eviction=priority
EOF
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker is not installed or not on PATH." >&2
    exit 1
  fi
}

ensure_host_dirs() {
  sudo mkdir -p "${DYNAMO_CACHE_DIR}"
  sudo chmod 777 "${DYNAMO_CACHE_DIR}"
}

container_exists() {
  docker ps -a --format '{{.Names}}' | grep -Fxq "${DYNAMO_CONTAINER_NAME}"
}

container_running() {
  docker ps --format '{{.Names}}' | grep -Fxq "${DYNAMO_CONTAINER_NAME}"
}

container_bootstrap_command() {
  cat <<EOF
set -euo pipefail

( python3 -m dynamo.frontend --discovery-backend '${DYNAMO_DISCOVERY_BACKEND}' ${RUN_FRONTEND_EXTRA_ARGS} 2>&1 | sed 's/^/[frontend] /' ) &
FRONTEND_WRAPPER_PID=\$!

( python3 -m dynamo.sglang \
    --model-path '${DYNAMO_MODEL_PATH}' \
    --discovery-backend '${DYNAMO_DISCOVERY_BACKEND}' \
    --enable-priority-scheduling \
    --radix-eviction-policy '${RUN_EVICTION_POLICY}' ${RUN_WORKER_EXTRA_ARGS} 2>&1 | sed 's/^/[worker] /' ) &
WORKER_WRAPPER_PID=\$!

trap 'kill \$FRONTEND_WRAPPER_PID \$WORKER_WRAPPER_PID 2>/dev/null || true; wait || true' TERM INT EXIT

wait -n \$FRONTEND_WRAPPER_PID \$WORKER_WRAPPER_PID
STATUS=\$?
echo "[launcher] A Dynamo process exited with status \$STATUS"
kill \$FRONTEND_WRAPPER_PID \$WORKER_WRAPPER_PID 2>/dev/null || true
wait || true
exit \$STATUS
EOF
}

start_container() {
  ensure_host_dirs

  if container_exists; then
    docker rm -f "${DYNAMO_CONTAINER_NAME}" >/dev/null 2>&1 || true
  fi

  docker run -d \
    --gpus all \
    --network host \
    --name "${DYNAMO_CONTAINER_NAME}" \
    -v "${DYNAMO_CACHE_DIR}:/models/hfcache" \
    "${RUN_IMAGE}" \
    bash -lc "$(container_bootstrap_command)" >/dev/null
}

wait_for_container() {
  local retries=20
  local delay=1

  for ((i = 1; i <= retries; i++)); do
    if container_running; then
      return 0
    fi
    sleep "${delay}"
  done

  echo "Container ${DYNAMO_CONTAINER_NAME} failed to start." >&2
  exit 1
}

wait_for_process() {
  local pattern="$1"
  local label="$2"
  local retries=30
  local delay=1

  for ((i = 1; i <= retries; i++)); do
    if docker exec "${DYNAMO_CONTAINER_NAME}" bash -lc "pgrep -af '${pattern}' >/dev/null"; then
      return 0
    fi
    sleep "${delay}"
  done

  echo "${label} did not stay running inside ${DYNAMO_CONTAINER_NAME}." >&2
  echo "Check logs with: $0 logs" >&2
  exit 1
}

wait_for_frontend() {
  local retries=60
  local delay=2

  for ((i = 1; i <= retries; i++)); do
    if curl -fsS "http://127.0.0.1:${DYNAMO_FRONTEND_PORT}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay}"
  done

  echo "Dynamo frontend did not become healthy on port ${DYNAMO_FRONTEND_PORT}." >&2
  echo "Check logs with: $0 logs" >&2
  exit 1
}

print_status() {
  echo "Container:"
  docker ps -a --filter "name=^${DYNAMO_CONTAINER_NAME}$"
  echo
  echo "Processes inside container:"
  docker exec "${DYNAMO_CONTAINER_NAME}" bash -lc "
    ps -ef | awk '
      /python3 -m dynamo.frontend/ || /python3 -m dynamo.sglang/ || (NR==1) { print }
    '
  "
}

test_basic() {
  curl "http://127.0.0.1:${DYNAMO_FRONTEND_PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"${DYNAMO_MODEL_PATH}\",
      \"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}],
      \"max_tokens\": 50
    }"
}

test_priority() {
  curl "http://127.0.0.1:${DYNAMO_FRONTEND_PORT}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"${DYNAMO_MODEL_PATH}\",
      \"messages\": [{\"role\": \"user\", \"content\": \"Say hello in one sentence.\"}],
      \"max_tokens\": 40,
      \"nvext\": {
        \"agent_hints\": {
          \"priority\": 10,
          \"speculative_prefill\": true,
          \"osl\": 128
        }
      }
    }"
}

run_specprefill_probe() {
  local mode="$1"

  DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT}" \
  DYNAMO_MODEL_PATH="${DYNAMO_MODEL_PATH}" \
  SPECPREFILL_MODE="${mode}" \
  python3 - <<'PY'
import json
import os
import sys
import urllib.request

port = os.environ["DYNAMO_FRONTEND_PORT"]
model = os.environ["DYNAMO_MODEL_PATH"]
mode = os.environ["SPECPREFILL_MODE"]
url = f"http://127.0.0.1:{port}/v1/chat/completions"

base_messages = [
    {"role": "system", "content": "You are a concise assistant. Answer in one short sentence."},
    {"role": "user", "content": "Give me a two-word name for a robot dog."},
]

first_payload = {
    "model": model,
    "messages": base_messages,
    "max_tokens": 24,
}

if mode == "enabled":
    first_payload["nvext"] = {
        "agent_hints": {
            "speculative_prefill": True,
            "osl": 64,
            "priority": 5,
        }
    }

def post(payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

first = post(first_payload)
assistant = first["choices"][0]["message"]["content"]

second_payload = {
    "model": model,
    "messages": base_messages + [
        {"role": "assistant", "content": assistant},
        {"role": "user", "content": "Now explain why that name fits in one short sentence."},
    ],
    "max_tokens": 32,
}

second = post(second_payload)
usage = second.get("usage", {})
details = usage.get("prompt_tokens_details", {}) or {}
timing = (second.get("nvext", {}) or {}).get("timing", {}) or {}

summary = {
    "mode": mode,
    "first_reply": assistant,
    "second_reply": second["choices"][0]["message"]["content"],
    "cached_tokens": details.get("cached_tokens"),
    "prompt_tokens": usage.get("prompt_tokens"),
    "completion_tokens": usage.get("completion_tokens"),
    "total_time_ms": timing.get("total_time_ms"),
    "finish_reason": second["choices"][0].get("finish_reason"),
}
print(json.dumps(summary, indent=2))
PY
}

test_specprefill_control() {
  run_specprefill_probe "control"
}

test_specprefill_enabled() {
  run_specprefill_probe "enabled"
}

test_specprefill_ab() {
  local control_file enabled_file
  control_file="$(mktemp)"
  enabled_file="$(mktemp)"

  run_specprefill_probe "control" > "${control_file}"
  run_specprefill_probe "enabled" > "${enabled_file}"

  python3 - "${control_file}" "${enabled_file}" <<'PY'
import json
import sys

control = json.load(open(sys.argv[1]))
enabled = json.load(open(sys.argv[2]))

def fmt(value):
    return "n/a" if value is None else value

print("Speculative prefill A/B summary")
print()
print(f"Control cached_tokens:        {fmt(control.get('cached_tokens'))}")
print(f"Enabled cached_tokens:        {fmt(enabled.get('cached_tokens'))}")
print(f"Control second-turn time ms:  {fmt(control.get('total_time_ms'))}")
print(f"Enabled second-turn time ms:  {fmt(enabled.get('total_time_ms'))}")
print()
print("Control second reply:")
print(control.get("second_reply", ""))
print()
print("Enabled second reply:")
print(enabled.get("second_reply", ""))
PY

  rm -f "${control_file}" "${enabled_file}"
}

show_logs() {
  docker logs --tail 200 "${DYNAMO_CONTAINER_NAME}" || true
}

open_shell() {
  docker exec -it "${DYNAMO_CONTAINER_NAME}" bash
}

stop_container() {
  docker rm -f "${DYNAMO_CONTAINER_NAME}" >/dev/null 2>&1 || true
}

start_stack() {
  require_docker
  start_container
  wait_for_container
  wait_for_process "dynamo.frontend" "Dynamo frontend"
  wait_for_process "dynamo.sglang" "Dynamo SGLang worker"
  wait_for_frontend

  cat <<EOF
Dynamo test stack is starting.

Container: ${DYNAMO_CONTAINER_NAME}
Image:     ${RUN_IMAGE}
Model:     ${DYNAMO_MODEL_PATH}
Eviction:  ${RUN_EVICTION_POLICY}
Frontend:  http://127.0.0.1:${DYNAMO_FRONTEND_PORT}
Worker:    http://127.0.0.1:${DYNAMO_SGLANG_PORT}

Next steps:
  $0 status
  $0 test
  $0 test-priority
  $0 logs
EOF
}

start_priority_stack() {
  RUN_IMAGE="${DYNAMO_PRIORITY_IMAGE}"
  RUN_EVICTION_POLICY="priority"
  start_stack
}

start_kv_stack() {
  RUN_FRONTEND_EXTRA_ARGS="--router-mode kv --router-queue-threshold 4.0"
  RUN_WORKER_EXTRA_ARGS="--enable-cache-report"
  start_stack
}

case "${ACTION}" in
  start)
    start_stack
    ;;
  start-kv)
    start_kv_stack
    ;;
  start-priority)
    start_priority_stack
    ;;
  test)
    test_basic
    ;;
  test-priority)
    test_priority
    ;;
  test-specprefill-control)
    test_specprefill_control
    ;;
  test-specprefill)
    test_specprefill_enabled
    ;;
  test-specprefill-ab)
    test_specprefill_ab
    ;;
  logs)
    show_logs
    ;;
  shell)
    open_shell
    ;;
  status)
    print_status
    ;;
  stop)
    stop_container
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: ${ACTION}" >&2
    usage
    exit 1
    ;;
esac
