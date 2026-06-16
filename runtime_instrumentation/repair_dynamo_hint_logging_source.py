#!/usr/bin/env python3
"""Repair Dynamo source logging so worker events expose hint proof fields.

This is intentionally small and idempotent. Use it when the broader runtime JSON
patch is already partly present, but the source still logs only `agent_hints`
instead of `agent_hints_source`, `agent_hints_keys`, and `hint_probe_id`.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(os.environ.get("SOURCE_DIR", ROOT / "upstream" / "dynamo"))


def write_if_changed(path: Path, text: str) -> None:
    old = path.read_text()
    if old == text:
        print(f"unchanged: {path}")
        return
    path.write_text(text)
    print(f"updated: {path}")


def repair_runtime_logging() -> None:
    path = SOURCE_DIR / "components/src/dynamo/common/runtime_logging.py"
    text = path.read_text()

    marker = '_OBSERVABILITY_KEY = "runtime_observability"\n'
    if "def _maybe_register_transfer_runtime_event" not in text:
        insertion = '''

def _maybe_register_transfer_runtime_event(event: dict[str, Any]) -> None:
    try:
        from sglang.srt.mem_cache.transfer_logging import register_runtime_event_metadata
    except Exception:
        return

    try:
        register_runtime_event_metadata(event)
    except Exception:
        return
'''
        if marker not in text:
            raise SystemExit(f"Could not find observability key marker in {path}")
        text = text.replace(marker, marker + insertion, 1)

    if "def extract_agent_hints_with_source" not in text:
        old = '''def extract_agent_hints(request: dict[str, Any]) -> dict[str, Any] | None:
    nvext = request.get("nvext")
    if isinstance(nvext, dict):
        agent_hints = nvext.get("agent_hints")
        if isinstance(agent_hints, dict):
            return _sanitize(agent_hints)

    runtime_observability = extract_runtime_observability(request)
    agent_hints = runtime_observability.get("agent_hints")
    if isinstance(agent_hints, dict):
        return _sanitize(agent_hints)

    nested_nvext = runtime_observability.get("nvext")
    if isinstance(nested_nvext, dict):
        agent_hints = nested_nvext.get("agent_hints")
        if isinstance(agent_hints, dict):
            return _sanitize(agent_hints)

    return None


'''
        new = '''def extract_agent_hints_with_source(
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


'''
        if old not in text:
            raise SystemExit(f"Could not find extract_agent_hints block in {path}")
        text = text.replace(old, new)

    old = '''    agent_hints = extract_agent_hints(request)
    if agent_hints:
        runtime_observability["agent_hints"] = agent_hints

    if request_context or agent_hints:
'''
    new = '''    agent_hints, agent_hints_source = extract_agent_hints_with_source(request)
    if agent_hints:
        runtime_observability["agent_hints"] = agent_hints
        runtime_observability["agent_hints_source"] = agent_hints_source
        runtime_observability["agent_hints_keys"] = sorted(str(key) for key in agent_hints)
        runtime_observability["hint_probe_id"] = agent_hints.get("hint_probe_id")

    if request_context or agent_hints:
'''
    if old in text:
        text = text.replace(old, new)

    emit_marker = '''    for key, value in payload.items():
        event[key] = _sanitize(value)

    logger.info(
'''
    emit_replacement = '''    for key, value in payload.items():
        event[key] = _sanitize(value)

    _maybe_register_transfer_runtime_event(event)

    logger.info(
'''
    if "_maybe_register_transfer_runtime_event(event)" not in text:
        if emit_marker not in text:
            raise SystemExit(f"Could not patch emit_runtime_event in {path}")
        text = text.replace(emit_marker, emit_replacement, 1)

    write_if_changed(path, text)


def repair_handler(path: Path, helper_name: str) -> None:
    text = path.read_text()
    text = text.replace("    extract_agent_hints,\n", "    agent_hint_log_fields,\n")
    text = text.replace("    agent_hints = extract_agent_hints(request)\n", "")
    text = text.replace(
        '''        "request_context": request_context,
        "agent_hints": agent_hints,
''',
        '''        "request_context": request_context,
        **agent_hint_log_fields(request),
''',
    )

    if "agent_hint_log_fields" not in text:
        raise SystemExit(f"Failed to add agent_hint_log_fields to {helper_name}: {path}")

    write_if_changed(path, text)


def main() -> None:
    repair_runtime_logging()
    repair_handler(
        SOURCE_DIR / "components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        "_decode_request_payload",
    )
    repair_handler(
        SOURCE_DIR / "components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py",
        "_prefill_request_payload",
    )
    print("Hint-aware worker logging source repair complete.")


if __name__ == "__main__":
    main()
