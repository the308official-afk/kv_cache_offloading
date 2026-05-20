#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-dynamo-sglang-worker}"
RESTART_CONTAINER=1

usage() {
  cat <<'USAGE'
Hot-patch worker-side Dynamo/SGLang Python logging inside a running container.

This does not rebuild any Docker image. It copies the installed Python files out
of the worker container, patches hint logging fields, copies them back, compile
checks them inside the container, and restarts only the worker container.

Usage:
  runtime_instrumentation/hotpatch_worker_hint_logging.sh
  CONTAINER_NAME=dynamo-sglang-worker runtime_instrumentation/hotpatch_worker_hint_logging.sh
  runtime_instrumentation/hotpatch_worker_hint_logging.sh --no-restart

Fields added to worker [RUNTIME_JSON] events:
  agent_hints
  agent_hints_source
  agent_hints_keys
  hint_probe_id
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --help|-h)
      usage
      exit 0
      ;;
    --no-restart)
      RESTART_CONTAINER=0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "docker was not found on PATH. Run this on the host where the containers are running." >&2
  exit 127
fi

if ! docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  echo "Container not found: $CONTAINER_NAME" >&2
  echo "Available containers:" >&2
  docker ps --format '  {{.Names}}  {{.Image}}  {{.Status}}' >&2 || true
  exit 1
fi

WORK_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

echo "Inspecting Python module paths in $CONTAINER_NAME..."
MODULE_PATHS_JSON="$(
  docker exec "$CONTAINER_NAME" sh -lc 'python3 - <<'"'"'PY'"'"'
import importlib.util
import json
from pathlib import Path
import sys

modules = {
    "decode_handler": "dynamo.sglang.request_handlers.llm.decode_handler",
    "prefill_handler": "dynamo.sglang.request_handlers.llm.prefill_handler",
}
paths = {}
for key, name in modules.items():
    spec = importlib.util.find_spec(name)
    if spec is None or not spec.origin:
        print(f"Could not find module path for {name}", file=sys.stderr)
        sys.exit(1)
    paths[key] = spec.origin

common_spec = importlib.util.find_spec("dynamo.common")
if (
    common_spec is None
    or common_spec.submodule_search_locations is None
    or not list(common_spec.submodule_search_locations)
):
    print("Could not find package path for dynamo.common", file=sys.stderr)
    sys.exit(1)
paths["runtime_logging"] = str(
    Path(list(common_spec.submodule_search_locations)[0]) / "runtime_logging.py"
)
print(json.dumps(paths))
PY'
)"

echo "$MODULE_PATHS_JSON" > "$WORK_DIR/module_paths.json"

python3 - "$WORK_DIR/module_paths.json" <<'PY'
import json
import sys
from pathlib import Path

paths = json.loads(Path(sys.argv[1]).read_text())
for key, value in paths.items():
    print(f"{key}: {value}")
PY

copy_from_container() {
  local key="$1"
  local remote_path
  remote_path="$(python3 - "$WORK_DIR/module_paths.json" "$key" <<'PY'
import json
import sys
from pathlib import Path

paths = json.loads(Path(sys.argv[1]).read_text())
print(paths[sys.argv[2]])
PY
)"
  docker cp "$CONTAINER_NAME:$remote_path" "$WORK_DIR/$key.py"
  cp "$WORK_DIR/$key.py" "$WORK_DIR/$key.py.original"
}

copy_from_container decode_handler
copy_from_container prefill_handler

echo "Patching copied Python files..."
python3 - "$WORK_DIR" <<'PY'
import sys
from pathlib import Path

work_dir = Path(sys.argv[1])

RUNTIME_LOGGING_SOURCE = '''"""Helpers for opt-in structured runtime JSON logging."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_RUNTIME_JSON_ENV = "DYN_RUNTIME_JSON_LOGS"
_RUNTIME_JSON_PREFIX = "[RUNTIME_JSON]"
_OBSERVABILITY_KEY = "runtime_observability"


def runtime_json_logs_enabled() -> bool:
    return os.environ.get(_RUNTIME_JSON_ENV, "").lower() not in ("", "0", "false")


def _sanitize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key is not None}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item) for item in value]

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _sanitize(model_dump())

    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        try:
            return _sanitize(tolist())
        except Exception:
            pass

    return str(value)


def extract_runtime_observability(request: dict[str, Any]) -> dict[str, Any]:
    extra_args = request.get("extra_args")
    if not isinstance(extra_args, dict):
        return {}
    runtime_observability = extra_args.get(_OBSERVABILITY_KEY)
    if not isinstance(runtime_observability, dict):
        return {}
    return _sanitize(runtime_observability)


def extract_request_context(request: dict[str, Any]) -> dict[str, Any] | None:
    nvext = request.get("nvext")
    if isinstance(nvext, dict):
        request_context = nvext.get("request_context")
        if isinstance(request_context, dict):
            return _sanitize(request_context)

    runtime_observability = extract_runtime_observability(request)
    request_context = runtime_observability.get("request_context")
    if isinstance(request_context, dict):
        return _sanitize(request_context)

    nested_nvext = runtime_observability.get("nvext")
    if isinstance(nested_nvext, dict):
        request_context = nested_nvext.get("request_context")
        if isinstance(request_context, dict):
            return _sanitize(request_context)

    return None


def extract_agent_hints_with_source(
    request: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    nvext = request.get("nvext")
    if isinstance(nvext, dict):
        agent_hints = nvext.get("agent_hints")
        if isinstance(agent_hints, dict):
            return _sanitize(agent_hints), "nvext.agent_hints"

    runtime_observability = extract_runtime_observability(request)
    agent_hints = runtime_observability.get("agent_hints")
    if isinstance(agent_hints, dict):
        return _sanitize(agent_hints), "runtime_observability.agent_hints"

    nested_nvext = runtime_observability.get("nvext")
    if isinstance(nested_nvext, dict):
        agent_hints = nested_nvext.get("agent_hints")
        if isinstance(agent_hints, dict):
            return _sanitize(agent_hints), "runtime_observability.nvext.agent_hints"

    return None, "missing"


def extract_agent_hints(request: dict[str, Any]) -> dict[str, Any] | None:
    agent_hints, _source = extract_agent_hints_with_source(request)
    return agent_hints


def agent_hint_log_fields(request: dict[str, Any]) -> dict[str, Any]:
    agent_hints, source = extract_agent_hints_with_source(request)
    if not isinstance(agent_hints, dict):
        return {
            "agent_hints": None,
            "agent_hints_source": source,
            "agent_hints_keys": [],
            "hint_probe_id": None,
        }
    return {
        "agent_hints": agent_hints,
        "agent_hints_source": source,
        "agent_hints_keys": sorted(str(key) for key in agent_hints),
        "hint_probe_id": agent_hints.get("hint_probe_id"),
    }


def preferred_request_id(request: dict[str, Any], fallback: str | None = None) -> str | None:
    request_context = extract_request_context(request)
    if isinstance(request_context, dict):
        request_id = request_context.get("request_id")
        if isinstance(request_id, str) and request_id:
            return request_id

    runtime_observability = extract_runtime_observability(request)
    runtime_request_id = runtime_observability.get("runtime_request_id")
    if isinstance(runtime_request_id, str) and runtime_request_id:
        return runtime_request_id

    frontend_request_id = runtime_observability.get("frontend_request_id")
    if isinstance(frontend_request_id, str) and frontend_request_id:
        return frontend_request_id

    return fallback


def emit_runtime_event(
    logger: logging.Logger,
    event_type: str,
    component: str,
    **payload: Any,
) -> None:
    if not runtime_json_logs_enabled():
        return

    event: dict[str, Any] = {
        "event_type": event_type,
        "component": component,
    }
    for key, value in payload.items():
        event[key] = _sanitize(value)

    logger.info(
        "%s %s",
        _RUNTIME_JSON_PREFIX,
        json.dumps(event, sort_keys=True, separators=(",", ":")),
    )
'''


def patch_runtime_logging(path: Path) -> None:
    path.write_text(RUNTIME_LOGGING_SOURCE)


def add_runtime_logging_import(text: str) -> str:
    if "from dynamo.common.runtime_logging import" in text:
        required = [
            "agent_hint_log_fields",
            "emit_runtime_event",
            "extract_request_context",
            "preferred_request_id",
        ]
        for name in required:
            if name not in text:
                marker = "from dynamo.common.runtime_logging import (\n"
                text = text.replace(marker, marker + f"    {name},\n", 1)
        return text

    import_block = (
        "from dynamo.common.runtime_logging import (\n"
        "    agent_hint_log_fields,\n"
        "    emit_runtime_event,\n"
        "    extract_request_context,\n"
        "    preferred_request_id,\n"
        ")\n"
    )
    marker = "from dynamo._core import Context\n"
    if marker not in text:
        raise SystemExit("Could not find Context import anchor for runtime_logging import")
    return text.replace(marker, marker + import_block, 1)


def insert_before_marker(text: str, insertion: str, markers: list[str], label: str) -> str:
    for marker in markers:
        if marker in text:
            return text.replace(marker, insertion + marker, 1)
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("class ") or line.startswith("def "):
            return "".join(lines[:index]) + insertion + "".join(lines[index:])
    raise SystemExit(f"Could not find {label} insertion anchor")


def insert_after_marker(text: str, insertion: str, markers: list[str], label: str) -> str:
    for marker in markers:
        if marker in text:
            return text.replace(marker, marker + insertion, 1)
    raise SystemExit(f"Could not find {label} insertion anchor")


def ensure_decode_helper(text: str) -> str:
    if "def _decode_request_payload(" in text:
        text = text.replace(
            '        "request_context": request_context,\n'
            '        "agent_hints": agent_hints,\n',
            '        "request_context": request_context,\n'
            '        **agent_hint_log_fields(request),\n',
            1,
        )
        text = text.replace("    agent_hints = extract_agent_hints(request)\n", "", 1)
        return text

    helper = '''

def _decode_request_payload(
    request: Dict[str, Any],
    runtime_context_id: str,
) -> Dict[str, Any]:
    request_context = extract_request_context(request)
    external_request_id = preferred_request_id(
        request, fallback=runtime_context_id
    ) or runtime_context_id
    return {
        "external_request_id": external_request_id,
        "runtime_context_id": runtime_context_id,
        "request_context": request_context,
        **agent_hint_log_fields(request),
    }
'''
    return insert_before_marker(
        text,
        helper,
        [
            "\ndef _top_logprobs_allowed() -> bool:\n",
            "\nclass DecodeWorkerHandler",
            "\nclass DecodeHandler",
            "\nclass ",
        ],
        "decode helper",
    )


def ensure_prefill_helper(text: str) -> str:
    if "def _prefill_request_payload(" in text:
        text = text.replace(
            '        "request_context": request_context,\n'
            '        "agent_hints": agent_hints,\n',
            '        "request_context": request_context,\n'
            '        **agent_hint_log_fields(request),\n',
            1,
        )
        text = text.replace("    agent_hints = extract_agent_hints(request)\n", "", 1)
        return text

    helper = '''

def _prefill_request_payload(
    request: Dict[str, Any],
    runtime_context_id: str,
) -> Dict[str, Any]:
    request_context = extract_request_context(request)
    external_request_id = preferred_request_id(
        request, fallback=runtime_context_id
    ) or runtime_context_id
    return {
        "external_request_id": external_request_id,
        "runtime_context_id": runtime_context_id,
        "request_context": request_context,
        **agent_hint_log_fields(request),
    }
'''
    return insert_before_marker(
        text,
        helper,
        [
            "\nclass PrefillWorkerHandler",
            "\nclass PrefillHandler",
            "\nclass ",
        ],
        "prefill helper",
    )


def ensure_decode_emit(text: str) -> str:
    if '"worker.decode.request_received"' in text:
        return text
    insertion = (
        "        runtime_context_id = context.id()\n"
        + "        emit_runtime_event(\n"
        + "            logging.getLogger(__name__),\n"
        + '            "worker.decode.request_received",\n'
        + '            "worker.decode",\n'
        + "            **_decode_request_payload(request, runtime_context_id),\n"
        + "            model=request.get(\"model\"),\n"
        + "            serving_mode=str(getattr(getattr(self, \"config\", None), \"serving_mode\", None)),\n"
        + "        )\n"
    )
    return insert_after_marker(
        text,
        insertion,
        [
            '        logging.debug(f"New Request ID: {context.id()}")\n',
            '        logging.debug("New Request ID: %s", context.id())\n',
            "        trace_id = context.trace_id\n",
        ],
        "decode request_received log",
    )


def ensure_prefill_emit(text: str) -> str:
    if '"worker.prefill.request_received"' in text:
        return text
    insertion = (
        "        runtime_context_id = context.id()\n"
        + "        emit_runtime_event(\n"
        + "            logging.getLogger(__name__),\n"
        + '            "worker.prefill.request_received",\n'
        + '            "worker.prefill",\n'
        + "            **_prefill_request_payload(request.get(\"request\", request), runtime_context_id),\n"
        + "        )\n\n"
    )
    return insert_after_marker(
        text,
        insertion,
        [
            '        logging.debug(f"New Request ID: {context.id()}")\n',
            '        logging.debug("New Request ID: %s", context.id())\n',
            "        trace_id = context.trace_id\n",
        ],
        "prefill request_received log",
    )


def patch_worker_handler(path: Path, helper_name: str) -> None:
    text = path.read_text()
    text = add_runtime_logging_import(text)
    if helper_name == "_decode_request_payload":
        text = ensure_decode_helper(text)
        text = ensure_decode_emit(text)
    elif helper_name == "_prefill_request_payload":
        text = ensure_prefill_helper(text)
        text = ensure_prefill_emit(text)
    else:
        raise SystemExit(f"Unknown helper: {helper_name}")
    path.write_text(text)


patch_runtime_logging(work_dir / "runtime_logging.py")
patch_worker_handler(work_dir / "decode_handler.py", "_decode_request_payload")
patch_worker_handler(work_dir / "prefill_handler.py", "_prefill_request_payload")
PY

echo "Copying patched files back into $CONTAINER_NAME..."
copy_to_container() {
  local key="$1"
  local remote_path
  remote_path="$(python3 - "$WORK_DIR/module_paths.json" "$key" <<'PY'
import json
import sys
from pathlib import Path

paths = json.loads(Path(sys.argv[1]).read_text())
print(paths[sys.argv[2]])
PY
)"
  docker cp "$WORK_DIR/$key.py" "$CONTAINER_NAME:$remote_path"
}

copy_to_container runtime_logging
copy_to_container decode_handler
copy_to_container prefill_handler

echo "Compile-checking patched files inside $CONTAINER_NAME..."
docker exec "$CONTAINER_NAME" sh -lc 'python3 - <<'"'"'PY'"'"'
import inspect
import py_compile
from pathlib import Path

modules = [
    "dynamo.common.runtime_logging",
    "dynamo.sglang.request_handlers.llm.decode_handler",
    "dynamo.sglang.request_handlers.llm.prefill_handler",
]
for name in modules:
    mod = __import__(name, fromlist=["*"])
    path = inspect.getfile(mod)
    cfile = f"/tmp/{Path(path).name}.{name.replace(chr(46), chr(95))}.pyc"
    py_compile.compile(path, cfile=cfile, doraise=True)
    print(f"compiled: {path}")
PY'

if [[ "$RESTART_CONTAINER" == "1" ]]; then
  echo "Restarting $CONTAINER_NAME..."
  docker restart "$CONTAINER_NAME" >/dev/null
else
  echo "Skipping restart because --no-restart was provided."
fi

echo "Worker hot-patch complete."
echo "After the next run, check for:"
echo "  docker logs $CONTAINER_NAME 2>&1 | grep -E 'agent_hints_source|hint_probe_id|agent_hints_keys'"
