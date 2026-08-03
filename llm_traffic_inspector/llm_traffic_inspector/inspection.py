from __future__ import annotations

import json
from typing import Any

from .hints import detect_hints, flatten_with_values
from .redaction import redact_json, safe_headers, sha256_short, summarize_value


def parse_json_body(body: bytes, content_type: str = "") -> tuple[Any | None, str | None]:
    if not body:
        return None, None
    should_try = "json" in content_type.lower() or body.lstrip().startswith((b"{", b"["))
    if not should_try:
        return None, "not_json"
    try:
        return json.loads(body.decode("utf-8")), None
    except Exception as exc:  # noqa: BLE001 - diagnostics should preserve parse failure.
        return None, f"{type(exc).__name__}: {exc}"


def inspect_request(
    *,
    method: str,
    path: str,
    query_string: bytes,
    client_host: str,
    headers: dict[str, str],
    body: bytes,
    capture_mode: str,
    upstream_url: str,
) -> dict[str, Any]:
    safe_request_headers = safe_headers(headers)
    content_type = headers.get("content-type", headers.get("Content-Type", ""))
    payload, json_error = parse_json_body(body, content_type)
    metrics = request_metrics(payload)
    field_paths = sorted({path for path, _ in flatten_with_values(payload)}) if payload is not None else []
    hint_findings = [
        {
            "path": item.path,
            "category": item.category,
            "example_safe_value": item.example_safe_value,
        }
        for item in detect_hints(payload, safe_request_headers, endpoint=path)
    ]

    body_record: dict[str, Any]
    if payload is None:
        body_record = {
            "mode": capture_mode,
            "json_parse_status": json_error or "empty",
            "sha256_16": sha256_short(body) if body else "",
        }
    elif capture_mode == "full":
        body_record = {
            "mode": "full",
            "json_parse_status": "ok",
            "json": redact_json(payload),
        }
    else:
        body_record = {
            "mode": "safe",
            "json_parse_status": "ok",
            "json_structure": summarize_value(payload),
            "sha256_16": sha256_short(body),
        }

    return {
        "method": method,
        "endpoint": "/" + path.lstrip("/"),
        "query_string": query_string.decode("utf-8", errors="replace"),
        "client_address": client_host,
        "content_type": content_type,
        "safe_request_headers": safe_request_headers,
        "request_body_size_bytes": len(body),
        "request_body": body_record,
        "json_field_paths": field_paths,
        "candidate_hint_fields": hint_findings,
        "model": metrics["model"],
        "stream_requested": metrics["stream_requested"],
        "message_count": metrics["message_count"],
        "tool_count": metrics["tool_count"],
        "system_prompt_chars": metrics["system_prompt_chars"],
        "total_message_content_chars": metrics["total_message_content_chars"],
        "upstream_url": upstream_url,
    }


def request_metrics(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "model": None,
            "stream_requested": False,
            "message_count": 0,
            "tool_count": 0,
            "system_prompt_chars": 0,
            "total_message_content_chars": 0,
        }
    messages = payload.get("messages")
    input_value = payload.get("input")
    system_value = payload.get("system")
    instructions = payload.get("instructions")
    tools = payload.get("tools")
    message_count = len(messages) if isinstance(messages, list) else 0
    if message_count == 0 and isinstance(input_value, list):
        message_count = len(input_value)
    tool_count = len(tools) if isinstance(tools, list) else 0
    system_prompt_chars = 0
    if isinstance(instructions, str):
        system_prompt_chars += len(instructions)
    system_prompt_chars += content_chars(system_value)
    if isinstance(messages, list):
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") in {"system", "developer"}:
                system_prompt_chars += content_chars(msg.get("content"))
    total_message_content_chars = content_chars(messages) + content_chars(input_value) + content_chars(system_value)
    return {
        "model": payload.get("model"),
        "stream_requested": bool(payload.get("stream")),
        "message_count": message_count,
        "tool_count": tool_count,
        "system_prompt_chars": system_prompt_chars,
        "total_message_content_chars": total_message_content_chars,
    }


def content_chars(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value)
    if isinstance(value, list):
        return sum(content_chars(item) for item in value)
    if isinstance(value, dict):
        total = 0
        for key, item in value.items():
            if key in {"text", "content", "input", "output", "tool_result"}:
                total += content_chars(item)
            elif isinstance(item, (dict, list)):
                total += content_chars(item)
        return total
    return 0


def response_usage_metadata(payload: Any) -> dict[str, Any]:
    usage = find_first_key(payload, "usage")
    service_tier = find_first_key(payload, "service_tier")
    cached = collect_cached_token_fields(payload)
    return {
        "usage": usage if isinstance(usage, dict) else None,
        "cached_token_fields": cached,
        "service_tier": service_tier,
    }


def find_first_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for item in value.values():
            found = find_first_key(item, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_first_key(item, key)
            if found is not None:
                return found
    return None


def collect_cached_token_fields(value: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if "cached" in str(key).lower() and "token" in str(key).lower():
                out[path] = item
            out.update(collect_cached_token_fields(item, path))
    elif isinstance(value, list):
        for idx, item in enumerate(value[:20]):
            out.update(collect_cached_token_fields(item, f"{prefix}[{idx}]"))
    return out

