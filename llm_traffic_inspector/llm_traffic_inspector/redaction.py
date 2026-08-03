from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Any


REDACTED = "[REDACTED]"

SECRET_HEADER_NAMES = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "api-key",
    "cookie",
    "set-cookie",
}

SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|authorization|bearer|oauth|session|secret|password|token|cookie)",
    re.IGNORECASE,
)

BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
LONG_SECRETISH_RE = re.compile(r"\b(sk-[A-Za-z0-9_-]{12,}|[A-Za-z0-9_-]{32,})\b")


def sha256_short(data: bytes | str, length: int = 16) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8", errors="replace")
    return hashlib.sha256(data).hexdigest()[:length]


def redact_header_value(name: str, value: str) -> str:
    if name.lower() in SECRET_HEADER_NAMES:
        return REDACTED
    return redact_secretish_text(value)


def safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(k): redact_header_value(str(k), str(v)) for k, v in headers.items()}


def redact_secretish_text(value: str) -> str:
    value = BEARER_RE.sub("Bearer " + REDACTED, value)
    value = LONG_SECRETISH_RE.sub(REDACTED, value)
    return value


def redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if SECRET_KEY_RE.search(str(key)):
                out[str(key)] = REDACTED
            else:
                out[str(key)] = redact_json(item)
        return out
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, str):
        return redact_secretish_text(value)
    return value


def summarize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            "type": "object",
            "key_count": len(value),
            "keys": {str(k): summarize_value(v) for k, v in value.items()},
        }
    if isinstance(value, list):
        examples = [summarize_value(item) for item in value[:3]]
        return {"type": "array", "length": len(value), "examples": examples}
    if isinstance(value, str):
        return {
            "type": "string",
            "chars": len(value),
            "sha256_16": sha256_short(value),
        }
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if value is None:
        return {"type": "null"}
    return {"type": type(value).__name__}

