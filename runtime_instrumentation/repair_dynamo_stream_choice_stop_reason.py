#!/usr/bin/env python3
"""Repair Dynamo source when ChatChoiceStream no longer has stop_reason.

Some source snapshots still assign `choice.stop_reason = None` while flushing
buffered streaming chat choices. Newer `ChatChoiceStream` definitions no longer
expose that field; stop-reason details are carried through nvext response
metadata instead. Removing the stale assignment unblocks the Rust build.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(os.environ.get("SOURCE_DIR", ROOT / "upstream" / "dynamo"))
TARGET = SOURCE_DIR / "lib/llm/src/preprocessor.rs"
STALE_LINE = "                            choice.stop_reason = None;\n"


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Expected file not found: {TARGET}")

    text = TARGET.read_text()
    if STALE_LINE not in text:
        print(f"No stale choice.stop_reason assignment found in {TARGET}")
        return

    TARGET.write_text(text.replace(STALE_LINE, ""))
    print(f"removed stale choice.stop_reason assignment from: {TARGET}")


if __name__ == "__main__":
    main()
