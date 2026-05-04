#!/usr/bin/env python3

"""Run a small multi-config HintBench suite and compare the results."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
HINTBENCH_DIR = REPO_ROOT / "hintbench"
EXPERIMENTS_DIR = HINTBENCH_DIR / "experiments"
RESULTS_DIR = HINTBENCH_DIR / "results"
ANALYSIS_DIR = HINTBENCH_DIR / "analysis"
DEFAULT_RESULTS_TIMEZONE = "America/Chicago"
DEFAULT_CONFIGS = [
    str(EXPERIMENTS_DIR / "baseline_round_robin.yaml"),
    str(EXPERIMENTS_DIR / "kv_router.yaml"),
    str(EXPERIMENTS_DIR / "hint_routing.yaml"),
]


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


def run_cmd(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=capture_output,
        check=False,
    )
    if completed.returncode != 0:
        if capture_output:
            if completed.stdout:
                print(completed.stdout, end="")
            if completed.stderr:
                print(completed.stderr, end="", file=sys.stderr)
        raise SystemExit(completed.returncode)
    return completed


def restart_head(router_mode: str, model: str) -> None:
    stop_cmd = ["./run_dynamo_head.sh", "stop"]
    run_cmd(stop_cmd, env=os.environ.copy())

    start_env = os.environ.copy()
    start_env["DYNAMO_ROUTER_MODE"] = router_mode
    start_env["DYNAMO_MODEL_PATH"] = model
    start_cmd = ["./run_dynamo_head.sh", "start"]
    run_cmd(start_cmd, env=start_env)


def extract_run_dir(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("Run directory: "):
            return line.split("Run directory: ", 1)[1].strip()
    raise SystemExit("Could not find 'Run directory:' in run_experiment.py output.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--frontend-url",
        default="http://127.0.0.1:8000/v1/chat/completions",
        help="OpenAI-style chat completions endpoint on the head node.",
    )
    parser.add_argument(
        "--results-dir",
        default=str(RESULTS_DIR),
        help="Directory where per-run output should be stored.",
    )
    parser.add_argument(
        "--results-timezone",
        default=os.environ.get("HINTBENCH_RESULTS_TIMEZONE", DEFAULT_RESULTS_TIMEZONE),
        help=(
            "Timezone used for result folder timestamps and suite output naming. "
            f"Default: {DEFAULT_RESULTS_TIMEZONE}"
        ),
    )
    parser.add_argument(
        "--skip-head-restart",
        action="store_true",
        help="Do not restart the head node between configs. Use only if you manage router mode manually.",
    )
    parser.add_argument(
        "--configs",
        nargs="+",
        default=DEFAULT_CONFIGS,
        help="Experiment configs to run in order.",
    )
    args = parser.parse_args()

    results_tz = ZoneInfo(args.results_timezone)
    suite_started_at = datetime.now(results_tz)
    suite_id = suite_started_at.strftime("%Y%m%d_%H%M%S")
    suite_dir = Path(args.results_dir) / f"suite_{suite_id}"
    suite_dir.mkdir(parents=True, exist_ok=True)

    run_dirs: list[str] = []

    for config_str in args.configs:
        config_path = Path(config_str)
        config = parse_flat_yaml(config_path)
        experiment_name = str(config.get("name", config_path.stem))
        router_mode = str(config.get("router_mode", "round-robin"))
        model = str(config.get("model", "Qwen/Qwen2.5-0.5B"))

        print(f"\n=== Running {experiment_name} ===")
        print(f"router mode: {router_mode}")
        print(f"model:       {model}")

        if not args.skip_head_restart:
            print("Restarting head node for requested router mode...")
            restart_head(router_mode, model)

        experiment_cmd = [
            sys.executable,
            str(HINTBENCH_DIR / "run_experiment.py"),
            "--config",
            str(config_path),
            "--frontend-url",
            args.frontend_url,
            "--results-dir",
            args.results_dir,
            "--results-timezone",
            args.results_timezone,
        ]
        completed = run_cmd(experiment_cmd, env=os.environ.copy(), capture_output=True)
        if completed.stdout:
            print(completed.stdout, end="")
        run_dir = extract_run_dir(completed.stdout)
        run_dirs.append(run_dir)

    compare_json = suite_dir / "comparison.json"
    compare_stdout = suite_dir / "comparison.txt"

    compare_cmd = [
        sys.executable,
        str(ANALYSIS_DIR / "compare_runs.py"),
        *run_dirs,
        "--json-output",
        str(compare_json),
    ]
    completed = run_cmd(compare_cmd, env=os.environ.copy(), capture_output=True)
    compare_stdout.write_text(completed.stdout, encoding="utf-8")

    print("\n=== Combined comparison ===")
    print(completed.stdout, end="")
    print(f"Suite directory: {suite_dir}")
    print(f"Comparison text: {compare_stdout}")
    print(f"Comparison JSON: {compare_json}")


if __name__ == "__main__":
    main()
