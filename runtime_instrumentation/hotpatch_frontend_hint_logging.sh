#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-dynamo-frontend}"
RESTART_CONTAINER=1

usage() {
  cat <<'USAGE'
Hot-patch frontend-side Dynamo request hint logging inside a running container.

This does not rebuild any Docker image. It copies the installed frontend Python
file out of the container, adds one incoming-request [RUNTIME_JSON] checkpoint,
copies the patched file back, compile-checks it, and restarts only the frontend
container.

Usage:
  runtime_instrumentation/hotpatch_frontend_hint_logging.sh
  CONTAINER_NAME=dynamo-frontend runtime_instrumentation/hotpatch_frontend_hint_logging.sh
  runtime_instrumentation/hotpatch_frontend_hint_logging.sh --no-restart

Fields added to frontend [RUNTIME_JSON] events:
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

candidate_modules = [
    "dynamo.frontend.sglang_processor",
    "dynamo.frontend.vllm_processor",
    "dynamo.frontend.processor",
    "dynamo.frontend.main",
]
paths = {}

selected_module = None
selected_origin = None
for name in candidate_modules:
    spec = importlib.util.find_spec(name)
    if spec is None or not spec.origin:
        continue
    try:
        text = Path(spec.origin).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    if "async def generator" in text and "request" in text:
        selected_module = name
        selected_origin = spec.origin
        break

frontend_spec = importlib.util.find_spec("dynamo.frontend")
if (
    selected_origin is None
    and frontend_spec is not None
    and frontend_spec.submodule_search_locations is not None
):
    for package_root in frontend_spec.submodule_search_locations:
        for path in sorted(Path(package_root).glob("*.py")):
            if path.name.startswith("__"):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "async def generator" in text and "request" in text:
                selected_module = f"dynamo.frontend.{path.stem}"
                selected_origin = str(path)
                break
        if selected_origin is not None:
            break

if selected_origin is None or selected_module is None:
    print("Could not find an installed Dynamo frontend processor with async generator(request)", file=sys.stderr)
    if frontend_spec is not None and frontend_spec.submodule_search_locations is not None:
        print("Available dynamo.frontend Python files:", file=sys.stderr)
        for package_root in frontend_spec.submodule_search_locations:
            for path in sorted(Path(package_root).glob("*.py")):
                print(f"  {path}", file=sys.stderr)
    sys.exit(1)

paths["frontend_processor"] = selected_origin
paths["frontend_processor_module"] = selected_module

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

FRONTEND_PROCESSOR_MODULE="$(
  python3 - "$WORK_DIR/module_paths.json" <<'PY'
import json
import sys
from pathlib import Path

paths = json.loads(Path(sys.argv[1]).read_text())
print(paths["frontend_processor_module"])
PY
)"

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

copy_from_container frontend_processor

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
import sys
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

    line = f"{_RUNTIME_JSON_PREFIX} {json.dumps(event, sort_keys=True, separators=(',', ':'))}"
    logger.info("%s", line)
    if os.environ.get("DYN_RUNTIME_JSON_PRINT", "1").lower() not in ("", "0", "false"):
        print(line, file=sys.stderr, flush=True)
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
        marker = "from dynamo.common.runtime_logging import (\n"
        for name in required:
            if name not in text:
                if marker not in text:
                    raise SystemExit("Found runtime_logging import, but not in expected multiline form")
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
    markers = [
        "from dynamo._internal import ModelDeploymentCard\n",
        "from dynamo._core import Client\n",
        "from dynamo.llm import (\n",
    ]
    for marker in markers:
        if marker in text:
            return text.replace(marker, marker + import_block, 1)

    lines = text.splitlines(keepends=True)
    last_import_index = -1
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_index = index
    if last_import_index >= 0:
        return "".join(
            lines[: last_import_index + 1]
            + [import_block]
            + lines[last_import_index + 1 :]
        )

    raise SystemExit("Could not find frontend import anchor for runtime_logging import")


def insert_event_after_function_signature(
    text: str,
    function_prefix: str,
    event_type: str,
) -> str:
    if f'"{event_type}"' in text:
        return text

    lines = text.splitlines(keepends=True)
    def_start = None
    for index, line in enumerate(lines):
        if line.startswith(function_prefix):
            def_start = index
            break
    if def_start is None:
        return text

    insert_at = None
    for index in range(def_start, len(lines)):
        if lines[index].rstrip().endswith(":"):
            insert_at = index + 1
            break
    if insert_at is None:
        raise SystemExit("Could not find end of frontend generator signature")

    stripped = lines[insert_at].strip() if insert_at < len(lines) else ""
    if stripped.startswith(('"""', "'''")):
        quote = stripped[:3]
        if stripped.count(quote) >= 2 and len(stripped) > 3:
            insert_at += 1
        else:
            insert_at += 1
            while insert_at < len(lines) and quote not in lines[insert_at]:
                insert_at += 1
            insert_at += 1

    event_lines = [
        "        frontend_request_id = preferred_request_id(request)\n",
        "        emit_runtime_event(\n",
        "            __import__(\"logging\").getLogger(__name__),\n",
        f'            "{event_type}",\n',
        '            "frontend.processor",\n',
        "            frontend_request_id=frontend_request_id,\n",
        "            model=request.get(\"model\"),\n",
        "            request_keys=sorted(str(key) for key in request),\n",
        "            request_context=extract_request_context(request),\n",
        "            **agent_hint_log_fields(request),\n",
        "        )\n",
    ]
    return "".join(lines[:insert_at] + event_lines + lines[insert_at:])


def ensure_frontend_received_event(text: str) -> str:
    updated = insert_event_after_function_signature(
        text,
        "    async def generator(",
        "frontend.request.received",
    )
    updated = insert_event_after_function_signature(
        updated,
        "    async def _generator_inner(",
        "frontend.request.inner_received",
    )
    if (
        '"frontend.request.received"' not in updated
        and '"frontend.request.inner_received"' not in updated
    ):
        raise SystemExit("Could not find frontend generator insertion anchor")
    return updated


def patch_frontend_processor(path: Path) -> None:
    text = path.read_text()
    text = add_runtime_logging_import(text)
    text = ensure_frontend_received_event(text)
    path.write_text(text)


patch_runtime_logging(work_dir / "runtime_logging.py")
patch_frontend_processor(work_dir / "frontend_processor.py")
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
copy_to_container frontend_processor

echo "Compile-checking patched files inside $CONTAINER_NAME..."
FRONTEND_PROCESSOR_PATH="$(
  python3 - "$WORK_DIR/module_paths.json" <<'PY'
import json
import sys
from pathlib import Path

paths = json.loads(Path(sys.argv[1]).read_text())
print(paths["frontend_processor"])
PY
)"
RUNTIME_LOGGING_PATH="$(
  python3 - "$WORK_DIR/module_paths.json" <<'PY'
import json
import sys
from pathlib import Path

paths = json.loads(Path(sys.argv[1]).read_text())
print(paths["runtime_logging"])
PY
)"
docker exec \
  -e FRONTEND_PROCESSOR_PATH="$FRONTEND_PROCESSOR_PATH" \
  -e RUNTIME_LOGGING_PATH="$RUNTIME_LOGGING_PATH" \
  "$CONTAINER_NAME" sh -lc 'python3 - <<'"'"'PY'"'"'
import os
import py_compile
from pathlib import Path

paths = [
    os.environ["RUNTIME_LOGGING_PATH"],
    os.environ["FRONTEND_PROCESSOR_PATH"],
]
for path in paths:
    cfile = f"/tmp/{Path(path).name}.{Path(path).stem}.pyc"
    py_compile.compile(path, cfile=cfile, doraise=True)
    print(f"compiled: {path}")
PY'

docker exec "$CONTAINER_NAME" sh -lc 'python3 - <<'"'"'PY'"'"'
from dynamo.common.runtime_logging import agent_hint_log_fields

sample = {
    "nvext": {
        "agent_hints": {
            "hint_probe_id": "frontend-hotpatch-self-test",
            "priority": 5,
        }
    }
}
print(agent_hint_log_fields(sample))
PY'

if [[ "$RESTART_CONTAINER" == "1" ]]; then
  echo "Restarting $CONTAINER_NAME..."
  docker restart "$CONTAINER_NAME" >/dev/null
else
  echo "Skipping restart because --no-restart was provided."
fi

echo "Frontend hot-patch complete."
echo "After the next run, check for:"
echo "  docker logs $CONTAINER_NAME 2>&1 | grep -E 'frontend.request.received|agent_hints_source|hint_probe_id|agent_hints_keys'"
