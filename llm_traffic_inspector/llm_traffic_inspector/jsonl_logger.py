from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonlLogger:
    def __init__(self, log_directory: Path, capture_mode: str) -> None:
        self.log_directory = log_directory
        self.capture_mode = capture_mode
        self.log_directory.mkdir(parents=True, exist_ok=True)
        if capture_mode == "full":
            try:
                os.chmod(self.log_directory, 0o700)
            except OSError:
                pass
        self.path = self.log_directory / f"traffic_{datetime.now(timezone.utc):%Y%m%d}.jsonl"

    def write(self, record: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        if self.capture_mode == "full":
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass

