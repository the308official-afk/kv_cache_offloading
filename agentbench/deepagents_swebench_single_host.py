#!/usr/bin/env python3

"""Run one SWE-bench Pro task through Deep Agents against a local Dynamo frontend."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

CURRENT_FILE = Path(__file__).resolve()
REPO_ROOT = CURRENT_FILE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
    from agentbench.deepagents_app.src.agent import (
        run_task_workflow,
    )
    from agentbench.log_utils import log_checkpoint, set_checkpoint_log_file
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "The Deep Agents app modules could not be imported. "
        "If dependencies are missing, install them with: python3 -m pip install -r agentbench/requirements.txt. "
        f"Original import error: {exc}"
    ) from exc


RESULTS_DIR = REPO_ROOT / "agentbench" / "results"
REPOS_DIR = REPO_ROOT / "agentbench" / "repos"
DEFAULT_RESULTS_TIMEZONE = "America/Chicago"
DEFAULT_HINTS = {
    "priority": 5,
    "reuse_likelihood": 0.9,
    "agent_phase": "execution",
    "latency_sensitivity": 0.7,
    "program_id": "agentbench.deepagents_app",
    "context_type": "software_engineering_long_horizon",
    "expected_output_tokens": 512,
}


def task_source_label(
    *,
    dataset_name: str | None,
    split: str,
    csv_path: str | None,
    json_path: str | None,
) -> str:
    if json_path:
        return f"json:{json_path}"
    if csv_path:
        return f"csv:{csv_path}"
    return f"dataset:{dataset_name}:{split}"


def run_command(command: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    # Debugging note: every git/process hook in the wrapper flows through here.
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            check=check,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        program = command[0] if command else "command"
        raise SystemExit(
            f"Required executable not found: {program}. "
            "Install it first, or disable automatic SWE-bench repo checkout with "
            "--no-auto-repo-checkout if you only want dataset-backed task text."
        ) from exc


def infer_swebench_repo_url(task: dict) -> str | None:
    # Debugging note: this is the SWE-bench -> GitHub adaptation hook.
    # It teaches the wrapper how to turn dataset repo metadata into a cloneable URL.
    repo = str(task.get("repo") or "").strip()
    if not repo or "/" not in repo or " " in repo:
        return None
    if repo.startswith(("http://", "https://")):
        return repo
    return f"https://github.com/{repo}.git"


def infer_swebench_base_commit(task: dict) -> str | None:
    for key in ("base_commit", "commit", "revision", "sha"):
        value = str(task.get(key) or "").strip()
        if value:
            return value
    return None


def repo_cache_dir_name(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    repo_path = parsed.path.strip("/")
    if repo_path.endswith(".git"):
        repo_path = repo_path[:-4]
    return repo_path.replace("/", "__") or "repo"


def ensure_shared_repo_checkout(repo_url: str) -> Path:
    # Debugging note: this is the shared single-GPU repo cache under agentbench/repos/.
    # Automatic SWE-bench runs reuse this checkout instead of inventing a new repo path each time.
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    shared_repo_dir = REPOS_DIR / repo_cache_dir_name(repo_url)
    if not shared_repo_dir.exists():
        run_command(["git", "clone", repo_url, str(shared_repo_dir)])
        return shared_repo_dir

    git_dir = shared_repo_dir / ".git"
    if not git_dir.exists():
        raise SystemExit(
            f"Shared repo path exists but is not a git checkout: {shared_repo_dir}"
        )

    run_command(["git", "fetch", "--all", "--tags"], cwd=shared_repo_dir)
    return shared_repo_dir


def should_auto_materialize_swebench_repo(
    *,
    dataset_name: str | None,
    csv_path: str | None,
    json_path: str | None,
) -> bool:
    if csv_path or json_path or not dataset_name:
        return False
    return "swe-bench" in dataset_name.lower()


def load_swebench_task(
    *,
    dataset_name: str | None,
    split: str,
    csv_path: str | None,
    json_path: str | None,
    index: int,
    instance_id: str | None,
) -> dict:
    # [CHECK_POINT 1] One SWE-bench Pro task enters the agent harness here.
    # Debugging note: this wrapper can load one task from three sources:
    # Hugging Face SWE-bench, CSV, or local JSON.
    if json_path:
        return json.loads(Path(json_path).read_text(encoding="utf-8"))

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


def save_result(run_dir: Path, payload: dict) -> None:
    # Debugging note: this is the saved-artifacts hook for the benchmark wrapper.
    # The final run summary is always materialized as result.json here.
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


def prepare_workspace(
    *,
    run_dir: Path,
    repo_path: str | None,
    repo_url: str | None,
    checkout_commit: str | None = None,
    inferred_from_task: bool = False,
    shared_repo_source: Path | None = None,
) -> tuple[Path | None, dict]:
    # [CHECK_POINT 2] A writable repo workspace for the agent is prepared here.
    # Debugging note: this wrapper supports three workspace modes:
    # 1. explicit local repo path
    # 2. explicit remote repo URL
    # 3. automatic SWE-bench shared checkout under agentbench/repos/
    if not repo_path and not repo_url:
        return None, {"workspace_mode": "none"}

    workspace_dir = run_dir / "workspace"
    metadata: dict[str, str] = {"workspace_mode": "none"}

    if repo_path:
        source_repo = Path(repo_path).expanduser().resolve()
        if not source_repo.exists():
            raise SystemExit(f"--repo-path does not exist: {source_repo}")
        try:
            run_command(["git", "clone", "--no-hardlinks", str(source_repo), str(workspace_dir)])
            metadata = {
                "workspace_mode": "local_clone",
                "source_repo_path": str(source_repo),
                "workspace_path": str(workspace_dir),
            }
        except Exception:  # noqa: BLE001
            shutil.copytree(source_repo, workspace_dir, dirs_exist_ok=True)
            git_dir = workspace_dir / ".git"
            if not git_dir.exists():
                metadata = {
                    "workspace_mode": "local_copy_non_git",
                    "source_repo_path": str(source_repo),
                    "workspace_path": str(workspace_dir),
                }
            else:
                metadata = {
                    "workspace_mode": "local_copy_git_repo",
                    "source_repo_path": str(source_repo),
                    "workspace_path": str(workspace_dir),
                }
        if checkout_commit and (workspace_dir / ".git").exists():
            run_command(["git", "checkout", checkout_commit], cwd=workspace_dir)
            metadata["checked_out_commit"] = checkout_commit
        return workspace_dir, metadata

    if shared_repo_source is not None:
        # Debugging note: automatic SWE-bench runs now operate directly inside the shared checkout.
        # This means repo edits persist across runs until the repo is manually cleaned or reset.
        if checkout_commit:
            run_command(["git", "checkout", checkout_commit], cwd=shared_repo_source)
        metadata = {
            "workspace_mode": "shared_checkout_in_place",
            "source_repo_url": repo_url,
            "workspace_path": str(shared_repo_source),
            "shared_repo_path": str(shared_repo_source),
        }
        if checkout_commit:
            metadata["checked_out_commit"] = checkout_commit
        return shared_repo_source, metadata

    assert repo_url is not None
    run_command(["git", "clone", "--no-hardlinks", repo_url, str(workspace_dir)])
    metadata = {
        "workspace_mode": "auto_remote_clone" if inferred_from_task else "remote_clone",
        "source_repo_url": repo_url,
        "workspace_path": str(workspace_dir),
    }
    if checkout_commit:
        run_command(["git", "checkout", checkout_commit], cwd=workspace_dir)
        metadata["checked_out_commit"] = checkout_commit
    return workspace_dir, metadata


def collect_workspace_artifacts(run_dir: Path, workspace_dir: Path | None) -> dict:
    # [CHECK_POINT 6] Git patch and workspace artifacts are captured here.
    # Debugging note: this is where repo-aware runs become benchmark artifacts:
    # patch file, git status, git diff stat, and workspace metadata.
    if workspace_dir is None:
        return {"workspace_present": False}

    artifacts: dict[str, object] = {
        "workspace_present": True,
        "workspace_path": str(workspace_dir),
        "git_repo": False,
    }
    git_dir = workspace_dir / ".git"
    if not git_dir.exists():
        return artifacts

    artifacts["git_repo"] = True
    status = run_command(["git", "status", "--short"], cwd=workspace_dir, check=False)
    diff = run_command(["git", "diff", "--binary"], cwd=workspace_dir, check=False)
    diff_stat = run_command(["git", "diff", "--stat"], cwd=workspace_dir, check=False)
    head = run_command(["git", "rev-parse", "HEAD"], cwd=workspace_dir, check=False)

    patch_path = run_dir / "workspace.patch"
    patch_path.write_text(diff.stdout, encoding="utf-8")
    (run_dir / "git_status.txt").write_text(status.stdout, encoding="utf-8")
    (run_dir / "git_diff_stat.txt").write_text(diff_stat.stdout, encoding="utf-8")

    artifacts.update(
        {
            "git_head": head.stdout.strip(),
            "git_status": status.stdout,
            "git_diff_stat": diff_stat.stdout,
            "patch_file": str(patch_path),
            "patch_nonempty": bool(diff.stdout.strip()),
        }
    )
    return artifacts


def main() -> None:
    # Debugging note: main() is the wrapper entry point.
    # It is responsible for the outer pipeline:
    # load task -> choose workspace -> call Deep Agents app -> save artifacts.
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="ScaleAI/SWE-bench_Pro")
    parser.add_argument("--split", default="test")
    parser.add_argument("--csv-path")
    parser.add_argument("--json-path")
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--instance-id")
    parser.add_argument(
        "--repo-path",
        help="Local repo checkout to clone into the run workspace before invoking the agent.",
    )
    parser.add_argument(
        "--repo-url",
        help="Remote git URL to clone into the run workspace before invoking the agent.",
    )
    parser.add_argument(
        "--no-auto-repo-checkout",
        action="store_true",
        help="Disable automatic GitHub repo clone + base-commit checkout for SWE-bench dataset tasks.",
    )
    parser.add_argument(
        "--frontend-url",
        default="http://127.0.0.1:8000/v1/chat/completions",
    )
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B")
    parser.add_argument(
        "--app-variant",
        default="local",
        choices=["local", "upstream_deploy_coding_agent"],
        help="Choose whether to run the local Deep Agents app or the cloned upstream deploy-coding-agent instructions/skills.",
    )
    parser.add_argument(
        "--hint-json",
        default=json.dumps(DEFAULT_HINTS),
        help="JSON object passed as nvext.agent_hints on every model call.",
    )
    parser.add_argument(
        "--results-timezone",
        default=DEFAULT_RESULTS_TIMEZONE,
    )
    parser.add_argument(
        "--step-limit",
        type=int,
        default=4,
        help="Maximum number of explicit decomposition steps to dispatch.",
    )
    args = parser.parse_args()

    results_tz = ZoneInfo(args.results_timezone)
    run_started_at = datetime.now(results_tz)
    run_id = run_started_at.strftime("%Y%m%d_%H%M%S")

    task = load_swebench_task(
        dataset_name=args.dataset,
        split=args.split,
        csv_path=args.csv_path,
        json_path=args.json_path,
        index=args.index,
        instance_id=args.instance_id,
    )
    safe_instance = str(task.get("instance_id", f"task_{args.index}")).replace("/", "__")
    run_dir = RESULTS_DIR / f"{safe_instance}_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_log_path = run_dir / "checkpoints.json"
    set_checkpoint_log_file(checkpoint_log_path)
    # [CHECK_POINT 1] SWE-bench task loaded before entering the Deep Agents harness.
    # [CHECK_POINT 1] Normalized task payload logged here before prompt expansion.
    log_checkpoint(
        check_point="1. SWE-bench task loaded before Deep Agents harness",
        task_index=args.index,
        payload={
            "task_source": task_source_label(
                dataset_name=args.dataset,
                split=args.split,
                csv_path=args.csv_path,
                json_path=args.json_path,
            ),
            "app_variant": args.app_variant,
            "task": task,
        },
    )

    # Debugging note: this block is the automatic SWE-bench repo materialization decision.
    # If the task came from the dataset and no manual repo override was passed,
    # the wrapper will infer a GitHub repo + commit from the task metadata.
    auto_repo_checkout = {
        "enabled": False,
        "repo_url": None,
        "checkout_commit": None,
        "used": False,
    }
    repo_path = args.repo_path
    repo_url = args.repo_url
    inferred_checkout_commit: str | None = None
    inferred_from_task = False
    shared_repo_source: Path | None = None
    if (
        not args.no_auto_repo_checkout
        and repo_path is None
        and repo_url is None
        and should_auto_materialize_swebench_repo(
            dataset_name=args.dataset,
            csv_path=args.csv_path,
            json_path=args.json_path,
        )
    ):
        inferred_repo_url = infer_swebench_repo_url(task)
        inferred_checkout_commit = infer_swebench_base_commit(task)
        auto_repo_checkout = {
            "enabled": True,
            "repo_url": inferred_repo_url,
            "checkout_commit": inferred_checkout_commit,
            "used": bool(inferred_repo_url),
        }
        if inferred_repo_url:
            repo_url = inferred_repo_url
            inferred_from_task = True
            shared_repo_source = ensure_shared_repo_checkout(inferred_repo_url)

    workspace_dir, workspace_metadata = prepare_workspace(
        run_dir=run_dir,
        repo_path=repo_path,
        repo_url=repo_url,
        checkout_commit=inferred_checkout_commit if inferred_from_task else None,
        inferred_from_task=inferred_from_task,
        shared_repo_source=shared_repo_source,
    )
    task = dict(task)
    if workspace_dir is not None:
        task["workspace_path"] = str(workspace_dir)

    base_hints = json.loads(args.hint_json)
    workflow = run_task_workflow(
        # Debugging note: this is the exact hand-off from the outer wrapper
        # into the Deep Agents app layer.
        frontend_url=args.frontend_url,
        model=args.model,
        task=task,
        base_hints=base_hints,
        step_limit=args.step_limit,
        workspace_dir=workspace_dir,
        app_variant=args.app_variant,
        task_index=args.index,
        task_source=task_source_label(
            dataset_name=args.dataset,
            split=args.split,
            csv_path=args.csv_path,
            json_path=args.json_path,
        ),
    )
    prompt = workflow["prompt"]
    decomposition_plan = workflow["decomposition_plan"]
    (run_dir / "plan.json").write_text(
        json.dumps(decomposition_plan, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )

    step_results = workflow["step_results"]
    (run_dir / "step_results.json").write_text(
        json.dumps(step_results, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )

    result = workflow["result"]
    (run_dir / "final_summary.txt").write_text(result["response_text"], encoding="utf-8")

    workspace_artifacts = collect_workspace_artifacts(run_dir, workspace_dir)

    payload = {
        "run_started_at": run_started_at.isoformat(),
        "frontend_url": args.frontend_url,
        "model": args.model,
        "hint_json": workflow["resolved_hints"],
        "task": task,
        "active_harness": "agentbench.deepagents_app",
        "app_variant": workflow["app_variant"],
        "deepagents_runtime_source": workflow["deepagents_runtime_source"],
        "checkpoint_log_file": str(checkpoint_log_path),
        "auto_repo_checkout": auto_repo_checkout,
        "workspace": workspace_metadata,
        "workspace_artifacts": workspace_artifacts,
        "prompt": prompt,
        "decomposition_plan": decomposition_plan,
        "step_results": step_results,
        "result": result,
    }
    save_result(run_dir, payload)
    set_checkpoint_log_file(None)

    print(f"AgentBench run complete: {safe_instance}")
    print(f"Run directory: {run_dir}")
    print(f"Result file: {run_dir / 'result.json'}")


if __name__ == "__main__":
    main()
