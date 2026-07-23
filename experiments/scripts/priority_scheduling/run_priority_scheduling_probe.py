#!/usr/bin/env python3
"""Run a synthetic mixed-priority scheduling probe against an OpenAI-compatible endpoint."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_OUT_ROOT = REPO_ROOT / "experiments" / "reports" / "priority_scheduling"
DEFAULT_CACHE_EVENT_LOG = (
    REPO_ROOT
    / "experiments"
    / "raw"
    / "sglang_transfer_logs"
    / "latest_sglang_transfer_events.jsonl"
)
RUNTIME_JSON_PREFIX = "[RUNTIME_JSON]"
SGLANG_EVENT_PREFIX = "[SGLANG_TRANSFER_JSON] "
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

#
# Important: the synthetic priority-scheduling probe keeps nvext.agent_hints
# limited to the Dynamo-safe runtime-control field we actually want scheduled
# against: priority. Request identity and experiment metadata travel separately
# through request_context / agent_context / annotations.
#
DEFAULT_HINTS: dict[str, Any] = {}

NO_HINT_PROFILES = {"", "none", "off", "no-hints", "no_hints"}

ISOLATION_WORD_BANK = [
    "anchor", "apex", "arc", "aster", "atlas", "aurora", "axis", "blaze",
    "bloom", "cinder", "cobalt", "comet", "cosmos", "crystal", "delta",
    "ember", "falcon", "flare", "flux", "frost", "glacier", "harbor",
    "helios", "horizon", "ion", "jade", "keystone", "lagoon", "lattice",
    "lumen", "marble", "matrix", "meridian", "meteor", "nova", "onyx",
    "orbit", "photon", "pixel", "plasma", "prism", "pulse", "quartz",
    "quasar", "radar", "rift", "sable", "shadow", "signal", "solar",
    "spark", "spiral", "summit", "tangent", "tensor", "thunder", "topaz",
    "vector", "vertex", "violet", "wave", "zenith", "zircon",
]

REQUEST_COLUMNS = [
    "run_id",
    "request_id",
    "request_role",
    "hint_kind",
    "priority_class",
    "hint_profile",
    "request_source",
    "source_repo",
    "source_instance_id",
    "source_task_index",
    "arrival_index",
    "attached_rank",
    "completed_rank",
    "overtook_earlier_low_attached_count",
    "overtook_earlier_low_completed_count",
    "worker_queue_wait_ms",
    "client_latency_ms",
    "agent_hints_priority",
    "agent_hints_latency_sensitivity",
    "worker_agent_hints_priority",
    "worker_agent_hints_latency_sensitivity",
    "top_level_priority_sent",
    "worker_top_level_priority",
    "sglang_priority_hint_seen",
    "sglang_scheduler_priority_applied",
    "worker_runtime_matched",
    "planned_offset_ms",
    "client_send_timestamp_utc",
    "client_response_timestamp_utc",
    "status",
    "error",
    "input_len_words",
    "output_len_tokens",
    "prompt_hash",
    "top_level_priority_mode",
    "top_level_priority_attempted",
    "top_level_priority_value",
    "top_level_priority_fallback_used",
    "top_level_priority_unsupported",
    "worker_request_received_timestamp",
    "worker_request_attached_timestamp",
    "worker_request_completed_timestamp",
    "worker_service_ms",
    "worker_total_runtime_ms",
    "worker_prompt_tokens",
    "worker_cached_tokens",
    "sglang_priority_events",
]

READABLE_REQUEST_COLUMNS = [
    "request",
    "prio_class",
    "request_source",
    "source_instance_id",
    "source_task_index",
    "arrival",
    "attach",
    "complete",
    "attach_priority_gain",
    "completion_priority_gain",
    "beat_low_attach",
    "beat_low_complete",
    "queue_ms",
    "latency_ms",
    "hint_kind",
    "worker_hint_prio",
    "worker_latency_sensitivity",
    "sent_top_prio",
    "worker_top_prio",
    "sglang_prio",
    "runtime_match",
    "effect",
]

PROOF_REQUEST_COLUMNS = [
    "request",
    "prio_class",
    "arrival",
    "attach",
    "complete",
    "beat_low_attach",
    "beat_low_complete",
    "queue_ms",
    "latency_ms",
    "hint_kind",
    "worker_hint_prio",
    "worker_latency_sensitivity",
    "sent_top_prio",
    "worker_top_prio",
    "sglang_prio",
    "runtime_match",
    "effect",
]

SUMMARY_COLUMNS = [
    "run_id",
    "model",
    "mode",
    "request_source",
    "swebench_dataset",
    "swebench_split",
    "swebench_start_index",
    "trajectory_prompt_catalog",
    "trajectory_stages",
    "trajectory_start_task_index",
    "trajectory_prompt_prefix_mode",
    "low_n",
    "high_n",
    "input_words",
    "output_tokens",
    "arrival_gap_ms",
    "inter_gap_ms",
    "hint_kind",
    "top_prio_compat",
    "worker_hint_status",
    "worker_top_prio_status",
    "sglang_prio_status",
    "runtime_cov",
    "attach_cov",
    "complete_cov",
    "low_wait_ms",
    "high_wait_ms",
    "low_latency_ms",
    "high_latency_ms",
    "high_attach_leapfrogs",
    "high_complete_leapfrogs",
    "effect_status",
]


@dataclass(frozen=True)
class RequestSpec:
    request_role: str
    priority_class: str
    priority_value: int
    hint_profile: str
    arrival_index: int
    planned_offset_ms: int
    prompt: str
    request_source: str = "synthetic"
    source_repo: str = ""
    source_instance_id: str = ""
    source_task_index: str = ""


def now_run_id() -> str:
    return f"priority_scheduling_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frontend-url",
        default=f"http://127.0.0.1:{os.environ.get('DYNAMO_FRONTEND_PORT', '8000')}/v1/chat/completions",
    )
    parser.add_argument("--model", default=os.environ.get("MODEL_NAME", ""))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--cache-event-log", default=str(DEFAULT_CACHE_EVENT_LOG))
    parser.add_argument("--worker-runtime-log", default="")
    parser.add_argument("--postprocess-only", action="store_true")
    parser.add_argument(
        "--attribution-mode",
        default=os.environ.get("PRIORITY_SCHEDULING_ATTRIBUTION_MODE", "precise"),
        choices=("light", "precise"),
    )
    parser.add_argument("--low-priority-count", type=int, default=int(os.environ.get("LOW_PRIORITY_COUNT", "8")))
    parser.add_argument("--high-priority-count", type=int, default=int(os.environ.get("HIGH_PRIORITY_COUNT", "4")))
    parser.add_argument("--low-priority-value", type=int, default=int(os.environ.get("LOW_PRIORITY_VALUE", "1")))
    parser.add_argument("--high-priority-value", type=int, default=int(os.environ.get("HIGH_PRIORITY_VALUE", "10")))
    parser.add_argument(
        "--hint-kind",
        default=os.environ.get("PRIORITY_HINT_KIND", "priority"),
        choices=("priority", "latency_sensitivity"),
        help="Which nvext.agent_hints field marks the high-urgency requests.",
    )
    parser.add_argument(
        "--low-latency-sensitivity-value",
        type=float,
        default=float(os.environ.get("LOW_LATENCY_SENSITIVITY_VALUE", "0.2")),
    )
    parser.add_argument(
        "--high-latency-sensitivity-value",
        type=float,
        default=float(os.environ.get("HIGH_LATENCY_SENSITIVITY_VALUE", "1.0")),
    )
    parser.add_argument("--input-len-words", type=int, default=int(os.environ.get("PRIORITY_INPUT_LEN", "4000")))
    parser.add_argument("--output-len-tokens", type=int, default=int(os.environ.get("PRIORITY_OUTPUT_LEN", "128")))
    parser.add_argument("--arrival-gap-ms", type=int, default=int(os.environ.get("PRIORITY_ARRIVAL_GAP_MS", "200")))
    parser.add_argument(
        "--inter-request-gap-ms",
        type=int,
        default=int(os.environ.get("PRIORITY_INTER_REQUEST_GAP_MS", "20")),
    )
    parser.add_argument("--seed", type=int, default=int(os.environ.get("PRIORITY_PROBE_SEED", "42")))
    parser.add_argument(
        "--request-source",
        default=os.environ.get("PRIORITY_REQUEST_SOURCE", "synthetic"),
        choices=("synthetic", "swebench_dataset", "swebench_trajectory"),
        help="Prompt source for priority requests.",
    )
    parser.add_argument(
        "--swebench-dataset",
        default=os.environ.get("PRIORITY_SWEBENCH_DATASET", "ScaleAI/SWE-bench_Pro"),
        help="Hugging Face dataset name for swebench_dataset mode.",
    )
    parser.add_argument(
        "--swebench-split",
        default=os.environ.get("PRIORITY_SWEBENCH_SPLIT", "test"),
        help="Dataset split for swebench_dataset mode.",
    )
    parser.add_argument(
        "--swebench-start-index",
        type=int,
        default=int(os.environ.get("PRIORITY_SWEBENCH_START_INDEX", "0")),
        help="First dataset row used for the mixed-priority burst.",
    )
    parser.add_argument(
        "--swebench-allow-reuse",
        action="store_true",
        default=os.environ.get("PRIORITY_SWEBENCH_ALLOW_REUSE", "0").strip().lower()
        in {"1", "true", "yes"},
        help="Allow cycling SWE-bench rows if the split is smaller than the burst.",
    )
    parser.add_argument(
        "--trajectory-prompt-catalog",
        default=os.environ.get(
            "PRIORITY_TRAJECTORY_PROMPT_CATALOG",
            str(REPO_ROOT / "experiments" / "reports" / "latest_swebench_trajectory_prompt_catalog.csv"),
        ),
        help="Prompt catalog CSV built from Experiment 6 traces.",
    )
    parser.add_argument(
        "--trajectory-stages",
        default=os.environ.get("PRIORITY_TRAJECTORY_STAGES", "planning execution patch_generation review"),
        help="Whitespace-separated trajectory stages to use as priority request prompts.",
    )
    parser.add_argument(
        "--trajectory-start-task-index",
        type=int,
        default=int(os.environ.get("PRIORITY_TRAJECTORY_START_TASK_INDEX", "0")),
        help="First catalog task_index to use for trajectory prompts.",
    )
    parser.add_argument(
        "--trajectory-prompt-prefix-mode",
        choices=("none", "task_stage"),
        default=os.environ.get(
            "PRIORITY_TRAJECTORY_PROMPT_PREFIX_MODE",
            os.environ.get("PRIORITY_TRAJECTORY_REPLAY_HEADER_MODE", "task_stage"),
        ),
        help="Prefix trajectory prompts with a task/stage identifier so prompts diverge early.",
    )
    parser.add_argument(
        "--trajectory-allow-reuse",
        action="store_true",
        default=os.environ.get("PRIORITY_TRAJECTORY_ALLOW_REUSE", "0").strip().lower()
        in {"1", "true", "yes"},
        help="Allow cycling trajectory prompt rows if the catalog has too few rows.",
    )
    parser.add_argument(
        "--prompt-isolation-mode",
        default=os.environ.get("RETENTION_PROMPT_ISOLATION_MODE", "disjoint"),
        choices=("standard", "strict", "disjoint"),
        help=(
            "Prompt-isolation mode for synthetic priority prompts. "
            "'standard' keeps the older mostly-uniform repeated-word prompt. "
            "'strict' makes seeded runs diverge early while keeping token counts stable. "
            "'disjoint' makes seeded runs use clearly separated prompt families."
        ),
    )
    parser.add_argument("--request-timeout", type=float, default=float(os.environ.get("REQUEST_TIMEOUT", "600")))
    parser.add_argument(
        "--top-level-priority-mode",
        default=os.environ.get("PRIORITY_TOP_LEVEL_PRIORITY_MODE", "auto"),
        choices=("auto", "force", "disable"),
        help=(
            "How to handle top-level request priority. "
            "'auto' retries without top-level priority if the frontend rejects it, "
            "'force' always sends it, and 'disable' never sends it."
        ),
    )
    parser.add_argument(
        "--request-context-mode",
        default=os.environ.get("PRIORITY_REQUEST_CONTEXT_MODE", "auto"),
        choices=("auto", "force", "disable"),
        help=(
            "How to handle nvext.request_context. "
            "'auto' retries without it if the frontend rejects that field, "
            "'force' always sends it, and 'disable' never sends it."
        ),
    )
    parser.add_argument("--ignore-eos", action="store_true")
    args = parser.parse_args()

    if not args.model:
        parser.error("--model is required or MODEL_NAME must be set")
    if args.low_priority_count < 0 or args.high_priority_count < 0:
        parser.error("priority counts must be >= 0")
    if args.low_priority_count == 0 and args.high_priority_count == 0:
        parser.error("at least one request is required")
    if args.input_len_words <= 0 or args.output_len_tokens <= 0:
        parser.error("input/output lengths must be positive")
    if args.arrival_gap_ms < 0 or args.inter_request_gap_ms < 0:
        parser.error("timing gaps must be >= 0")
    return args


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def format_swebench_dataset_prompt(task: dict[str, Any]) -> str:
    try:
        prompts_module = importlib.import_module("agentbench.deepagents_app.src.prompts")
    except Exception as exc:  # noqa: BLE001 - keep the missing dependency message actionable.
        raise SystemExit(f"Could not import SWE-bench prompt formatter: {exc}") from exc
    return str(prompts_module.format_swebench_task_prompt(task))


def load_swebench_dataset_split(args: argparse.Namespace) -> Any:
    try:
        datasets_module = importlib.import_module("datasets")
    except Exception as exc:  # noqa: BLE001 - show the exact install fix.
        raise SystemExit(
            "PRIORITY_REQUEST_SOURCE=swebench_dataset requires the datasets package. "
            "Install it with: python3 -m pip install -r agentbench/requirements.txt"
        ) from exc
    return datasets_module.load_dataset(args.swebench_dataset, split=args.swebench_split)


def dataset_row_to_task(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception as exc:  # noqa: BLE001 - report malformed dataset rows clearly.
        raise SystemExit(f"Could not convert SWE-bench dataset row to dict: {exc}") from exc


def swebench_task_source_meta(task: dict[str, Any], *, dataset_index: int) -> dict[str, str]:
    return {
        "request_source": "swebench_dataset",
        "source_repo": str(task.get("repo", "")),
        "source_instance_id": str(task.get("instance_id", f"swebench_index_{dataset_index}")),
        "source_task_index": str(dataset_index),
    }


def parse_stage_filter(value: str) -> set[str]:
    return {item.strip() for item in value.split() if item.strip()}


def catalog_int(row: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(row.get(key, "") or default)
    except ValueError:
        return default


def read_trajectory_catalog(path_value: str) -> list[dict[str, str]]:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise SystemExit(
            f"SWE-bench trajectory prompt catalog not found: {path}\n"
            "Run Experiment 6 first so latest_swebench_trajectory_prompt_catalog.csv exists."
        )
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"SWE-bench trajectory prompt catalog is empty: {path}")
    return rows


def trajectory_prompt_text(row: dict[str, str]) -> str:
    raw_path = row.get("prompt_text_path") or ""
    if not raw_path:
        raise SystemExit(f"Trajectory catalog row is missing prompt_text_path: {row}")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        raise SystemExit(f"Trajectory prompt file not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def trajectory_prompt_prefix(row: dict[str, str], mode: str) -> str:
    if mode == "none":
        return ""
    if mode != "task_stage":
        raise SystemExit(f"Unsupported PRIORITY_TRAJECTORY_PROMPT_PREFIX_MODE: {mode}")
    task_index = catalog_int(row, "task_index", -1)
    stage = str(row.get("stage_name") or row.get("phase") or "unknown")
    instance_id = str(row.get("instance_id") or f"trajectory_task_{task_index}")
    repo = str(row.get("repo") or "unknown")
    prompt_hash = str(row.get("prompt_hash") or "")
    return (
        "[PRIORITY_TRAJECTORY_PROMPT="
        f"task_{task_index:04d}|stage={stage}|instance={instance_id}|repo={repo}|prompt_hash={prompt_hash}"
        "]\n\n"
    )


def trajectory_source_meta(row: dict[str, str]) -> dict[str, str]:
    task_index = catalog_int(row, "task_index", -1)
    stage_index = catalog_int(row, "stage_index", -1)
    stage = str(row.get("stage_name") or row.get("phase") or "unknown")
    instance_id = str(row.get("instance_id") or f"trajectory_task_{task_index}")
    return {
        "request_source": "swebench_trajectory",
        "source_repo": str(row.get("repo") or ""),
        "source_instance_id": f"{instance_id}::{stage}",
        "source_task_index": f"{task_index}:{stage_index}",
    }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_text() -> str:
    return utc_now().isoformat()


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def ms_between(start: datetime | None, end: datetime | None) -> int | str:
    if start is None or end is None:
        return ""
    return int(round((end - start).total_seconds() * 1000))


def round_ms(value: float | None) -> int | str:
    if value is None:
        return ""
    return int(round(value))


def maybe_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def maybe_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean_int(values: list[int]) -> int | str:
    if not values:
        return ""
    return int(round(sum(values) / len(values)))


def safe_int_str(value: Any) -> int | str:
    parsed = maybe_int(value)
    return parsed if parsed is not None else ""


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def clean_log_line(line: str) -> str:
    return ANSI_RE.sub("", line)


def parse_runtime_json_payload(line: str) -> tuple[dict[str, Any] | None, str | None]:
    if RUNTIME_JSON_PREFIX not in line:
        return None, None
    prefix, payload = line.split(RUNTIME_JSON_PREFIX, 1)
    payload = payload.strip()
    json_start = payload.find("{")
    if json_start >= 0:
        payload = payload[json_start:]
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None, None
    timestamp = None
    prefix = prefix.strip()
    if prefix:
        timestamp = prefix.split()[0]
    if isinstance(parsed, dict) and not parsed.get("timestamp") and timestamp:
        parsed["timestamp"] = timestamp
    return (parsed if isinstance(parsed, dict) else None), timestamp


def parse_sglang_event_line(line: str) -> dict[str, Any] | None:
    text = line.strip()
    if not text:
        return None
    if text.startswith(SGLANG_EVENT_PREFIX):
        text = text[len(SGLANG_EVENT_PREFIX) :]
    elif not text.startswith("{"):
        return None
    try:
        event = json.loads(text)
    except json.JSONDecodeError:
        return None
    return event if isinstance(event, dict) else None


def build_hint_payload(
    *,
    args: argparse.Namespace,
    run_id: str,
    request_role: str,
    priority_class: str,
    priority_value: int,
    arrival_index: int,
    output_len_tokens: int,
) -> dict[str, Any]:
    payload = dict(DEFAULT_HINTS)
    if args.hint_kind == "latency_sensitivity":
        payload["latency_sensitivity"] = (
            args.high_latency_sensitivity_value
            if priority_class == "high-priority"
            else args.low_latency_sensitivity_value
        )
    else:
        payload["priority"] = priority_value
    return payload


def request_context(
    *,
    run_id: str,
    request_role: str,
    arrival_index: int,
    priority_class: str,
    prompt_hash: str,
    request_source: str,
    source_repo: str,
    source_instance_id: str,
    source_task_index: str,
) -> dict[str, Any]:
    if request_source == "swebench_dataset":
        task_instance_id = source_instance_id or "swebench_dataset_priority_scheduling_probe"
        app_variant = "swebench_dataset_priority_scheduling_probe"
    else:
        task_instance_id = "synthetic_priority_scheduling_probe"
        app_variant = "synthetic_priority_scheduling_probe"
    return {
        "request_id": f"{run_id}::{request_role}",
        "parent_run_id": run_id,
        "task_instance_id": task_instance_id,
        "phase": "priority_scheduling_probe",
        "step_index": arrival_index,
        "step_title": request_role,
        "app_variant": app_variant,
        "priority_class": priority_class,
        "prompt_hash": prompt_hash,
        "request_source": request_source,
        "source_repo": source_repo,
        "source_instance_id": source_instance_id,
        "source_task_index": source_task_index,
    }


def build_agent_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_type_id": "synthetic_priority_scheduling_probe:v1",
        "session_id": str(context.get("parent_run_id") or "priority_scheduling_probe"),
        "trajectory_id": str(context.get("request_id") or ""),
        "parent_trajectory_id": str(context.get("parent_run_id") or ""),
    }


def build_annotations(context: dict[str, Any]) -> list[str]:
    annotations: list[str] = []
    for key in (
        "request_id",
        "parent_run_id",
        "task_instance_id",
        "phase",
        "step_index",
        "step_title",
        "app_variant",
        "priority_class",
        "prompt_hash",
        "request_source",
        "source_repo",
        "source_instance_id",
        "source_task_index",
    ):
        value = context.get(key)
        if value in (None, ""):
            continue
        annotations.append(f"{key}:{value}")
    return annotations


def top_level_priority_from_hints(hints: dict[str, Any] | None) -> int | None:
    if not hints:
        return None
    value = hints.get("priority")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def priority_unsupported(status: int, error: str) -> bool:
    if status != 400 or not error:
        return False
    normalized = error.lower()
    return "unsupported parameter" in normalized and "priority" in normalized


def request_context_unsupported(status: int, error: str) -> bool:
    if status != 400 or not error:
        return False
    normalized = error.lower()
    return "request_context" in normalized and "unknown field" in normalized


def request_succeeded(status: Any) -> bool:
    try:
        code = int(status)
    except (TypeError, ValueError):
        return False
    return 200 <= code < 300


def post_json(url: str, payload: dict[str, Any], *, timeout: float) -> tuple[int, dict[str, Any] | None, str]:
    encoded = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw), ""
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, None, body[:1000]
    except Exception as exc:  # noqa: BLE001
        return 0, None, str(exc)


def get_nested(mapping: dict[str, Any], paths: list[tuple[str, ...]]) -> Any:
    for path in paths:
        current: Any = mapping
        found = True
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                found = False
                break
        if found:
            return current
    return None


def usage_prompt_tokens(usage: dict[str, Any]) -> tuple[int | None, int | None]:
    prompt_tokens = maybe_int(
        get_nested(
            usage,
            [("prompt_tokens",), ("input_tokens",)],
        )
    )
    cached_tokens = maybe_int(
        get_nested(
            usage,
            [
                ("prompt_tokens_details", "cached_tokens"),
                ("prompt_token_details", "cached_tokens"),
                ("input_tokens_details", "cached_tokens"),
                ("cached_prompt_tokens",),
                ("cached_tokens",),
            ],
        )
    )
    return prompt_tokens, cached_tokens


def build_prompt_body(*, request_role: str, target_len: int, seed: int, isolation_mode: str) -> tuple[list[str], str]:
    family_key = f"{request_role}:{seed}:{target_len}:{isolation_mode}"
    family_id = short_hash(family_key)
    if isolation_mode == "standard":
        words = ["priority"] * target_len
        for idx in range(0, target_len, 256):
            words[idx] = f"marker{idx}"
        return words, f"standard:{family_id}"
    if isolation_mode == "disjoint":
        rng = random.Random(family_key)
        vocab = list(ISOLATION_WORD_BANK)
        rng.shuffle(vocab)
        prefix_len = min(64, target_len, len(vocab))
        prefix_words = [f"{word}{family_id[:4]}" for word in vocab[:prefix_len]]
        cycle_words = prefix_words or [f"prio{family_id[:4]}"]
        body_words: list[str] = []
        for idx in range(target_len):
            if idx < prefix_len:
                body_words.append(prefix_words[idx])
                continue
            cycle_idx = (idx - prefix_len) % len(cycle_words)
            body_words.append(cycle_words[cycle_idx])
        return body_words, f"disjoint:{family_id}"
    if isolation_mode != "strict":
        raise ValueError(f"Unknown prompt isolation mode: {isolation_mode}")

    rng = random.Random(family_key)
    vocab = list(ISOLATION_WORD_BANK)
    rng.shuffle(vocab)
    prefix_len = min(48, target_len, len(vocab))
    prefix_words = vocab[:prefix_len]
    cycle_words = vocab[prefix_len:] or vocab
    stride = rng.randrange(3, len(cycle_words), 2) if len(cycle_words) > 3 else 1
    offset = rng.randrange(len(cycle_words)) if cycle_words else 0
    body_words: list[str] = []
    for idx in range(target_len):
        if idx < prefix_len:
            body_words.append(prefix_words[idx])
            continue
        cycle_idx = (offset + (idx - prefix_len) * stride) % len(cycle_words)
        body_words.append(cycle_words[cycle_idx])
    return body_words, f"strict:{family_id}"


def make_prompt(*, request_role: str, target_len: int, seed: int, isolation_mode: str) -> str:
    words, family_id = build_prompt_body(
        request_role=request_role,
        target_len=target_len,
        seed=seed,
        isolation_mode=isolation_mode,
    )
    marker = short_hash(f"{request_role}:{seed}:{target_len}")
    header = (
        f"Priority scheduling probe request {request_role}. "
        f"Marker {marker}. "
        f"Prompt family {family_id}. "
        "Return a concise answer. "
        "The repeated words below create queueing pressure only. "
    )
    return header + " ".join(words)


def build_swebench_request_specs(args: argparse.Namespace) -> list[RequestSpec]:
    dataset = load_swebench_dataset_split(args)
    total_requests = args.low_priority_count + args.high_priority_count
    if len(dataset) == 0:
        raise SystemExit("SWE-bench dataset split is empty.")
    if total_requests > len(dataset) and not args.swebench_allow_reuse:
        raise SystemExit(
            "Not enough SWE-bench rows for this priority burst without reuse. "
            f"need={total_requests} available={len(dataset)}. "
            "Use smaller LOW_PRIORITY_COUNT/HIGH_PRIORITY_COUNT or set PRIORITY_SWEBENCH_ALLOW_REUSE=1."
        )

    start_index = args.swebench_start_index % len(dataset)

    def row_for(offset: int) -> tuple[int, dict[str, Any], str, dict[str, str]]:
        if not args.swebench_allow_reuse and offset >= len(dataset):
            raise SystemExit("Internal SWE-bench row selection overflow without reuse.")
        dataset_index = (start_index + offset) % len(dataset)
        task = dataset_row_to_task(dataset[dataset_index])
        prompt = format_swebench_dataset_prompt(task)
        meta = swebench_task_source_meta(task, dataset_index=dataset_index)
        return dataset_index, task, prompt, meta

    specs: list[RequestSpec] = []
    arrival_index = 0
    row_offset = 0
    for idx in range(args.low_priority_count):
        request_role = f"low_{idx:04d}"
        _dataset_index, _task, prompt, meta = row_for(row_offset)
        row_offset += 1
        specs.append(
            RequestSpec(
                request_role=request_role,
                priority_class="low-priority",
                priority_value=args.low_priority_value,
                hint_profile="low-priority",
                arrival_index=arrival_index,
                planned_offset_ms=idx * args.inter_request_gap_ms,
                prompt=prompt,
                **meta,
            )
        )
        arrival_index += 1

    high_start_ms = args.arrival_gap_ms
    for idx in range(args.high_priority_count):
        request_role = f"high_{idx:04d}"
        _dataset_index, _task, prompt, meta = row_for(row_offset)
        row_offset += 1
        specs.append(
            RequestSpec(
                request_role=request_role,
                priority_class="high-priority",
                priority_value=args.high_priority_value,
                hint_profile="high-priority",
                arrival_index=arrival_index,
                planned_offset_ms=high_start_ms + idx * args.inter_request_gap_ms,
                prompt=prompt,
                **meta,
            )
        )
        arrival_index += 1
    return specs


def build_trajectory_request_specs(args: argparse.Namespace) -> list[RequestSpec]:
    catalog_rows = read_trajectory_catalog(args.trajectory_prompt_catalog)
    stage_filter = parse_stage_filter(args.trajectory_stages)
    if not stage_filter:
        raise SystemExit("PRIORITY_TRAJECTORY_STAGES / --trajectory-stages must not be empty")

    prompt_rows = [
        row
        for row in catalog_rows
        if (
            (row.get("stage_name") in stage_filter or row.get("phase") in stage_filter)
            and catalog_int(row, "task_index", -1) >= args.trajectory_start_task_index
        )
    ]
    prompt_rows.sort(
        key=lambda row: (
            catalog_int(row, "task_index", -1),
            catalog_int(row, "stage_index", -1),
            str(row.get("stage_name") or row.get("phase") or ""),
        )
    )

    total_requests = args.low_priority_count + args.high_priority_count
    if len(prompt_rows) < total_requests and not args.trajectory_allow_reuse:
        raise SystemExit(
            "Not enough SWE-bench trajectory prompt rows for this priority burst without reuse. "
            f"need={total_requests} available={len(prompt_rows)}. "
            "Use smaller LOW_PRIORITY_COUNT/HIGH_PRIORITY_COUNT or set PRIORITY_TRAJECTORY_ALLOW_REUSE=1."
        )
    if not prompt_rows and total_requests > 0:
        raise SystemExit("No SWE-bench trajectory prompt rows matched PRIORITY_TRAJECTORY_STAGES.")

    def row_for(offset: int) -> tuple[str, dict[str, str]]:
        if not args.trajectory_allow_reuse and offset >= len(prompt_rows):
            raise SystemExit("Internal trajectory row selection overflow without reuse.")
        row = prompt_rows[offset % len(prompt_rows)]
        prompt = trajectory_prompt_prefix(row, args.trajectory_prompt_prefix_mode) + trajectory_prompt_text(row)
        return prompt, row

    specs: list[RequestSpec] = []
    arrival_index = 0
    row_offset = 0
    for idx in range(args.low_priority_count):
        request_role = f"low_{idx:04d}"
        prompt, row = row_for(row_offset)
        row_offset += 1
        specs.append(
            RequestSpec(
                request_role=request_role,
                priority_class="low-priority",
                priority_value=args.low_priority_value,
                hint_profile="low-priority",
                arrival_index=arrival_index,
                planned_offset_ms=idx * args.inter_request_gap_ms,
                prompt=prompt,
                **trajectory_source_meta(row),
            )
        )
        arrival_index += 1

    high_start_ms = args.arrival_gap_ms
    for idx in range(args.high_priority_count):
        request_role = f"high_{idx:04d}"
        prompt, row = row_for(row_offset)
        row_offset += 1
        specs.append(
            RequestSpec(
                request_role=request_role,
                priority_class="high-priority",
                priority_value=args.high_priority_value,
                hint_profile="high-priority",
                arrival_index=arrival_index,
                planned_offset_ms=high_start_ms + idx * args.inter_request_gap_ms,
                prompt=prompt,
                **trajectory_source_meta(row),
            )
        )
        arrival_index += 1
    return specs


def build_request_specs(args: argparse.Namespace) -> list[RequestSpec]:
    if args.request_source == "swebench_dataset":
        return build_swebench_request_specs(args)
    if args.request_source == "swebench_trajectory":
        return build_trajectory_request_specs(args)

    specs: list[RequestSpec] = []
    arrival_index = 0
    for idx in range(args.low_priority_count):
        request_role = f"low_{idx:04d}"
        specs.append(
            RequestSpec(
                request_role=request_role,
                priority_class="low-priority",
                priority_value=args.low_priority_value,
                hint_profile="low-priority",
                arrival_index=arrival_index,
                planned_offset_ms=idx * args.inter_request_gap_ms,
                prompt=make_prompt(
                    request_role=request_role,
                    target_len=args.input_len_words,
                    seed=args.seed + idx,
                    isolation_mode=args.prompt_isolation_mode,
                ),
            )
        )
        arrival_index += 1

    high_start_ms = args.arrival_gap_ms
    for idx in range(args.high_priority_count):
        request_role = f"high_{idx:04d}"
        specs.append(
            RequestSpec(
                request_role=request_role,
                priority_class="high-priority",
                priority_value=args.high_priority_value,
                hint_profile="high-priority",
                arrival_index=arrival_index,
                planned_offset_ms=high_start_ms + idx * args.inter_request_gap_ms,
                prompt=make_prompt(
                    request_role=request_role,
                    target_len=args.input_len_words,
                    seed=args.seed + 10_000 + idx,
                    isolation_mode=args.prompt_isolation_mode,
                ),
            )
        )
        arrival_index += 1
    return specs


def send_one_request(
    args: argparse.Namespace,
    run_id: str,
    run_start_monotonic: float,
    spec: RequestSpec,
) -> dict[str, Any]:
    target_monotonic = run_start_monotonic + (spec.planned_offset_ms / 1000.0)
    while True:
        now = time.perf_counter()
        remaining = target_monotonic - now
        if remaining <= 0:
            break
        time.sleep(min(remaining, 0.01))

    prompt_hash = short_hash(spec.prompt)
    hints = build_hint_payload(
        args=args,
        run_id=run_id,
        request_role=spec.request_role,
        priority_class=spec.priority_class,
        priority_value=spec.priority_value,
        arrival_index=spec.arrival_index,
        output_len_tokens=args.output_len_tokens,
    )
    context = request_context(
        run_id=run_id,
        request_role=spec.request_role,
        arrival_index=spec.arrival_index,
        priority_class=spec.priority_class,
        prompt_hash=prompt_hash,
        request_source=spec.request_source,
        source_repo=spec.source_repo,
        source_instance_id=spec.source_instance_id,
        source_task_index=spec.source_task_index,
    )
    base_nvext: dict[str, Any] = {
        "agent_context": build_agent_context(context),
        "annotations": build_annotations(context),
        "agent_hints": hints,
    }
    payload: dict[str, Any] = {
        "model": args.model,
        "messages": [{"role": "user", "content": spec.prompt}],
        "max_tokens": args.output_len_tokens,
        "temperature": 0,
        "nvext": dict(base_nvext),
    }
    should_attempt_request_context = args.request_context_mode != "disable"
    if args.ignore_eos:
        payload["ignore_eos"] = True

    priority = top_level_priority_from_hints(hints)
    latency_sensitivity = maybe_float(hints.get("latency_sensitivity"))
    should_attempt_top_level_priority = (
        priority is not None and args.top_level_priority_mode != "disable"
    )
    include_top_level_priority = should_attempt_top_level_priority
    include_request_context = should_attempt_request_context
    fallback_used = False
    top_level_priority_unsupported = False
    request_context_fallback_used = False
    send_started = utc_now()
    send_finished = send_started
    latency_ms = 0.0
    status = 0
    response_json = None
    error = ""

    while True:
        payload["nvext"] = dict(base_nvext)
        if include_request_context:
            payload["nvext"]["request_context"] = context
        else:
            payload["nvext"].pop("request_context", None)
        if include_top_level_priority and priority is not None:
            payload["priority"] = priority
        else:
            payload.pop("priority", None)

        send_started = utc_now()
        start = time.perf_counter()
        status, response_json, error = post_json(args.frontend_url, payload, timeout=args.request_timeout)
        latency_ms = (time.perf_counter() - start) * 1000
        send_finished = utc_now()
        if (
            include_top_level_priority
            and args.top_level_priority_mode == "auto"
            and priority_unsupported(status, error)
        ):
            include_top_level_priority = False
            fallback_used = True
            top_level_priority_unsupported = True
            continue
        if (
            include_request_context
            and args.request_context_mode == "auto"
            and request_context_unsupported(status, error)
        ):
            include_request_context = False
            request_context_fallback_used = True
            continue
        break

    usage = response_json.get("usage", {}) if isinstance(response_json, dict) else {}
    prompt_tokens, cached_tokens = usage_prompt_tokens(usage if isinstance(usage, dict) else {})

    return {
        "run_id": run_id,
        "request_id": context["request_id"],
        "request_role": spec.request_role,
        "hint_kind": args.hint_kind,
        "priority_class": spec.priority_class,
        "hint_profile": spec.hint_profile,
        "request_source": spec.request_source,
        "source_repo": spec.source_repo,
        "source_instance_id": spec.source_instance_id,
        "source_task_index": spec.source_task_index,
        "arrival_index": spec.arrival_index,
        "planned_offset_ms": spec.planned_offset_ms,
        "client_send_timestamp_utc": send_started.isoformat(),
        "client_response_timestamp_utc": send_finished.isoformat(),
        "client_latency_ms": round_ms(latency_ms),
        "status": status,
        "error": error,
        "input_len_words": len(spec.prompt.split()),
        "output_len_tokens": args.output_len_tokens,
        "prompt_hash": prompt_hash,
        "agent_hints_priority": priority if priority is not None else "",
        "agent_hints_latency_sensitivity": (
            latency_sensitivity if latency_sensitivity is not None else ""
        ),
        "top_level_priority_mode": args.top_level_priority_mode,
        "top_level_priority_attempted": should_attempt_top_level_priority,
        "top_level_priority_sent": include_top_level_priority and request_succeeded(status),
        "top_level_priority_value": priority if priority is not None else "",
        "top_level_priority_fallback_used": fallback_used,
        "top_level_priority_unsupported": top_level_priority_unsupported,
        "worker_runtime_matched": False,
        "worker_request_received_timestamp": "",
        "worker_request_attached_timestamp": "",
        "worker_request_completed_timestamp": "",
        "worker_queue_wait_ms": "",
        "worker_service_ms": "",
        "worker_total_runtime_ms": "",
        "worker_prompt_tokens": prompt_tokens if prompt_tokens is not None else "",
        "worker_cached_tokens": cached_tokens if cached_tokens is not None else "",
        "worker_agent_hints_priority": "",
        "worker_agent_hints_latency_sensitivity": "",
        "worker_top_level_priority": "",
        "sglang_priority_events": 0,
        "sglang_priority_hint_seen": False,
        "sglang_scheduler_priority_applied": False,
        "attached_rank": "",
        "completed_rank": "",
        "overtook_earlier_low_attached_count": 0,
        "overtook_earlier_low_completed_count": 0,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def request_scheduling_signal(row: dict[str, Any]) -> str:
    priority_class = str(row.get("priority_class") or "")
    attached_leapfrogs = maybe_int(row.get("overtook_earlier_low_attached_count")) or 0
    attached_gain = maybe_int(row.get("attach_priority_gain")) or 0
    matched = truthy(row.get("worker_runtime_matched"))

    if priority_class == "low-priority":
        return "baseline_low"
    if not matched:
        return "unknown"
    if attached_leapfrogs > 0:
        return "yes_strong"
    if attached_gain > 0:
        return "yes_partial"
    return "no"


def build_readable_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    readable_rows: list[dict[str, Any]] = []
    for row in rows:
        arrival_index = maybe_int(row.get("arrival_index"))
        attached_rank = maybe_int(row.get("attached_rank"))
        completed_rank = maybe_int(row.get("completed_rank"))
        attach_priority_gain = (
            arrival_index - attached_rank
            if arrival_index is not None and attached_rank is not None
            else None
        )
        completion_priority_gain = (
            arrival_index - completed_rank
            if arrival_index is not None and completed_rank is not None
            else None
        )
        readable = {
            "request": row.get("request_role", ""),
            "prio_class": row.get("priority_class", ""),
            "request_source": row.get("request_source", ""),
            "source_instance_id": row.get("source_instance_id", ""),
            "source_task_index": row.get("source_task_index", ""),
            "arrival": safe_int_str(row.get("arrival_index")),
            "attach": safe_int_str(row.get("attached_rank")),
            "complete": safe_int_str(row.get("completed_rank")),
            "attach_priority_gain": attach_priority_gain if attach_priority_gain is not None else "",
            "completion_priority_gain": (
                completion_priority_gain if completion_priority_gain is not None else ""
            ),
            "beat_low_attach": safe_int_str(
                row.get("overtook_earlier_low_attached_count")
            ),
            "beat_low_complete": safe_int_str(
                row.get("overtook_earlier_low_completed_count")
            ),
            "queue_ms": safe_int_str(row.get("worker_queue_wait_ms")),
            "latency_ms": safe_int_str(row.get("client_latency_ms")),
            "hint_kind": row.get("hint_kind", ""),
            "worker_hint_prio": safe_int_str(row.get("worker_agent_hints_priority")),
            "worker_latency_sensitivity": row.get("worker_agent_hints_latency_sensitivity", ""),
            "sent_top_prio": row.get("top_level_priority_sent", ""),
            "worker_top_prio": safe_int_str(row.get("worker_top_level_priority")),
            "sglang_prio": row.get(
                "sglang_scheduler_priority_applied", ""
            ),
            "runtime_match": row.get("worker_runtime_matched", ""),
        }
        readable["effect"] = request_scheduling_signal(readable | row)
        readable_rows.append(readable)
    return readable_rows


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def runtime_annotations(record: dict[str, Any]) -> list[str]:
    nvext = record.get("nvext")
    if isinstance(nvext, dict) and isinstance(nvext.get("annotations"), list):
        return [str(item) for item in nvext["annotations"] if item not in (None, "")]
    runtime_observability = record.get("runtime_observability")
    if isinstance(runtime_observability, dict):
        nested = runtime_observability.get("annotations")
        if isinstance(nested, list):
            return [str(item) for item in nested if item not in (None, "")]
        nested_nvext = runtime_observability.get("nvext")
        if isinstance(nested_nvext, dict) and isinstance(nested_nvext.get("annotations"), list):
            return [str(item) for item in nested_nvext["annotations"] if item not in (None, "")]
    return []


def runtime_annotation_map(record: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in runtime_annotations(record):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key and value and key not in values:
            values[key] = value
    return values


def runtime_agent_context(record: dict[str, Any]) -> dict[str, Any]:
    nvext = record.get("nvext")
    if isinstance(nvext, dict) and isinstance(nvext.get("agent_context"), dict):
        return nvext["agent_context"]
    runtime_observability = record.get("runtime_observability")
    if isinstance(runtime_observability, dict):
        nested = runtime_observability.get("agent_context")
        if isinstance(nested, dict):
            return nested
        nested_nvext = runtime_observability.get("nvext")
        if isinstance(nested_nvext, dict) and isinstance(nested_nvext.get("agent_context"), dict):
            return nested_nvext["agent_context"]
    return {}


def runtime_request_context(record: dict[str, Any]) -> dict[str, Any]:
    request_context = record.get("request_context")
    if isinstance(request_context, dict):
        return request_context
    runtime_observability = record.get("runtime_observability")
    if isinstance(runtime_observability, dict):
        nested = runtime_observability.get("request_context")
        if isinstance(nested, dict):
            return nested
        nested_nvext = runtime_observability.get("nvext")
        if isinstance(nested_nvext, dict) and isinstance(nested_nvext.get("request_context"), dict):
            return nested_nvext["request_context"]
    nvext = record.get("nvext")
    if isinstance(nvext, dict) and isinstance(nvext.get("request_context"), dict):
        return nvext["request_context"]
    annotations = runtime_annotation_map(record)
    agent_context = runtime_agent_context(record)
    request_id = annotations.get("request_id")
    if not request_id and isinstance(agent_context.get("trajectory_id"), str):
        request_id = agent_context.get("trajectory_id")
    parent_run_id = annotations.get("parent_run_id")
    if not parent_run_id and isinstance(agent_context.get("session_id"), str):
        parent_run_id = agent_context.get("session_id")
    if not request_id and not parent_run_id and not annotations:
        return {}
    return {
        "request_id": request_id or "",
        "parent_run_id": parent_run_id or "",
        "task_instance_id": annotations.get("task_instance_id", ""),
        "phase": annotations.get("phase", ""),
        "step_index": annotations.get("step_index", ""),
        "step_title": annotations.get("step_title", ""),
        "app_variant": annotations.get("app_variant", ""),
        "priority_class": annotations.get("priority_class", ""),
        "prompt_hash": annotations.get("prompt_hash", ""),
    }


def runtime_agent_hints(record: dict[str, Any]) -> dict[str, Any]:
    agent_hints = record.get("agent_hints")
    if isinstance(agent_hints, dict):
        return agent_hints
    runtime_observability = record.get("runtime_observability")
    if isinstance(runtime_observability, dict):
        nested = runtime_observability.get("agent_hints")
        if isinstance(nested, dict):
            return nested
        nested_nvext = runtime_observability.get("nvext")
        if isinstance(nested_nvext, dict) and isinstance(nested_nvext.get("agent_hints"), dict):
            return nested_nvext["agent_hints"]
    nvext = record.get("nvext")
    if isinstance(nvext, dict) and isinstance(nvext.get("agent_hints"), dict):
        return nvext["agent_hints"]
    return {}


def record_request_ids(record: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in (
        "request_id",
        "external_request_id",
        "runtime_request_id",
        "runtime_context_id",
        "frontend_request_id",
        "sglang_request_id",
        "hint_probe_id",
    ):
        value = record.get(key)
        if isinstance(value, str) and value:
            values.add(value)
    request_context = runtime_request_context(record)
    for key in ("request_id", "parent_run_id", "task_instance_id"):
        value = request_context.get(key)
        if isinstance(value, str) and value:
            values.add(value)
    hints = runtime_agent_hints(record)
    for key in ("request_id", "hint_probe_id"):
        value = hints.get(key)
        if isinstance(value, str) and value:
            values.add(value)
    return values


def build_worker_runtime_alias_map(worker_runtime_log: Path) -> dict[str, set[str]]:
    alias_map: dict[str, set[str]] = {}
    if not worker_runtime_log.exists():
        return alias_map
    for raw_line in worker_runtime_log.read_text(encoding="utf-8", errors="replace").splitlines():
        record, _line_ts = parse_runtime_json_payload(clean_log_line(raw_line))
        if not isinstance(record, dict):
            continue
        request_context = runtime_request_context(record)
        canonical_request_id = request_context.get("request_id")
        if not isinstance(canonical_request_id, str) or not canonical_request_id:
            canonical_request_id = record.get("external_request_id")
        if not isinstance(canonical_request_id, str) or not canonical_request_id:
            continue
        alias_map.setdefault(canonical_request_id, set()).add(canonical_request_id)
        for alias in record_request_ids(record):
            alias_map.setdefault(alias, set()).add(canonical_request_id)
    return alias_map


def extract_runtime_records(worker_runtime_log: Path) -> dict[str, dict[str, Any]]:
    records_by_request: dict[str, dict[str, Any]] = {}
    if not worker_runtime_log.exists():
        return records_by_request

    for raw_line in worker_runtime_log.read_text(encoding="utf-8", errors="replace").splitlines():
        record, _line_ts = parse_runtime_json_payload(clean_log_line(raw_line))
        if not isinstance(record, dict):
            continue
        event_type = str(record.get("event_type") or "")
        if not event_type.startswith("worker.decode."):
            continue

        request_context = runtime_request_context(record)
        request_id = request_context.get("request_id") or record.get("external_request_id")
        if not isinstance(request_id, str) or not request_id:
            continue

        info = records_by_request.setdefault(
            request_id,
            {
                "event_types": set(),
                "received_dt": None,
                "attached_dt": None,
                "completed_dt": None,
                "agent_hints_priority": None,
                "agent_hints_latency_sensitivity": None,
                "top_level_priority": None,
                "prompt_tokens": None,
                "cached_tokens": None,
            },
        )
        info["event_types"].add(event_type)

        timestamp_dt = parse_dt(str(record.get("timestamp") or ""))
        if event_type.endswith("request_received") and info["received_dt"] is None:
            info["received_dt"] = timestamp_dt
        elif event_type.endswith("request_attached") and info["attached_dt"] is None:
            info["attached_dt"] = timestamp_dt
        elif event_type.endswith("request_completed"):
            info["completed_dt"] = timestamp_dt

        hints = runtime_agent_hints(record)
        hint_priority = maybe_int(hints.get("priority"))
        if hint_priority is not None and info["agent_hints_priority"] is None:
            info["agent_hints_priority"] = hint_priority
        hint_latency_sensitivity = maybe_float(hints.get("latency_sensitivity"))
        if (
            hint_latency_sensitivity is not None
            and info["agent_hints_latency_sensitivity"] is None
        ):
            info["agent_hints_latency_sensitivity"] = hint_latency_sensitivity

        top_level_priority = maybe_int(record.get("priority"))
        if top_level_priority is not None and info["top_level_priority"] is None:
            info["top_level_priority"] = top_level_priority

        usage = record.get("usage")
        if isinstance(usage, dict):
            prompt_tokens, cached_tokens = usage_prompt_tokens(usage)
            if prompt_tokens is not None and info["prompt_tokens"] is None:
                info["prompt_tokens"] = prompt_tokens
            if cached_tokens is not None and info["cached_tokens"] is None:
                info["cached_tokens"] = cached_tokens

    return records_by_request


def event_request_id(event: dict[str, Any]) -> str:
    for key in ("request_id", "external_request_id", "runtime_request_id", "hint_probe_id"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    for parent_key in ("request_context", "runtime_observability", "agent_hints"):
        nested = event.get(parent_key)
        if not isinstance(nested, dict):
            continue
        for key in ("request_id", "external_request_id", "runtime_request_id", "hint_probe_id"):
            value = nested.get(key)
            if isinstance(value, str) and value:
                return value
    return ""


def attach_sglang_priority_events(
    rows: list[dict[str, Any]],
    cache_event_log: Path,
    worker_runtime_log: Path | None,
) -> None:
    if not cache_event_log.exists():
        return
    by_request_id = {str(row.get("request_id")): row for row in rows if row.get("request_id")}
    worker_alias_map = (
        build_worker_runtime_alias_map(worker_runtime_log)
        if isinstance(worker_runtime_log, Path) and worker_runtime_log.exists()
        else {}
    )
    with cache_event_log.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            event = parse_sglang_event_line(line)
            if not event or event.get("event") != "sglang.priority":
                continue

            request_ids_with_source: list[str] = []
            direct_request_id = event_request_id(event)
            if direct_request_id:
                request_ids_with_source.append(direct_request_id)
            for alias_key in (
                "request_id",
                "external_request_id",
                "runtime_request_id",
                "runtime_context_id",
                "hint_probe_id",
                "sglang_request_id",
            ):
                alias_value = event.get(alias_key)
                if not isinstance(alias_value, str) or not alias_value:
                    continue
                for mapped in sorted(worker_alias_map.get(alias_value, set())):
                    request_ids_with_source.append(mapped)

            matched = []
            for request_id in request_ids_with_source:
                if request_id in by_request_id and request_id not in matched:
                    matched.append(request_id)
            if len(matched) != 1:
                continue

            row = by_request_id[matched[0]]
            row["sglang_priority_events"] = int(row.get("sglang_priority_events") or 0) + 1
            action = str(event.get("action") or event.get("function") or "").lower()
            if action == "priority_hint_seen":
                row["sglang_priority_hint_seen"] = True
            if action == "scheduler_priority_applied":
                row["sglang_scheduler_priority_applied"] = True
            top_level_priority = maybe_int(event.get("worker_top_level_priority"))
            if top_level_priority is not None and str(row.get("worker_top_level_priority", "")) == "":
                row["worker_top_level_priority"] = top_level_priority
            agent_hints_priority = maybe_int(event.get("worker_agent_hints_priority"))
            if agent_hints_priority is not None and str(row.get("worker_agent_hints_priority", "")) == "":
                row["worker_agent_hints_priority"] = agent_hints_priority
            agent_hints_latency_sensitivity = maybe_float(
                event.get("worker_agent_hints_latency_sensitivity")
            )
            if (
                agent_hints_latency_sensitivity is not None
                and str(row.get("worker_agent_hints_latency_sensitivity", "")) == ""
            ):
                row["worker_agent_hints_latency_sensitivity"] = agent_hints_latency_sensitivity


def attach_worker_runtime(rows: list[dict[str, Any]], worker_runtime_log: Path) -> None:
    if not worker_runtime_log.exists():
        return
    records_by_request = extract_runtime_records(worker_runtime_log)
    for row in rows:
        info = records_by_request.get(str(row.get("request_id")))
        if not info:
            continue
        row["worker_runtime_matched"] = True
        received_dt = info.get("received_dt")
        attached_dt = info.get("attached_dt")
        completed_dt = info.get("completed_dt")
        row["worker_request_received_timestamp"] = received_dt.isoformat() if isinstance(received_dt, datetime) else ""
        row["worker_request_attached_timestamp"] = attached_dt.isoformat() if isinstance(attached_dt, datetime) else ""
        row["worker_request_completed_timestamp"] = completed_dt.isoformat() if isinstance(completed_dt, datetime) else ""
        row["worker_queue_wait_ms"] = ms_between(received_dt, attached_dt)
        row["worker_service_ms"] = ms_between(attached_dt, completed_dt)
        row["worker_total_runtime_ms"] = ms_between(received_dt, completed_dt)
        if info.get("prompt_tokens") is not None:
            row["worker_prompt_tokens"] = info["prompt_tokens"]
        if info.get("cached_tokens") is not None:
            row["worker_cached_tokens"] = info["cached_tokens"]
        if info.get("agent_hints_priority") is not None:
            row["worker_agent_hints_priority"] = info["agent_hints_priority"]
        if info.get("agent_hints_latency_sensitivity") is not None:
            row["worker_agent_hints_latency_sensitivity"] = info[
                "agent_hints_latency_sensitivity"
            ]
        if info.get("top_level_priority") is not None:
            row["worker_top_level_priority"] = info["top_level_priority"]


def assign_order_metrics(rows: list[dict[str, Any]]) -> None:
    attached_rows = [
        row for row in rows
        if parse_dt(str(row.get("worker_request_attached_timestamp") or "")) is not None
    ]
    attached_rows.sort(key=lambda row: parse_dt(str(row.get("worker_request_attached_timestamp"))) or datetime.max.replace(tzinfo=timezone.utc))
    for index, row in enumerate(attached_rows, start=1):
        row["attached_rank"] = index

    completed_rows = [
        row for row in rows
        if parse_dt(str(row.get("worker_request_completed_timestamp") or "")) is not None
    ]
    completed_rows.sort(key=lambda row: parse_dt(str(row.get("worker_request_completed_timestamp"))) or datetime.max.replace(tzinfo=timezone.utc))
    for index, row in enumerate(completed_rows, start=1):
        row["completed_rank"] = index

    low_rows = [row for row in rows if row.get("priority_class") == "low-priority"]
    high_rows = [row for row in rows if row.get("priority_class") == "high-priority"]
    for row in high_rows:
        high_arrival = maybe_int(row.get("arrival_index"))
        high_attached = maybe_int(row.get("attached_rank"))
        high_completed = maybe_int(row.get("completed_rank"))
        if high_arrival is None:
            continue
        earlier_lows = [
            candidate for candidate in low_rows
            if maybe_int(candidate.get("arrival_index")) is not None
            and maybe_int(candidate.get("arrival_index")) < high_arrival
        ]
        attached_leapfrogs = 0
        completed_leapfrogs = 0
        if high_attached is not None:
            for candidate in earlier_lows:
                low_attached = maybe_int(candidate.get("attached_rank"))
                if low_attached is not None and low_attached > high_attached:
                    attached_leapfrogs += 1
        if high_completed is not None:
            for candidate in earlier_lows:
                low_completed = maybe_int(candidate.get("completed_rank"))
                if low_completed is not None and low_completed > high_completed:
                    completed_leapfrogs += 1
        row["overtook_earlier_low_attached_count"] = attached_leapfrogs
        row["overtook_earlier_low_completed_count"] = completed_leapfrogs


def request_priority_status(rows: list[dict[str, Any]], *, field: str, expected: int) -> str:
    values = []
    for row in rows:
        value = maybe_int(row.get(field))
        if value is not None:
            values.append(value)
    if not rows:
        return "missing"
    if not values:
        return "none"
    if all(value == expected for value in values) and len(values) == len(rows):
        return "full"
    return "partial"


def request_float_status(rows: list[dict[str, Any]], *, field: str, expected: float) -> str:
    values = []
    for row in rows:
        value = maybe_float(row.get(field))
        if value is not None:
            values.append(value)
    if not rows:
        return "missing"
    if not values:
        return "none"
    if all(abs(value - expected) < 1e-9 for value in values) and len(values) == len(rows):
        return "full"
    return "partial"


def frontend_priority_compatibility(rows: list[dict[str, Any]]) -> str:
    if any(truthy(row.get("top_level_priority_unsupported")) for row in rows):
        return "unsupported"
    if any(priority_unsupported(maybe_int(row.get("status")) or 0, str(row.get("error") or "")) for row in rows):
        return "unsupported"
    if any(truthy(row.get("top_level_priority_sent")) for row in rows):
        return "supported"
    return "not_attempted"


def worker_priority_path_status(high_rows: list[dict[str, Any]]) -> str:
    if any(truthy(row.get("sglang_scheduler_priority_applied")) for row in high_rows):
        return "applied"
    if any(truthy(row.get("sglang_priority_hint_seen")) for row in high_rows):
        return "seen_not_applied"
    if any(maybe_int(row.get("worker_agent_hints_priority")) is not None for row in high_rows):
        return "worker_received_hint"
    return "not_seen"


def worker_hint_path_status(high_rows: list[dict[str, Any]], hint_kind: str) -> str:
    if hint_kind == "priority":
        return worker_priority_path_status(high_rows)
    if any(
        maybe_float(row.get("worker_agent_hints_latency_sensitivity")) is not None
        for row in high_rows
    ):
        return "worker_received_hint"
    return "not_seen"


def build_summary(
    *,
    args: argparse.Namespace,
    run_id: str,
    requests_csv: Path,
    worker_runtime_log: Path | None,
    cache_event_log: Path | None,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    low_rows = [row for row in rows if row.get("priority_class") == "low-priority"]
    high_rows = [row for row in rows if row.get("priority_class") == "high-priority"]
    matched_rows = [row for row in rows if truthy(row.get("worker_runtime_matched"))]
    attached_rows = [row for row in rows if str(row.get("worker_request_attached_timestamp") or "")]
    completed_rows = [row for row in rows if str(row.get("worker_request_completed_timestamp") or "")]

    low_queue_waits = [value for value in (maybe_int(row.get("worker_queue_wait_ms")) for row in low_rows) if value is not None]
    high_queue_waits = [value for value in (maybe_int(row.get("worker_queue_wait_ms")) for row in high_rows) if value is not None]
    low_client_latencies = [
        value
        for value in (
            maybe_int(row.get("client_latency_ms"))
            for row in low_rows
            if request_succeeded(row.get("status"))
        )
        if value is not None
    ]
    high_client_latencies = [
        value
        for value in (
            maybe_int(row.get("client_latency_ms"))
            for row in high_rows
            if request_succeeded(row.get("status"))
        )
        if value is not None
    ]

    high_attached_leapfrogs = sum(maybe_int(row.get("overtook_earlier_low_attached_count")) or 0 for row in high_rows)
    high_completed_leapfrogs = sum(maybe_int(row.get("overtook_earlier_low_completed_count")) or 0 for row in high_rows)

    runtime_coverage = f"{len(matched_rows)} / {len(rows)}"
    attached_coverage = f"{len(attached_rows)} / {len(rows)}"
    completed_coverage = f"{len(completed_rows)} / {len(rows)}"
    event_types_seen: list[str] = []
    if matched_rows:
        has_received = any(str(row.get("worker_request_received_timestamp") or "") for row in matched_rows)
        has_attached = bool(attached_rows)
        has_completed = bool(completed_rows)
        if has_received:
            event_types_seen.append("received")
        if has_attached:
            event_types_seen.append("attached")
        if has_completed:
            event_types_seen.append("completed")

    summary = {
        "run_id": run_id,
        "model": args.model,
        "mode": args.attribution_mode,
        "request_source": args.request_source,
        "swebench_dataset": args.swebench_dataset if args.request_source == "swebench_dataset" else "",
        "swebench_split": args.swebench_split if args.request_source == "swebench_dataset" else "",
        "swebench_start_index": (
            args.swebench_start_index if args.request_source == "swebench_dataset" else ""
        ),
        "trajectory_prompt_catalog": (
            args.trajectory_prompt_catalog if args.request_source == "swebench_trajectory" else ""
        ),
        "trajectory_stages": args.trajectory_stages if args.request_source == "swebench_trajectory" else "",
        "trajectory_start_task_index": (
            args.trajectory_start_task_index if args.request_source == "swebench_trajectory" else ""
        ),
        "trajectory_prompt_prefix_mode": (
            args.trajectory_prompt_prefix_mode if args.request_source == "swebench_trajectory" else ""
        ),
        "low_n": args.low_priority_count,
        "high_n": args.high_priority_count,
        "input_words": args.input_len_words if args.request_source == "synthetic" else args.request_source,
        "output_tokens": args.output_len_tokens,
        "arrival_gap_ms": args.arrival_gap_ms,
        "inter_gap_ms": args.inter_request_gap_ms,
        "hint_kind": args.hint_kind,
        "top_prio_compat": frontend_priority_compatibility(rows),
        "worker_hint_status": (
            request_priority_status(
                high_rows,
                field="worker_agent_hints_priority",
                expected=args.high_priority_value,
            )
            if args.hint_kind == "priority"
            else request_float_status(
                high_rows,
                field="worker_agent_hints_latency_sensitivity",
                expected=args.high_latency_sensitivity_value,
            )
        ),
        "worker_top_prio_status": request_priority_status(
            high_rows,
            field="worker_top_level_priority",
            expected=args.high_priority_value,
        ),
        "sglang_prio_status": worker_hint_path_status(high_rows, args.hint_kind),
        "runtime_cov": runtime_coverage,
        "attach_cov": attached_coverage,
        "complete_cov": completed_coverage,
        "low_wait_ms": mean_int(low_queue_waits),
        "high_wait_ms": mean_int(high_queue_waits),
        "low_latency_ms": mean_int(low_client_latencies),
        "high_latency_ms": mean_int(high_client_latencies),
        "high_attach_leapfrogs": high_attached_leapfrogs,
        "high_complete_leapfrogs": high_completed_leapfrogs,
        "effect_status": "yes" if high_attached_leapfrogs > 0 else "no",
    }
    return summary


def build_summary_md(summary: dict[str, Any]) -> str:
    effect = summary.get("effect_status", "no")
    lines = [
        f"# Priority Scheduling Probe: {summary['run_id']}",
        "",
        "## Setup",
        "",
        f"- Model: `{summary['model']}`",
        f"- Attribution mode: `{summary['mode']}`",
        f"- Request source: `{summary['request_source']}`",
        f"- SWE-bench dataset: `{summary['swebench_dataset']}`",
        f"- SWE-bench split: `{summary['swebench_split']}`",
        f"- SWE-bench start index: `{summary['swebench_start_index']}`",
        f"- Low-priority requests: `{summary['low_n']}`",
        f"- High-priority requests: `{summary['high_n']}`",
        f"- Input length (words): `{summary['input_words']}`",
        f"- Output length (tokens): `{summary['output_tokens']}`",
        f"- Arrival gap ms: `{summary['arrival_gap_ms']}`",
        f"- Inter-request gap ms: `{summary['inter_gap_ms']}`",
        f"- Hint kind: `{summary['hint_kind']}`",
        "",
        "## What happened",
        "",
        f"- Frontend top-level priority compatibility: `{summary['top_prio_compat']}`",
        f"- Worker high-hint received status: `{summary['worker_hint_status']}`",
        f"- Worker high top-level priority status: `{summary['worker_top_prio_status']}`",
        f"- SGLang priority-path status: `{summary['sglang_prio_status']}`",
        f"- Worker runtime coverage: `{summary['runtime_cov']}`",
        f"- Worker attached-event coverage: `{summary['attach_cov']}`",
        f"- Worker completed-event coverage: `{summary['complete_cov']}`",
        f"- Mean low queue wait ms: `{summary['low_wait_ms']}`",
        f"- Mean high queue wait ms: `{summary['high_wait_ms']}`",
        f"- Mean low client latency ms: `{summary['low_latency_ms']}`",
        f"- Mean high client latency ms: `{summary['high_latency_ms']}`",
        f"- High-priority attached leapfrogs: `{summary['high_attach_leapfrogs']}`",
        f"- High-priority completed leapfrogs: `{summary['high_complete_leapfrogs']}`",
        f"- Scheduling effect observed: `{effect}`",
        "",
    ]
    return "\n".join(lines)


def output_paths(root: Path, run_id: str) -> dict[str, Path]:
    run_dir = root / run_id
    return {
        "run_dir": run_dir,
        "requests_csv": run_dir / "priority_scheduling_requests.csv",
        "readable_requests_csv": run_dir / "priority_scheduling_readable.csv",
        "proof_requests_csv": run_dir / "priority_scheduling_proof.csv",
        "summary_csv": run_dir / "priority_scheduling_summary.csv",
        "summary_md": run_dir / "priority_scheduling_summary.md",
        "latest_requests_csv": root.parent / "priority_scheduling_requests.csv",
        "latest_readable_requests_csv": root.parent / "priority_scheduling_readable.csv",
        "latest_proof_requests_csv": root.parent / "priority_scheduling_proof.csv",
        "latest_summary_csv": root.parent / "priority_scheduling_summary.csv",
        "latest_summary_md": root.parent / "priority_scheduling_summary.md",
        "latest_named_requests_csv": root.parent / "latest_priority_scheduling_requests.csv",
        "latest_named_readable_requests_csv": root.parent / "latest_priority_scheduling_readable.csv",
        "latest_named_proof_requests_csv": root.parent / "latest_priority_scheduling_proof.csv",
        "latest_named_summary_csv": root.parent / "latest_priority_scheduling_summary.csv",
        "latest_named_summary_md": root.parent / "latest_priority_scheduling_summary.md",
        "latest_named_run_txt": root.parent / "latest_priority_scheduling_run.txt",
    }


def save_outputs(paths: dict[str, Path], rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    readable_rows = build_readable_rows(rows)
    write_csv(paths["requests_csv"], rows, REQUEST_COLUMNS)
    write_csv(paths["readable_requests_csv"], readable_rows, READABLE_REQUEST_COLUMNS)
    write_csv(paths["proof_requests_csv"], readable_rows, PROOF_REQUEST_COLUMNS)
    write_csv(paths["summary_csv"], [summary], SUMMARY_COLUMNS)
    paths["summary_md"].write_text(build_summary_md(summary), encoding="utf-8")

    for source_key, latest_key in (
        ("readable_requests_csv", "latest_requests_csv"),
        ("readable_requests_csv", "latest_readable_requests_csv"),
        ("proof_requests_csv", "latest_proof_requests_csv"),
        ("summary_csv", "latest_summary_csv"),
        ("summary_md", "latest_summary_md"),
        ("readable_requests_csv", "latest_named_requests_csv"),
        ("readable_requests_csv", "latest_named_readable_requests_csv"),
        ("proof_requests_csv", "latest_named_proof_requests_csv"),
        ("summary_csv", "latest_named_summary_csv"),
        ("summary_md", "latest_named_summary_md"),
    ):
        paths[latest_key].parent.mkdir(parents=True, exist_ok=True)
        paths[latest_key].write_text(paths[source_key].read_text(encoding="utf-8"), encoding="utf-8")

    paths["latest_named_run_txt"].parent.mkdir(parents=True, exist_ok=True)
    paths["latest_named_run_txt"].write_text(
        "\n".join(
            [
                f"run_id={summary['run_id']}",
                f"run_dir={paths['run_dir']}",
                f"requests_csv={paths['requests_csv']}",
                f"readable_csv={paths['readable_requests_csv']}",
                f"proof_csv={paths['proof_requests_csv']}",
                f"summary_csv={paths['summary_csv']}",
                f"summary_md={paths['summary_md']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def load_rows_for_postprocess(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv_rows(path):
        converted: dict[str, Any] = {}
        for key, value in row.items():
            converted[key] = value
        status = maybe_int(converted.get("status"))
        error = str(converted.get("error") or "")
        if priority_unsupported(status or 0, error):
            converted["top_level_priority_unsupported"] = True
        rows.append(converted)
    return rows


def run_requests(args: argparse.Namespace, run_id: str) -> list[dict[str, Any]]:
    specs = build_request_specs(args)
    run_start_monotonic = time.perf_counter() + 0.1
    max_workers = max(1, len(specs))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(send_one_request, args, run_id, run_start_monotonic, spec)
            for spec in specs
        ]
        rows = [future.result() for future in futures]
    rows.sort(key=lambda row: maybe_int(row.get("arrival_index")) or 0)
    return rows


def main() -> int:
    args = parse_args()
    run_id = args.run_id or now_run_id()
    root = Path(args.output_root).resolve()
    paths = output_paths(root, run_id)
    worker_runtime_log = Path(args.worker_runtime_log).resolve() if args.worker_runtime_log else None
    cache_event_log = Path(args.cache_event_log).resolve() if args.cache_event_log else None

    if args.postprocess_only:
        rows = load_rows_for_postprocess(paths["requests_csv"])
    else:
        rows = run_requests(args, run_id)

    if isinstance(worker_runtime_log, Path) and worker_runtime_log.exists():
        attach_worker_runtime(rows, worker_runtime_log)
    if (
        args.attribution_mode == "precise"
        and isinstance(cache_event_log, Path)
        and cache_event_log.exists()
    ):
        attach_sglang_priority_events(rows, cache_event_log, worker_runtime_log)

    assign_order_metrics(rows)
    summary = build_summary(
        args=args,
        run_id=run_id,
        requests_csv=paths["requests_csv"],
        worker_runtime_log=worker_runtime_log,
        cache_event_log=cache_event_log,
        rows=rows,
    )
    save_outputs(paths, rows, summary)

    print(f"Priority scheduling run_id={run_id}")
    print(f"Requests CSV: {paths['requests_csv']}")
    print(f"Readable CSV: {paths['readable_requests_csv']}")
    print(f"Proof CSV: {paths['proof_requests_csv']}")
    print(f"Summary CSV: {paths['summary_csv']}")
    print(f"Summary MD: {paths['summary_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
