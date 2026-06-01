#!/usr/bin/env python3

"""Estimate HBM bytes per agent/inference phase bucket from Nsight Compute CSV."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


READ_METRICS = {
    "dram__bytes_read.sum",
    "dram__sectors_read.sum",
}
WRITE_METRICS = {
    "dram__bytes_write.sum",
    "dram__sectors_write.sum",
}
TOTAL_METRICS = {
    "dram__bytes.sum",
}
SECTOR_SIZE_BYTES = 32.0


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip().replace(",", "")
    if not cleaned or cleaned.upper() in {"N/A", "NAN", "INF"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        match = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", cleaned)
        if not match:
            return None
        return float(match.group(0))


def convert_to_bytes(value: float, metric_name: str, metric_unit: str | None) -> float:
    unit = (metric_unit or "").strip().lower()
    if metric_name in READ_METRICS | WRITE_METRICS and "sector" in metric_name:
        return value * SECTOR_SIZE_BYTES
    if unit in {"kbyte", "kbytes", "kb"}:
        return value * 1_000.0
    if unit in {"mbyte", "mbytes", "mb"}:
        return value * 1_000_000.0
    if unit in {"gbyte", "gbytes", "gb"}:
        return value * 1_000_000_000.0
    if unit in {"kib", "kibibyte", "kibibytes"}:
        return value * 1024.0
    if unit in {"mib", "mebibyte", "mebibytes"}:
        return value * 1024.0 * 1024.0
    if unit in {"gib", "gibibyte", "gibibytes"}:
        return value * 1024.0 * 1024.0 * 1024.0
    return value


def find_ncu_header(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        lowered = line.lower()
        if "metric name" in lowered and "metric value" in lowered:
            return index
    raise SystemExit("Could not find an Nsight Compute CSV header with Metric Name and Metric Value.")


def load_ncu_raw_rows(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header_index = find_ncu_header(lines)
    reader = csv.DictReader(lines[header_index:])
    return [dict(row) for row in reader]


def pick_field(row: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    by_normalized = {normalize_header(key): key for key in row}
    for candidate in candidates:
        key = by_normalized.get(normalize_header(candidate))
        if key is not None:
            value = row.get(key)
            if value is not None:
                return value
    return None


def load_ncu_kernel_metrics(path: Path) -> dict[str, dict[str, Any]]:
    rows = load_ncu_raw_rows(path)
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        kernel_name = pick_field(row, ("Kernel Name", "Kernel", "Name"))
        metric_name = pick_field(row, ("Metric Name", "Metric"))
        metric_unit = pick_field(row, ("Metric Unit", "Unit"))
        metric_value = pick_field(row, ("Metric Value", "Value"))
        if not kernel_name or not metric_name:
            continue
        metric_name = metric_name.strip()
        if metric_name not in READ_METRICS | WRITE_METRICS | TOTAL_METRICS:
            continue
        parsed = parse_number(metric_value)
        if parsed is None:
            continue
        byte_value = convert_to_bytes(parsed, metric_name, metric_unit)
        grouped[kernel_name.strip()][metric_name].append(byte_value)

    metrics: dict[str, dict[str, Any]] = {}
    for kernel_name, metric_values in grouped.items():
        read_values = [value for metric in READ_METRICS for value in metric_values.get(metric, [])]
        write_values = [value for metric in WRITE_METRICS for value in metric_values.get(metric, [])]
        total_values = [value for metric in TOTAL_METRICS for value in metric_values.get(metric, [])]
        read_avg = sum(read_values) / len(read_values) if read_values else 0.0
        write_avg = sum(write_values) / len(write_values) if write_values else 0.0
        total_avg = sum(total_values) / len(total_values) if total_values else read_avg + write_avg
        metrics[kernel_name] = {
            "kernel_name": kernel_name,
            "ncu_metric_samples": max(len(read_values), len(write_values), len(total_values)),
            "avg_hbm_read_bytes_per_launch": read_avg,
            "avg_hbm_write_bytes_per_launch": write_avg,
            "avg_hbm_total_bytes_per_launch": total_avg,
            "metrics_found": ",".join(sorted(metric_values)),
        }
    return metrics


def normalize_kernel_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().replace("`", ""))


def find_metric_for_kernel(kernel_name: str, metrics: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    normalized = normalize_kernel_name(kernel_name)
    normalized_metrics = {normalize_kernel_name(name): payload for name, payload in metrics.items()}
    if normalized in normalized_metrics:
        return normalized_metrics[normalized]
    for metric_name, payload in normalized_metrics.items():
        if normalized and normalized in metric_name:
            return payload
        if metric_name and metric_name in normalized:
            return payload
    return None


def round_float(value: float, digits: int = 3) -> float:
    return round(value, digits)


def summarize_hbm(
    top_rows: list[dict[str, str]],
    ncu_metrics: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    kernel_metric_rows = [
        {
            "kernel_name": payload["kernel_name"],
            "ncu_metric_samples": payload["ncu_metric_samples"],
            "avg_hbm_read_bytes_per_launch": round_float(payload["avg_hbm_read_bytes_per_launch"]),
            "avg_hbm_write_bytes_per_launch": round_float(payload["avg_hbm_write_bytes_per_launch"]),
            "avg_hbm_total_bytes_per_launch": round_float(payload["avg_hbm_total_bytes_per_launch"]),
            "metrics_found": payload["metrics_found"],
        }
        for payload in ncu_metrics.values()
    ]
    kernel_metric_rows.sort(key=lambda row: float(row["avg_hbm_total_bytes_per_launch"]), reverse=True)

    estimate_rows: list[dict[str, Any]] = []
    bucket_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in top_rows:
        metric = find_metric_for_kernel(row.get("kernel_name") or "", ncu_metrics)
        kernel_count = int(float(row.get("kernel_count") or 0))
        duration_ms = float(row.get("duration_ms") or 0.0)
        read_total = kernel_count * float(metric["avg_hbm_read_bytes_per_launch"]) if metric else 0.0
        write_total = kernel_count * float(metric["avg_hbm_write_bytes_per_launch"]) if metric else 0.0
        hbm_total = kernel_count * float(metric["avg_hbm_total_bytes_per_launch"]) if metric else 0.0
        matched = metric is not None
        key = (row.get("agent_phase") or "", row.get("inference_phase") or "", row.get("bucket") or "")
        bucket_entry = bucket_rows.setdefault(
            key,
            {
                "agent_phase": key[0],
                "inference_phase": key[1],
                "bucket": key[2],
                "selected_kernel_rows": 0,
                "matched_kernel_rows": 0,
                "kernel_count": 0,
                "duration_ms": 0.0,
                "matched_duration_ms": 0.0,
                "estimated_hbm_read_gb": 0.0,
                "estimated_hbm_write_gb": 0.0,
                "estimated_hbm_total_gb": 0.0,
            },
        )
        bucket_entry["selected_kernel_rows"] += 1
        bucket_entry["kernel_count"] += kernel_count
        bucket_entry["duration_ms"] += duration_ms
        if matched:
            bucket_entry["matched_kernel_rows"] += 1
            bucket_entry["matched_duration_ms"] += duration_ms
            bucket_entry["estimated_hbm_read_gb"] += read_total / 1_000_000_000.0
            bucket_entry["estimated_hbm_write_gb"] += write_total / 1_000_000_000.0
            bucket_entry["estimated_hbm_total_gb"] += hbm_total / 1_000_000_000.0
        estimate_rows.append(
            {
                "agent_phase": row.get("agent_phase"),
                "inference_phase": row.get("inference_phase"),
                "bucket": row.get("bucket"),
                "kernel_name": row.get("kernel_name"),
                "nsys_kernel_count": kernel_count,
                "nsys_duration_ms": round_float(duration_ms),
                "ncu_kernel_name": metric["kernel_name"] if metric else "",
                "ncu_matched": int(matched),
                "avg_hbm_read_bytes_per_launch": round_float(float(metric["avg_hbm_read_bytes_per_launch"])) if metric else 0.0,
                "avg_hbm_write_bytes_per_launch": round_float(float(metric["avg_hbm_write_bytes_per_launch"])) if metric else 0.0,
                "avg_hbm_total_bytes_per_launch": round_float(float(metric["avg_hbm_total_bytes_per_launch"])) if metric else 0.0,
                "estimated_hbm_read_gb": round_float(read_total / 1_000_000_000.0),
                "estimated_hbm_write_gb": round_float(write_total / 1_000_000_000.0),
                "estimated_hbm_total_gb": round_float(hbm_total / 1_000_000_000.0),
            }
        )

    summary_rows = []
    for entry in bucket_rows.values():
        matched_duration_ms = float(entry["matched_duration_ms"])
        total_gb = float(entry["estimated_hbm_total_gb"])
        bandwidth = total_gb / (matched_duration_ms / 1000.0) if matched_duration_ms else 0.0
        duration_ms = float(entry["duration_ms"])
        entry["duration_ms"] = round_float(duration_ms)
        entry["matched_duration_ms"] = round_float(matched_duration_ms)
        entry["matched_duration_pct"] = round_float((matched_duration_ms / duration_ms * 100.0) if duration_ms else 0.0)
        entry["estimated_hbm_read_gb"] = round_float(float(entry["estimated_hbm_read_gb"]))
        entry["estimated_hbm_write_gb"] = round_float(float(entry["estimated_hbm_write_gb"]))
        entry["estimated_hbm_total_gb"] = round_float(total_gb)
        entry["estimated_hbm_bandwidth_gb_s"] = round_float(bandwidth)
        summary_rows.append(entry)
    summary_rows.sort(key=lambda row: (str(row["agent_phase"]), str(row["inference_phase"]), str(row["bucket"])))
    estimate_rows.sort(key=lambda row: float(row["estimated_hbm_total_gb"]), reverse=True)
    return kernel_metric_rows, estimate_rows, summary_rows


def write_markdown(path: Path, summary_rows: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    lines = [
        "# HBM Phase Bucket Estimate",
        "",
        "This report joins Nsight Compute per-launch HBM metrics with Nsight Systems phase-aware kernel counts.",
        "Treat values as estimates for selected representative kernels, not full-process byte accounting.",
        "",
        f"Nsight Compute CSV: `{metadata['ncu_csv']}`",
        f"Top kernel CSV: `{metadata['top_agent_phase_kernels']}`",
        "",
        "| agent phase | inference phase | bucket | selected kernels | matched kernels | matched duration pct | estimated HBM GB | estimated GB/s |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['agent_phase']} | {row['inference_phase']} | {row['bucket']} | "
            f"{row['selected_kernel_rows']} | {row['matched_kernel_rows']} | "
            f"{row['matched_duration_pct']} | {row['estimated_hbm_total_gb']} | "
            f"{row['estimated_hbm_bandwidth_gb_s']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-agent-phase-kernels", required=True, type=Path)
    parser.add_argument("--ncu-csv", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    top_path = args.top_agent_phase_kernels.resolve()
    ncu_csv = args.ncu_csv.resolve()
    if not top_path.is_file():
        raise SystemExit(f"top agent phase kernels CSV not found: {top_path}")
    if not ncu_csv.is_file():
        raise SystemExit(f"Nsight Compute CSV not found: {ncu_csv}")

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    top_rows = read_csv_rows(top_path)
    ncu_metrics = load_ncu_kernel_metrics(ncu_csv)
    kernel_metric_rows, estimate_rows, summary_rows = summarize_hbm(top_rows, ncu_metrics)

    metadata = {
        "top_agent_phase_kernels": str(top_path),
        "ncu_csv": str(ncu_csv),
        "metric_names": sorted(READ_METRICS | WRITE_METRICS | TOTAL_METRICS),
        "note": "HBM values are estimated by multiplying Nsight Compute per-launch bytes by Nsight Systems kernel counts.",
    }
    (out_dir / "hbm_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    write_csv(out_dir / "hbm_ncu_kernel_metrics.csv", kernel_metric_rows)
    write_csv(out_dir / "hbm_top_kernel_estimates.csv", estimate_rows)
    write_csv(out_dir / "hbm_phase_bucket_summary.csv", summary_rows)
    write_markdown(out_dir / "hbm_summary.md", summary_rows, metadata)

    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
