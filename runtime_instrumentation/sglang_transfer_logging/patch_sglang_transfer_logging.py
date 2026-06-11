#!/usr/bin/env python3
"""Patch extracted SGLang source with structured host/device transfer logging."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


HELPER_SOURCE = r'''"""Structured transfer logging for local SGLang instrumentation.

This module is intentionally dependency-light and enabled only when
SGLANG_TRANSFER_LOG=1. It is written beside memory_pool_host.py by the repo
patcher so the patched SGLang package can be bind-mounted into a worker image.
"""

from __future__ import annotations

import contextlib
import contextvars
import copy
import hashlib
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any

try:
    import torch
except Exception:  # pragma: no cover - instrumentation must not break startup.
    torch = None


_PREFIX = "[SGLANG_TRANSFER_JSON] "
_LOCK = threading.Lock()
_VALID_PROFILES = {"off", "light", "timing", "full"}


def _profile() -> str:
    raw = (os.environ.get("SGLANG_TRANSFER_LOG_PROFILE") or "").strip().lower()
    if not raw:
        return "light" if os.environ.get("SGLANG_TRANSFER_LOG") == "1" else "off"
    if raw not in _VALID_PROFILES:
        return "light"
    return raw


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except Exception:
        return default


_DETAIL_LIMIT = _env_int("SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS", 16 if _profile() == "full" else 4)
_TOKEN_PREVIEW = _env_int("SGLANG_TRANSFER_LOG_TOKEN_PREVIEW", 8 if _profile() == "full" else 0)
_INDEX_PREVIEW = int(os.environ.get("SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT", "32") or 32)
_MAX_TOKEN_ID = int(os.environ.get("SGLANG_TRANSFER_LOG_MAX_REASONABLE_TOKEN_ID", "10000000") or 10000000)
_MAX_SEMANTIC_TOKENS = int(os.environ.get("SGLANG_TRANSFER_LOG_MAX_SEMANTIC_TOKENS", "1000000") or 1000000)
_SEMANTIC_CONTEXT = contextvars.ContextVar("sglang_transfer_semantic_context", default=None)
_REQUEST_METADATA_KEYS = (
    "request_id",
    "external_request_id",
    "runtime_request_id",
    "runtime_context_id",
    "frontend_request_id",
    "sglang_request_id",
    "parent_run_id",
    "task_instance_id",
    "phase",
    "agent_phase",
    "step_index",
    "step_title",
    "app_variant",
    "hint_profile",
    "hint_probe_id",
)
_REQUEST_METADATA_ALIASES = {
    "rid": "sglang_request_id",
    "req_id": "sglang_request_id",
    "request_uuid": "sglang_request_id",
    "request_id": "request_id",
    "external_request_id": "external_request_id",
    "runtime_request_id": "runtime_request_id",
    "runtime_context_id": "runtime_context_id",
    "frontend_request_id": "frontend_request_id",
    "sglang_request_id": "sglang_request_id",
    "agent_phase": "agent_phase",
    "phase": "phase",
}
_REQUEST_CONTEXT_KEYS = ("request_context", "runtime_observability", "nvext", "sglang_transfer_context")
_AGENT_HINT_KEYS = ("agent_hints", "hints", "request_hints")
_REQUEST_LOOKUP_HINTS = (
    "request",
    "context",
    "hint",
    "req",
    "rid",
    "runtime",
    "observability",
    "metadata",
    "meta",
    "nvext",
    "agent",
    "operation",
    "op",
    "node",
)
_TOKEN_ATTR_NAMES = (
    "token_ids",
    "input_ids",
    "output_ids",
    "tokens",
    "input_tokens",
    "prefix_tokens",
    "new_input_tokens",
    "origin_input_ids",
    "fill_ids",
)
_STRUCTURAL_TOKEN_ATTR_NAMES = ("key",)


def _enabled() -> bool:
    return os.environ.get("SGLANG_TRANSFER_LOG") == "1" and _profile() != "off"


def _verbose() -> bool:
    return _env_bool("SGLANG_TRANSFER_LOG_VERBOSE", False)


def _sync_timing_enabled() -> bool:
    return _env_bool("SGLANG_TRANSFER_LOG_SYNC_TIMING", _profile() in {"timing", "full"})


def _semantic_tokens_enabled() -> bool:
    return _env_bool("SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS", _profile() == "full")


def _overhead_timing_enabled() -> bool:
    return _env_bool("SGLANG_TRANSFER_LOG_OVERHEAD_TIMING", False)


def _overhead_start(overhead: dict[str, float] | None) -> int | None:
    return time.perf_counter_ns() if overhead is not None else None


def _overhead_add(overhead: dict[str, float] | None, name: str, started_ns: int | None) -> None:
    if overhead is None or started_ns is None:
        return
    overhead[name] = overhead.get(name, 0.0) + (time.perf_counter_ns() - started_ns) / 1_000_000.0


def _overhead_call(overhead: dict[str, float] | None, name: str, fn: Any, *args: Any, **kwargs: Any) -> Any:
    started_ns = _overhead_start(overhead)
    try:
        return fn(*args, **kwargs)
    finally:
        _overhead_add(overhead, name, started_ns)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def _attach_overhead(target: dict[str, Any], overhead: dict[str, float] | None) -> None:
    if not overhead:
        return
    target["instrumentation_overhead_enabled"] = True
    for name, value in overhead.items():
        field = f"overhead_{name}_ms"
        target[field] = _safe_float(target.get(field)) + float(value)


def _finalize_overhead(target: dict[str, Any]) -> None:
    overhead_fields = [
        key
        for key in target
        if key.startswith("overhead_")
        and key.endswith("_ms")
        and key not in {
            "overhead_total_logger_ms",
            "overhead_token_ms",
            "overhead_json_write_ms",
        }
    ]
    if not overhead_fields:
        return
    target["instrumentation_overhead_enabled"] = True
    target["overhead_token_ms"] = sum(
        _safe_float(target.get(key))
        for key in (
            "overhead_semantic_token_extract_ms",
            "overhead_semantic_token_hash_ms",
            "overhead_local_token_preview_ms",
        )
    )
    target["overhead_json_write_ms"] = sum(
        _safe_float(target.get(key))
        for key in (
            "overhead_json_serialize_ms",
            "overhead_stderr_print_ms",
            "overhead_file_write_ms",
        )
    )
    target["overhead_total_logger_ms"] = sum(_safe_float(target.get(key)) for key in overhead_fields)


def _is_tensor(value: Any) -> bool:
    return torch is not None and isinstance(value, torch.Tensor)


def _tensor_nbytes(value: Any) -> int:
    if not _is_tensor(value):
        return 0
    try:
        return int(value.numel()) * int(value.element_size())
    except Exception:
        return 0


def _tensor_detail(name: str, value: Any) -> dict[str, Any] | None:
    if not _is_tensor(value):
        return None
    detail: dict[str, Any] = {
        "name": name,
        "shape": list(value.shape),
        "dtype": str(value.dtype),
        "device": str(value.device),
        "numel": int(value.numel()),
        "element_size": int(value.element_size()),
        "num_bytes": _tensor_nbytes(value),
    }
    return detail


def _walk_tensors(name: str, value: Any, details: list[dict[str, Any]], depth: int = 0) -> int:
    if depth > 3:
        return 0
    if _is_tensor(value):
        detail = _tensor_detail(name, value)
        if detail and len(details) < _DETAIL_LIMIT:
            details.append(detail)
        return _tensor_nbytes(value)
    if isinstance(value, dict):
        total = 0
        for key, item in list(value.items())[:64]:
            total += _walk_tensors(f"{name}.{key}", item, details, depth + 1)
        return total
    if isinstance(value, (list, tuple)):
        total = 0
        for index, item in enumerate(value[:64]):
            total += _walk_tensors(f"{name}[{index}]", item, details, depth + 1)
        return total
    return 0


def _allow_cuda_token_sync() -> bool:
    return _env_bool("SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC", False)


def _allow_cuda_index_sync() -> bool:
    return _env_bool("SGLANG_TRANSFER_LOG_INDEX_PREVIEW", False)


def _flatten_ints(value: Any, limit: int, *, allow_cuda_tensor_sync: bool = False) -> list[int]:
    if limit <= 0:
        return []
    if _is_tensor(value):
        if str(value.device) != "cpu" and not allow_cuda_tensor_sync:
            return []
        try:
            value = value.detach().flatten()[:limit].cpu().tolist()
        except Exception:
            return []
    if isinstance(value, bool):
        return []
    if isinstance(value, int):
        return [int(value)]
    if isinstance(value, (list, tuple)):
        out: list[int] = []
        for item in value:
            out.extend(_flatten_ints(item, limit - len(out), allow_cuda_tensor_sync=allow_cuda_tensor_sync))
            if len(out) >= limit:
                return out[:limit]
        return out
    return []


def _hash_ints(values: list[int]) -> str:
    return hashlib.sha256(
        json.dumps(values, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _sanitize_metadata(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return str(type(value).__name__)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _sanitize_metadata(item, depth + 1)
            for key, item in value.items()
            if key is not None
        }
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_metadata(item, depth + 1) for item in list(value)[:64]]
    return str(value)


def _is_metadata_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def _merge_request_metadata(target: dict[str, Any], source: dict[str, Any], source_name: str) -> None:
    for alias, canonical in _REQUEST_METADATA_ALIASES.items():
        value = source.get(alias)
        if _is_metadata_scalar(value) and value not in (None, "") and canonical not in target:
            target[canonical] = _sanitize_metadata(value)
            target.setdefault("request_metadata_source", f"{source_name}.{alias}")

    for key in _REQUEST_METADATA_KEYS:
        value = source.get(key)
        if value not in (None, "") and key not in target:
            target[key] = _sanitize_metadata(value)
            target.setdefault("request_metadata_source", source_name)

    for key in _AGENT_HINT_KEYS:
        value = source.get(key)
        if isinstance(value, dict):
            target.setdefault("agent_hints", _sanitize_metadata(value))
            target.setdefault("agent_hints_source", f"{source_name}.{key}")
            if "hint_probe_id" not in target and value.get("hint_probe_id") not in (None, ""):
                target["hint_probe_id"] = _sanitize_metadata(value["hint_probe_id"])
            if "phase" not in target and value.get("agent_phase") not in (None, ""):
                target["phase"] = _sanitize_metadata(value["agent_phase"])

    request_context = source.get("request_context")
    if isinstance(request_context, dict):
        target.setdefault("request_context", _sanitize_metadata(request_context))
        _merge_request_metadata(target, request_context, f"{source_name}.request_context")

    runtime_observability = source.get("runtime_observability")
    if isinstance(runtime_observability, dict):
        target.setdefault("runtime_observability", _sanitize_metadata(runtime_observability))
        _merge_request_metadata(target, runtime_observability, f"{source_name}.runtime_observability")

    nvext = source.get("nvext")
    if isinstance(nvext, dict):
        if isinstance(nvext.get("request_context"), dict):
            target.setdefault("request_context", _sanitize_metadata(nvext["request_context"]))
        _merge_request_metadata(target, nvext, f"{source_name}.nvext")


def _request_metadata_candidates_from_value(
    source: str,
    value: Any,
    *,
    depth: int = 0,
    seen: set[int] | None = None,
) -> dict[str, Any]:
    if depth > 4:
        return {}
    if seen is None:
        seen = set()
    if not isinstance(value, (str, bytes, int, float, bool, list, tuple, dict)) and not _is_tensor(value):
        ident = id(value)
        if ident in seen:
            return {}
        seen.add(ident)

    metadata: dict[str, Any] = {}
    if isinstance(value, dict):
        _merge_request_metadata(metadata, value, source)
        for key, item in list(value.items())[:128]:
            if item is None:
                continue
            key_text = str(key).lower()
            if key in _REQUEST_CONTEXT_KEYS + _AGENT_HINT_KEYS or any(hint in key_text for hint in _REQUEST_LOOKUP_HINTS):
                nested = _request_metadata_candidates_from_value(
                    f"{source}.{key}", item, depth=depth + 1, seen=seen
                )
                _merge_request_metadata(metadata, nested, f"{source}.{key}")
        return metadata

    object_values: dict[str, Any] = {}
    for attr in _REQUEST_METADATA_KEYS + tuple(_REQUEST_METADATA_ALIASES) + _REQUEST_CONTEXT_KEYS + _AGENT_HINT_KEYS:
        try:
            object_values[attr] = getattr(value, attr)
        except Exception:
            continue
    try:
        object_vars = vars(value)
    except Exception:
        object_vars = {}
    if isinstance(object_vars, dict):
        for key, item in list(object_vars.items())[:128]:
            key_text = str(key).lower()
            if key in _REQUEST_CONTEXT_KEYS + _AGENT_HINT_KEYS or any(hint in key_text for hint in _REQUEST_LOOKUP_HINTS):
                object_values.setdefault(str(key), item)

    if object_values:
        _merge_request_metadata(metadata, object_values, source)
        for key, item in list(object_values.items())[:128]:
            if item is not None:
                nested = _request_metadata_candidates_from_value(
                    f"{source}.{key}", item, depth=depth + 1, seen=seen
                )
                _merge_request_metadata(metadata, nested, f"{source}.{key}")
        return metadata
    return metadata


def _request_metadata_summary(locals_dict: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for name, value in locals_dict.items():
        if name == "self" or name.startswith("__sgl_transfer"):
            continue
        lowered = name.lower()
        if (
            any(key in lowered for key in _REQUEST_LOOKUP_HINTS)
            or isinstance(value, dict)
        ):
            nested = _request_metadata_candidates_from_value(name, value)
            _merge_request_metadata(metadata, nested, name)
    return metadata


def _looks_like_token_ids(values: list[int]) -> bool:
    return bool(values) and all(0 <= value <= _MAX_TOKEN_ID for value in values)


def _semantic_token_candidate(source: str, value: Any) -> tuple[str, list[int]] | None:
    values = _flatten_ints(
        value,
        _MAX_SEMANTIC_TOKENS,
        allow_cuda_tensor_sync=_allow_cuda_token_sync(),
    )
    if not _looks_like_token_ids(values):
        return None
    return source, values


def _semantic_token_candidates_from_value(
    source: str,
    value: Any,
    *,
    depth: int = 0,
    seen: set[int] | None = None,
) -> list[tuple[str, list[int]]]:
    if depth > 4:
        return []
    if seen is None:
        seen = set()
    if not isinstance(value, (str, bytes, int, float, bool, list, tuple, dict)) and not _is_tensor(value):
        ident = id(value)
        if ident in seen:
            return []
        seen.add(ident)

    candidates: list[tuple[str, list[int]]] = []
    candidate = _semantic_token_candidate(source, value)
    if candidate:
        candidates.append(candidate)

    if isinstance(value, dict):
        for key, item in list(value.items())[:64]:
            key_text = str(key)
            if key_text in _TOKEN_ATTR_NAMES or key_text in _STRUCTURAL_TOKEN_ATTR_NAMES:
                candidates.extend(
                    _semantic_token_candidates_from_value(
                        f"{source}.{key_text}", item, depth=depth + 1, seen=seen
                    )
                )
        return candidates

    if isinstance(value, (list, tuple)):
        combined: list[int] = []
        for index, item in enumerate(value[:64]):
            nested = _semantic_token_candidates_from_value(
                f"{source}[{index}]", item, depth=depth + 1, seen=seen
            )
            if not nested:
                continue
            _, nested_values = max(nested, key=lambda item: len(item[1]))
            combined.extend(nested_values)
            if len(combined) >= _MAX_SEMANTIC_TOKENS:
                break
        if combined:
            candidates.append((f"{source}[*]", combined[:_MAX_SEMANTIC_TOKENS]))
        return candidates

    for attr in _TOKEN_ATTR_NAMES + _STRUCTURAL_TOKEN_ATTR_NAMES:
        try:
            attr_value = getattr(value, attr)
        except Exception:
            continue
        candidates.extend(
            _semantic_token_candidates_from_value(
                f"{source}.{attr}", attr_value, depth=depth + 1, seen=seen
            )
        )
    return candidates


def _semantic_token_summary(
    function: str,
    locals_dict: dict[str, Any],
    overhead: dict[str, float] | None = None,
) -> dict[str, Any]:
    request_metadata = _overhead_call(
        overhead,
        "request_metadata_extract",
        _request_metadata_summary,
        locals_dict,
    )
    if not _semantic_tokens_enabled():
        return request_metadata

    direct_names = (
        "token_ids",
        "input_ids",
        "output_ids",
        "tokens",
        "input_tokens",
        "prefix_tokens",
    )
    object_name_hints = ("node", "nodes", "leaf", "root", "req", "request", "operation", "cache", "entry", "key")

    token_extract_started_ns = _overhead_start(overhead)
    try:
        candidates: list[tuple[str, list[int]]] = []
        for name, value in locals_dict.items():
            if name == "self" or name.startswith("__sgl_transfer"):
                continue
            lowered = name.lower()
            if (
                any(candidate == lowered or candidate in lowered for candidate in direct_names)
                or any(hint in lowered for hint in object_name_hints)
                or isinstance(value, (list, tuple, dict))
            ):
                candidates.extend(
                    _semantic_token_candidates_from_value(f"{function}.{name}", value)
                )
    finally:
        _overhead_add(overhead, "semantic_token_extract", token_extract_started_ns)

    if not candidates:
        summary = {
            "semantic_token_count": 0,
            "semantic_token_ids_preview": [],
            "semantic_token_source": None,
        }
        summary.update(request_metadata)
        return summary

    source, values = max(candidates, key=lambda item: len(item[1]))
    preview = values[:_TOKEN_PREVIEW]
    summary: dict[str, Any] = {
        "semantic_context_function": function,
        "semantic_token_source": source,
        "semantic_token_count": len(values),
        "semantic_token_ids_preview": preview,
        "semantic_token_preview_count": len(preview),
        "semantic_token_ids_sha256": _overhead_call(
            overhead,
            "semantic_token_hash",
            _hash_ints,
            values,
        ),
    }
    if os.environ.get("SGLANG_TRANSFER_LOG_FULL_TOKENS") == "1":
        summary["semantic_token_ids"] = values
    if request_metadata:
        summary.update(request_metadata)
    return summary


def _looks_like_token_name(name: str) -> bool:
    lowered = name.lower()
    if "__sgl_transfer" in lowered:
        return False
    clean = lowered.strip("_")
    if clean in _TOKEN_ATTR_NAMES:
        return True
    return clean.endswith("_token_ids") or clean.endswith("_input_ids")


@contextlib.contextmanager
def transfer_token_context(*, function: str, locals_dict: dict[str, Any]):
    if not _enabled():
        yield
        return

    overhead = {} if _overhead_timing_enabled() else None
    summary = _semantic_token_summary(function, locals_dict, overhead=overhead)
    _attach_overhead(summary, overhead)
    context = _merge_transfer_context_pair(
        current_transfer_context(),
        summary,
    )
    token = _SEMANTIC_CONTEXT.set(context)
    try:
        yield
    finally:
        _SEMANTIC_CONTEXT.reset(token)


@contextlib.contextmanager
def transfer_request_context(*, function: str, locals_dict: dict[str, Any]):
    if not _enabled():
        yield
        return

    overhead = {} if _overhead_timing_enabled() else None
    context = current_transfer_context() or {}
    request_metadata = _overhead_call(
        overhead,
        "request_metadata_extract",
        _request_metadata_summary,
        locals_dict,
    )
    self_obj = locals_dict.get("self")
    if self_obj is not None:
        _merge_request_metadata(
            request_metadata,
            _request_metadata_candidates_from_value("self", self_obj),
            "self",
        )
    if request_metadata:
        request_metadata["request_context_function"] = function
    _attach_overhead(request_metadata, overhead)
    context = _merge_transfer_context_pair(context, request_metadata)
    _attach_transfer_context_to_locals(
        function=function,
        locals_dict=locals_dict,
        context=context,
    )
    token = _SEMANTIC_CONTEXT.set(context)
    try:
        yield
    finally:
        _SEMANTIC_CONTEXT.reset(token)


def current_transfer_context() -> dict[str, Any] | None:
    context = _SEMANTIC_CONTEXT.get()
    if isinstance(context, dict):
        return copy.deepcopy(context)
    return None


def _merge_transfer_context_pair(
    base: dict[str, Any] | None,
    overlay: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = copy.deepcopy(base) if isinstance(base, dict) else {}
    if not isinstance(overlay, dict):
        return merged
    for key, value in overlay.items():
        if value in (None, "", [], {}):
            continue
        merged[key] = copy.deepcopy(value)
    return merged


def _attach_transfer_context_to_object(obj: Any, context: dict[str, Any] | None) -> None:
    if obj is None or not isinstance(context, dict):
        return
    try:
        setattr(obj, "sglang_transfer_context", copy.deepcopy(context))
    except Exception:
        return


def _attach_transfer_context_to_locals(
    *,
    function: str,
    locals_dict: dict[str, Any],
    context: dict[str, Any] | None,
) -> None:
    if not isinstance(context, dict):
        return

    for name in ("req", "request", "operation", "op"):
        _attach_transfer_context_to_object(locals_dict.get(name), context)

    if function.startswith("Req."):
        _attach_transfer_context_to_object(locals_dict.get("self"), context)


def merge_transfer_contexts(contexts: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    valid = [context for context in contexts if isinstance(context, dict)]
    if not valid:
        return None
    merged: dict[str, Any] = {}
    token_ids: list[int] = []
    token_hashes: list[str] = []
    token_sources: list[str] = []
    overhead_values: dict[str, float] = {}
    for context in valid:
        for key, value in context.items():
            if key in {
                "semantic_token_ids",
                "semantic_token_ids_preview",
                "semantic_token_ids_sha256",
                "semantic_token_source",
                "semantic_token_count",
                "semantic_token_preview_count",
            }:
                continue
            if key.startswith("overhead_") and key.endswith("_ms"):
                overhead_values[key] = overhead_values.get(key, 0.0) + _safe_float(value)
                continue
            merged.setdefault(key, copy.deepcopy(value))
        if isinstance(context.get("semantic_token_ids"), list):
            token_ids.extend(int(value) for value in context["semantic_token_ids"] if isinstance(value, int))
        if context.get("semantic_token_ids_sha256"):
            token_hashes.append(str(context["semantic_token_ids_sha256"]))
        if context.get("semantic_token_source"):
            token_sources.append(str(context["semantic_token_source"]))

    if token_ids:
        preview = token_ids[:_TOKEN_PREVIEW]
        merged["semantic_token_ids"] = token_ids
        merged["semantic_token_ids_preview"] = preview
        merged["semantic_token_preview_count"] = len(preview)
        merged["semantic_token_count"] = len(token_ids)
        merged["semantic_token_ids_sha256"] = _hash_ints(token_ids)
        merged["semantic_token_source"] = ",".join(sorted(set(token_sources))) or "merged_cache_operations"
    elif token_hashes:
        merged["semantic_token_ids_sha256_parts"] = sorted(set(token_hashes))
        merged["semantic_token_source"] = ",".join(sorted(set(token_sources))) or "merged_cache_operations"
    if overhead_values:
        merged.update(overhead_values)
        merged["instrumentation_overhead_enabled"] = True
    return merged


@contextlib.contextmanager
def transfer_existing_context(context: dict[str, Any] | None):
    if not isinstance(context, dict):
        yield
        return
    token = _SEMANTIC_CONTEXT.set(copy.deepcopy(context))
    try:
        yield
    finally:
        _SEMANTIC_CONTEXT.reset(token)


def _local_token_summary(locals_dict: dict[str, Any]) -> dict[str, Any]:
    if not _semantic_tokens_enabled() or _TOKEN_PREVIEW <= 0:
        return {
            "local_token_ids_preview": [],
            "local_token_preview_count": 0,
            "local_token_source": None,
        }

    token_values: list[int] = []
    source = None
    for name, value in locals_dict.items():
        lowered = name.lower()
        if "__sgl_transfer" in lowered:
            continue
        if _looks_like_token_name(name):
            values = _flatten_ints(value, _TOKEN_PREVIEW - len(token_values))
            if values and source is None:
                source = name
            token_values.extend(values)
            if len(token_values) >= _TOKEN_PREVIEW:
                break

    return {
        "local_token_ids_preview": token_values[:_TOKEN_PREVIEW],
        "local_token_preview_count": len(token_values[:_TOKEN_PREVIEW]),
        "local_token_source": source,
    }


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except Exception:
        return default


def _dtype_itemsize(dtype: Any) -> int | None:
    if dtype is None:
        return None
    try:
        return torch.empty((), dtype=dtype).element_size() if torch is not None else None
    except Exception:
        return _safe_int(getattr(dtype, "itemsize", None))


def _num_items(value: Any) -> int | None:
    if _is_tensor(value):
        try:
            return int(value.numel())
        except Exception:
            return None
    try:
        return len(value)
    except Exception:
        return None


def _kv_payload_summary(function: str, locals_dict: dict[str, Any]) -> dict[str, Any]:
    self_obj = locals_dict.get("self")
    if self_obj is None:
        return {}

    num_items = _num_items(locals_dict.get("host_indices"))
    if num_items is None:
        num_items = _num_items(locals_dict.get("device_indices"))
    if not num_items:
        return {}

    page_size = _safe_int(getattr(self_obj, "page_size", 1), 1) or 1
    layer_count = 1 if function == "load_to_device_per_layer" else _safe_int(
        getattr(self_obj, "layer_num", None)
    )
    if not layer_count:
        return {}

    dtype_itemsize = _dtype_itemsize(getattr(self_obj, "dtype", None))
    bytes_per_token_per_layer = None
    formula = None
    head_num = _safe_int(getattr(self_obj, "head_num", None))
    head_dim = _safe_int(getattr(self_obj, "head_dim", None))
    if head_num and head_dim and dtype_itemsize:
        bytes_per_token_per_layer = 2 * head_num * head_dim * dtype_itemsize
        formula = "2*head_num*head_dim*dtype.itemsize"
    else:
        element_dim = _safe_int(getattr(self_obj, "element_dim", None))
        if element_dim and dtype_itemsize:
            bytes_per_token_per_layer = 2 * element_dim * dtype_itemsize
            formula = "2*element_dim*dtype.itemsize"

    if not bytes_per_token_per_layer:
        return {}

    bytes_per_token_all_layers = bytes_per_token_per_layer * layer_count
    bytes_per_page_all_layers = bytes_per_token_all_layers * page_size
    token_total = int(num_items * bytes_per_token_all_layers)
    page_total = int(num_items * bytes_per_page_all_layers)
    return {
        "kv_num_items": int(num_items),
        "kv_item_granularity_assumption": "token",
        "kv_page_size": int(page_size),
        "kv_layer_count_estimated": int(layer_count),
        "kv_dtype_itemsize": int(dtype_itemsize) if dtype_itemsize else None,
        "kv_bytes_per_token_per_layer_estimated": int(bytes_per_token_per_layer),
        "kv_bytes_per_token_all_layers_estimated": int(bytes_per_token_all_layers),
        "kv_bytes_per_page_all_layers_estimated": int(bytes_per_page_all_layers),
        "kv_bytes_per_item_estimated": int(bytes_per_token_all_layers),
        "kv_num_bytes_estimated": token_total,
        "kv_num_kb_estimated": token_total / 1024.0,
        "kv_num_mb_estimated": token_total / (1024.0 * 1024.0),
        "kv_num_bytes_estimated_token_granular": token_total,
        "kv_num_mb_estimated_token_granular": token_total / (1024.0 * 1024.0),
        "kv_num_bytes_estimated_page_granular": page_total,
        "kv_num_mb_estimated_page_granular": page_total / (1024.0 * 1024.0),
        "kv_estimate_formula": formula,
    }


def _cache_scalar_summary(locals_dict: dict[str, Any]) -> dict[str, Any]:
    scalar_names = {
        "prefix_len",
        "new_prefix_len",
        "cached_tokens",
        "matched_tokens",
        "match_len",
        "evicted_tokens",
        "evicted_num_tokens",
        "num_tokens",
        "num_cached_tokens",
        "token_count",
        "cache_hit",
        "hit",
        "is_hit",
        "evictable_size",
        "total_size",
    }
    summary: dict[str, Any] = {}
    for name, value in locals_dict.items():
        if name == "self" or name.startswith("__sgl_"):
            continue
        lowered = name.lower()
        if lowered in scalar_names and isinstance(value, (bool, int, float, str)):
            summary[f"cache_{lowered}"] = value
    self_obj = locals_dict.get("self")
    if self_obj is not None:
        for attr in ("evictable_size", "total_size", "max_cache_size", "page_size"):
            try:
                value = getattr(self_obj, attr)
            except Exception:
                continue
            if isinstance(value, (bool, int, float, str)):
                summary[f"cache_{attr}"] = value
    return summary


def _log_cache_event_impl(
    *,
    function: str,
    action: str,
    locals_dict: dict[str, Any],
    error: str | None = None,
) -> None:
    if not _enabled():
        return

    overhead = {} if _overhead_timing_enabled() else None
    payload: dict[str, Any] = {
        "event": "sglang.cache",
        "transfer_log_profile": _profile(),
        "function": function,
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "timestamp_ns": time.time_ns(),
    }
    if error or _verbose():
        payload["error"] = error

    payload.update(
        _overhead_call(
            overhead,
            "request_metadata_extract",
            _request_metadata_summary,
            locals_dict,
        )
    )
    payload.update(
        _overhead_call(
            overhead,
            "semantic_token_extract",
            _semantic_token_summary,
            function,
            locals_dict,
            overhead,
        )
    )
    payload.update(_cache_scalar_summary(locals_dict))
    context = current_transfer_context()
    if context:
        payload.update(context)

    _attach_overhead(payload, overhead)
    if overhead is not None or payload.get("instrumentation_overhead_enabled"):
        payload.setdefault("instrumentation_overhead_note", "Timing fields are approximate and add measurement overhead.")
        payload["overhead_json_serialize_ms"] = _safe_float(payload.get("overhead_json_serialize_ms"))
        _finalize_overhead(payload)
        json_started_ns = time.perf_counter_ns()
        line = _PREFIX + json.dumps(payload, sort_keys=True, default=str)
        json_ms = (time.perf_counter_ns() - json_started_ns) / 1_000_000.0
        payload["overhead_json_serialize_ms"] = _safe_float(payload.get("overhead_json_serialize_ms")) + json_ms
        _finalize_overhead(payload)
        line = _PREFIX + json.dumps(payload, sort_keys=True, default=str)
    else:
        line = _PREFIX + json.dumps(payload, sort_keys=True, default=str)

    with _LOCK:
        print(line, file=sys.stderr, flush=True)
        path = os.environ.get("SGLANG_TRANSFER_LOG_PATH")
        if path:
            try:
                with open(path, "a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
            except Exception as exc:
                print(
                    _PREFIX
                    + json.dumps(
                        {
                            "event": "sglang.cache_log_error",
                            "path": path,
                            "error": repr(exc),
                        },
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                    flush=True,
                )


def log_cache_event(
    *,
    function: str,
    action: str,
    locals_dict: dict[str, Any],
    error: str | None = None,
) -> None:
    try:
        _log_cache_event_impl(
            function=function,
            action=action,
            locals_dict=locals_dict,
            error=error,
        )
    except Exception as exc:  # pragma: no cover - instrumentation must not break serving.
        if _verbose():
            try:
                print(
                    _PREFIX
                    + json.dumps(
                        {
                            "event": "sglang.cache_log_error",
                            "function": function,
                            "action": action,
                            "error": repr(exc),
                        },
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                    flush=True,
                )
            except Exception:
                pass


def _index_summary(locals_dict: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for name, value in locals_dict.items():
        lowered = name.lower()
        if lowered not in {"host_indices", "device_indices", "indices", "cache_loc", "cache_indices"}:
            continue
        count = _num_items(value)
        if _is_tensor(value):
            try:
                count = int(value.numel())
            except Exception:
                count = None
        if not _allow_cuda_index_sync():
            summary[f"{lowered}_count"] = count
            continue
        preview = _flatten_ints(value, _INDEX_PREVIEW, allow_cuda_tensor_sync=True)
        summary[f"{lowered}_count"] = count if count is not None else len(preview)
        if preview or _verbose():
            summary[f"{lowered}_preview"] = preview
            summary[f"{lowered}_preview_count"] = len(preview)
    return summary


def _walk_cuda_devices(value: Any, devices: set[Any], depth: int = 0) -> None:
    if depth > 3 or torch is None:
        return
    if _is_tensor(value):
        try:
            if str(value.device).startswith("cuda"):
                devices.add(value.device)
        except Exception:
            return
        return
    if isinstance(value, dict):
        for item in list(value.values())[:64]:
            _walk_cuda_devices(item, devices, depth + 1)
        return
    if isinstance(value, (list, tuple)):
        for item in value[:64]:
            _walk_cuda_devices(item, devices, depth + 1)


def _synchronize_cuda_tensors(locals_dict: dict[str, Any]) -> int:
    if torch is None or not hasattr(torch, "cuda"):
        return 0
    try:
        if not torch.cuda.is_available():
            return 0
    except Exception:
        return 0

    devices: set[Any] = set()
    for name, value in locals_dict.items():
        if name == "self" or name.startswith("__sgl_transfer"):
            continue
        _walk_cuda_devices(value, devices)
    for device in devices:
        try:
            torch.cuda.synchronize(device)
        except Exception:
            pass
    return len(devices)


def log_transfer_event(
    *,
    function: str,
    direction: str,
    started_ns: int,
    locals_dict: dict[str, Any],
    error: str | None = None,
) -> None:
    if not _enabled():
        return

    overhead = {} if _overhead_timing_enabled() else None
    wall_ended_ns = time.perf_counter_ns()
    wall_ms = (wall_ended_ns - started_ns) / 1_000_000.0
    cuda_sync_device_count = 0
    cuda_sync_wait_ms = None
    elapsed_ms_cuda_sync = None
    if _sync_timing_enabled():
        sync_started_ns = time.perf_counter_ns()
        cuda_sync_device_count = _synchronize_cuda_tensors(locals_dict)
        sync_ended_ns = time.perf_counter_ns()
        _overhead_add(overhead, "cuda_sync_timing", sync_started_ns)
        if cuda_sync_device_count:
            cuda_sync_wait_ms = (sync_ended_ns - sync_started_ns) / 1_000_000.0
            elapsed_ms_cuda_sync = (sync_ended_ns - started_ns) / 1_000_000.0

    tensor_details: list[dict[str, Any]] = []
    total_bytes = 0
    tensor_scan_started_ns = _overhead_start(overhead)
    try:
        for name, value in locals_dict.items():
            if name == "self" or name.startswith("__sgl_transfer"):
                continue
            total_bytes += _walk_tensors(name, value, tensor_details)
    finally:
        _overhead_add(overhead, "tensor_scan", tensor_scan_started_ns)

    payload: dict[str, Any] = {
        "event": "sglang.transfer",
        "transfer_log_profile": _profile(),
        "function": function,
        "direction": direction,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "timestamp_ns": time.time_ns(),
        "elapsed_ms": wall_ms,
        "elapsed_ms_wall": wall_ms,
        "num_bytes_observed": total_bytes,
        "num_kb_observed": total_bytes / 1024.0,
        "num_mb_observed": total_bytes / (1024.0 * 1024.0),
    }
    if _verbose():
        payload["tensor_details"] = tensor_details
    if error or _verbose():
        payload["error"] = error
    if elapsed_ms_cuda_sync is not None:
        payload["elapsed_ms_cuda_sync"] = elapsed_ms_cuda_sync
        payload["cuda_sync_wait_ms"] = cuda_sync_wait_ms
        payload["cuda_sync_device_count"] = cuda_sync_device_count

    local_summary = _overhead_call(overhead, "local_token_preview", _local_token_summary, locals_dict)
    semantic_context = _SEMANTIC_CONTEXT.get()
    has_semantic_context = isinstance(semantic_context, dict)
    if has_semantic_context:
        payload.update(semantic_context)
    has_semantic_tokens = bool(
        has_semantic_context and int(semantic_context.get("semantic_token_count") or 0) > 0
    )
    has_local_tokens = bool(local_summary["local_token_preview_count"])
    if has_semantic_tokens:
        payload["token_ids_preview"] = semantic_context.get("semantic_token_ids_preview", [])
        payload["token_preview_count"] = semantic_context.get("semantic_token_preview_count", 0)
        payload["token_preview_source"] = "semantic_context"
    elif has_local_tokens:
        payload["token_ids_preview"] = local_summary["local_token_ids_preview"]
        payload["token_preview_count"] = local_summary["local_token_preview_count"]
        payload["token_preview_source"] = "local_heuristic"
        payload.update(local_summary)
    elif _verbose():
        payload.update(local_summary)
        payload["token_ids_preview"] = []
        payload["token_preview_count"] = 0
        payload["token_preview_source"] = "none"

    payload.update(
        _overhead_call(
            overhead,
            "request_metadata_extract",
            _request_metadata_summary,
            locals_dict,
        )
    )

    payload.update(_overhead_call(overhead, "index_summary", _index_summary, locals_dict))
    payload.update(
        _overhead_call(
            overhead,
            "kv_payload_estimate",
            _kv_payload_summary,
            function,
            locals_dict,
        )
    )

    _attach_overhead(payload, overhead)
    if overhead is not None or payload.get("instrumentation_overhead_enabled"):
        payload.setdefault("instrumentation_overhead_note", "Timing fields are approximate and add measurement overhead.")
        payload["overhead_json_serialize_ms"] = _safe_float(payload.get("overhead_json_serialize_ms"))
        _finalize_overhead(payload)
        json_started_ns = time.perf_counter_ns()
        line = _PREFIX + json.dumps(payload, sort_keys=True, default=str)
        json_ms = (time.perf_counter_ns() - json_started_ns) / 1_000_000.0
        payload["overhead_json_serialize_ms"] = _safe_float(payload.get("overhead_json_serialize_ms")) + json_ms
        _finalize_overhead(payload)
        line = _PREFIX + json.dumps(payload, sort_keys=True, default=str)
    else:
        line = _PREFIX + json.dumps(payload, sort_keys=True, default=str)
    with _LOCK:
        stderr_started_ns = _overhead_start(overhead)
        print(line, file=sys.stderr, flush=True)
        _overhead_add(overhead, "stderr_print", stderr_started_ns)
        path = os.environ.get("SGLANG_TRANSFER_LOG_PATH")
        if path:
            try:
                file_started_ns = _overhead_start(overhead)
                with open(path, "a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
                _overhead_add(overhead, "file_write", file_started_ns)
            except Exception as exc:
                print(
                    _PREFIX
                    + json.dumps(
                        {
                            "event": "sglang.transfer_log_error",
                            "path": path,
                            "error": repr(exc),
                        },
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                    flush=True,
                )
'''


TARGET_FUNCTIONS = {
    "backup_from_device_all_layer": "device_to_host",
    "load_to_device_per_layer": "host_to_device",
}

SEMANTIC_CONTEXT_FUNCTIONS = ("write_backup", "load_back")
CACHE_EVENT_FUNCTIONS = (
    "match_prefix",
    "insert",
    "cache_finished_req",
    "cache_unfinished_req",
    "evict",
)


def find_first(sglang_root: Path, filename: str) -> Path:
    matches = sorted(sglang_root.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"Could not find {filename} under {sglang_root}")
    if len(matches) > 1:
        print(f"Found multiple {filename} files; using first:")
        for match in matches:
            print(f"  {match}")
    return matches[0]


def find_optional_first(sglang_root: Path, filename: str) -> Path | None:
    matches = sorted(sglang_root.rglob(filename))
    if not matches:
        return None
    if len(matches) > 1:
        print(f"Found multiple {filename} files; using first:")
        for match in matches:
            print(f"  {match}")
    return matches[0]


def find_optional_preferred(
    sglang_root: Path,
    filename: str,
    preferred_subpath: str,
) -> Path | None:
    matches = sorted(sglang_root.rglob(filename))
    if not matches:
        return None

    preferred = [
        match for match in matches
        if match.as_posix().endswith(preferred_subpath)
    ]
    if preferred:
        return preferred[0]

    if len(matches) > 1:
        print(f"Found multiple {filename} files; using first:")
        for match in matches:
            print(f"  {match}")
    return matches[0]


def insert_after_future(text: str, imports: list[str], marker: str) -> str:
    if marker in text:
        return text
    lines = text.splitlines(keepends=True)
    insert_at = 0
    for index, line in enumerate(lines):
        if line.startswith("from __future__ import "):
            insert_at = index + 1
    lines[insert_at:insert_at] = imports
    return "".join(lines)


def insert_memory_imports(text: str) -> str:
    return insert_after_future(
        text,
        [
            "import time as _sgl_transfer_time\n",
            "from .transfer_logging import log_transfer_event as _sgl_log_transfer_event\n",
        ],
        "from .transfer_logging import log_transfer_event as _sgl_log_transfer_event",
    )


def insert_hiradix_imports(text: str) -> str:
    text = insert_after_future(
        text,
        [
            "from .transfer_logging import transfer_token_context as _sgl_transfer_token_context\n",
        ],
        "from .transfer_logging import transfer_token_context as _sgl_transfer_token_context",
    )
    return insert_after_future(
        text,
        [
            "from .transfer_logging import log_cache_event as _sgl_log_cache_event\n",
        ],
        "from .transfer_logging import log_cache_event as _sgl_log_cache_event",
    )


def insert_cache_controller_imports(text: str) -> str:
    return insert_after_future(
        text,
        [
            "from sglang.srt.mem_cache.transfer_logging import (\n",
            "    current_transfer_context as _sgl_current_transfer_context,\n",
            "    merge_transfer_contexts as _sgl_merge_transfer_contexts,\n",
            "    transfer_existing_context as _sgl_transfer_existing_context,\n",
            ")\n",
        ],
        "from sglang.srt.mem_cache.transfer_logging import (",
    )


def insert_request_context_imports(text: str) -> str:
    return insert_after_future(
        text,
        [
            "from sglang.srt.mem_cache.transfer_logging import transfer_request_context as _sgl_transfer_request_context\n",
        ],
        "from sglang.srt.mem_cache.transfer_logging import transfer_request_context as _sgl_transfer_request_context",
    )


def insert_absolute_cache_event_imports(text: str) -> str:
    return insert_after_future(
        text,
        [
            "from sglang.srt.mem_cache.transfer_logging import log_cache_event as _sgl_log_cache_event\n",
        ],
        "from sglang.srt.mem_cache.transfer_logging import log_cache_event as _sgl_log_cache_event",
    )


def find_function_bounds(lines: list[str], function_name: str) -> tuple[int, int, int] | None:
    pattern = re.compile(rf"^(\s*)(async\s+def|def)\s+{re.escape(function_name)}\b")
    for start, line in enumerate(lines):
        match = pattern.match(line)
        if not match:
            continue
        indent = len(match.group(1))
        signature_end = start
        paren_balance = line.count("(") - line.count(")")
        while signature_end + 1 < len(lines) and (
            paren_balance > 0 or not lines[signature_end].rstrip().endswith(":")
        ):
            signature_end += 1
            paren_balance += lines[signature_end].count("(") - lines[signature_end].count(")")

        end = len(lines)
        for index in range(signature_end + 1, len(lines)):
            stripped = lines[index].strip()
            if not stripped:
                continue
            current_indent = len(lines[index]) - len(lines[index].lstrip(" "))
            if current_indent <= indent and not stripped.startswith("#"):
                end = index
                break
        return start, signature_end, end
    return None


def find_all_function_bounds(lines: list[str], function_name: str) -> list[tuple[int, int, int]]:
    bounds: list[tuple[int, int, int]] = []
    search_from = 0
    while search_from < len(lines):
        found = find_function_bounds(lines[search_from:], function_name)
        if found is None:
            break
        start, signature_end, end = found
        adjusted = (start + search_from, signature_end + search_from, end + search_from)
        bounds.append(adjusted)
        search_from = adjusted[2]
    return bounds


def wrap_transfer_occurrence(
    lines: list[str],
    function_name: str,
    direction: str,
    bounds: tuple[int, int, int],
) -> bool:
    start, signature_end, end = bounds
    body_text = "".join(lines[signature_end + 1 : end])
    if f'function="{function_name}"' in body_text and "_sgl_log_transfer_event" in body_text:
        return False

    def_indent = len(lines[start]) - len(lines[start].lstrip(" "))
    body_indent = " " * (def_indent + 4)
    nested_indent = " " * (def_indent + 8)

    original_body = lines[signature_end + 1 : end]
    wrapped_body = [
        f"{body_indent}__sgl_transfer_started_ns = _sgl_transfer_time.perf_counter_ns()\n",
        f"{body_indent}__sgl_transfer_error = None\n",
        f"{body_indent}try:\n",
    ]
    for line in original_body:
        if line.strip():
            wrapped_body.append("    " + line)
        else:
            wrapped_body.append(line)
    wrapped_body.extend(
        [
            f"{body_indent}except BaseException as __sgl_transfer_exc:\n",
            f"{nested_indent}__sgl_transfer_error = repr(__sgl_transfer_exc)\n",
            f"{nested_indent}raise\n",
            f"{body_indent}finally:\n",
            f"{nested_indent}_sgl_log_transfer_event(\n",
            f'{nested_indent}    function="{function_name}",\n',
            f'{nested_indent}    direction="{direction}",\n',
            f"{nested_indent}    started_ns=__sgl_transfer_started_ns,\n",
            f"{nested_indent}    locals_dict=locals(),\n",
            f"{nested_indent}    error=__sgl_transfer_error,\n",
            f"{nested_indent})\n",
        ]
    )

    lines[signature_end + 1 : end] = wrapped_body
    return True


def wrap_context_occurrence(
    lines: list[str],
    function_name: str,
    bounds: tuple[int, int, int],
) -> bool:
    start, signature_end, end = bounds
    body_text = "".join(lines[signature_end + 1 : end])
    if "_sgl_transfer_token_context" in body_text:
        return False

    def_indent = len(lines[start]) - len(lines[start].lstrip(" "))
    body_indent = " " * (def_indent + 4)
    original_body = lines[signature_end + 1 : end]
    wrapped_body = [
        f"{body_indent}with _sgl_transfer_token_context(function=\"{function_name}\", locals_dict=locals()):\n",
    ]
    for line in original_body:
        if line.strip():
            wrapped_body.append("    " + line)
        else:
            wrapped_body.append(line)
    lines[signature_end + 1 : end] = wrapped_body
    return True


def wrap_cache_event_occurrence(
    lines: list[str],
    function_name: str,
    bounds: tuple[int, int, int],
) -> bool:
    start, signature_end, end = bounds
    body_text = "".join(lines[signature_end + 1 : end])
    if f'function="{function_name}"' in body_text and "_sgl_log_cache_event" in body_text:
        return False

    def_indent = len(lines[start]) - len(lines[start].lstrip(" "))
    body_indent = " " * (def_indent + 4)
    nested_indent = " " * (def_indent + 8)
    original_body = lines[signature_end + 1 : end]
    wrapped_body = [
        f"{body_indent}__sgl_cache_event_error = None\n",
        f"{body_indent}try:\n",
    ]
    for line in original_body:
        if line.strip():
            wrapped_body.append("    " + line)
        else:
            wrapped_body.append(line)
    wrapped_body.extend(
        [
            f"{body_indent}except BaseException as __sgl_cache_event_exc:\n",
            f"{nested_indent}__sgl_cache_event_error = repr(__sgl_cache_event_exc)\n",
            f"{nested_indent}raise\n",
            f"{body_indent}finally:\n",
            f"{nested_indent}_sgl_log_cache_event(\n",
            f'{nested_indent}    function="{function_name}",\n',
            f'{nested_indent}    action="{function_name}",\n',
            f"{nested_indent}    locals_dict=locals(),\n",
            f"{nested_indent}    error=__sgl_cache_event_error,\n",
            f"{nested_indent})\n",
        ]
    )
    lines[signature_end + 1 : end] = wrapped_body
    return True


def wrap_transfer_function(text: str, function_name: str, direction: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    bounds = find_all_function_bounds(lines, function_name)
    changed = 0
    for occurrence in reversed(bounds):
        if wrap_transfer_occurrence(lines, function_name, direction, occurrence):
            changed += 1
    return "".join(lines), changed


def wrap_context_function(text: str, function_name: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    bounds = find_all_function_bounds(lines, function_name)
    changed = 0
    for occurrence in reversed(bounds):
        if wrap_context_occurrence(lines, function_name, occurrence):
            changed += 1
    return "".join(lines), changed


def wrap_cache_event_function(text: str, function_name: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    bounds = find_all_function_bounds(lines, function_name)
    changed = 0
    for occurrence in reversed(bounds):
        if wrap_cache_event_occurrence(lines, function_name, occurrence):
            changed += 1
    return "".join(lines), changed


def wrap_request_context_function(text: str, function_name: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    bounds = find_all_function_bounds(lines, function_name)
    changed = 0
    for start, signature_end, end in reversed(bounds):
        body_text = "".join(lines[signature_end + 1 : end])
        if "_sgl_transfer_request_context" in body_text:
            continue
        def_indent = len(lines[start]) - len(lines[start].lstrip(" "))
        body_indent = " " * (def_indent + 4)
        original_body = lines[signature_end + 1 : end]
        wrapped_body = [
            f"{body_indent}with _sgl_transfer_request_context(function=\"{function_name}\", locals_dict=locals()):\n",
        ]
        for line in original_body:
            if line.strip():
                wrapped_body.append("    " + line)
            else:
                wrapped_body.append(line)
        lines[signature_end + 1 : end] = wrapped_body
        changed += 1
    return "".join(lines), changed


def wrap_call_with_request_context(
    text: str,
    call_marker: str,
    function_label: str,
) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    changed = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        if call_marker not in line:
            index += 1
            continue
        if index > 0 and "_sgl_transfer_request_context" in lines[index - 1]:
            index += 1
            continue

        indent_len = len(line) - len(line.lstrip(" "))
        indent = " " * indent_len
        call_end = index
        paren_balance = line.count("(") - line.count(")")
        while call_end + 1 < len(lines) and paren_balance > 0:
            call_end += 1
            paren_balance += lines[call_end].count("(") - lines[call_end].count(")")

        block = lines[index : call_end + 1]
        wrapped = [
            f"{indent}with _sgl_transfer_request_context(function=\"{function_label}\", locals_dict=locals()):\n",
        ]
        wrapped.extend("    " + item if item.strip() else item for item in block)
        lines[index : call_end + 1] = wrapped
        changed += 1
        index += len(wrapped)
    return "".join(lines), changed


def add_cache_operation_context_capture(text: str) -> tuple[str, bool]:
    if "self.sglang_transfer_context = _sgl_current_transfer_context()" in text:
        return text, False

    pattern = re.compile(r"^(\s*)self\.node_ids\s*=\s*\[node_id\]\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return text, False
    indent = match.group(1)
    insert_at = match.end()
    insertion = (
        "\n"
        f"{indent}self.sglang_transfer_context = _sgl_current_transfer_context()"
    )
    return text[:insert_at] + insertion + text[insert_at:], True


def add_cache_operation_merge_context(text: str) -> tuple[str, bool]:
    if "merged_op.sglang_transfer_context = _sgl_merge_transfer_contexts" in text:
        return text, False

    pattern = re.compile(r"^(\s*)merged_op\.node_ids\s*=\s*node_ids\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return text, False
    indent = match.group(1)
    insert_at = match.end()
    insertion = (
        "\n"
        f"{indent}merged_op.sglang_transfer_context = _sgl_merge_transfer_contexts(\n"
        f"{indent}    [getattr(op, \"sglang_transfer_context\", None) for op in ops]\n"
        f"{indent})"
    )
    return text[:insert_at] + insertion + text[insert_at:], True


def wrap_call_with_operation_context(text: str, call_marker: str) -> tuple[str, int]:
    lines = text.splitlines(keepends=True)
    changed = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        if call_marker not in line:
            index += 1
            continue
        if index > 0 and "_sgl_transfer_existing_context" in lines[index - 1]:
            index += 1
            continue

        indent_len = len(line) - len(line.lstrip(" "))
        indent = " " * indent_len
        call_end = index
        paren_balance = line.count("(") - line.count(")")
        while call_end + 1 < len(lines) and paren_balance > 0:
            call_end += 1
            paren_balance += lines[call_end].count("(") - lines[call_end].count(")")

        block = lines[index : call_end + 1]
        wrapped = [
            f"{indent}with _sgl_transfer_existing_context("
            "getattr(locals().get(\"op\"), \"sglang_transfer_context\", None)"
            "):\n"
        ]
        wrapped.extend("    " + item if item.strip() else item for item in block)
        lines[index : call_end + 1] = wrapped
        changed += 1
        index += len(wrapped)
    return "".join(lines), changed


def patch_memory_pool_host(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    text = insert_memory_imports(text)
    patched: list[str] = []
    for function_name, direction in TARGET_FUNCTIONS.items():
        text, changed = wrap_transfer_function(text, function_name, direction)
        if changed:
            patched.append(f"{function_name} ({changed} occurrence{'s' if changed != 1 else ''})")
    if patched:
        path.write_text(text, encoding="utf-8")
    return patched


def patch_hiradix_cache(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    text = insert_hiradix_imports(text)
    patched: list[str] = []
    for function_name in SEMANTIC_CONTEXT_FUNCTIONS:
        text, changed = wrap_context_function(text, function_name)
        if changed:
            patched.append(f"{function_name} ({changed} occurrence{'s' if changed != 1 else ''})")
    for function_name in CACHE_EVENT_FUNCTIONS:
        text, changed = wrap_cache_event_function(text, function_name)
        if changed:
            patched.append(f"{function_name} cache event ({changed} occurrence{'s' if changed != 1 else ''})")
    if patched:
        path.write_text(text, encoding="utf-8")
    return patched


def patch_cache_controller(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    text = insert_cache_controller_imports(text)
    patched: list[str] = []

    text, changed = add_cache_operation_context_capture(text)
    if changed:
        patched.append("CacheOperation context capture")

    text, changed = add_cache_operation_merge_context(text)
    if changed:
        patched.append("CacheOperation merge context")

    for marker, label in (
        ("self.mem_pool_host.backup_from_device_all_layer(", "write-back transfer context"),
        ("self.mem_pool_host.load_to_device_per_layer(", "load-back transfer context"),
    ):
        text, changed_count = wrap_call_with_operation_context(text, marker)
        if changed_count:
            patched.append(f"{label} ({changed_count} call{'s' if changed_count != 1 else ''})")

    if patched:
        path.write_text(text, encoding="utf-8")
    return patched


def patch_radix_cache(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    text = insert_request_context_imports(text)
    text = insert_absolute_cache_event_imports(text)
    patched: list[str] = []

    for function_name in ("cache_finished_req", "cache_unfinished_req"):
        text, changed = wrap_request_context_function(text, function_name)
        if changed:
            patched.append(f"{function_name} request context ({changed} occurrence{'s' if changed != 1 else ''})")
    for function_name in CACHE_EVENT_FUNCTIONS:
        text, changed = wrap_cache_event_function(text, function_name)
        if changed:
            patched.append(f"{function_name} cache event ({changed} occurrence{'s' if changed != 1 else ''})")

    if patched:
        path.write_text(text, encoding="utf-8")
    return patched


def patch_schedule_batch(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    text = insert_request_context_imports(text)
    patched: list[str] = []

    text, changed = wrap_call_with_request_context(
        text,
        "tree_cache.match_prefix(",
        "Req.init_next_round_input.match_prefix",
    )
    if changed:
        patched.append(f"Req.init_next_round_input match_prefix context ({changed} call{'s' if changed != 1 else ''})")

    if patched:
        path.write_text(text, encoding="utf-8")
    return patched


def patch_schedule_policy(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    text = insert_request_context_imports(text)
    patched: list[str] = []

    text, changed = wrap_call_with_request_context(
        text,
        "self.tree_cache.init_load_back(",
        "SchedulePolicy.add_one_req.init_load_back",
    )
    if changed:
        patched.append(f"SchedulePolicy init_load_back context ({changed} call{'s' if changed != 1 else ''})")

    if patched:
        path.write_text(text, encoding="utf-8")
    return patched


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sglang-root",
        type=Path,
        default=Path("upstream/sglang/python/sglang"),
        help="Path to the extracted Python sglang package.",
    )
    args = parser.parse_args()

    sglang_root = args.sglang_root.resolve()
    memory_pool_host = find_first(sglang_root, "memory_pool_host.py")
    hiradix_cache = find_optional_first(sglang_root, "hiradix_cache.py")
    cache_controller = find_optional_preferred(
        sglang_root,
        "cache_controller.py",
        "srt/managers/cache_controller.py",
    )
    radix_cache = find_optional_first(sglang_root, "radix_cache.py")
    schedule_batch = find_optional_preferred(
        sglang_root,
        "schedule_batch.py",
        "srt/managers/schedule_batch.py",
    )
    schedule_policy = find_optional_preferred(
        sglang_root,
        "schedule_policy.py",
        "srt/managers/schedule_policy.py",
    )

    helper_path = memory_pool_host.with_name("transfer_logging.py")
    helper_path.write_text(HELPER_SOURCE + "\n", encoding="utf-8")
    memory_patched = patch_memory_pool_host(memory_pool_host)
    hiradix_patched = patch_hiradix_cache(hiradix_cache) if hiradix_cache else []
    cache_controller_patched = patch_cache_controller(cache_controller) if cache_controller else []
    radix_cache_patched = patch_radix_cache(radix_cache) if radix_cache else []
    schedule_batch_patched = patch_schedule_batch(schedule_batch) if schedule_batch else []
    schedule_policy_patched = patch_schedule_policy(schedule_policy) if schedule_policy else []

    print(f"memory_pool_host: {memory_pool_host}")
    print(f"transfer_logging: {helper_path}")
    if memory_patched:
        print("patched transfer functions:")
        for function_name in memory_patched:
            print(f"  - {function_name}")
    else:
        print("no transfer functions patched; they may already be instrumented or absent")

    if hiradix_cache:
        print(f"hiradix_cache: {hiradix_cache}")
        if hiradix_patched:
            print("patched HiRadix semantic context/cache event functions:")
            for function_name in hiradix_patched:
                print(f"  - {function_name}")
        else:
            print("no HiRadix semantic/cache functions patched; they may already be instrumented or absent")
    else:
        print("hiradix_cache: not found; semantic/cache event context was not patched")

    if cache_controller:
        print(f"cache_controller: {cache_controller}")
        if cache_controller_patched:
            print("patched async transfer context propagation:")
            for item in cache_controller_patched:
                print(f"  - {item}")
        else:
            print("no cache-controller propagation patched; it may already be instrumented or unsupported")
    else:
        print("cache_controller: not found; async transfer context propagation was not patched")

    if radix_cache:
        print(f"radix_cache: {radix_cache}")
        if radix_cache_patched:
            print("patched request context around cache insertion:")
            for item in radix_cache_patched:
                print(f"  - {item}")
        else:
            print("no radix-cache request context patched; it may already be instrumented or unsupported")
    else:
        print("radix_cache: not found; cache insertion request context was not patched")

    if schedule_batch:
        print(f"schedule_batch: {schedule_batch}")
        if schedule_batch_patched:
            print("patched request context around prefix matching:")
            for item in schedule_batch_patched:
                print(f"  - {item}")
        else:
            print("no schedule-batch request context patched; it may already be instrumented or unsupported")
    else:
        print("schedule_batch: not found; prefix-match request context was not patched")

    if schedule_policy:
        print(f"schedule_policy: {schedule_policy}")
        if schedule_policy_patched:
            print("patched request context around host load-back:")
            for item in schedule_policy_patched:
                print(f"  - {item}")
        else:
            print("no schedule-policy request context patched; it may already be instrumented or unsupported")
    else:
        print("schedule_policy: not found; load-back request context was not patched")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
