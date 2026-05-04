#!/usr/bin/env python3

"""Aggregate JSONL request records into a compact summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--input-file", required=True)
  parser.add_argument("--output-file", required=True)
  args = parser.parse_args()

  records = [
      json.loads(line)
      for line in Path(args.input_file).read_text().splitlines()
      if line.strip()
  ]

  latencies = [r["latency_ms"] for r in records if r.get("latency_ms") is not None]
  cached_tokens = [r["cached_tokens"] or 0 for r in records if r.get("cached_tokens") is not None]
  successes = [r for r in records if r.get("success")]

  summary = {
      "total_requests": len(records),
      "successful_requests": len(successes),
      "failed_requests": len(records) - len(successes),
      "avg_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
      "avg_cached_tokens": round(sum(cached_tokens) / len(cached_tokens), 3) if cached_tokens else None,
  }

  output_path = Path(args.output_file)
  output_path.parent.mkdir(parents=True, exist_ok=True)
  output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
  main()

