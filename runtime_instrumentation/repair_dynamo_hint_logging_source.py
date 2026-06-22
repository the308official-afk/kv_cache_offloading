#!/usr/bin/env python3
"""Repair Dynamo source logging so worker events expose hint proof fields.

This is intentionally small and idempotent. Use it when the broader runtime JSON
patch is already partly present, but the source still logs only `agent_hints`
instead of `agent_hints_source`, `agent_hints_keys`, and `hint_probe_id`.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(os.environ.get("SOURCE_DIR", ROOT / "upstream" / "dynamo"))

RUNTIME_LOGGING_TEMPLATE = textwrap.dedent(
    '''\
    """Helpers for opt-in structured runtime JSON logging."""

    from __future__ import annotations

    import json
    import logging
    import os
    from typing import Any

    _RUNTIME_JSON_ENV = "DYN_RUNTIME_JSON_LOGS"
    _RUNTIME_JSON_PREFIX = "[RUNTIME_JSON]"
    _OBSERVABILITY_KEY = "runtime_observability"


    def _maybe_register_transfer_runtime_event(event: dict[str, Any]) -> None:
        try:
            from sglang.srt.mem_cache.transfer_logging import register_runtime_event_metadata
        except Exception:
            return

        try:
            register_runtime_event_metadata(event)
        except Exception:
            return


    def runtime_json_logs_enabled() -> bool:
        return os.environ.get(_RUNTIME_JSON_ENV, "").lower() not in ("", "0", "false")


    def _sanitize(value: Any) -> Any:
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, item in value.items():
                if key is None:
                    continue
                sanitized[str(key)] = _sanitize(item)
            return sanitized
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


    def build_runtime_observability_extra_args(
        request: dict[str, Any],
        frontend_request_id: str,
        runtime_request_id: str,
    ) -> dict[str, Any] | None:
        base_extra_args = request.get("extra_args")
        extra_args = _sanitize(base_extra_args) if isinstance(base_extra_args, dict) else {}

        runtime_observability: dict[str, Any] = {
            "frontend_request_id": frontend_request_id,
            "runtime_request_id": runtime_request_id,
        }

        request_context = extract_request_context(request)
        if request_context:
            runtime_observability["request_context"] = request_context

        agent_hints, agent_hints_source = extract_agent_hints_with_source(request)
        if agent_hints:
            runtime_observability["agent_hints"] = agent_hints
            runtime_observability["agent_hints_source"] = agent_hints_source
            runtime_observability["agent_hints_keys"] = sorted(str(key) for key in agent_hints)
            runtime_observability["hint_probe_id"] = agent_hints.get("hint_probe_id")

        if request_context or agent_hints:
            runtime_observability["nvext"] = {}
            if request_context:
                runtime_observability["nvext"]["request_context"] = request_context
            if agent_hints:
                runtime_observability["nvext"]["agent_hints"] = agent_hints

        extra_args[_OBSERVABILITY_KEY] = runtime_observability
        return extra_args


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

        _maybe_register_transfer_runtime_event(event)

        logger.info(
            "%s %s",
            _RUNTIME_JSON_PREFIX,
            json.dumps(event, sort_keys=True, separators=(",", ":")),
        )
    '''
)


def write_if_changed(path: Path, text: str) -> None:
    old = path.read_text()
    if old == text:
        print(f"unchanged: {path}")
        return
    path.write_text(text)
    print(f"updated: {path}")


def repair_runtime_logging() -> None:
    path = SOURCE_DIR / "components/src/dynamo/common/runtime_logging.py"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(RUNTIME_LOGGING_TEMPLATE)
        print(f"created: {path}")
        return

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

    if helper_name == "_decode_request_payload":
        old_import = """from dynamo._core import Context
from dynamo.common.constants import DisaggregationMode
"""
        new_import = """from dynamo._core import Context
from dynamo.common.constants import DisaggregationMode
from dynamo.common.runtime_logging import (
    agent_hint_log_fields,
    emit_runtime_event,
    extract_request_context,
    preferred_request_id,
)
"""
        if "from dynamo.common.runtime_logging import (" not in text:
            if old_import not in text:
                raise SystemExit(f"Could not patch runtime logging imports in {path}")
            text = text.replace(old_import, new_import, 1)

        helper_block = '''

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
        anchor = '_TOP_LOGPROBS_UNSUPPORTED_MSG = (\n'
        if "_decode_request_payload(" not in text:
            end_marker = ')\n\n\ndef _top_logprobs_allowed()'
            if end_marker not in text:
                raise SystemExit(f"Could not insert decode payload helper in {path}")
            text = text.replace(end_marker, ')\n' + helper_block + '\n\ndef _top_logprobs_allowed()', 1)

        old_generate = '''        logging.debug(f"New Request ID: {context.id()}")
        trace_id = context.trace_id
'''
        new_generate = '''        runtime_context_id = context.id()
        logging.debug(f"New Request ID: {runtime_context_id}")
        emit_runtime_event(
            logging.getLogger(__name__),
            "worker.decode.request_received",
            "worker.decode",
            **_decode_request_payload(request, runtime_context_id),
            model=self.config.server_args.served_model_name,
            serving_mode=str(self.serving_mode),
        )
        trace_id = context.trace_id
'''
        if 'worker.decode.request_received' not in text:
            if old_generate not in text:
                raise SystemExit(f"Could not patch decode generate() runtime event in {path}")
            text = text.replace(old_generate, new_generate, 1)

    elif helper_name == "_prefill_request_payload":
        old_import = """from dynamo._core import Context
from dynamo.common.utils.otel_tracing import build_trace_headers
"""
        new_import = """from dynamo._core import Context
from dynamo.common.runtime_logging import (
    agent_hint_log_fields,
    emit_runtime_event,
    extract_request_context,
    preferred_request_id,
)
from dynamo.common.utils.otel_tracing import build_trace_headers
"""
        if "from dynamo.common.runtime_logging import (" not in text:
            if old_import not in text:
                raise SystemExit(f"Could not patch runtime logging imports in {path}")
            text = text.replace(old_import, new_import, 1)

        helper_block = '''

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
        if "_prefill_request_payload(" not in text:
            end_marker = "_DP_RANK_UNSET = 2**32 - 1\n"
            if end_marker not in text:
                raise SystemExit(f"Could not insert prefill payload helper in {path}")
            text = text.replace(end_marker, end_marker + helper_block + "\n", 1)

        old_generate = '''        logging.debug(f"New Request ID: {context.id()}")
        trace_id = context.trace_id
'''
        new_generate = '''        runtime_context_id = context.id()
        logging.debug(f"New Request ID: {runtime_context_id}")
        trace_id = context.trace_id

        emit_runtime_event(
            logging.getLogger(__name__),
            "worker.prefill.request_received",
            "worker.prefill",
            **_prefill_request_payload(inner_request, runtime_context_id),
            model=self.config.server_args.served_model_name,
            serving_mode="prefill",
        )
'''
        if 'worker.prefill.request_received' not in text:
            # this replacement must happen after inner_request is defined, so we
            # rewrite the old logging/trace block and keep the surrounding request
            # parsing intact.
            if old_generate not in text:
                raise SystemExit(f"Could not patch prefill generate() runtime event in {path}")
            text = text.replace(old_generate, '        runtime_context_id = context.id()\n        logging.debug(f"New Request ID: {runtime_context_id}")\n        trace_id = context.trace_id\n', 1)
            after_request_parse = '''            sampling_params = {
                k: v for k, v in sampling_params.items() if v is not None
            }
'''
            insertion = '''            sampling_params = {
                k: v for k, v in sampling_params.items() if v is not None
            }

        emit_runtime_event(
            logging.getLogger(__name__),
            "worker.prefill.request_received",
            "worker.prefill",
            **_prefill_request_payload(inner_request, runtime_context_id),
            model=self.config.server_args.served_model_name,
            serving_mode="prefill",
        )
'''
            if after_request_parse not in text:
                raise SystemExit(f"Could not place prefill runtime event after request parsing in {path}")
            text = text.replace(after_request_parse, insertion, 1)

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
