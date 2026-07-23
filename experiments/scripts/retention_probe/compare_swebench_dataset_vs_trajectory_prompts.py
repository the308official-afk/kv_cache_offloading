#!/usr/bin/env python3
"""Compare the exact Exp9 dataset prompts with Exp9 trajectory prompts.

This is an offline inspection tool: it does not start Dynamo and does not send
requests. It reconstructs the prompt sequence that Exp9 would use for
RETENTION_REQUEST_SOURCE=swebench_dataset and swebench_trajectory, then writes
CSV/markdown summaries plus optional full prompt text files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import importlib.util
import json
import os
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
RETENTION_PROBE_PATH = REPO_ROOT / "experiments" / "scripts" / "retention_probe" / "run_kv_retention_probe.py"


def load_retention_probe_module() -> Any:
    spec = importlib.util.spec_from_file_location("kv_retention_probe_for_prompt_compare", RETENTION_PROBE_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load retention probe module from {RETENTION_PROBE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RETENTION_PROBE = load_retention_probe_module()


def parse_counts(value: str) -> list[int]:
    counts: list[int] = []
    for item in value.split():
        item = item.strip()
        if not item:
            continue
        try:
            count = int(item)
        except ValueError as exc:
            raise SystemExit(f"Invalid distractor count {item!r}") from exc
        if count < 0:
            raise SystemExit(f"Distractor count must be >= 0: {count}")
        counts.append(count)
    return counts or [0]


def parse_stage_filter(value: str) -> set[str]:
    return {item.strip() for item in value.split() if item.strip()}


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def prefix_hash(text: str, width: int) -> str:
    return short_hash(text[:width])


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("_") or "unknown"


def maybe_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_dataset_split(dataset_name: str, split: str) -> Any:
    try:
        datasets_module = importlib.import_module("datasets")
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "This prompt comparison requires the datasets package. "
            "Install it with: python3 -m pip install -r agentbench/requirements.txt"
        ) from exc
    return datasets_module.load_dataset(dataset_name, split=split)


def dataset_row_to_task(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Could not convert SWE-bench dataset row to dict: {exc}") from exc


def format_dataset_prompt(task: dict[str, Any]) -> str:
    return str(RETENTION_PROBE.format_swebench_dataset_prompt(task))


def read_catalog(path_value: str) -> list[dict[str, str]]:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise SystemExit(f"Trajectory catalog not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"Trajectory catalog is empty: {path}")
    return rows


def catalog_int(row: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(row.get(key, "") or default)
    except ValueError:
        return default


def read_catalog_prompt(row: dict[str, str]) -> str:
    raw_path = row.get("prompt_text_path") or ""
    if not raw_path:
        raise SystemExit(f"Catalog row is missing prompt_text_path: {json.dumps(row, sort_keys=True)}")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise SystemExit(f"Catalog prompt file not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_prompt_file(prompt_dir: Path, *, source: str, request_role: str, label: str, prompt: str) -> Path:
    prompt_dir.mkdir(parents=True, exist_ok=True)
    path = prompt_dir / f"{safe_name(source)}__{safe_name(request_role)}__{safe_name(label)}__{short_hash(prompt)}.txt"
    path.write_text(prompt, encoding="utf-8")
    return path


def prompt_row(
    *,
    source: str,
    request_role: str,
    role: str,
    position: int,
    included_in_counts: list[int],
    repo: str,
    instance_id: str,
    source_index: str,
    phase: str,
    stage_name: str,
    prompt: str,
    prompt_path: Path,
    preview_chars: int,
) -> dict[str, Any]:
    words = prompt.split()
    preview = prompt[:preview_chars].replace("\r", " ").replace("\n", "\\n")
    return {
        "source": source,
        "request_role": request_role,
        "role": role,
        "position": position,
        "included_in_counts": " ".join(str(count) for count in included_in_counts),
        "repo": repo,
        "instance_id": instance_id,
        "source_index": source_index,
        "phase": phase,
        "stage_name": stage_name,
        "prompt_hash": short_hash(prompt),
        "prompt_prefix_hash_256": prefix_hash(prompt, 256),
        "prompt_prefix_hash_512": prefix_hash(prompt, 512),
        "prompt_prefix_hash_1024": prefix_hash(prompt, 1024),
        "prompt_chars": len(prompt),
        "prompt_words": len(words),
        "prompt_text_path": maybe_relative(prompt_path),
        "prompt_preview": preview,
    }


def counts_including_position(counts: list[int], position: int) -> list[int]:
    return [count for count in counts if position <= count]


def build_dataset_rows(
    *,
    dataset_name: str,
    split: str,
    protected_index: int,
    distractor_counts: list[int],
    prompt_dir: Path,
    preview_chars: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dataset = load_dataset_split(dataset_name, split)
    if protected_index < 0 or protected_index >= len(dataset):
        raise SystemExit(f"Dataset protected index out of range: {protected_index}; split rows={len(dataset)}")

    max_count = max(distractor_counts)
    protected_task = dataset_row_to_task(dataset[protected_index])
    protected_prompt = format_dataset_prompt(protected_task)
    protected_repo = str(protected_task.get("repo", ""))
    protected_instance = str(protected_task.get("instance_id", f"dataset_index_{protected_index}"))

    rows: list[dict[str, Any]] = []
    prompt_path = write_prompt_file(
        prompt_dir,
        source="swebench_dataset",
        request_role="a_first",
        label=f"index{protected_index}",
        prompt=protected_prompt,
    )
    rows.append(
        prompt_row(
            source="swebench_dataset",
            request_role="a_first",
            role="protected",
            position=0,
            included_in_counts=distractor_counts,
            repo=protected_repo,
            instance_id=protected_instance,
            source_index=str(protected_index),
            phase="dataset_task",
            stage_name="dataset_task",
            prompt=protected_prompt,
            prompt_path=prompt_path,
            preview_chars=preview_chars,
        )
    )

    selected = []
    cursor = protected_index + 1
    seen: set[int] = set()
    while len(selected) < max_count and len(seen) < max(len(dataset) - 1, 0):
        idx = cursor % len(dataset)
        cursor += 1
        if idx == protected_index or idx in seen:
            continue
        seen.add(idx)
        selected.append(idx)

    for position, idx in enumerate(selected, start=1):
        task = dataset_row_to_task(dataset[idx])
        prompt = format_dataset_prompt(task)
        prompt_path = write_prompt_file(
            prompt_dir,
            source="swebench_dataset",
            request_role=f"distractor_{position:04d}",
            label=f"index{idx}",
            prompt=prompt,
        )
        rows.append(
            prompt_row(
                source="swebench_dataset",
                request_role=f"distractor_{position - 1:04d}",
                role="distractor",
                position=position,
                included_in_counts=counts_including_position(distractor_counts, position),
                repo=str(task.get("repo", "")),
                instance_id=str(task.get("instance_id", f"dataset_index_{idx}")),
                source_index=str(idx),
                phase="dataset_task",
                stage_name="dataset_task",
                prompt=prompt,
                prompt_path=prompt_path,
                preview_chars=preview_chars,
            )
        )

    replay_path = write_prompt_file(
        prompt_dir,
        source="swebench_dataset",
        request_role="a_replay",
        label=f"index{protected_index}",
        prompt=protected_prompt,
    )
    rows.append(
        prompt_row(
            source="swebench_dataset",
            request_role="a_replay",
            role="protected",
            position=max_count + 1,
            included_in_counts=distractor_counts,
            repo=protected_repo,
            instance_id=protected_instance,
            source_index=str(protected_index),
            phase="dataset_task",
            stage_name="dataset_task",
            prompt=protected_prompt,
            prompt_path=replay_path,
            preview_chars=preview_chars,
        )
    )

    summaries = summarize_source(
        source="swebench_dataset",
        requested_counts=distractor_counts,
        available_distractor_tasks=max(len(dataset) - 1, 0),
        selected_distractor_tasks=len(selected),
        rows=rows,
    )
    return rows, summaries


def build_trajectory_rows(
    *,
    catalog_path: str,
    protected_task_index: int,
    protected_stage: str,
    trajectory_stages: str,
    distractor_counts: list[int],
    prompt_dir: Path,
    preview_chars: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    catalog_rows = read_catalog(catalog_path)
    stage_filter = parse_stage_filter(trajectory_stages)
    if not stage_filter:
        raise SystemExit("trajectory_stages must not be empty")

    protected_candidates = [
        row for row in catalog_rows if catalog_int(row, "task_index", -1) == protected_task_index
    ]
    if protected_stage:
        protected_candidates = [
            row for row in protected_candidates
            if row.get("stage_name") == protected_stage or row.get("phase") == protected_stage
        ]
    if not protected_candidates:
        raise SystemExit(
            f"Protected trajectory prompt not found for task_index={protected_task_index} "
            f"stage={protected_stage!r}"
        )
    protected_row = sorted(
        protected_candidates,
        key=lambda row: (catalog_int(row, "stage_index"), str(row.get("stage_name", ""))),
    )[-1]
    protected_prompt = read_catalog_prompt(protected_row)

    task_rows: dict[int, list[dict[str, str]]] = {}
    for row in catalog_rows:
        phase = row.get("phase") or row.get("stage_name") or ""
        if phase not in stage_filter and row.get("stage_name") not in stage_filter:
            continue
        task_index = catalog_int(row, "task_index", -1)
        if task_index < 0 or task_index == protected_task_index:
            continue
        task_rows.setdefault(task_index, []).append(row)
    for rows in task_rows.values():
        rows.sort(key=lambda row: (catalog_int(row, "stage_index"), str(row.get("stage_name", ""))))

    max_count = max(distractor_counts)
    selected_task_indices = sorted(task_rows)[:max_count]

    rows_out: list[dict[str, Any]] = []
    protected_path = write_prompt_file(
        prompt_dir,
        source="swebench_trajectory",
        request_role="a_first",
        label=f"task{protected_task_index}_{protected_row.get('stage_name', protected_stage)}",
        prompt=protected_prompt,
    )
    rows_out.append(
        prompt_row(
            source="swebench_trajectory",
            request_role="a_first",
            role="protected",
            position=0,
            included_in_counts=distractor_counts,
            repo=protected_row.get("repo", ""),
            instance_id=protected_row.get("instance_id", ""),
            source_index=str(protected_task_index),
            phase=protected_row.get("phase", ""),
            stage_name=protected_row.get("stage_name", ""),
            prompt=protected_prompt,
            prompt_path=protected_path,
            preview_chars=preview_chars,
        )
    )

    request_position = 1
    for task_position, task_index in enumerate(selected_task_indices, start=1):
        for stage_position, row in enumerate(task_rows[task_index]):
            prompt = read_catalog_prompt(row)
            prompt_path = write_prompt_file(
                prompt_dir,
                source="swebench_trajectory",
                request_role=f"distractor_{task_position - 1:04d}_{stage_position:02d}",
                label=f"task{task_index}_{row.get('stage_name', '')}",
                prompt=prompt,
            )
            rows_out.append(
                prompt_row(
                    source="swebench_trajectory",
                    request_role=f"distractor_{task_position - 1:04d}_{stage_position:02d}",
                    role="distractor",
                    position=request_position,
                    included_in_counts=counts_including_position(distractor_counts, task_position),
                    repo=row.get("repo", ""),
                    instance_id=row.get("instance_id", ""),
                    source_index=str(task_index),
                    phase=row.get("phase", ""),
                    stage_name=row.get("stage_name", ""),
                    prompt=prompt,
                    prompt_path=prompt_path,
                    preview_chars=preview_chars,
                )
            )
            request_position += 1

    replay_path = write_prompt_file(
        prompt_dir,
        source="swebench_trajectory",
        request_role="a_replay",
        label=f"task{protected_task_index}_{protected_row.get('stage_name', protected_stage)}",
        prompt=protected_prompt,
    )
    rows_out.append(
        prompt_row(
            source="swebench_trajectory",
            request_role="a_replay",
            role="protected",
            position=request_position,
            included_in_counts=distractor_counts,
            repo=protected_row.get("repo", ""),
            instance_id=protected_row.get("instance_id", ""),
            source_index=str(protected_task_index),
            phase=protected_row.get("phase", ""),
            stage_name=protected_row.get("stage_name", ""),
            prompt=protected_prompt,
            prompt_path=replay_path,
            preview_chars=preview_chars,
        )
    )

    summaries = summarize_source(
        source="swebench_trajectory",
        requested_counts=distractor_counts,
        available_distractor_tasks=len(task_rows),
        selected_distractor_tasks=len(selected_task_indices),
        rows=rows_out,
    )
    return rows_out, summaries


def summarize_source(
    *,
    source: str,
    requested_counts: list[int],
    available_distractor_tasks: int,
    selected_distractor_tasks: int,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    distractors = [row for row in rows if row["role"] == "distractor"]
    protected = [row for row in rows if row["role"] == "protected" and row["request_role"] == "a_first"]
    protected_row = protected[0] if protected else {}
    summaries: list[dict[str, Any]] = []
    for count in requested_counts:
        count_distractors = [
            row for row in distractors
            if str(count) in str(row.get("included_in_counts", "")).split()
        ]
        chars = [int(row["prompt_chars"]) for row in count_distractors]
        words = [int(row["prompt_words"]) for row in count_distractors]
        prefix_256 = {str(row.get("prompt_prefix_hash_256", "")) for row in count_distractors}
        prefix_512 = {str(row.get("prompt_prefix_hash_512", "")) for row in count_distractors}
        prefix_1024 = {str(row.get("prompt_prefix_hash_1024", "")) for row in count_distractors}
        summaries.append(
            {
                "source": source,
                "requested_distractor_count": count,
                "available_distractor_tasks": available_distractor_tasks,
                "selected_distractor_tasks": min(selected_distractor_tasks, count),
                "enough_tasks_for_count": str(available_distractor_tasks >= count).lower(),
                "distractor_prompt_requests": len(count_distractors),
                "protected_prompt_chars": protected_row.get("prompt_chars", ""),
                "protected_prompt_words": protected_row.get("prompt_words", ""),
                "protected_prompt_hash": protected_row.get("prompt_hash", ""),
                "distractor_total_prompt_chars": sum(chars),
                "distractor_total_prompt_words": sum(words),
                "unique_prefix_256_count": len(prefix_256),
                "unique_prefix_512_count": len(prefix_512),
                "unique_prefix_1024_count": len(prefix_1024),
                "unique_prefix_256_rate": round(len(prefix_256) / len(count_distractors), 4) if count_distractors else "",
                "unique_prefix_512_rate": round(len(prefix_512) / len(count_distractors), 4) if count_distractors else "",
                "unique_prefix_1024_rate": round(len(prefix_1024) / len(count_distractors), 4) if count_distractors else "",
                "distractor_min_prompt_chars": min(chars) if chars else "",
                "distractor_median_prompt_chars": int(statistics.median(chars)) if chars else "",
                "distractor_mean_prompt_chars": int(sum(chars) / len(chars)) if chars else "",
                "distractor_max_prompt_chars": max(chars) if chars else "",
            }
        )
    return summaries


def write_markdown(path: Path, summary_rows: list[dict[str, Any]], prompt_rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Exp9 Prompt Source Comparison",
        "",
        "This report compares what Exp9 would send for `swebench_dataset` versus `swebench_trajectory`.",
        "It is offline only: no Dynamo requests are sent.",
        "",
        "## Summary",
        "",
        "| Source | Count | Enough Tasks | Distractor Prompt Requests | Unique Prefix 256 | Unique Prefix 512 | Unique Prefix 1024 | Protected Chars | Median Distractor Chars | Total Distractor Chars |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| "
            + " | ".join(
                str(row.get(key, ""))
                for key in (
                    "source",
                    "requested_distractor_count",
                    "enough_tasks_for_count",
                    "distractor_prompt_requests",
                    "unique_prefix_256_count",
                    "unique_prefix_512_count",
                    "unique_prefix_1024_count",
                    "protected_prompt_chars",
                    "distractor_median_prompt_chars",
                    "distractor_total_prompt_chars",
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## First Prompts",
            "",
            "| Source | Role | Request Role | Index | Stage | Chars | Words | Hash | Prefix 256 | Prefix 512 | Prefix 1024 | Prompt Text Path | Preview |",
            "|---|---|---|---|---|---:|---:|---|---|---|---|---|---|",
        ]
    )
    for row in prompt_rows[:40]:
        preview = str(row.get("prompt_preview", "")).replace("|", "\\|")
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("source", "")),
                    str(row.get("role", "")),
                    str(row.get("request_role", "")),
                    str(row.get("source_index", "")),
                    str(row.get("stage_name", "")),
                    str(row.get("prompt_chars", "")),
                    str(row.get("prompt_words", "")),
                    str(row.get("prompt_hash", "")),
                    str(row.get("prompt_prefix_hash_256", "")),
                    str(row.get("prompt_prefix_hash_512", "")),
                    str(row.get("prompt_prefix_hash_1024", "")),
                    f"`{row.get('prompt_text_path', '')}`",
                    preview,
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=os.environ.get("RETENTION_SWEBENCH_DATASET", "ScaleAI/SWE-bench_Pro"))
    parser.add_argument("--split", default=os.environ.get("RETENTION_SWEBENCH_SPLIT", "test"))
    parser.add_argument("--dataset-protected-index", type=int, default=int(os.environ.get("RETENTION_SWEBENCH_INDEX", "0")))
    parser.add_argument(
        "--dataset-distractor-counts",
        default=os.environ.get("EXP9_COMPARE_DATASET_DISTRACTOR_COUNTS", "200 400 730"),
    )
    parser.add_argument(
        "--trajectory-catalog",
        default=os.environ.get(
            "RETENTION_TRAJECTORY_PROMPT_CATALOG",
            "experiments/reports/latest_swebench_trajectory_prompt_catalog.csv",
        ),
    )
    parser.add_argument(
        "--trajectory-protected-task-index",
        type=int,
        default=int(os.environ.get("RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX", "0")),
    )
    parser.add_argument(
        "--trajectory-protected-stage",
        default=os.environ.get("RETENTION_TRAJECTORY_PROTECTED_STAGE", "planning"),
    )
    parser.add_argument(
        "--trajectory-stages",
        default=os.environ.get("RETENTION_TRAJECTORY_STAGES", "planning"),
    )
    parser.add_argument(
        "--trajectory-distractor-counts",
        default=os.environ.get("EXP9_COMPARE_TRAJECTORY_DISTRACTOR_COUNTS", "100 200 300 390"),
    )
    parser.add_argument("--preview-chars", type=int, default=int(os.environ.get("EXP9_COMPARE_PREVIEW_CHARS", "240")))
    parser.add_argument(
        "--out-dir",
        default=os.environ.get(
            "EXP9_PROMPT_SOURCE_COMPARISON_DIR",
            f"experiments/reports/exp9_prompt_source_comparison/exp9_prompt_source_comparison_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        ),
    )
    parser.add_argument(
        "--reports-prefix",
        default=os.environ.get("EXP9_PROMPT_SOURCE_REPORTS_PREFIX", "experiments/reports/latest_exp9_prompt_source"),
    )
    parser.add_argument(
        "--charts-prefix",
        default=os.environ.get("EXP9_PROMPT_SOURCE_CHARTS_PREFIX", "experiments/charts/exp9_prompt_source"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    prompt_dir = out_dir / "prompts"
    reports_prefix = Path(args.reports_prefix)
    if not reports_prefix.is_absolute():
        reports_prefix = REPO_ROOT / reports_prefix
    charts_prefix = Path(args.charts_prefix)
    if not charts_prefix.is_absolute():
        charts_prefix = REPO_ROOT / charts_prefix

    dataset_counts = parse_counts(args.dataset_distractor_counts)
    trajectory_counts = parse_counts(args.trajectory_distractor_counts)

    dataset_rows, dataset_summary = build_dataset_rows(
        dataset_name=args.dataset,
        split=args.split,
        protected_index=args.dataset_protected_index,
        distractor_counts=dataset_counts,
        prompt_dir=prompt_dir,
        preview_chars=args.preview_chars,
    )
    trajectory_rows, trajectory_summary = build_trajectory_rows(
        catalog_path=args.trajectory_catalog,
        protected_task_index=args.trajectory_protected_task_index,
        protected_stage=args.trajectory_protected_stage,
        trajectory_stages=args.trajectory_stages,
        distractor_counts=trajectory_counts,
        prompt_dir=prompt_dir,
        preview_chars=args.preview_chars,
    )

    prompt_rows = dataset_rows + trajectory_rows
    summary_rows = dataset_summary + trajectory_summary
    prompt_fieldnames = [
        "source",
        "request_role",
        "role",
        "position",
        "included_in_counts",
        "repo",
        "instance_id",
        "source_index",
        "phase",
        "stage_name",
        "prompt_hash",
        "prompt_prefix_hash_256",
        "prompt_prefix_hash_512",
        "prompt_prefix_hash_1024",
        "prompt_chars",
        "prompt_words",
        "prompt_text_path",
        "prompt_preview",
    ]
    summary_fieldnames = [
        "source",
        "requested_distractor_count",
        "available_distractor_tasks",
        "selected_distractor_tasks",
        "enough_tasks_for_count",
        "distractor_prompt_requests",
        "protected_prompt_chars",
        "protected_prompt_words",
        "protected_prompt_hash",
        "distractor_total_prompt_chars",
        "distractor_total_prompt_words",
        "unique_prefix_256_count",
        "unique_prefix_512_count",
        "unique_prefix_1024_count",
        "unique_prefix_256_rate",
        "unique_prefix_512_rate",
        "unique_prefix_1024_rate",
        "distractor_min_prompt_chars",
        "distractor_median_prompt_chars",
        "distractor_mean_prompt_chars",
        "distractor_max_prompt_chars",
    ]

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "prompt_rows.csv", prompt_rows, prompt_fieldnames)
    write_csv(out_dir / "summary.csv", summary_rows, summary_fieldnames)
    write_markdown(out_dir / "summary.md", summary_rows, prompt_rows)

    write_csv(reports_prefix.with_name(reports_prefix.name + "_prompts.csv"), prompt_rows, prompt_fieldnames)
    write_csv(reports_prefix.with_name(reports_prefix.name + "_summary.csv"), summary_rows, summary_fieldnames)
    write_markdown(reports_prefix.with_name(reports_prefix.name + "_summary.md"), summary_rows, prompt_rows)

    write_csv(charts_prefix.with_name(charts_prefix.name + "_prompts.csv"), prompt_rows, prompt_fieldnames)
    write_csv(charts_prefix.with_name(charts_prefix.name + "_summary.csv"), summary_rows, summary_fieldnames)
    write_markdown(charts_prefix.with_name(charts_prefix.name + "_summary.md"), summary_rows, prompt_rows)

    print("Exp9 prompt source comparison ready.")
    print(f"run_dir: {maybe_relative(out_dir)}")
    print(f"prompt_rows: {maybe_relative(out_dir / 'prompt_rows.csv')}")
    print(f"summary: {maybe_relative(out_dir / 'summary.csv')}")
    print(f"latest_prompts: {maybe_relative(reports_prefix.with_name(reports_prefix.name + '_prompts.csv'))}")
    print(f"latest_summary: {maybe_relative(reports_prefix.with_name(reports_prefix.name + '_summary.csv'))}")
    print(f"charts_prompts: {maybe_relative(charts_prefix.with_name(charts_prefix.name + '_prompts.csv'))}")
    print(f"charts_summary: {maybe_relative(charts_prefix.with_name(charts_prefix.name + '_summary.csv'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
