#!/usr/bin/env python3

"""Phase 1.5 experiment runner.

This ties together:
- workload generation
- async request sending
- metrics collection

It currently supports the shared-prefix workload and the simple flat YAML
experiment configs in hintbench/experiments/.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS_DIR = REPO_ROOT / "hintbench" / "experiments"
WORKLOADS_DIR = REPO_ROOT / "hintbench" / "workloads"
CLIENTS_DIR = REPO_ROOT / "hintbench" / "clients"
METRICS_DIR = REPO_ROOT / "hintbench" / "metrics"
RESULTS_DIR = REPO_ROOT / "hintbench" / "results"
DEFAULT_RESULTS_TIMEZONE = "America/Chicago"


def parse_flat_yaml(path: Path) -> dict:
    data: dict[str, object] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.isdigit():
            data[key] = int(value)
            continue
        try:
            data[key] = float(value)
            continue
        except ValueError:
            pass
        data[key] = value
    return data


def run_cmd(cmd: list[str], env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(cmd, cwd=REPO_ROOT, env=env, check=False)
    if completed.returncode != 0:
      raise SystemExit(completed.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=str(EXPERIMENTS_DIR / "baseline_round_robin.yaml"),
        help="Path to a hintbench experiment config.",
    )
    parser.add_argument(
        "--frontend-url",
        default="http://127.0.0.1:8000/v1/chat/completions",
        help="OpenAI-style chat completions endpoint on the head node.",
    )
    parser.add_argument(
        "--results-dir",
        default=str(RESULTS_DIR),
        help="Directory where experiment run output should be stored.",
    )
    parser.add_argument(
        "--results-timezone",
        default=os.environ.get("HINTBENCH_RESULTS_TIMEZONE", DEFAULT_RESULTS_TIMEZONE),
        help=(
            "Timezone used for result folder timestamps. "
            f"Default: {DEFAULT_RESULTS_TIMEZONE}"
        ),
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = parse_flat_yaml(config_path)

    experiment_name = str(config.get("name", config_path.stem))
    model = str(config.get("model", "Qwen/Qwen2.5-0.5B"))
    workload = str(config.get("workload", "shared_prefix"))
    concurrency = int(config.get("concurrency", 4))
    num_conversations = int(config.get("num_conversations", 4))
    turns_per_conversation = int(config.get("turns_per_conversation", 3))

    if workload != "shared_prefix":
        raise SystemExit(f"Unsupported workload for Phase 1.5: {workload}")

    results_tz = ZoneInfo(args.results_timezone)
    run_started_at = datetime.now(results_tz)
    run_id = run_started_at.strftime("%Y%m%d_%H%M%S")
    run_dir = Path(args.results_dir) / f"{experiment_name}_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    workload_file = run_dir / "workload.jsonl"
    results_file = run_dir / "results.jsonl"
    summary_file = run_dir / "summary.json"
    metadata_file = run_dir / "metadata.json"

    workload_cmd = [
        sys.executable,
        str(WORKLOADS_DIR / "shared_prefix.py"),
        "--num-conversations",
        str(num_conversations),
        "--turns-per-conversation",
        str(turns_per_conversation),
    ]
    workload_output = subprocess.check_output(workload_cmd, cwd=REPO_ROOT, text=True)
    workload_file.write_text(workload_output, encoding="utf-8")

    client_cmd = [
        sys.executable,
        str(CLIENTS_DIR / "async_loadgen.py"),
        "--frontend-url",
        args.frontend_url,
        "--model",
        model,
        "--workload-file",
        str(workload_file),
        "--output-file",
        str(results_file),
        "--concurrency",
        str(concurrency),
    ]
    run_cmd(client_cmd, env=os.environ.copy())

    collector_cmd = [
        sys.executable,
        str(METRICS_DIR / "collector.py"),
        "--input-file",
        str(results_file),
        "--output-file",
        str(summary_file),
    ]
    run_cmd(collector_cmd, env=os.environ.copy())

    metadata = {
        "experiment_name": experiment_name,
        "config_path": str(config_path),
        "frontend_url": args.frontend_url,
        "model": model,
        "workload": workload,
        "router_mode": config.get("router_mode"),
        "concurrency": concurrency,
        "num_conversations": num_conversations,
        "turns_per_conversation": turns_per_conversation,
        "results_timezone": args.results_timezone,
        "run_started_at": run_started_at.isoformat(),
        "run_dir": str(run_dir),
    }
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Experiment complete: {experiment_name}")
    print(f"Run directory: {run_dir}")
    print(f"Workload file: {workload_file}")
    print(f"Results file: {results_file}")
    print(f"Summary file: {summary_file}")


if __name__ == "__main__":
    main()
