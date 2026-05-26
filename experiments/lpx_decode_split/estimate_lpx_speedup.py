#!/usr/bin/env python3

"""Estimate GPU+LPU decode speedup from classified kernel-time buckets."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_float_list(raw: str) -> list[float]:
    values = [float(part.strip()) for part in raw.split(",") if part.strip()]
    if not values:
        raise argparse.ArgumentTypeError("at least one value is required")
    if any(value < 0 for value in values):
        raise argparse.ArgumentTypeError("values must be non-negative")
    return values


def bucket_duration(payload: dict[str, Any], bucket: str) -> float:
    for row in payload.get("bucket_summary", []):
        if row.get("bucket") == bucket:
            return float(row.get("duration_ms") or 0.0)
    return 0.0


def estimate(
    payload: dict[str, Any],
    *,
    lpu_speedups: list[float],
    transfer_ms_per_token: list[float],
    completion_tokens: int,
) -> list[dict[str, Any]]:
    attention_ms = bucket_duration(payload, "attention_kv")
    ffn_ms = bucket_duration(payload, "ffn_mlp")
    other_ms = bucket_duration(payload, "other")
    baseline_ms = float(payload.get("total_kernel_duration_ms") or (attention_ms + ffn_ms + other_ms))

    rows: list[dict[str, Any]] = []
    for speedup in lpu_speedups:
        for transfer_cost in transfer_ms_per_token:
            transfer_ms = transfer_cost * completion_tokens
            projected_ms = attention_ms + (ffn_ms / speedup) + other_ms + transfer_ms
            rows.append(
                {
                    "lpu_ffn_speedup": speedup,
                    "transfer_ms_per_token": transfer_cost,
                    "completion_tokens": completion_tokens,
                    "baseline_kernel_ms": round(baseline_ms, 3),
                    "attention_kv_ms": round(attention_ms, 3),
                    "ffn_mlp_ms": round(ffn_ms, 3),
                    "other_ms": round(other_ms, 3),
                    "activation_transfer_ms": round(transfer_ms, 3),
                    "projected_kernel_ms": round(projected_ms, 3),
                    "projected_speedup": round(baseline_ms / projected_ms, 4) if projected_ms > 0 else None,
                    "ffn_share_pct": round((ffn_ms / baseline_ms * 100.0), 3) if baseline_ms > 0 else None,
                }
            )
    rows.sort(key=lambda row: (float(row["transfer_ms_per_token"]), float(row["lpu_ffn_speedup"])))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# LPX What-If Speedup",
        "",
        "| LPU FFN speedup | transfer ms/token | baseline ms | projected ms | projected speedup | FFN share pct |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row['lpu_ffn_speedup']} | "
            f"{row['transfer_ms_per_token']} | "
            f"{row['baseline_kernel_ms']} | "
            f"{row['projected_kernel_ms']} | "
            f"{row['projected_speedup']} | "
            f"{row['ffn_share_pct']} |"
        )
    lines.extend(
        [
            "",
            "Model:",
            "",
            "```text",
            "projected_kernel_ms = attention_kv_ms + ffn_mlp_ms / lpu_ffn_speedup + other_ms + activation_transfer_ms",
            "activation_transfer_ms = transfer_ms_per_token * completion_tokens",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classification-json", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--completion-tokens", type=int, default=256)
    parser.add_argument("--lpu-speedups", type=parse_float_list, default=parse_float_list("2,4,8"))
    parser.add_argument("--transfer-ms-per-token", type=parse_float_list, default=parse_float_list("0,0.05,0.1,0.25"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if any(value <= 0 for value in args.lpu_speedups):
        raise SystemExit("--lpu-speedups values must be positive")
    payload = json.loads(args.classification_json.read_text(encoding="utf-8"))
    out_dir = args.out_dir or args.classification_json.parent / "lpx_what_if"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = estimate(
        payload,
        lpu_speedups=args.lpu_speedups,
        transfer_ms_per_token=args.transfer_ms_per_token,
        completion_tokens=args.completion_tokens,
    )
    write_csv(out_dir / "lpx_speedup_estimates.csv", rows)
    write_markdown(out_dir / "summary.md", rows)
    (out_dir / "lpx_speedup_estimates.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
