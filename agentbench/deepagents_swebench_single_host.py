#!/usr/bin/env python3

"""Run one SWE-bench Pro task through Deep Agents against a local Dynamo frontend."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from datasets import load_dataset
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "datasets is required. Install with: python3 -m pip install -r agentbench/requirements.txt"
    ) from exc

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "pandas is required. Install with: python3 -m pip install -r agentbench/requirements.txt"
    ) from exc

try:
    from deepagents import create_deep_agent
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "deepagents is required. Install with: python3 -m pip install -r agentbench/requirements.txt"
    ) from exc

try:
    from langchain_openai import ChatOpenAI
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "langchain-openai is required. Install with: python3 -m pip install -r agentbench/requirements.txt"
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "agentbench" / "results"
DEFAULT_RESULTS_TIMEZONE = "America/Chicago"
DEFAULT_HINTS = {
    "priority": 5,
    "reuse_likelihood": 0.9,
    "agent_phase": "execution",
    "latency_sensitivity": 0.7,
    "program_id": "agentbench.deepagents.swebench_pro",
    "context_type": "software_engineering_long_horizon",
    "expected_output_tokens": 512,
}


def frontend_base_url(frontend_url: str) -> str:
    if "/v1/chat/completions" in frontend_url:
        return frontend_url.replace("/v1/chat/completions", "/v1")
    return frontend_url.rstrip("/")


def load_swebench_task(
    *,
    dataset_name: str | None,
    split: str,
    csv_path: str | None,
    index: int,
    instance_id: str | None,
) -> dict:
    if csv_path:
        rows = pd.read_csv(csv_path)
        if instance_id:
            matched = rows[rows["instance_id"] == instance_id]
            if matched.empty:
                raise SystemExit(f"instance_id not found in CSV: {instance_id}")
            return matched.iloc[0].to_dict()
        if index < 0 or index >= len(rows):
            raise SystemExit(f"index out of range for CSV: {index}")
        return rows.iloc[index].to_dict()

    if not dataset_name:
        raise SystemExit("Either --dataset or --csv-path is required.")

    ds = load_dataset(dataset_name, split=split)
    if instance_id:
        matches = [row for row in ds if row.get("instance_id") == instance_id]
        if not matches:
            raise SystemExit(f"instance_id not found in dataset: {instance_id}")
        return dict(matches[0])
    if index < 0 or index >= len(ds):
        raise SystemExit(f"index out of range for dataset: {index}")
    return dict(ds[index])


def format_task_prompt(task: dict) -> str:
    repo = task.get("repo", "unknown_repo")
    instance_id = task.get("instance_id", "unknown_instance")
    problem_statement = task.get("problem_statement", "").strip()
    requirements = str(task.get("requirements", "")).strip()
    interface = str(task.get("interface", "")).strip()
    selected_tests = str(task.get("selected_test_files_to_run", "")).strip()

    return f"""You are working on one SWE-bench Pro software engineering task.

Task metadata:
- instance_id: {instance_id}
- repo: {repo}

Problem statement:
{problem_statement}

Requirements:
{requirements if requirements else "None provided."}

Interface / environment notes:
{interface if interface else "None provided."}

Selected tests to run:
{selected_tests if selected_tests else "Not provided."}

Your job:
1. Break this task into concrete steps.
2. Identify what information would be needed to solve it well.
3. Produce a structured plan for solving it.
4. Give a first-pass solution strategy.

Do not claim that code was changed or tests were run unless you actually did so.
Focus on decomposition, reasoning, and a clear action plan."""


def build_agent(frontend_url: str, model: str, hint_json: str):
    extra_body = {"nvext": {"agent_hints": json.loads(hint_json)}}
    llm = ChatOpenAI(
        model=model,
        base_url=frontend_base_url(frontend_url),
        api_key="dummy",
        temperature=0.0,
        max_tokens=2048,
        timeout=300,
        extra_body=extra_body,
    )
    return create_deep_agent(
        model=llm,
        system_prompt=(
            "You are a careful software engineering agent. "
            "Break hard tasks into manageable steps, keep your reasoning organized, "
            "and produce a clear plan before attempting a solution."
        ),
    )


def save_result(run_dir: Path, payload: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "result.json").write_text(
        json.dumps(payload, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )


def stringify_unknown(value):
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump()
        except Exception:  # noqa: BLE001
            pass
    if hasattr(value, "dict"):
        try:
            return value.dict()
        except Exception:  # noqa: BLE001
            pass
    return repr(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="ScaleAI/SWE-bench_Pro")
    parser.add_argument("--split", default="test")
    parser.add_argument("--csv-path")
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--instance-id")
    parser.add_argument(
        "--frontend-url",
        default="http://127.0.0.1:8000/v1/chat/completions",
    )
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B")
    parser.add_argument(
        "--hint-json",
        default=json.dumps(DEFAULT_HINTS),
        help="JSON object passed as nvext.agent_hints on every model call.",
    )
    parser.add_argument(
        "--results-timezone",
        default=DEFAULT_RESULTS_TIMEZONE,
    )
    args = parser.parse_args()

    task = load_swebench_task(
        dataset_name=args.dataset,
        split=args.split,
        csv_path=args.csv_path,
        index=args.index,
        instance_id=args.instance_id,
    )
    prompt = format_task_prompt(task)
    agent = build_agent(args.frontend_url, args.model, args.hint_json)

    results_tz = ZoneInfo(args.results_timezone)
    run_started_at = datetime.now(results_tz)
    run_id = run_started_at.strftime("%Y%m%d_%H%M%S")
    safe_instance = str(task.get("instance_id", f"task_{args.index}")).replace("/", "__")
    run_dir = RESULTS_DIR / f"{safe_instance}_{run_id}"

    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})

    payload = {
        "run_started_at": run_started_at.isoformat(),
        "frontend_url": args.frontend_url,
        "model": args.model,
        "hint_json": json.loads(args.hint_json),
        "task": task,
        "prompt": prompt,
        "result": result,
    }
    save_result(run_dir, payload)

    print(f"AgentBench run complete: {safe_instance}")
    print(f"Run directory: {run_dir}")
    print(f"Result file: {run_dir / 'result.json'}")


if __name__ == "__main__":
    main()
