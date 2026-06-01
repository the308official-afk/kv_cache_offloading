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
import hashlib
import json
import os
import sys
import threading
import time
from typing import Any

try:
    import torch
except Exception:  # pragma: no cover - instrumentation must not break startup.
    torch = None


_PREFIX = "[SGLANG_TRANSFER_JSON] "
_LOCK = threading.Lock()
_DETAIL_LIMIT = int(os.environ.get("SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS", "16") or 16)
_TOKEN_PREVIEW = int(os.environ.get("SGLANG_TRANSFER_LOG_TOKEN_PREVIEW", "32") or 32)
_INDEX_PREVIEW = int(os.environ.get("SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT", "32") or 32)
_MAX_TOKEN_ID = int(os.environ.get("SGLANG_TRANSFER_LOG_MAX_REASONABLE_TOKEN_ID", "10000000") or 10000000)
_MAX_SEMANTIC_TOKENS = int(os.environ.get("SGLANG_TRANSFER_LOG_MAX_SEMANTIC_TOKENS", "1000000") or 1000000)
_SEMANTIC_CONTEXT = contextvars.ContextVar("sglang_transfer_semantic_context", default=None)


def _enabled() -> bool:
    return os.environ.get("SGLANG_TRANSFER_LOG") == "1"


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
    return os.environ.get("SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC") == "1"


def _allow_cuda_index_sync() -> bool:
    return os.environ.get("SGLANG_TRANSFER_LOG_INDEX_PREVIEW") == "1"


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


def _semantic_token_summary(function: str, locals_dict: dict[str, Any]) -> dict[str, Any]:
    direct_names = (
        "token_ids",
        "input_ids",
        "output_ids",
        "tokens",
        "input_tokens",
        "prefix_tokens",
    )
    attr_names = (
        "token_ids",
        "input_ids",
        "output_ids",
        "tokens",
        "prefix_tokens",
        "prefix",
        "key",
    )
    object_name_hints = ("node", "leaf", "root", "req", "request", "cache", "entry")

    candidates: list[tuple[str, list[int]]] = []
    for name, value in locals_dict.items():
        if name == "self" or name.startswith("__sgl_transfer"):
            continue
        lowered = name.lower()
        if any(candidate == lowered or candidate in lowered for candidate in direct_names):
            candidate = _semantic_token_candidate(f"{function}.{name}", value)
            if candidate:
                candidates.append(candidate)
        if any(hint in lowered for hint in object_name_hints):
            for attr in attr_names:
                try:
                    attr_value = getattr(value, attr)
                except Exception:
                    continue
                candidate = _semantic_token_candidate(f"{function}.{name}.{attr}", attr_value)
                if candidate:
                    candidates.append(candidate)

    if not candidates:
        return {
            "semantic_token_count": 0,
            "semantic_token_ids_preview": [],
            "semantic_token_source": None,
        }

    source, values = max(candidates, key=lambda item: len(item[1]))
    preview = values[:_TOKEN_PREVIEW]
    summary: dict[str, Any] = {
        "semantic_context_function": function,
        "semantic_token_source": source,
        "semantic_token_count": len(values),
        "semantic_token_ids_preview": preview,
        "semantic_token_preview_count": len(preview),
        "semantic_token_ids_sha256": _hash_ints(values),
    }
    if os.environ.get("SGLANG_TRANSFER_LOG_FULL_TOKENS") == "1":
        summary["semantic_token_ids"] = values
    return summary


@contextlib.contextmanager
def transfer_token_context(*, function: str, locals_dict: dict[str, Any]):
    context = _semantic_token_summary(function, locals_dict)
    token = _SEMANTIC_CONTEXT.set(context)
    try:
        yield
    finally:
        _SEMANTIC_CONTEXT.reset(token)


def _local_token_summary(locals_dict: dict[str, Any]) -> dict[str, Any]:
    token_values: list[int] = []
    candidate_names = (
        "token_ids",
        "input_ids",
        "output_ids",
        "tokens",
        "token",
        "input_tokens",
    )
    source = None
    for name, value in locals_dict.items():
        lowered = name.lower()
        if any(candidate in lowered for candidate in candidate_names):
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


def _index_summary(locals_dict: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for name, value in locals_dict.items():
        lowered = name.lower()
        if lowered not in {"host_indices", "device_indices", "indices", "cache_loc", "cache_indices"}:
            continue
        count = None
        if _is_tensor(value):
            try:
                count = int(value.numel())
            except Exception:
                count = None
            if str(value.device) != "cpu" and not _allow_cuda_index_sync():
                summary[f"{lowered}_count"] = count
                summary[f"{lowered}_preview"] = []
                summary[f"{lowered}_preview_skipped"] = "cuda_tensor_set_SGLANG_TRANSFER_LOG_INDEX_PREVIEW=1"
                continue
        preview = _flatten_ints(value, _INDEX_PREVIEW, allow_cuda_tensor_sync=_allow_cuda_index_sync())
        summary[f"{lowered}_count"] = count if count is not None else len(preview)
        summary[f"{lowered}_preview"] = preview
        summary[f"{lowered}_preview_count"] = len(preview)
    return summary


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

    ended_ns = time.perf_counter_ns()
    tensor_details: list[dict[str, Any]] = []
    total_bytes = 0
    for name, value in locals_dict.items():
        if name == "self" or name.startswith("__sgl_transfer"):
            continue
        total_bytes += _walk_tensors(name, value, tensor_details)

    payload: dict[str, Any] = {
        "event": "sglang.transfer",
        "function": function,
        "direction": direction,
        "timestamp_ns": time.time_ns(),
        "elapsed_ms": (ended_ns - started_ns) / 1_000_000.0,
        "num_bytes_observed": total_bytes,
        "num_kb_observed": total_bytes / 1024.0,
        "num_mb_observed": total_bytes / (1024.0 * 1024.0),
        "tensor_details": tensor_details,
        "error": error,
    }

    local_summary = _local_token_summary(locals_dict)
    semantic_context = _SEMANTIC_CONTEXT.get()
    if semantic_context:
        payload.update(semantic_context)
        payload["token_ids_preview"] = semantic_context.get("semantic_token_ids_preview", [])
        payload["token_preview_count"] = semantic_context.get("semantic_token_preview_count", 0)
        payload["token_preview_source"] = "semantic_context"
    else:
        payload["token_ids_preview"] = local_summary["local_token_ids_preview"]
        payload["token_preview_count"] = local_summary["local_token_preview_count"]
        payload["token_preview_source"] = "local_heuristic"
    payload.update(local_summary)
    payload.update(_index_summary(locals_dict))

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
    return insert_after_future(
        text,
        [
            "from .transfer_logging import transfer_token_context as _sgl_transfer_token_context\n",
        ],
        "from .transfer_logging import transfer_token_context as _sgl_transfer_token_context",
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

    helper_path = memory_pool_host.with_name("transfer_logging.py")
    helper_path.write_text(HELPER_SOURCE + "\n", encoding="utf-8")
    memory_patched = patch_memory_pool_host(memory_pool_host)
    hiradix_patched = patch_hiradix_cache(hiradix_cache) if hiradix_cache else []

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
            print("patched semantic context functions:")
            for function_name in hiradix_patched:
                print(f"  - {function_name}")
        else:
            print("no semantic context functions patched; they may already be instrumented or absent")
    else:
        print("hiradix_cache: not found; semantic token context was not patched")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
