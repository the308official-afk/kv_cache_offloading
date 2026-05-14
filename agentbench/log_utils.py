"""Small logging helpers for AgentBench checkpoint instrumentation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentbench.constants import (
    AGENTBENCH_LOG_EVERY_N,
    AGENTBENCH_LOG_MODE,
    AGENTBENCH_SHORT_PREVIEW_CHARS,
)

CHECKPOINT_LOG_FILE: Path | None = None
LIFECYCLE_LOG_FILE: Path | None = None
LIFECYCLE_SEQUENCE_INDEX = 0


def _truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _compact_value(value: Any) -> Any:
    if isinstance(value, str):
        return _truncate_text(value, AGENTBENCH_SHORT_PREVIEW_CHARS)
    if isinstance(value, list):
        return [_compact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _compact_value(item) for key, item in value.items()}
    return value


def should_log_task(*, task_index: int | None) -> bool:
    if AGENTBENCH_LOG_MODE == "off":
        return False
    if task_index is None:
        return True
    if task_index == 0:
        return True
    every_n = max(1, AGENTBENCH_LOG_EVERY_N)
    return task_index % every_n == 0


def set_checkpoint_log_file(path: str | Path | None) -> None:
    global CHECKPOINT_LOG_FILE
    CHECKPOINT_LOG_FILE = Path(path) if path is not None else None


def set_lifecycle_log_file(path: str | Path | None) -> None:
    global LIFECYCLE_LOG_FILE, LIFECYCLE_SEQUENCE_INDEX
    LIFECYCLE_LOG_FILE = Path(path) if path is not None else None
    if LIFECYCLE_LOG_FILE is None:
        LIFECYCLE_SEQUENCE_INDEX = 0
        return
    existing = load_logged_events(LIFECYCLE_LOG_FILE)
    if existing:
        LIFECYCLE_SEQUENCE_INDEX = max(
            int(item.get("sequence_index", 0))
            for item in existing
            if isinstance(item, dict)
        )
    else:
        LIFECYCLE_SEQUENCE_INDEX = 0


def _write_checkpoint_file(*, body: dict[str, Any]) -> None:
    if CHECKPOINT_LOG_FILE is None:
        return
    CHECKPOINT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if CHECKPOINT_LOG_FILE.exists():
        try:
            loaded = json.loads(CHECKPOINT_LOG_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                existing = loaded
        except Exception:  # noqa: BLE001
            existing = []
    existing.append(body)
    CHECKPOINT_LOG_FILE.write_text(
        json.dumps(existing, indent=2, default=str),
        encoding="utf-8",
    )


def load_logged_events(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    log_path = Path(path)
    if not log_path.exists():
        return []
    try:
        loaded = json.loads(log_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    if isinstance(loaded, list):
        return [item for item in loaded if isinstance(item, dict)]
    if isinstance(loaded, dict):
        events = loaded.get("events")
        if isinstance(events, list):
            return [item for item in events if isinstance(item, dict)]
    return []


def _append_logged_event(*, path: Path | None, body: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_logged_events(path)
    existing.append(body)
    path.write_text(
        json.dumps(existing, indent=2, default=str),
        encoding="utf-8",
    )


def log_checkpoint(*, check_point: str, payload: dict[str, Any], task_index: int | None) -> None:
    if not should_log_task(task_index=task_index):
        return

    print(f"# [CHECK_POINT] {check_point}")
    body = {
        "check_point": check_point,
        "task_index": task_index,
        **payload,
    }
    _write_checkpoint_file(body=body)
    if AGENTBENCH_LOG_MODE == "full":
        print(json.dumps(body, indent=2, default=str))
        return

    print(json.dumps(_compact_value(body), indent=2, default=str))


def log_lifecycle_event(*, stage: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    global LIFECYCLE_SEQUENCE_INDEX
    LIFECYCLE_SEQUENCE_INDEX += 1
    body = {
        "sequence_index": LIFECYCLE_SEQUENCE_INDEX,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        **(payload or {}),
    }
    _append_logged_event(path=LIFECYCLE_LOG_FILE, body=body)
    return body
