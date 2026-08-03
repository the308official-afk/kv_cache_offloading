from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_records(log_directory: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(log_directory.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise SystemExit(f"Invalid JSONL in {path}:{line_number}: {exc}") from exc
    return records


def build_hint_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(record.get("provider") or "", record.get("endpoint") or "")].append(record)

    rows: list[dict[str, Any]] = []
    for (provider, endpoint), group in sorted(grouped.items()):
        total = len(group)
        hint_counts: Counter[str] = Counter()
        hint_category: dict[str, str] = {}
        hint_example: dict[str, str] = {}
        for record in group:
            seen_in_request: set[str] = set()
            for finding in record.get("candidate_hint_fields") or []:
                path = finding.get("path", "")
                if not path:
                    continue
                seen_in_request.add(path)
                hint_category[path] = finding.get("category", "")
                hint_example.setdefault(path, finding.get("example_safe_value", ""))
            hint_counts.update(seen_in_request)
        for path, count in sorted(hint_counts.items()):
            rows.append(
                {
                    "provider": provider,
                    "endpoint": endpoint,
                    "requests": total,
                    "candidate_hint_field": path,
                    "hint_category": hint_category.get(path, ""),
                    "example_safe_value": hint_example.get(path, ""),
                    "requests_with_field": count,
                    "percent_requests_with_field": f"{(count / total * 100):.1f}%" if total else "0.0%",
                }
            )
    return rows


def build_overview(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(record.get("provider") or "", record.get("endpoint") or "")].append(record)

    rows: list[dict[str, str]] = []
    for (provider, endpoint), group in sorted(grouped.items()):
        header_names = sorted(
            {
                name.lower()
                for record in group
                for name in (record.get("safe_request_headers") or {}).keys()
            }
        )
        field_paths = sorted(
            {
                path
                for record in group
                for path in (record.get("json_field_paths") or [])
            }
        )
        candidate_paths = sorted(
            {
                item.get("path", "")
                for record in group
                for item in (record.get("candidate_hint_fields") or [])
                if item.get("path")
            }
        )
        rows.append(
            {
                "provider": provider,
                "endpoint": endpoint,
                "requests": str(len(group)),
                "header_names_observed": " ".join(header_names),
                "json_field_paths_observed": " ".join(field_paths),
                "candidate_hint_fields_observed": " ".join(candidate_paths),
                "cache_control_usage": yes_no(any("cache_control" in p for p in candidate_paths)),
                "service_tier_usage": yes_no(any("service_tier" in p for p in candidate_paths)),
                "reasoning_control_usage": yes_no(any("reasoning" in p for p in candidate_paths)),
                "dynamo_nvext_usage": yes_no(any(p.startswith("nvext") for p in candidate_paths)),
            }
        )
    return rows


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["provider", "endpoint", "requests"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_report(records: list[dict[str, Any]], overview: list[dict[str, str]], hint_rows: list[dict[str, Any]]) -> None:
    print("LLM Traffic Hint Report")
    print("=======================")
    print(f"Requests analyzed: {len(records)}")
    print()
    for row in overview:
        print(f"{row['provider']} {row['endpoint']}: {row['requests']} request(s)")
        print(f"  cache_control: {row['cache_control_usage']}")
        print(f"  service_tier: {row['service_tier_usage']}")
        print(f"  reasoning controls: {row['reasoning_control_usage']}")
        print(f"  nvext: {row['dynamo_nvext_usage']}")
    print()
    if hint_rows:
        print("Candidate hint fields:")
        for row in hint_rows:
            print(
                "  {field} | {category} | {pct} | example={example}".format(
                    field=row["candidate_hint_field"],
                    category=row["hint_category"],
                    pct=row["percent_requests_with_field"],
                    example=row["example_safe_value"],
                )
            )
    else:
        print("No candidate hint fields observed.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze LLM traffic inspector JSONL logs.")
    parser.add_argument("--log-dir", type=Path, default=Path("./logs"))
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--overview-csv", type=Path, default=None)
    args = parser.parse_args(argv)

    records = load_records(args.log_dir)
    overview = build_overview(records)
    hint_rows = build_hint_rows(records)
    print_report(records, overview, hint_rows)

    output_csv = args.output_csv or args.log_dir / "hint_report.csv"
    overview_csv = args.overview_csv or args.log_dir / "traffic_overview.csv"
    write_csv(output_csv, hint_rows)
    write_csv(overview_csv, overview)
    print()
    print(f"Hint CSV: {output_csv}")
    print(f"Overview CSV: {overview_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

