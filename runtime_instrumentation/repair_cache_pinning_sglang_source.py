#!/usr/bin/env python3
"""Patch isolated cache-pinning SGLang source with direct pin-path logs."""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(
    os.environ.get("SOURCE_DIR", ROOT / "upstream" / "sglang_cache_pinning")
)


def write_if_changed(path: Path, text: str) -> None:
    old = path.read_text()
    if old == text:
        print(f"unchanged: {path}")
        return
    path.write_text(text)
    print(f"updated: {path}")


def ensure_helper(text: str, path: Path) -> str:
    marker = "def _emit_cache_pinning_event("
    if marker in text:
        return text
    anchor = "logger = logging.getLogger(__name__)\n\n\n"
    helper = """logger = logging.getLogger(__name__)\n\n\ndef _emit_cache_pinning_event(event_type: str, **payload):\n    try:\n        logger.info(\n            \"[CACHE_PINNING_JSON] %s\",\n            json.dumps({\"event_type\": event_type, **payload}, sort_keys=True),\n        )\n    except Exception as exc:\n        logger.info(\n            \"[CACHE_PINNING_JSON] %s\",\n            json.dumps(\n                {\n                    \"event_type\": event_type,\n                    \"logging_error\": str(exc),\n                },\n                sort_keys=True,\n            ),\n        )\n\n\n"""
    if anchor not in text:
        raise SystemExit(f"Could not find helper anchor in {path}")
    return text.replace(anchor, helper, 1)


def repair_hiradix_cache() -> None:
    path = SOURCE_DIR / "python/sglang/srt/mem_cache/hiradix_cache.py"
    text = path.read_text()
    text = ensure_helper(text, path)

    if 'event_type": "worker.pin_prefix_applied"' not in text:
        old = """        logger.info(
            "[PIN] pin_prefix: nodes_pinned=%d, ttl=%ds", nodes_pinned, ttl_seconds
        )
        if budget_exceeded:
"""
        new = """        logger.info(
            "[PIN] pin_prefix: nodes_pinned=%d, ttl=%ds", nodes_pinned, ttl_seconds
        )
        _emit_cache_pinning_event(
            "worker.pin_prefix_applied",
            nodes_pinned=nodes_pinned,
            ttl_seconds=ttl_seconds,
            token_count=len(token_ids),
            budget_exceeded=budget_exceeded,
        )
        if budget_exceeded:
"""
        if old not in text:
            raise SystemExit(f"Could not find pin_prefix logger block in {path}")
        text = text.replace(old, new, 1)

    if 'event_type": "worker.pin_refreshed_host_insert"' not in text:
        old = """            # Refresh pin TTL on host insert hit
            if self._is_pinned(node):
                node.pin_expiry = time.monotonic() + node.pin_ttl
"""
        new = """            # Refresh pin TTL on host insert hit
            if self._is_pinned(node):
                node.pin_expiry = time.monotonic() + node.pin_ttl
                _emit_cache_pinning_event(
                    "worker.pin_refreshed_host_insert",
                    ttl_seconds=node.pin_ttl,
                    node_tokens=len(node.key),
                )
"""
        if old not in text:
            raise SystemExit(f"Could not find host-insert refresh block in {path}")
        text = text.replace(old, new, 1)

    if 'event_type": "worker.pin_refreshed_cache_hit"' not in text:
        old = """            # Refresh pin TTL on cache hit
            if self._is_pinned(child):
                child.pin_expiry = time.monotonic() + child.pin_ttl
"""
        new = """            # Refresh pin TTL on cache hit
            if self._is_pinned(child):
                child.pin_expiry = time.monotonic() + child.pin_ttl
                _emit_cache_pinning_event(
                    "worker.pin_refreshed_cache_hit",
                    ttl_seconds=child.pin_ttl,
                    node_tokens=len(child.key),
                )
"""
        if old not in text:
            raise SystemExit(f"Could not find cache-hit refresh block in {path}")
        text = text.replace(old, new, 1)

    write_if_changed(path, text)


def main() -> None:
    repair_hiradix_cache()
    print("Cache-pinning SGLang source repair complete.")


if __name__ == "__main__":
    main()
