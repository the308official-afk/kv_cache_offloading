#!/usr/bin/env python3
"""Repair Dynamo source when old router field names remain in the clone.

Some Dynamo source snapshots contain a stale reference to
`overlap_score_credit` even though the current `KvRouterConfig` field is named
`overlap_score_weight`. The stale name breaks the Docker build during the Rust
wheel step. This script performs the narrow rename in source files only.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(os.environ.get("SOURCE_DIR", ROOT / "runtime_upstream" / "dynamo"))
OLD = "overlap_score_credit"
NEW = "overlap_score_weight"


def main() -> None:
    if not SOURCE_DIR.exists():
        raise SystemExit(f"Dynamo source directory not found: {SOURCE_DIR}")

    changed = 0
    for path in SOURCE_DIR.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", "target", ".venv"} for part in path.parts):
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        if OLD not in text:
            continue
        path.write_text(text.replace(OLD, NEW))
        changed += 1
        print(f"updated: {path}")

    if changed == 0:
        print(f"No {OLD} references found under {SOURCE_DIR}")
    else:
        print(f"Replaced {OLD} with {NEW} in {changed} file(s).")


if __name__ == "__main__":
    main()
