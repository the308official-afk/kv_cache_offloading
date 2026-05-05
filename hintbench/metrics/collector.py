#!/usr/bin/env python3

"""Aggregate JSONL request records into a compact summary."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def percentile(values: list[float], pct: float) -> float | None:
  if not values:
      return None
  if len(values) == 1:
      return values[0]
  ordered = sorted(values)
  rank = (len(ordered) - 1) * pct
  lower = int(rank)
  upper = min(lower + 1, len(ordered) - 1)
  weight = rank - lower
  return ordered[lower] * (1 - weight) + ordered[upper] * weight


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
  ttfts = [r["ttft_ms"] for r in records if r.get("ttft_ms") is not None]
  cached_tokens = [r["cached_tokens"] or 0 for r in records if r.get("cached_tokens") is not None]
  kv_hit_rates = [r["kv_hit_rate"] for r in records if r.get("kv_hit_rate") is not None]
  successes = [r for r in records if r.get("success")]

  summary = {
      "total_requests": len(records),
      "successful_requests": len(successes),
      "failed_requests": len(records) - len(successes),
      "avg_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
      "p50_latency_ms": round(percentile(latencies, 0.50), 3) if latencies else None,
      "p95_latency_ms": round(percentile(latencies, 0.95), 3) if latencies else None,
      "p99_latency_ms": round(percentile(latencies, 0.99), 3) if latencies else None,
      "avg_ttft_ms": round(sum(ttfts) / len(ttfts), 3) if ttfts else None,
      "avg_cached_tokens": round(sum(cached_tokens) / len(cached_tokens), 3) if cached_tokens else None,
      "avg_kv_hit_rate": round(statistics.mean(kv_hit_rates), 3) if kv_hit_rates else None,
  }

  output_path = Path(args.output_file)
  output_path.parent.mkdir(parents=True, exist_ok=True)
  output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
  main()
