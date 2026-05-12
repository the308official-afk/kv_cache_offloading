#!/usr/bin/env python3

"""Run one SWE-bench Pro task through Deep Agents against a local Dynamo frontend."""

from __future__ import annotations

import argparse
import json
import os
import re
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
FRONTEND_CONTAINER_NAME = "dynamo-frontend"
WORKER_CONTAINER_NAME = "dynamo-sglang-worker"
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
FRONTEND_SELECTION_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T[0-9:.]+Z).*Selected worker: "
    r"worker_id=(?P<worker_id>\d+) dp_rank=(?P<dp_rank>\d+), "
    r"logit: (?P<logit>-?\d+(?:\.\d+)?), cached blocks: (?P<cached_blocks>\d+), "
    r"tree size: (?P<tree_size>\d+), total blocks: (?P<total_blocks>\d+)"
)
WORKER_PREFILL_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T[0-9:.]+Z).*Prefill batch, "
    r"#new-seq: (?P<new_seq>\d+), #new-token: (?P<new_token>\d+), "
    r"#cached-token: (?P<cached_token>\d+), token usage: (?P<token_usage>\d+(?:\.\d+)?), "
    r"#running-req: (?P<running_req>\d+), #queue-req: (?P<queue_req>\d+), "
    r"input throughput \(token/s\): (?P<input_throughput>\d+(?:\.\d+)?), "
    r"cuda graph: (?P<cuda_graph>True|False)"
)
WORKER_DECODE_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T[0-9:.]+Z).*Decode batch, "
    r"#running-req: (?P<running_req>\d+), #token: (?P<token>\d+), "
    r"token usage: (?P<token_usage>\d+(?:\.\d+)?), cuda graph: (?P<cuda_graph>True|False), "
    r"gen throughput \(token/s\): (?P<gen_throughput>\d+(?:\.\d+)?), #queue-req: (?P<queue_req>\d+)"
)


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


def _strip_ansi(value: str) -> str:
    return ANSI_ESCAPE_RE.sub("", value)


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_float(value: object) -> float | None:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _format_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _diff_ms(start: str | None, end: str | None) -> float | None:
    start_dt = _parse_iso_timestamp(start)
    end_dt = _parse_iso_timestamp(end)
    if start_dt is None or end_dt is None:
        return None
    return round((end_dt - start_dt).total_seconds() * 1000.0, 3)


def parse_frontend_scheduler_events(log_path: str | None) -> list[dict]:
    if not log_path:
        return []
    path = Path(log_path)
    if not path.exists():
        return []

    events: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = _strip_ansi(raw_line)
        match = FRONTEND_SELECTION_RE.search(line)
        if not match:
            continue
        events.append(
            {
                "timestamp": match.group("timestamp"),
                "worker_id": match.group("worker_id"),
                "dp_rank": _format_int(match.group("dp_rank")),
                "logit": _format_float(match.group("logit")),
                "cached_blocks": _format_int(match.group("cached_blocks")),
                "tree_size": _format_int(match.group("tree_size")),
                "total_blocks": _format_int(match.group("total_blocks")),
            }
        )
    return events


def _finalize_worker_request_observation(observation: dict) -> dict:
    decode_events = observation.pop("decode_events", [])
    if decode_events:
        observation["first_decode_timestamp"] = decode_events[0]["timestamp"]
        observation["last_decode_timestamp"] = decode_events[-1]["timestamp"]
        observation["decode_event_count"] = len(decode_events)
        observation["max_decode_tokens"] = max(item["token"] for item in decode_events)
        observation["max_decode_queue_req"] = max(item["queue_req"] for item in decode_events)
        observation["max_gen_throughput_tps"] = max(item["gen_throughput_tps"] for item in decode_events)
        observation["decode_cuda_graph_seen"] = any(item["cuda_graph"] for item in decode_events)
    else:
        observation["first_decode_timestamp"] = None
        observation["last_decode_timestamp"] = None
        observation["decode_event_count"] = 0
        observation["max_decode_tokens"] = None
        observation["max_decode_queue_req"] = None
        observation["max_gen_throughput_tps"] = None
        observation["decode_cuda_graph_seen"] = False
    return observation


def parse_worker_request_observations(log_path: str | None) -> list[dict]:
    if not log_path:
        return []
    path = Path(log_path)
    if not path.exists():
        return []

    observations: list[dict] = []
    current: dict | None = None
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = _strip_ansi(raw_line)
        prefill_match = WORKER_PREFILL_RE.search(line)
        if prefill_match:
            if current is not None:
                observations.append(_finalize_worker_request_observation(current))
            current = {
                "prefill_timestamp": prefill_match.group("timestamp"),
                "new_seq_count": _format_int(prefill_match.group("new_seq")),
                "new_token_count": _format_int(prefill_match.group("new_token")),
                "cached_token_count": _format_int(prefill_match.group("cached_token")),
                "prefill_token_usage": _format_float(prefill_match.group("token_usage")),
                "prefill_running_req": _format_int(prefill_match.group("running_req")),
                "prefill_queue_req": _format_int(prefill_match.group("queue_req")),
                "input_throughput_tps": _format_float(prefill_match.group("input_throughput")),
                "prefill_cuda_graph": prefill_match.group("cuda_graph") == "True",
                "decode_events": [],
            }
            continue

        decode_match = WORKER_DECODE_RE.search(line)
        if decode_match and current is not None:
            current["decode_events"].append(
                {
                    "timestamp": decode_match.group("timestamp"),
                    "running_req": _format_int(decode_match.group("running_req")),
                    "token": _format_int(decode_match.group("token")),
                    "token_usage": _format_float(decode_match.group("token_usage")),
                    "cuda_graph": decode_match.group("cuda_graph") == "True",
                    "gen_throughput_tps": _format_float(decode_match.group("gen_throughput")),
                    "queue_req": _format_int(decode_match.group("queue_req")),
                }
            )

    if current is not None:
        observations.append(_finalize_worker_request_observation(current))
    return observations


def build_runtime_events(
    measurements: list[dict],
    *,
    frontend_scheduler_events: list[dict] | None = None,
    worker_request_observations: list[dict] | None = None,
) -> list[dict]:
    events = []
    frontend_scheduler_events = frontend_scheduler_events or []
    worker_request_observations = worker_request_observations or []

    for index, item in enumerate(measurements):
        request_context = item.get("request_context") or {}
        cached_token_count = item.get("cached_input_tokens")
        if cached_token_count is None:
            cached_token_count = item.get("cached_prompt_tokens")
        cache_hit = cached_token_count is not None and cached_token_count > 0
        input_tokens = item.get("input_tokens")
        recomputed_prefix_tokens = None
        if isinstance(input_tokens, int) and isinstance(cached_token_count, int):
            recomputed_prefix_tokens = max(input_tokens - cached_token_count, 0)

        frontend_event = frontend_scheduler_events[index] if index < len(frontend_scheduler_events) else None
        worker_observation = (
            worker_request_observations[index] if index < len(worker_request_observations) else None
        )
        timestamp = None
        worker_id = None
        router_mode = None
        scheduler = None
        worker_metrics = None
        source = "agentbench_response_proxy"
        ttft_ms = None
        decode_ms = None

        if frontend_event is not None:
            timestamp = frontend_event.get("timestamp")
            worker_id = frontend_event.get("worker_id")
            router_mode = "kv_router_scheduler"
            scheduler = {
                "dp_rank": frontend_event.get("dp_rank"),
                "logit": frontend_event.get("logit"),
                "cached_blocks": frontend_event.get("cached_blocks"),
                "tree_size": frontend_event.get("tree_size"),
                "total_blocks": frontend_event.get("total_blocks"),
            }
            source = "frontend_log_alignment"

        if worker_observation is not None:
            if timestamp is None:
                timestamp = worker_observation.get("prefill_timestamp")
            observed_cached = worker_observation.get("cached_token_count")
            if isinstance(observed_cached, int):
                cached_token_count = observed_cached
                cache_hit = observed_cached > 0
                if isinstance(input_tokens, int):
                    recomputed_prefix_tokens = max(input_tokens - observed_cached, 0)
            worker_metrics = {
                "prefill_timestamp": worker_observation.get("prefill_timestamp"),
                "first_decode_timestamp": worker_observation.get("first_decode_timestamp"),
                "last_decode_timestamp": worker_observation.get("last_decode_timestamp"),
                "new_seq_count": worker_observation.get("new_seq_count"),
                "new_token_count": worker_observation.get("new_token_count"),
                "prefill_token_usage": worker_observation.get("prefill_token_usage"),
                "prefill_running_req": worker_observation.get("prefill_running_req"),
                "prefill_queue_req": worker_observation.get("prefill_queue_req"),
                "input_throughput_tps": worker_observation.get("input_throughput_tps"),
                "prefill_cuda_graph": worker_observation.get("prefill_cuda_graph"),
                "decode_event_count": worker_observation.get("decode_event_count"),
                "max_decode_tokens": worker_observation.get("max_decode_tokens"),
                "max_decode_queue_req": worker_observation.get("max_decode_queue_req"),
                "max_gen_throughput_tps": worker_observation.get("max_gen_throughput_tps"),
                "decode_cuda_graph_seen": worker_observation.get("decode_cuda_graph_seen"),
            }
            ttft_ms = _diff_ms(timestamp or worker_observation.get("prefill_timestamp"), worker_observation.get("first_decode_timestamp"))
            decode_ms = _diff_ms(
                worker_observation.get("first_decode_timestamp"),
                worker_observation.get("last_decode_timestamp"),
            )
            source = "frontend_worker_log_alignment" if frontend_event is not None else "worker_log_alignment"

        events.append(
            {
                "timestamp": timestamp,
                "request_id": request_context.get("request_id"),
                "parent_run_id": request_context.get("parent_run_id"),
                "task_instance_id": request_context.get("task_instance_id"),
                "phase": item.get("phase"),
                "step_index": item.get("step_index"),
                "step_title": item.get("step_title"),
                "worker_id": worker_id,
                "worker_host": None,
                "model_name": item.get("model_name_reported") or item.get("model"),
                "router_mode": router_mode,
                "request_hints": item.get("hints"),
                "cache": {
                    "cache_hit": cache_hit,
                    "cached_token_count": cached_token_count,
                    "reused_prefix_tokens": cached_token_count,
                    "recomputed_prefix_tokens": recomputed_prefix_tokens,
                },
                "placement": {
                    "actual_tier": None,
                    "stayed_on_gpu": None,
                    "moved_to_cpu": None,
                    "moved_to_nvme": None,
                    "fetched_from_cpu": None,
                    "fetched_from_nvme": None,
                    "recomputed_instead_of_fetch": None,
                },
                "eviction": {
                    "eviction_happened": None,
                    "evicted_block_count": None,
                    "evicted_token_estimate": None,
                    "eviction_reason": None,
                },
                "latency": {
                    "ttft_ms": ttft_ms,
                    "end_to_end_ms": item.get("latency_ms"),
                    "prefill_ms": None,
                    "decode_ms": decode_ms,
                    "fetch_ms": None,
                    "recompute_ms": None,
                },
                "scheduler": scheduler,
                "worker_metrics": worker_metrics,
                "alignment": {
                    "strategy": "sequential_log_order",
                    "sequence_index": index,
                    "frontend_event_found": frontend_event is not None,
                    "worker_observation_found": worker_observation is not None,
                },
                "source": source,
            }
        )
    return events


def write_runtime_events_jsonl(run_dir: Path, runtime_events: list[dict]) -> Path:
    output_path = run_dir / "runtime_events.jsonl"
    lines = [json.dumps(item, default=stringify_unknown) for item in runtime_events]
    output_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return output_path


def write_runtime_events_json(run_dir: Path, runtime_events: list[dict]) -> Path:
    output_path = run_dir / "runtime_events.json"
    output_path.write_text(
        json.dumps(runtime_events, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )
    return output_path


def collect_runtime_logs(run_dir: Path, *, since_iso: str) -> dict[str, object]:
    if shutil.which("docker") is None:
        return {
            "docker_available": False,
            "frontend_log_file": None,
            "worker_log_file": None,
        }

    results: dict[str, object] = {
        "docker_available": True,
        "frontend_log_file": None,
        "worker_log_file": None,
    }
    targets = [
        (FRONTEND_CONTAINER_NAME, "frontend_runtime.log", "frontend_log_file"),
        (WORKER_CONTAINER_NAME, "worker_runtime.log", "worker_log_file"),
    ]
    for container_name, filename, metadata_key in targets:
        completed = run_command(
            ["docker", "logs", "--since", since_iso, container_name],
            check=False,
        )
        output_path = run_dir / filename
        output_path.write_text(
            (completed.stdout or "") + (completed.stderr or ""),
            encoding="utf-8",
        )
        results[metadata_key] = str(output_path)
        results[f"{container_name}_exit_code"] = completed.returncode
    return results


def summarize_measurements(measurements: list[dict]) -> dict:
    total_latency_ms = 0.0
    phase_counts: dict[str, int] = {}
    phases_over_limit: list[dict[str, object]] = []
    for item in measurements:
        phase = str(item.get("phase") or "unknown")
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        latency_ms = float(item.get("latency_ms") or 0.0)
        total_latency_ms += latency_ms
        prompt_tokens = item.get("prompt_tokens")
        if isinstance(prompt_tokens, int) and prompt_tokens >= 3500:
            phases_over_limit.append(
                {
                    "phase": phase,
                    "step_index": item.get("step_index"),
                    "prompt_tokens": prompt_tokens,
                }
            )

    return {
        "call_count": len(measurements),
        "phase_counts": phase_counts,
        "total_model_latency_ms": round(total_latency_ms, 3),
        "large_prompt_calls": phases_over_limit,
    }


def _classify_prefill_decode(item: dict) -> str:
    input_tokens = item.get("input_tokens")
    output_tokens = item.get("output_tokens")
    if isinstance(input_tokens, int) and isinstance(output_tokens, int):
        if input_tokens >= max(2 * output_tokens, 2000):
            return "prefill-heavy"
        if output_tokens >= max(2 * input_tokens, 1000):
            return "decode-heavy"
        return "mixed"
    prompt_chars = item.get("prompt_chars")
    if isinstance(prompt_chars, int) and prompt_chars >= 8000:
        return "likely prefill-heavy"
    return "unknown"


def _classify_reuse(item: dict) -> str:
    cached_input_tokens = item.get("cached_input_tokens")
    cached_prompt_tokens = item.get("cached_prompt_tokens")
    cached = 0
    if isinstance(cached_input_tokens, int):
        cached = max(cached, cached_input_tokens)
    if isinstance(cached_prompt_tokens, int):
        cached = max(cached, cached_prompt_tokens)
    if cached > 0:
        return f"yes ({cached} cached tokens)"
    if cached_input_tokens is None and cached_prompt_tokens is None:
        return "unknown"
    return "no"


def _classify_pressure(item: dict) -> str:
    input_tokens = item.get("input_tokens")
    prompt_tokens = item.get("prompt_tokens")
    prompt_chars = item.get("prompt_chars")
    finish_reason = item.get("finish_reason")
    max_prompt_tokens = None
    for value in (input_tokens, prompt_tokens):
        if isinstance(value, int):
            max_prompt_tokens = max(value, max_prompt_tokens or value)
    if isinstance(max_prompt_tokens, int):
        if max_prompt_tokens >= 12000:
            return "very high"
        if max_prompt_tokens >= 3500:
            return "high"
        if max_prompt_tokens >= 1500:
            return "moderate"
    if isinstance(prompt_chars, int):
        if prompt_chars >= 50000:
            return "very high"
        if prompt_chars >= 10000:
            return "high"
        if prompt_chars >= 5000:
            return "moderate"
    if finish_reason == "length":
        return "high"
    return "low"


def build_measurement_analysis(measurements: list[dict]) -> dict:
    rows = []
    for item in measurements:
        rows.append(
            {
                "phase": item.get("phase"),
                "step_index": item.get("step_index"),
                "latency_ms": item.get("latency_ms"),
                "input_tokens": item.get("input_tokens"),
                "output_tokens": item.get("output_tokens"),
                "cached_input_tokens": item.get("cached_input_tokens"),
                "finish_reason": item.get("finish_reason"),
                "prefill_decode_profile": _classify_prefill_decode(item),
                "reuse_signal": _classify_reuse(item),
                "pressure_risk": _classify_pressure(item),
            }
        )

    most_prefill_heavy = None
    highest_input_tokens = -1
    highest_pressure = None
    pressure_rank = {"low": 0, "moderate": 1, "high": 2, "very high": 3}
    strongest_reuse = None
    strongest_cached = -1
    longest_call = None
    longest_latency = -1.0

    for item in measurements:
        phase = item.get("phase")
        input_tokens = item.get("input_tokens")
        if isinstance(input_tokens, int) and input_tokens > highest_input_tokens:
            highest_input_tokens = input_tokens
            most_prefill_heavy = phase

        risk = _classify_pressure(item)
        if highest_pressure is None or pressure_rank[risk] > pressure_rank[highest_pressure["risk"]]:
            highest_pressure = {"phase": phase, "risk": risk}

        cached = 0
        for key in ("cached_input_tokens", "cached_prompt_tokens"):
            value = item.get(key)
            if isinstance(value, int):
                cached = max(cached, value)
        if cached > strongest_cached:
            strongest_cached = cached
            strongest_reuse = phase if cached > 0 else strongest_reuse

        latency_ms = item.get("latency_ms")
        if isinstance(latency_ms, (int, float)) and latency_ms > longest_latency:
            longest_latency = float(latency_ms)
            longest_call = phase

    return {
        "summary": {
            "most_prefill_heavy_phase": most_prefill_heavy,
            "strongest_reuse_phase": strongest_reuse,
            "highest_pressure_phase": highest_pressure["phase"] if highest_pressure else None,
            "highest_pressure_risk": highest_pressure["risk"] if highest_pressure else None,
            "slowest_phase": longest_call,
            "slowest_phase_latency_ms": round(longest_latency, 3) if longest_latency >= 0 else None,
        },
        "rows": rows,
    }


def _normalized_ratio(numerator: float | int | None, denominator: float | int | None) -> float:
    if numerator is None or denominator in (None, 0):
        return 0.0
    return max(0.0, min(float(numerator) / float(denominator), 1.0))


def _phase_future_turn_likelihood(phase: str) -> float:
    if phase == "planning":
        return 0.45
    if phase == "synthesis":
        return 0.2
    if phase.startswith("step_"):
        return 0.75
    return 0.4


def _phase_recency_proxy(phase: str, step_index: int | None, total_steps: int) -> float:
    if phase == "planning":
        return 0.35
    if phase == "synthesis":
        return 0.3
    if phase.startswith("step_") and step_index is not None and total_steps > 0:
        return max(0.2, min(step_index / total_steps, 1.0))
    return 0.4


def _priority_score(hints: dict) -> float:
    priority = hints.get("priority")
    if isinstance(priority, (int, float)):
        return max(0.0, min(float(priority) / 10.0, 1.0))
    return 0.5


def _reuse_score(item: dict) -> float:
    hints = item.get("hints") or {}
    hint_reuse = hints.get("reuse_likelihood")
    if not isinstance(hint_reuse, (int, float)):
        hint_reuse = 0.5
    cached_input = item.get("cached_input_tokens")
    input_tokens = item.get("input_tokens")
    observed_reuse = _normalized_ratio(cached_input, input_tokens)
    return round((0.6 * float(hint_reuse)) + (0.4 * observed_reuse), 4)


def _latency_value_score(item: dict, max_latency_ms: float) -> float:
    latency_ms = item.get("latency_ms")
    if not isinstance(latency_ms, (int, float)) or max_latency_ms <= 0:
        return 0.0
    return round(max(0.0, min(float(latency_ms) / max_latency_ms, 1.0)), 4)


def _size_penalty_score(item: dict, max_prompt_tokens: int) -> float:
    prompt_tokens = item.get("prompt_tokens") or item.get("input_tokens")
    if not isinstance(prompt_tokens, int) or max_prompt_tokens <= 0:
        return 0.0
    return round(max(0.0, min(prompt_tokens / max_prompt_tokens, 1.0)), 4)


def build_cache_value_analysis(measurements: list[dict]) -> dict:
    max_latency_ms = max(
        (float(item.get("latency_ms")) for item in measurements if isinstance(item.get("latency_ms"), (int, float))),
        default=0.0,
    )
    max_prompt_tokens = max(
        (
            int(item.get("prompt_tokens") or item.get("input_tokens"))
            for item in measurements
            if isinstance(item.get("prompt_tokens") or item.get("input_tokens"), int)
        ),
        default=0,
    )
    total_steps = sum(1 for item in measurements if str(item.get("phase") or "").startswith("step_"))

    rows = []
    for item in measurements:
        phase = str(item.get("phase") or "unknown")
        step_index = item.get("step_index")
        hints = item.get("hints") or {}

        reuse = _reuse_score(item)
        priority = _priority_score(hints)
        recency = _phase_recency_proxy(phase, step_index if isinstance(step_index, int) else None, total_steps)
        future_turn = _phase_future_turn_likelihood(phase)
        latency_value = _latency_value_score(item, max_latency_ms)
        size_penalty = _size_penalty_score(item, max_prompt_tokens)

        value_score = round(
            (
                0.28 * reuse
                + 0.18 * priority
                + 0.12 * recency
                + 0.18 * future_turn
                + 0.18 * latency_value
                - 0.12 * size_penalty
            ),
            4,
        )

        keep_recommendation = "keep"
        if value_score < 0.35:
            keep_recommendation = "evict-first"
        elif value_score < 0.55:
            keep_recommendation = "spill-or-recompute"

        rows.append(
            {
                "phase": phase,
                "step_index": step_index,
                "reuse_score": reuse,
                "priority_score": round(priority, 4),
                "recency_score": round(recency, 4),
                "future_turn_score": round(future_turn, 4),
                "latency_value_score": latency_value,
                "size_penalty_score": size_penalty,
                "cache_value_score": value_score,
                "keep_recommendation": keep_recommendation,
            }
        )

    sorted_rows = sorted(rows, key=lambda row: row["cache_value_score"], reverse=True)
    return {
        "formula_notes": {
            "description": "Higher scores mean the cached context is more worth keeping in fast memory.",
            "weights": {
                "reuse_score": 0.28,
                "priority_score": 0.18,
                "recency_score": 0.12,
                "future_turn_score": 0.18,
                "latency_value_score": 0.18,
                "size_penalty_score": -0.12,
            },
        },
        "summary": {
            "highest_value_phase": sorted_rows[0]["phase"] if sorted_rows else None,
            "lowest_value_phase": sorted_rows[-1]["phase"] if sorted_rows else None,
            "keep_candidates": [row["phase"] for row in sorted_rows if row["keep_recommendation"] == "keep"],
            "evict_first_candidates": [row["phase"] for row in sorted_rows if row["keep_recommendation"] == "evict-first"],
        },
        "rows": sorted_rows,
    }


def render_cache_value_markdown(analysis: dict) -> str:
    summary = analysis["summary"]
    notes = analysis["formula_notes"]
    rows = analysis["rows"]
    lines = [
        "# Cache Value Analysis",
        "",
        "## Summary",
        f"- Highest-value phase: `{summary.get('highest_value_phase')}`",
        f"- Lowest-value phase: `{summary.get('lowest_value_phase')}`",
        f"- Keep candidates: `{', '.join(summary.get('keep_candidates') or [])}`",
        f"- Evict-first candidates: `{', '.join(summary.get('evict_first_candidates') or [])}`",
        "",
        "## Formula Notes",
        f"- {notes['description']}",
        "- Score inputs: reuse, priority, recency, future-turn likelihood, latency cost, and prompt-size penalty.",
        "",
        "## Phase Table",
        "",
        "| Phase | Step | Reuse | Priority | Recency | Future turn | Latency value | Size penalty | Cache value | Recommendation |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {phase} | {step} | {reuse:.4f} | {priority:.4f} | {recency:.4f} | {future_turn:.4f} | {latency:.4f} | {size:.4f} | {value:.4f} | {recommendation} |".format(
                phase=row["phase"],
                step=row["step_index"] if row["step_index"] is not None else "-",
                reuse=row["reuse_score"],
                priority=row["priority_score"],
                recency=row["recency_score"],
                future_turn=row["future_turn_score"],
                latency=row["latency_value_score"],
                size=row["size_penalty_score"],
                value=row["cache_value_score"],
                recommendation=row["keep_recommendation"],
            )
        )
    return "\n".join(lines) + "\n"


def build_kv_hierarchy_analysis(measurements: list[dict], cache_value_analysis: dict) -> dict:
    cache_rows = {
        (row["phase"], row["step_index"]): row
        for row in cache_value_analysis.get("rows", [])
    }
    rows = []
    for item in measurements:
        phase = item.get("phase")
        step_index = item.get("step_index")
        cache_row = cache_rows.get((phase, step_index), {})
        prompt_tokens = item.get("prompt_tokens") or item.get("input_tokens")
        pressure = _classify_pressure(item)
        cache_value_score = float(cache_row.get("cache_value_score", 0.0))
        reuse_score = float(cache_row.get("reuse_score", 0.0))

        recommended_tier = "drop"
        reason = "low estimated reuse value"
        if cache_value_score >= 0.62 and pressure in {"moderate", "high"}:
            recommended_tier = "gpu"
            reason = "high value and still worth preserving in fastest memory"
        elif cache_value_score >= 0.48:
            recommended_tier = "cpu"
            reason = "worth keeping, but cheaper off-GPU residency is acceptable"
        elif cache_value_score >= 0.35:
            recommended_tier = "nvme"
            reason = "lower-value context; preserve only in colder storage if needed"

        movement_priority = "low"
        if recommended_tier == "gpu" and pressure in {"high", "very high"}:
            movement_priority = "high"
        elif recommended_tier in {"cpu", "nvme"}:
            movement_priority = "medium"

        rows.append(
            {
                "phase": phase,
                "step_index": step_index,
                "prompt_tokens": prompt_tokens,
                "pressure_risk": pressure,
                "reuse_score": reuse_score,
                "cache_value_score": cache_value_score,
                "recommended_tier": recommended_tier,
                "movement_priority": movement_priority,
                "reason": reason,
            }
        )

    gpu_candidates = [row["phase"] for row in rows if row["recommended_tier"] == "gpu"]
    cpu_candidates = [row["phase"] for row in rows if row["recommended_tier"] == "cpu"]
    nvme_candidates = [row["phase"] for row in rows if row["recommended_tier"] == "nvme"]
    drop_candidates = [row["phase"] for row in rows if row["recommended_tier"] == "drop"]

    return {
        "summary": {
            "gpu_candidates": gpu_candidates,
            "cpu_candidates": cpu_candidates,
            "nvme_candidates": nvme_candidates,
            "drop_candidates": drop_candidates,
        },
        "rows": rows,
    }


def render_kv_hierarchy_markdown(analysis: dict) -> str:
    summary = analysis["summary"]
    rows = analysis["rows"]
    lines = [
        "# KV Hierarchy Analysis",
        "",
        "## Summary",
        f"- GPU candidates: `{', '.join(summary.get('gpu_candidates') or [])}`",
        f"- CPU candidates: `{', '.join(summary.get('cpu_candidates') or [])}`",
        f"- NVMe candidates: `{', '.join(summary.get('nvme_candidates') or [])}`",
        f"- Drop candidates: `{', '.join(summary.get('drop_candidates') or [])}`",
        "",
        "## Phase Table",
        "",
        "| Phase | Step | Prompt tokens | Pressure | Reuse | Cache value | Recommended tier | Movement priority | Reason |",
        "| --- | --- | ---: | --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {phase} | {step} | {prompt_tokens} | {pressure} | {reuse:.4f} | {value:.4f} | {tier} | {priority} | {reason} |".format(
                phase=row["phase"],
                step=row["step_index"] if row["step_index"] is not None else "-",
                prompt_tokens=row["prompt_tokens"] if row["prompt_tokens"] is not None else "-",
                pressure=row["pressure_risk"],
                reuse=row["reuse_score"],
                value=row["cache_value_score"],
                tier=row["recommended_tier"],
                priority=row["movement_priority"],
                reason=row["reason"],
            )
        )
    return "\n".join(lines) + "\n"


def _runtime_reuse_strength(runtime_event: dict) -> str:
    cache = runtime_event.get("cache") or {}
    cached = cache.get("cached_token_count")
    recomputed = cache.get("recomputed_prefix_tokens")
    if isinstance(cached, int) and isinstance(recomputed, int):
        total = cached + recomputed
        if total > 0:
            ratio = cached / total
            if ratio >= 0.9:
                return "very strong"
            if ratio >= 0.7:
                return "strong"
            if ratio >= 0.4:
                return "moderate"
            return "weak"
    if isinstance(cached, int) and cached > 0:
        return "present"
    return "unknown"


def _runtime_alignment_status(recommended_tier: str | None, runtime_event: dict) -> str:
    actual_tier = (runtime_event.get("placement") or {}).get("actual_tier")
    if actual_tier:
        return "direct-match" if actual_tier == recommended_tier else "direct-mismatch"

    scheduler = runtime_event.get("scheduler") or {}
    cache = runtime_event.get("cache") or {}
    cached_blocks = scheduler.get("cached_blocks")
    cached_tokens = cache.get("cached_token_count")
    reuse_strength = _runtime_reuse_strength(runtime_event)

    if recommended_tier == "gpu":
        if isinstance(cached_blocks, int) and cached_blocks > 0 and reuse_strength in {"strong", "very strong"}:
            return "indirect-support"
        if reuse_strength in {"strong", "very strong"}:
            return "partial-support"
        return "insufficient-runtime-evidence"

    if recommended_tier in {"cpu", "nvme", "drop"}:
        if actual_tier is None and (cached_blocks is not None or cached_tokens is not None):
            return "not-directly-verifiable"
    return "insufficient-runtime-evidence"


def build_runtime_alignment_analysis(
    runtime_events: list[dict],
    cache_value_analysis: dict,
    kv_hierarchy_analysis: dict,
) -> dict:
    cache_rows = {
        (row.get("phase"), row.get("step_index")): row
        for row in cache_value_analysis.get("rows", [])
    }
    hierarchy_rows = {
        (row.get("phase"), row.get("step_index")): row
        for row in kv_hierarchy_analysis.get("rows", [])
    }

    rows = []
    direct_tier_verification_available = False
    indirect_support_count = 0
    aligned_runtime_events = 0
    observed_workers: set[str] = set()
    unverifiable_count = 0

    for event in runtime_events:
        phase = event.get("phase")
        step_index = event.get("step_index")
        key = (phase, step_index)
        cache_row = cache_rows.get(key, {})
        hierarchy_row = hierarchy_rows.get(key, {})
        scheduler = event.get("scheduler") or {}
        worker_metrics = event.get("worker_metrics") or {}
        placement = event.get("placement") or {}
        recommended_tier = hierarchy_row.get("recommended_tier")
        alignment_status = _runtime_alignment_status(recommended_tier, event)
        reuse_strength = _runtime_reuse_strength(event)
        has_frontend = bool((event.get("alignment") or {}).get("frontend_event_found"))
        has_worker = bool((event.get("alignment") or {}).get("worker_observation_found"))

        if placement.get("actual_tier") is not None:
            direct_tier_verification_available = True
        if alignment_status == "indirect-support":
            indirect_support_count += 1
        if alignment_status in {"not-directly-verifiable", "insufficient-runtime-evidence"}:
            unverifiable_count += 1
        if has_frontend and has_worker:
            aligned_runtime_events += 1
        if event.get("worker_id"):
            observed_workers.add(str(event["worker_id"]))

        rows.append(
            {
                "phase": phase,
                "step_index": step_index,
                "step_title": event.get("step_title"),
                "recommended_tier": recommended_tier,
                "keep_recommendation": cache_row.get("keep_recommendation"),
                "cache_value_score": cache_row.get("cache_value_score"),
                "worker_id": event.get("worker_id"),
                "router_mode": event.get("router_mode"),
                "scheduler_cached_blocks": scheduler.get("cached_blocks"),
                "scheduler_tree_size": scheduler.get("tree_size"),
                "cached_token_count": (event.get("cache") or {}).get("cached_token_count"),
                "recomputed_prefix_tokens": (event.get("cache") or {}).get("recomputed_prefix_tokens"),
                "ttft_ms": (event.get("latency") or {}).get("ttft_ms"),
                "decode_ms": (event.get("latency") or {}).get("decode_ms"),
                "max_gen_throughput_tps": worker_metrics.get("max_gen_throughput_tps"),
                "runtime_reuse_strength": reuse_strength,
                "alignment_status": alignment_status,
                "runtime_signal_source": event.get("source"),
                "frontend_event_found": has_frontend,
                "worker_observation_found": has_worker,
            }
        )

    return {
        "summary": {
            "direct_tier_verification_available": direct_tier_verification_available,
            "observed_worker_count": len(observed_workers),
            "observed_workers": sorted(observed_workers),
            "fully_aligned_runtime_events": aligned_runtime_events,
            "indirect_support_count": indirect_support_count,
            "unverifiable_row_count": unverifiable_count,
            "best_supported_gpu_candidate": next(
                (
                    row["phase"]
                    for row in rows
                    if row.get("recommended_tier") == "gpu"
                    and row.get("alignment_status") in {"indirect-support", "partial-support"}
                ),
                None,
            ),
        },
        "rows": rows,
    }


def render_runtime_alignment_markdown(analysis: dict) -> str:
    summary = analysis["summary"]
    rows = analysis["rows"]
    lines = [
        "# Runtime Alignment Analysis",
        "",
        "## Summary",
        f"- Direct tier verification available: `{summary.get('direct_tier_verification_available')}`",
        f"- Observed worker count: `{summary.get('observed_worker_count')}`",
        f"- Observed workers: `{', '.join(summary.get('observed_workers') or [])}`",
        f"- Fully aligned runtime events: `{summary.get('fully_aligned_runtime_events')}`",
        f"- Indirect-support rows: `{summary.get('indirect_support_count')}`",
        f"- Unverifiable rows: `{summary.get('unverifiable_row_count')}`",
        f"- Best-supported GPU candidate: `{summary.get('best_supported_gpu_candidate')}`",
        "",
        "## Notes",
        "- This report compares AgentBench recommendations with runtime-side scheduler and worker log signals.",
        "- It does not claim true placement verification unless `actual_tier` is emitted by the runtime.",
        "",
        "## Phase Table",
        "",
        "| Phase | Step | Recommended tier | Keep recommendation | Cache value | Worker | Cached blocks | Tree size | Cached tokens | Recomputed tokens | TTFT (ms) | Decode (ms) | Reuse strength | Alignment status | Source |",
        "| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in rows:
        value_display = (
            f"{row.get('cache_value_score'):.4f}"
            if isinstance(row.get("cache_value_score"), (int, float))
            else "-"
        )
        lines.append(
            "| {phase} | {step} | {tier} | {keep} | {value} | {worker} | {blocks} | {tree} | {cached} | {recomputed} | {ttft} | {decode} | {reuse} | {status} | {source} |".format(
                phase=row.get("phase"),
                step=row.get("step_index") if row.get("step_index") is not None else "-",
                tier=row.get("recommended_tier") or "-",
                keep=row.get("keep_recommendation") or "-",
                value=value_display,
                worker=row.get("worker_id") or "-",
                blocks=row.get("scheduler_cached_blocks") if row.get("scheduler_cached_blocks") is not None else "-",
                tree=row.get("scheduler_tree_size") if row.get("scheduler_tree_size") is not None else "-",
                cached=row.get("cached_token_count") if row.get("cached_token_count") is not None else "-",
                recomputed=row.get("recomputed_prefix_tokens") if row.get("recomputed_prefix_tokens") is not None else "-",
                ttft=row.get("ttft_ms") if row.get("ttft_ms") is not None else "-",
                decode=row.get("decode_ms") if row.get("decode_ms") is not None else "-",
                reuse=row.get("runtime_reuse_strength") or "-",
                status=row.get("alignment_status") or "-",
                source=row.get("runtime_signal_source") or "-",
            )
        )
    return "\n".join(lines) + "\n"


def render_measurement_analysis_markdown(analysis: dict) -> str:
    summary = analysis["summary"]
    rows = analysis["rows"]
    lines = [
        "# Measurement Analysis",
        "",
        "## Summary",
        f"- Most prefill-heavy phase: `{summary.get('most_prefill_heavy_phase')}`",
        f"- Strongest reuse phase: `{summary.get('strongest_reuse_phase')}`",
        f"- Highest pressure phase: `{summary.get('highest_pressure_phase')}` (`{summary.get('highest_pressure_risk')}`)",
        f"- Slowest phase: `{summary.get('slowest_phase')}` (`{summary.get('slowest_phase_latency_ms')} ms`)",
        "",
        "## Phase Table",
        "",
        "| Phase | Step | Latency (ms) | Input tokens | Output tokens | Cached input | Finish | Profile | Reuse | Pressure |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {phase} | {step} | {latency} | {input_tokens} | {output_tokens} | {cached_input_tokens} | {finish_reason} | {profile} | {reuse} | {pressure} |".format(
                phase=row.get("phase"),
                step=row.get("step_index") if row.get("step_index") is not None else "-",
                latency=row.get("latency_ms"),
                input_tokens=row.get("input_tokens") if row.get("input_tokens") is not None else "-",
                output_tokens=row.get("output_tokens") if row.get("output_tokens") is not None else "-",
                cached_input_tokens=row.get("cached_input_tokens") if row.get("cached_input_tokens") is not None else "-",
                finish_reason=row.get("finish_reason") or "-",
                profile=row.get("prefill_decode_profile"),
                reuse=row.get("reuse_signal"),
                pressure=row.get("pressure_risk"),
            )
        )
    return "\n".join(lines) + "\n"


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
    parent_run_id = f"{safe_instance}_{run_id}"
    run_dir = RESULTS_DIR / parent_run_id
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
            "parent_run_id": parent_run_id,
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
        parent_run_id=parent_run_id,
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
    measurements = workflow["measurements"]
    (run_dir / "measurements.json").write_text(
        json.dumps(measurements, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )
    measurement_analysis = build_measurement_analysis(measurements)
    (run_dir / "measurement_analysis.json").write_text(
        json.dumps(measurement_analysis, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )
    (run_dir / "measurement_analysis.md").write_text(
        render_measurement_analysis_markdown(measurement_analysis),
        encoding="utf-8",
    )
    cache_value_analysis = build_cache_value_analysis(measurements)
    (run_dir / "cache_value_analysis.json").write_text(
        json.dumps(cache_value_analysis, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )
    (run_dir / "cache_value_analysis.md").write_text(
        render_cache_value_markdown(cache_value_analysis),
        encoding="utf-8",
    )
    kv_hierarchy_analysis = build_kv_hierarchy_analysis(measurements, cache_value_analysis)
    (run_dir / "kv_hierarchy_analysis.json").write_text(
        json.dumps(kv_hierarchy_analysis, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )
    (run_dir / "kv_hierarchy_analysis.md").write_text(
        render_kv_hierarchy_markdown(kv_hierarchy_analysis),
        encoding="utf-8",
    )
    runtime_log_artifacts = collect_runtime_logs(run_dir, since_iso=run_started_at.isoformat())
    frontend_scheduler_events = parse_frontend_scheduler_events(
        runtime_log_artifacts.get("frontend_log_file")
        if isinstance(runtime_log_artifacts.get("frontend_log_file"), str)
        else None
    )
    worker_request_observations = parse_worker_request_observations(
        runtime_log_artifacts.get("worker_log_file")
        if isinstance(runtime_log_artifacts.get("worker_log_file"), str)
        else None
    )
    runtime_events = build_runtime_events(
        measurements,
        frontend_scheduler_events=frontend_scheduler_events,
        worker_request_observations=worker_request_observations,
    )
    runtime_events_file = write_runtime_events_jsonl(run_dir, runtime_events)
    runtime_events_pretty_file = write_runtime_events_json(run_dir, runtime_events)
    runtime_alignment_analysis = build_runtime_alignment_analysis(
        runtime_events,
        cache_value_analysis,
        kv_hierarchy_analysis,
    )
    (run_dir / "runtime_alignment_analysis.json").write_text(
        json.dumps(runtime_alignment_analysis, indent=2, default=stringify_unknown),
        encoding="utf-8",
    )
    (run_dir / "runtime_alignment_analysis.md").write_text(
        render_runtime_alignment_markdown(runtime_alignment_analysis),
        encoding="utf-8",
    )

    result = workflow["result"]
    (run_dir / "final_summary.txt").write_text(result["response_text"], encoding="utf-8")

    workspace_artifacts = collect_workspace_artifacts(run_dir, workspace_dir)

    payload = {
        "run_started_at": run_started_at.isoformat(),
        "parent_run_id": parent_run_id,
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
        "measurements_file": str(run_dir / "measurements.json"),
        "measurements_summary": summarize_measurements(measurements),
        "measurement_analysis_file": str(run_dir / "measurement_analysis.json"),
        "measurement_analysis_markdown_file": str(run_dir / "measurement_analysis.md"),
        "measurement_analysis": measurement_analysis,
        "runtime_events_file": str(runtime_events_file),
        "runtime_events_pretty_file": str(runtime_events_pretty_file),
        "runtime_events": runtime_events,
        "runtime_log_artifacts": runtime_log_artifacts,
        "runtime_alignment_analysis_file": str(run_dir / "runtime_alignment_analysis.json"),
        "runtime_alignment_analysis_markdown_file": str(run_dir / "runtime_alignment_analysis.md"),
        "runtime_alignment_analysis": runtime_alignment_analysis,
        "cache_value_analysis_file": str(run_dir / "cache_value_analysis.json"),
        "cache_value_analysis_markdown_file": str(run_dir / "cache_value_analysis.md"),
        "cache_value_analysis": cache_value_analysis,
        "kv_hierarchy_analysis_file": str(run_dir / "kv_hierarchy_analysis.json"),
        "kv_hierarchy_analysis_markdown_file": str(run_dir / "kv_hierarchy_analysis.md"),
        "kv_hierarchy_analysis": kv_hierarchy_analysis,
        "measurements": measurements,
        "result": result,
    }
    save_result(run_dir, payload)
    set_checkpoint_log_file(None)

    print(f"AgentBench run complete: {safe_instance}")
    print(f"Run directory: {run_dir}")
    print(f"Result file: {run_dir / 'result.json'}")


if __name__ == "__main__":
    main()
