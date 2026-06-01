#!/usr/bin/env python3

"""Verify a worker-only Nsight + phased AgentBench SWE-bench profile run."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_PHASES = ("planning", "execution", "patch_generation", "review")
BUCKETS = ("ffn_mlp", "attention_kv", "other")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def split_filter_values(values: list[str] | None) -> set[str]:
    if not values:
        return set()
    items: set[str] = set()
    for value in values:
        for item in value.split(","):
            stripped = item.strip()
            if stripped:
                items.add(stripped)
    return items


def parse_float(value: str | None) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def format_float(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def print_timing_table(
    rows: list[dict[str, str]],
    agent_phase_filter: set[str],
    inference_phase_filter: set[str],
) -> None:
    grouped: dict[tuple[str, str], dict[str, float]] = {}
    for row in rows:
        agent_phase = row.get("agent_phase") or "unknown"
        inference_phase = row.get("inference_phase") or "unknown"
        bucket = row.get("bucket") or "unknown"
        if agent_phase_filter and agent_phase not in agent_phase_filter:
            continue
        if inference_phase_filter and inference_phase not in inference_phase_filter:
            continue
        entry = grouped.setdefault((agent_phase, inference_phase), {bucket_name: 0.0 for bucket_name in BUCKETS})
        entry[bucket] = entry.get(bucket, 0.0) + parse_float(row.get("duration_ms"))

    if not grouped:
        print("No timing rows matched the selected filters.")
        return

    table_rows: list[dict[str, str]] = []
    for (agent_phase, inference_phase), bucket_ms in sorted(grouped.items()):
        total_ms = sum(bucket_ms.values())
        ffn_ms = bucket_ms.get("ffn_mlp", 0.0)
        attention_ms = bucket_ms.get("attention_kv", 0.0)
        other_ms = bucket_ms.get("other", 0.0)
        table_rows.append(
            {
                "agent_phase": agent_phase,
                "inference": inference_phase,
                "ffn_ms": format_float(ffn_ms),
                "attention_ms": format_float(attention_ms),
                "other_ms": format_float(other_ms),
                "total_ms": format_float(total_ms),
                "ffn_pct": format_float((ffn_ms / total_ms * 100.0) if total_ms else 0.0),
                "attention_pct": format_float((attention_ms / total_ms * 100.0) if total_ms else 0.0),
            }
        )

    headers = (
        ("agent_phase", "agent_phase"),
        ("inference", "inference"),
        ("ffn_ms", "ffn_ms"),
        ("attention_ms", "attention_ms"),
        ("other_ms", "other_ms"),
        ("total_ms", "total_ms"),
        ("ffn_pct", "ffn_pct"),
        ("attention_pct", "attention_pct"),
    )
    widths = {
        key: max(len(label), *(len(row[key]) for row in table_rows))
        for key, label in headers
    }
    header_line = "  ".join(label.ljust(widths[key]) for key, label in headers)
    divider = "  ".join("-" * widths[key] for key, _label in headers)
    print("\nAgent phase timing table:")
    print(header_line)
    print(divider)
    for row in table_rows:
        print("  ".join(row[key].ljust(widths[key]) for key, _label in headers))


def resolve_agentbench_result_dir(profile_dir: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit.resolve()
    pointer = profile_dir / "agentbench-result-dir.txt"
    if pointer.is_file():
        value = pointer.read_text(encoding="utf-8").strip()
        if value:
            return Path(value).resolve()
    return None


def phase_set_from_requests(classification: dict[str, Any]) -> set[str]:
    metadata = classification.get("metadata") or {}
    requests = metadata.get("phase_requests") or []
    phases = set()
    for request in requests:
        phase = request.get("agent_phase") if isinstance(request, dict) else None
        if phase:
            phases.add(str(phase))
    return phases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-dir", required=True, type=Path)
    parser.add_argument("--agentbench-result-dir", type=Path)
    parser.add_argument(
        "--expected-phases",
        default=",".join(DEFAULT_PHASES),
        help="Comma-separated agent_phase values expected in the worker trace.",
    )
    parser.add_argument(
        "--show-timing-table",
        action="store_true",
        help="Print a compact phase x prefill/decode x FFN/attention timing table.",
    )
    parser.add_argument(
        "--agent-phase",
        action="append",
        help="Filter --show-timing-table to one or more comma-separated agent phases.",
    )
    parser.add_argument(
        "--inference-phase",
        action="append",
        help="Filter --show-timing-table to one or more comma-separated inference phases, such as decode or prefill.",
    )
    args = parser.parse_args()

    profile_dir = args.profile_dir.resolve()
    if not profile_dir.is_dir():
        fail(f"profile directory does not exist: {profile_dir}")

    expected_phases = tuple(phase.strip() for phase in args.expected_phases.split(",") if phase.strip())
    if not expected_phases:
        fail("--expected-phases resolved to an empty list")

    nsys_reports = sorted(profile_dir.glob("*.nsys-rep"))
    sqlite_exports = sorted(profile_dir.glob("*.sqlite"))
    if not nsys_reports:
        fail(f"no .nsys-rep file found in {profile_dir}")
    if not sqlite_exports:
        fail(f"no .sqlite export found in {profile_dir}")

    worker_log = profile_dir / "dynamo-sglang-worker.full.log"
    if not worker_log.is_file():
        fail(f"worker log missing: {worker_log}")

    classification_path = profile_dir / "kernel_analysis" / "kernel_classification.json"
    if not classification_path.is_file():
        fail(f"kernel classification missing: {classification_path}")
    classification = load_json(classification_path)
    metadata = classification.get("metadata") or {}

    request_count = int(metadata.get("phase_request_count") or 0)
    if request_count < len(expected_phases):
        fail(f"expected at least {len(expected_phases)} phase requests, found {request_count}")

    observed_request_phases = phase_set_from_requests(classification)
    missing_request_phases = sorted(set(expected_phases) - observed_request_phases)
    if missing_request_phases:
        fail(f"worker runtime JSON is missing agent_phase values: {', '.join(missing_request_phases)}")

    phase_bucket_csv = profile_dir / "kernel_analysis" / "agent_phase_inference_bucket_summary.csv"
    if not phase_bucket_csv.is_file():
        fail(f"agent phase inference bucket CSV missing: {phase_bucket_csv}")
    rows = read_csv_rows(phase_bucket_csv)
    observed_triples = {
        (row.get("agent_phase"), row.get("inference_phase"), row.get("bucket"))
        for row in rows
    }
    for phase in expected_phases:
        for inference_phase in ("prefill", "decode"):
            if not any(item[0] == phase and item[1] == inference_phase for item in observed_triples):
                fail(f"no {inference_phase} kernel rows assigned to agent_phase={phase}")

    result_dir = resolve_agentbench_result_dir(profile_dir, args.agentbench_result_dir)
    measurements_path = result_dir / "others" / "measurements.json" if result_dir else None
    if not result_dir or not result_dir.is_dir():
        fail("AgentBench result directory was not found")
    if not measurements_path or not measurements_path.is_file():
        fail(f"AgentBench measurements missing: {measurements_path}")
    measurements = load_json(measurements_path)
    if not isinstance(measurements, list):
        fail(f"measurements file is not a list: {measurements_path}")
    measurement_phases = {
        str(row.get("phase"))
        for row in measurements
        if isinstance(row, dict) and row.get("phase")
    }
    missing_measurement_phases = sorted(set(expected_phases) - measurement_phases)
    if missing_measurement_phases:
        fail(f"AgentBench measurements are missing phases: {', '.join(missing_measurement_phases)}")

    print("Verified phased SWE-bench worker profile.")
    print(f"Profile directory: {profile_dir}")
    print(f"AgentBench result directory: {result_dir}")
    print(f"Nsight report: {nsys_reports[-1]}")
    print(f"SQLite export: {sqlite_exports[-1]}")
    print(f"Phase assignment: {metadata.get('phase_assignment_mode')}")
    print(f"Worker phase requests: {request_count}")
    print(f"Agent phases: {', '.join(expected_phases)}")
    print(f"Key table: {phase_bucket_csv}")
    if args.show_timing_table:
        print_timing_table(
            rows,
            split_filter_values(args.agent_phase),
            split_filter_values(args.inference_phase),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
