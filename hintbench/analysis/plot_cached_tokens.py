#!/usr/bin/env python3

"""Placeholder for cached-token plotting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary-file", required=True)
    args = parser.parse_args()
    summary = json.loads(Path(args.summary_file).read_text())
    print("Average cached tokens:", summary.get("avg_cached_tokens"))


if __name__ == "__main__":
    main()

