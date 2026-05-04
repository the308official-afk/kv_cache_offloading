#!/usr/bin/env python3

"""Placeholder for latency plotting.

Phase 1 keeps analysis lightweight. This script currently prints a short summary
from the aggregated metrics file and can later be extended into a real plotter.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary-file", required=True)
    args = parser.parse_args()
    summary = json.loads(Path(args.summary_file).read_text())
    print("Average latency (ms):", summary.get("avg_latency_ms"))
    print("Successful requests:", summary.get("successful_requests"))


if __name__ == "__main__":
    main()

