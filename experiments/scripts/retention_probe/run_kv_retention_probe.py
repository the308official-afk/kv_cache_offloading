#!/usr/bin/env python3
"""Run a synthetic KV-cache retention probe against an OpenAI-compatible endpoint."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_ROOT = REPO_ROOT / "experiments" / "reports" / "retention_probe"
DEFAULT_MATRIX = REPO_ROOT / "experiments" / "reports" / "design_space_retention_matrix.csv"
DEFAULT_CACHE_EVENT_LOG = (
    REPO_ROOT
    / "experiments"
    / "raw"
    / "sglang_transfer_logs"
    / "latest_sglang_transfer_events.jsonl"
)
PROMPT_GENERATOR_VERSION = "cache-word-v2"
SGLANG_EVENT_PREFIX = "[SGLANG_TRANSFER_JSON] "
RUNTIME_JSON_PREFIX = "[RUNTIME_JSON]"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
DEFAULT_PROBE_INPUT_LEN = 14000
DEFAULT_MAX_CONTEXT_TOKENS = 17146

DEFAULT_HINTS: dict[str, Any] = {
    "priority": 5,
    "reuse_likelihood": 0.9,
    "agent_phase": "retention_probe",
    "latency_sensitivity": 0.7,
    "program_id": "agentbench.synthetic_retention_probe",
    "context_type": "synthetic_kv_retention_probe",
    "expected_output_tokens": 1,
}

HINT_PROFILES: dict[str, dict[str, Any]] = {
    "baseline": {},
    "high-reuse": {
        "priority": 5,
        "reuse_likelihood": 1.0,
        "latency_sensitivity": 0.5,
        "expected_output_tokens": 1,
    },
    "low-reuse": {
        "priority": 5,
        "reuse_likelihood": 0.0,
        "latency_sensitivity": 0.5,
        "expected_output_tokens": 1,
    },
    "high-priority": {
        "priority": 10,
        "reuse_likelihood": 0.5,
        "latency_sensitivity": 1.0,
        "expected_output_tokens": 1,
    },
    "low-priority": {
        "priority": 1,
        "reuse_likelihood": 0.5,
        "latency_sensitivity": 0.2,
        "expected_output_tokens": 1,
    },
    "long-output": {
        "priority": 5,
        "reuse_likelihood": 0.8,
        "latency_sensitivity": 0.5,
        "expected_output_tokens": 2048,
    },
    "short-output": {
        "priority": 5,
        "reuse_likelihood": 0.8,
        "latency_sensitivity": 0.5,
        "expected_output_tokens": 128,
    },
}

NO_HINT_PROFILES = {"", "none", "off", "no-hints", "no_hints"}


REQUEST_COLUMNS = [
    "run_id",
    "sequence_index",
    "request_role",
    "request_id",
    "hint_profile",
    "hints_enabled",
    "agent_hints_priority",
    "top_level_priority_sent",
    "top_level_priority_value",
    "prompt_hash",
    "input_len",
    "output_len",
    "latency_ms",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cached_prompt_tokens",
    "cache_reuse_ratio",
    "sglang_cache_events",
    "sglang_cache_match_events",
    "sglang_cache_insert_events",
    "sglang_cache_evict_events",
    "sglang_cache_semantic_tokens",
    "sglang_cache_token_sha256",
    "sglang_cache_direct",
    "sglang_cache_request_id_source",
    "sglang_priority_events",
    "sglang_priority_hint_seen",
    "sglang_scheduler_priority_applied",
    "sglang_priority_eviction_events",
    "sglang_worker_top_level_priority",
    "sglang_worker_agent_hints_priority",
    "sglang_priority_request_id_source",
    "status",
    "error",
]

SUMMARY_COLUMNS = [
    "run_id",
    "model",
    "kv_tier_mode",
    "protected_hint_profile",
    "distractor_hint_profile",
    "protected_input_len",
    "distractor_input_len",
    "distractor_count",
    "output_len",
    "seed",
    "a_first_status",
    "a_replay_status",
    "a_first_latency_ms",
    "a_replay_latency_ms",
    "a_replay_latency_delta_ms",
    "a_replay_speedup_ratio",
    "worker_kv_capacity_tokens",
    "worker_context_len",
    "a_first_prompt_tokens",
    "first_distractor_prompt_tokens",
    "kv_tokens_left_after_a",
    "kv_tokens_left_after_a_after_first_distractor",
    "a_first_agent_hints_priority",
    "a_first_top_level_priority_sent",
    "a_first_top_level_priority_value",
    "a_first_cached_tokens",
    "a_replay_agent_hints_priority",
    "a_replay_top_level_priority_sent",
    "a_replay_top_level_priority_value",
    "a_replay_cached_tokens",
    "a_replay_cache_reuse_ratio",
    "a_replay_prompt_tokens",
    "a_first_sglang_cache_events",
    "a_replay_sglang_cache_events",
    "a_replay_sglang_cache_match_events",
    "a_replay_sglang_cache_semantic_tokens",
    "a_replay_sglang_cache_direct",
    "a_first_sglang_priority_hint_seen",
    "a_replay_sglang_priority_hint_seen",
    "a_first_sglang_scheduler_priority_applied",
    "a_replay_sglang_scheduler_priority_applied",
    "a_first_sglang_worker_top_level_priority",
    "a_replay_sglang_worker_top_level_priority",
    "a_first_sglang_worker_agent_hints_priority",
    "a_replay_sglang_worker_agent_hints_priority",
    "a_survived_cache_threshold",
    "cache_survival_source",
    "successful_requests",
    "failed_requests",
    "sglang_cache_event_log",
    "worker_runtime_log",
    "requests_csv",
]


def now_run_id() -> str:
    return f"retention_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Send protected prompt A, distractor prompts, then prompt A again "
            "to measure cache-retention evidence."
        )
    )
    parser.add_argument(
        "--frontend-url",
        default=f"http://127.0.0.1:{os.environ.get('DYNAMO_FRONTEND_PORT', '8000')}/v1/chat/completions",
    )
    parser.add_argument("--model", default=os.environ.get("MODEL_NAME", ""))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--matrix-path", default=str(DEFAULT_MATRIX))
    parser.add_argument("--append-matrix", action="store_true")
    parser.add_argument("--skip-matrix-write", action="store_true")
    parser.add_argument("--cache-event-log", default=str(DEFAULT_CACHE_EVENT_LOG))
    parser.add_argument("--worker-runtime-log", default="")
    parser.add_argument("--postprocess-only", action="store_true")
    parser.add_argument("--protected-input-len", type=int, default=DEFAULT_PROBE_INPUT_LEN)
    parser.add_argument("--distractor-input-len", type=int, default=DEFAULT_PROBE_INPUT_LEN)
    parser.add_argument("--distractor-count", type=int, default=10)
    parser.add_argument("--random-output-len", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--protected-hint-profile", default="high-priority")
    parser.add_argument("--distractor-hint-profile", default="none")
    parser.add_argument("--kv-tier-mode", default=os.environ.get("KV_TIER_MODE", os.environ.get("KV_TIER_MODES", "")))
    parser.add_argument("--request-timeout", type=float, default=600.0)
    parser.add_argument(
        "--max-context-tokens",
        type=int,
        default=int(os.environ.get("MAX_CONTEXT_TOKENS", str(DEFAULT_MAX_CONTEXT_TOKENS))),
    )
    parser.add_argument("--context-reserve-tokens", type=int, default=int(os.environ.get("CONTEXT_RESERVE_TOKENS", "2048")))
    parser.add_argument("--ignore-eos", action="store_true")
    parser.add_argument("--survival-cache-reuse-threshold", type=float, default=0.8)
    parser.add_argument("--stop-on-error", action="store_true")
    args = parser.parse_args()

    if not args.model:
        parser.error("--model is required or MODEL_NAME must be set")
    if args.distractor_count < 0:
        parser.error("--distractor-count must be >= 0")
    if args.protected_input_len <= 0 or args.distractor_input_len <= 0:
        parser.error("input lengths must be positive")
    if args.random_output_len <= 0:
        parser.error("--random-output-len must be positive")
    if args.max_context_tokens > 0:
        safe_input_limit = args.max_context_tokens - args.context_reserve_tokens - args.random_output_len
        if safe_input_limit <= 0:
            parser.error("--max-context-tokens is too small for the reserve/output settings")
        if args.protected_input_len > safe_input_limit:
            parser.error(
                f"--protected-input-len={args.protected_input_len} exceeds the approximate safe "
                f"limit {safe_input_limit} for max_context={args.max_context_tokens}. "
                "Reduce the length or set MAX_CONTEXT_TOKENS for a longer-context model."
            )
        if args.distractor_input_len > safe_input_limit:
            parser.error(
                f"--distractor-input-len={args.distractor_input_len} exceeds the approximate safe "
                f"limit {safe_input_limit} for max_context={args.max_context_tokens}. "
                "Reduce the length or set MAX_CONTEXT_TOKENS for a longer-context model."
            )
    return args


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def make_prompt(*, role: str, target_len: int, seed: int) -> str:
    rng = random.Random(f"{role}:{seed}:{target_len}")
    header = (
        f"KV cache retention probe prompt role={role}. "
        f"seed marker {rng.randrange(1_000_000):06d}. "
        "Return exactly one short answer token. "
        "The repeated body below exists only to create cache pressure. "
    )
    # Keep body words tokenizer-friendly. Long identifiers with underscores and
    # digits can explode into many tokenizer pieces and exceed context limits.
    body_words = ["cache"] * target_len
    for idx in range(0, target_len, 512):
        body_words[idx] = "retain" if rng.randrange(2) else "reuse"
    words = body_words
    return header + " ".join(words)


def build_hints(*, profile: str, run_id: str, request_role: str, sequence_index: int, output_len: int) -> dict[str, Any] | None:
    normalized = profile.strip()
    if normalized.lower() in NO_HINT_PROFILES:
        return None
    if normalized not in HINT_PROFILES:
        choices = ", ".join(["none", *sorted(HINT_PROFILES)])
        raise SystemExit(f"Unknown hint profile {profile!r}. Choose one of: {choices}")

    hints = dict(DEFAULT_HINTS)
    hints.update(HINT_PROFILES[normalized])
    hints["agent_phase"] = "retention_probe"
    hints["hint_profile"] = normalized
    hints["hint_probe_id"] = f"{run_id}::{request_role}::{sequence_index}"
    hints["phase_sequence_index"] = sequence_index
    hints["expected_output_tokens"] = output_len
    hints["retention_probe_role"] = request_role
    hints["cache_retention_priority"] = "high" if int(hints.get("priority", 0)) >= 10 else "normal"
    return hints


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


def request_context(
    *,
    run_id: str,
    request_role: str,
    sequence_index: int,
    prompt_hash: str,
    hint_profile: str,
) -> dict[str, Any]:
    return {
        "request_id": f"{run_id}::{request_role}::{sequence_index}",
        "parent_run_id": run_id,
        "task_instance_id": "synthetic_kv_retention_probe",
        "phase": "retention_probe",
        "step_index": sequence_index,
        "step_title": request_role,
        "app_variant": "synthetic_retention_probe",
        "prompt_hash": prompt_hash,
        "hint_profile": hint_profile,
    }


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
    except Exception as exc:  # noqa: BLE001 - report request failures without hiding later rows.
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


def as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def round_ms(value: float | None) -> int | str:
    if value is None:
        return ""
    return int(round(value))


def round_ratio(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}"


def send_probe_request(
    *,
    args: argparse.Namespace,
    run_id: str,
    sequence_index: int,
    request_role: str,
    prompt: str,
    hint_profile: str,
) -> dict[str, Any]:
    prompt_hash = short_hash(prompt)
    hints = build_hints(
        profile=hint_profile,
        run_id=run_id,
        request_role=request_role,
        sequence_index=sequence_index,
        output_len=args.random_output_len,
    )
    context = request_context(
        run_id=run_id,
        request_role=request_role,
        sequence_index=sequence_index,
        prompt_hash=prompt_hash,
        hint_profile=hint_profile,
    )
    payload: dict[str, Any] = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": args.random_output_len,
        "temperature": 0,
        "nvext": {"request_context": context},
    }
    if hints is not None:
        payload["nvext"]["agent_hints"] = hints
    priority = top_level_priority_from_hints(hints)
    if priority is not None:
        payload["priority"] = priority
    if args.ignore_eos:
        payload["ignore_eos"] = True

    start = time.perf_counter()
    status, response_json, error = post_json(args.frontend_url, payload, timeout=args.request_timeout)
    latency_ms = (time.perf_counter() - start) * 1000

    usage = response_json.get("usage", {}) if isinstance(response_json, dict) else {}
    prompt_tokens = as_int(
        get_nested(
            usage,
            [
                ("prompt_tokens",),
                ("input_tokens",),
            ],
        )
    )
    completion_tokens = as_int(
        get_nested(
            usage,
            [
                ("completion_tokens",),
                ("output_tokens",),
            ],
        )
    )
    total_tokens = as_int(get_nested(usage, [("total_tokens",)]))
    cached_tokens = as_int(
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
    cache_reuse_ratio = None
    if prompt_tokens and cached_tokens is not None:
        cache_reuse_ratio = cached_tokens / prompt_tokens

    return {
        "run_id": run_id,
        "sequence_index": sequence_index,
        "request_role": request_role,
        "request_id": context["request_id"],
        "hint_profile": hint_profile,
        "hints_enabled": bool(hints),
        "agent_hints_priority": priority if priority is not None else "",
        "top_level_priority_sent": bool(priority is not None),
        "top_level_priority_value": priority if priority is not None else "",
        "prompt_hash": prompt_hash,
        "input_len": len(prompt.split()),
        "output_len": args.random_output_len,
        "latency_ms": round_ms(latency_ms),
        "prompt_tokens": prompt_tokens if prompt_tokens is not None else "",
        "completion_tokens": completion_tokens if completion_tokens is not None else "",
        "total_tokens": total_tokens if total_tokens is not None else "",
        "cached_prompt_tokens": cached_tokens if cached_tokens is not None else "",
        "cache_reuse_ratio": round_ratio(cache_reuse_ratio),
        "sglang_cache_events": 0,
        "sglang_cache_match_events": 0,
        "sglang_cache_insert_events": 0,
        "sglang_cache_evict_events": 0,
        "sglang_cache_semantic_tokens": "",
        "sglang_cache_token_sha256": "",
        "sglang_cache_direct": False,
        "status": status,
        "error": error,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def append_matrix(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


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


def clean_log_line(line: str) -> str:
    return ANSI_RE.sub("", line)


def parse_runtime_json_payload(line: str) -> dict[str, Any] | None:
    if RUNTIME_JSON_PREFIX not in line:
        return None
    payload = line.split(RUNTIME_JSON_PREFIX, 1)[1].strip()
    json_start = payload.find("{")
    if json_start >= 0:
        payload = payload[json_start:]
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def request_context_from_record(record: dict[str, Any]) -> dict[str, Any]:
    request_context = record.get("request_context")
    if isinstance(request_context, dict):
        return request_context

    runtime_observability = record.get("runtime_observability")
    if isinstance(runtime_observability, dict):
        request_context = runtime_observability.get("request_context")
        if isinstance(request_context, dict):
            return request_context
        nvext = runtime_observability.get("nvext")
        if isinstance(nvext, dict) and isinstance(nvext.get("request_context"), dict):
            return nvext["request_context"]

    nvext = record.get("nvext")
    if isinstance(nvext, dict) and isinstance(nvext.get("request_context"), dict):
        return nvext["request_context"]
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

    request_context = request_context_from_record(record)
    for key in ("request_id", "parent_run_id", "task_instance_id"):
        value = request_context.get(key)
        if isinstance(value, str) and value:
            values.add(value)
    return values


def build_worker_runtime_alias_map(worker_runtime_log: Path) -> dict[str, set[str]]:
    alias_map: dict[str, set[str]] = {}
    if not worker_runtime_log.exists():
        return alias_map

    for raw_line in worker_runtime_log.read_text(encoding="utf-8", errors="replace").splitlines():
        record = parse_runtime_json_payload(clean_log_line(raw_line))
        if not isinstance(record, dict):
            continue
        request_context = request_context_from_record(record)
        canonical_request_id = request_context.get("request_id")
        if not isinstance(canonical_request_id, str) or not canonical_request_id:
            canonical_request_id = record.get("external_request_id")
        if not isinstance(canonical_request_id, str) or not canonical_request_id:
            continue

        for alias in record_request_ids(record):
            alias_map.setdefault(alias, set()).add(canonical_request_id)
        alias_map.setdefault(canonical_request_id, set()).add(canonical_request_id)
    return alias_map


def parse_worker_capacity(worker_runtime_log: Path | None) -> dict[str, int | None]:
    if not isinstance(worker_runtime_log, Path) or not worker_runtime_log.exists():
        return {
            "worker_kv_capacity_tokens": None,
            "worker_context_len": None,
        }

    kv_capacity = None
    context_len = None
    scheduler_re = re.compile(
        r"max_total_num_tokens=(?P<kv>\d+).*context_len=(?P<context>\d+)"
    )

    for raw_line in worker_runtime_log.read_text(encoding="utf-8", errors="replace").splitlines():
        line = clean_log_line(raw_line)
        match = scheduler_re.search(line)
        if match:
            kv_capacity = maybe_int(match.group("kv"))
            context_len = maybe_int(match.group("context"))

    return {
        "worker_kv_capacity_tokens": kv_capacity,
        "worker_context_len": context_len,
    }


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


def attach_cache_events(
    rows: list[dict[str, Any]],
    cache_event_log: Path,
    worker_runtime_log: Path | None = None,
) -> None:
    by_request_id = {str(row.get("request_id")): row for row in rows if row.get("request_id")}
    worker_alias_map = (
        build_worker_runtime_alias_map(worker_runtime_log)
        if isinstance(worker_runtime_log, Path)
        else {}
    )
    for row in rows:
        row["sglang_cache_events"] = 0
        row["sglang_cache_match_events"] = 0
        row["sglang_cache_insert_events"] = 0
        row["sglang_cache_evict_events"] = 0
        row["sglang_cache_semantic_tokens"] = ""
        row["sglang_cache_token_sha256"] = ""
        row["sglang_cache_direct"] = False
        row["sglang_cache_request_id_source"] = ""
        row["sglang_priority_events"] = 0
        row["sglang_priority_hint_seen"] = False
        row["sglang_scheduler_priority_applied"] = False
        row["sglang_priority_eviction_events"] = 0
        row["sglang_worker_top_level_priority"] = ""
        row["sglang_worker_agent_hints_priority"] = ""
        row["sglang_priority_request_id_source"] = ""

    if not cache_event_log.exists():
        return

    max_semantic_tokens: dict[str, int] = {}
    token_hashes: dict[str, set[str]] = {}

    with cache_event_log.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            event = parse_sglang_event_line(line)
            if not event or event.get("event") not in {"sglang.cache", "sglang.priority"}:
                continue
            request_ids_with_source: list[tuple[str, str]] = []
            direct_request_id = event_request_id(event)
            if direct_request_id:
                request_ids_with_source.append((direct_request_id, "event_request_id"))

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
                for mapped_request_id in sorted(worker_alias_map.get(alias_value, set())):
                    request_ids_with_source.append(
                        (mapped_request_id, f"worker_runtime.{alias_key}")
                    )

            matched_request_ids: dict[str, str] = {}
            for request_id, source in request_ids_with_source:
                if request_id in by_request_id:
                    matched_request_ids.setdefault(request_id, source)

            if len(matched_request_ids) != 1:
                continue
            request_id, request_id_source = next(iter(matched_request_ids.items()))
            row = by_request_id[request_id]

            if event.get("event") == "sglang.priority":
                action = str(event.get("action") or event.get("function") or "").lower()
                row["sglang_priority_events"] = int(row["sglang_priority_events"]) + 1
                if not row.get("sglang_priority_request_id_source"):
                    row["sglang_priority_request_id_source"] = request_id_source
                if action == "priority_hint_seen":
                    row["sglang_priority_hint_seen"] = True
                if action == "scheduler_priority_applied":
                    row["sglang_scheduler_priority_applied"] = True
                if "evict" in action:
                    row["sglang_priority_eviction_events"] = int(row["sglang_priority_eviction_events"]) + 1
                top_level_priority = maybe_int(event.get("worker_top_level_priority"))
                if top_level_priority is not None and row.get("sglang_worker_top_level_priority", "") == "":
                    row["sglang_worker_top_level_priority"] = top_level_priority
                agent_hint_priority = maybe_int(event.get("worker_agent_hints_priority"))
                if agent_hint_priority is not None and row.get("sglang_worker_agent_hints_priority", "") == "":
                    row["sglang_worker_agent_hints_priority"] = agent_hint_priority
                continue

            action = str(event.get("action") or event.get("function") or "").lower()
            row["sglang_cache_events"] = int(row["sglang_cache_events"]) + 1
            row["sglang_cache_direct"] = True
            if not row.get("sglang_cache_request_id_source"):
                row["sglang_cache_request_id_source"] = request_id_source
            if "match" in action:
                row["sglang_cache_match_events"] = int(row["sglang_cache_match_events"]) + 1
            if "insert" in action or "cache_finished" in action or "cache_unfinished" in action:
                row["sglang_cache_insert_events"] = int(row["sglang_cache_insert_events"]) + 1
            if "evict" in action:
                row["sglang_cache_evict_events"] = int(row["sglang_cache_evict_events"]) + 1

            semantic_count = maybe_int(event.get("semantic_token_count"))
            if semantic_count is not None:
                max_semantic_tokens[request_id] = max(max_semantic_tokens.get(request_id, 0), semantic_count)
            token_hash = event.get("semantic_token_ids_sha256")
            if isinstance(token_hash, str) and token_hash:
                token_hashes.setdefault(request_id, set()).add(token_hash)

    for request_id, row in by_request_id.items():
        if request_id in max_semantic_tokens:
            row["sglang_cache_semantic_tokens"] = max_semantic_tokens[request_id]
        if request_id in token_hashes:
            row["sglang_cache_token_sha256"] = ";".join(sorted(token_hashes[request_id]))


def display_path(path: Path) -> str:
    if str(path) in {"", "."}:
        return ""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def maybe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def maybe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def int_or_empty(value: Any) -> int | str:
    parsed = maybe_int(value)
    return "" if parsed is None else parsed


def request_succeeded(row: dict[str, Any]) -> bool:
    return str(row.get("status")) in {"200", "201"}


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def build_summary(
    *,
    args: argparse.Namespace,
    run_id: str,
    rows: list[dict[str, Any]],
    requests_csv: Path,
    cache_event_log: Path,
    worker_runtime_log: Path | None,
) -> dict[str, Any]:
    first = next((row for row in rows if row["request_role"] == "a_first"), {})
    replay = next((row for row in rows if row["request_role"] == "a_replay"), {})
    first_distractor = next((row for row in rows if str(row.get("request_role", "")).startswith("distractor_")), {})
    first_ok = request_succeeded(first)
    replay_ok = request_succeeded(replay)
    first_latency = maybe_float(first.get("latency_ms")) if first_ok else None
    replay_latency = maybe_float(replay.get("latency_ms")) if replay_ok else None
    latency_delta = None
    speedup = None
    if first_ok and replay_ok and first_latency is not None and replay_latency is not None and replay_latency > 0:
        latency_delta = replay_latency - first_latency
        speedup = first_latency / replay_latency

    replay_ratio = maybe_float(replay.get("cache_reuse_ratio")) if replay_ok else None
    survived: str | bool = ""
    source = "not_available"
    if replay_ratio is not None:
        survived = replay_ratio >= args.survival_cache_reuse_threshold
        source = "response_usage_cached_tokens"
    elif replay_ok and truthy(replay.get("sglang_cache_direct")):
        source = "sglang_cache_events"

    worker_capacity = parse_worker_capacity(worker_runtime_log)
    a_first_prompt_tokens = maybe_int(first.get("prompt_tokens"))
    first_distractor_prompt_tokens = maybe_int(first_distractor.get("prompt_tokens"))
    worker_kv_capacity_tokens = worker_capacity["worker_kv_capacity_tokens"]
    kv_tokens_left_after_a = (
        worker_kv_capacity_tokens - a_first_prompt_tokens
        if worker_kv_capacity_tokens is not None and a_first_prompt_tokens is not None
        else None
    )
    kv_tokens_left_after_a_after_first_distractor = (
        worker_kv_capacity_tokens - a_first_prompt_tokens - first_distractor_prompt_tokens
        if worker_kv_capacity_tokens is not None
        and a_first_prompt_tokens is not None
        and first_distractor_prompt_tokens is not None
        else None
    )

    failed = [row for row in rows if str(row.get("status")) not in {"200", "201"}]
    summary = {
        "run_id": run_id,
        "model": args.model,
        "kv_tier_mode": args.kv_tier_mode,
        "protected_hint_profile": args.protected_hint_profile,
        "distractor_hint_profile": args.distractor_hint_profile,
        "protected_input_len": args.protected_input_len,
        "distractor_input_len": args.distractor_input_len,
        "distractor_count": args.distractor_count,
        "output_len": args.random_output_len,
        "seed": args.seed,
        "a_first_status": first.get("status", ""),
        "a_replay_status": replay.get("status", ""),
        "a_first_latency_ms": round_ms(first_latency),
        "a_replay_latency_ms": round_ms(replay_latency),
        "a_replay_latency_delta_ms": round_ms(latency_delta),
        "a_replay_speedup_ratio": round_ratio(speedup),
        "worker_kv_capacity_tokens": int_or_empty(worker_kv_capacity_tokens),
        "worker_context_len": int_or_empty(worker_capacity["worker_context_len"]),
        "a_first_prompt_tokens": int_or_empty(a_first_prompt_tokens),
        "first_distractor_prompt_tokens": int_or_empty(first_distractor_prompt_tokens),
        "kv_tokens_left_after_a": int_or_empty(kv_tokens_left_after_a),
        "kv_tokens_left_after_a_after_first_distractor": int_or_empty(kv_tokens_left_after_a_after_first_distractor),
        "a_first_agent_hints_priority": int_or_empty(first.get("agent_hints_priority")),
        "a_first_top_level_priority_sent": truthy(first.get("top_level_priority_sent")),
        "a_first_top_level_priority_value": int_or_empty(first.get("top_level_priority_value")),
        "a_first_cached_tokens": int_or_empty(first.get("cached_prompt_tokens")),
        "a_replay_agent_hints_priority": int_or_empty(replay.get("agent_hints_priority")),
        "a_replay_top_level_priority_sent": truthy(replay.get("top_level_priority_sent")),
        "a_replay_top_level_priority_value": int_or_empty(replay.get("top_level_priority_value")),
        "a_replay_cached_tokens": int_or_empty(replay.get("cached_prompt_tokens")),
        "a_replay_cache_reuse_ratio": round_ratio(replay_ratio),
        "a_replay_prompt_tokens": int_or_empty(replay.get("prompt_tokens")),
        "a_first_sglang_cache_events": int_or_empty(first.get("sglang_cache_events")),
        "a_replay_sglang_cache_events": int_or_empty(replay.get("sglang_cache_events")),
        "a_replay_sglang_cache_match_events": int_or_empty(replay.get("sglang_cache_match_events")),
        "a_replay_sglang_cache_semantic_tokens": int_or_empty(replay.get("sglang_cache_semantic_tokens")),
        "a_replay_sglang_cache_direct": truthy(replay.get("sglang_cache_direct")),
        "a_first_sglang_priority_hint_seen": truthy(first.get("sglang_priority_hint_seen")),
        "a_replay_sglang_priority_hint_seen": truthy(replay.get("sglang_priority_hint_seen")),
        "a_first_sglang_scheduler_priority_applied": truthy(first.get("sglang_scheduler_priority_applied")),
        "a_replay_sglang_scheduler_priority_applied": truthy(replay.get("sglang_scheduler_priority_applied")),
        "a_first_sglang_worker_top_level_priority": int_or_empty(first.get("sglang_worker_top_level_priority")),
        "a_replay_sglang_worker_top_level_priority": int_or_empty(replay.get("sglang_worker_top_level_priority")),
        "a_first_sglang_worker_agent_hints_priority": int_or_empty(first.get("sglang_worker_agent_hints_priority")),
        "a_replay_sglang_worker_agent_hints_priority": int_or_empty(replay.get("sglang_worker_agent_hints_priority")),
        "a_survived_cache_threshold": survived,
        "cache_survival_source": source,
        "successful_requests": len(rows) - len(failed),
        "failed_requests": len(failed),
        "sglang_cache_event_log": display_path(cache_event_log),
        "worker_runtime_log": display_path(worker_runtime_log or Path("")),
        "requests_csv": display_path(requests_csv),
    }
    return summary


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# KV Retention Probe Summary",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- model: `{summary['model']}`",
        f"- kv_tier_mode: `{summary['kv_tier_mode']}`",
        f"- protected_hint_profile: `{summary['protected_hint_profile']}`",
        f"- distractor_hint_profile: `{summary['distractor_hint_profile']}`",
        f"- distractor_count: `{summary['distractor_count']}`",
        "",
        "## A Prompt Replay",
        "",
        f"- first status: `{summary['a_first_status']}`",
        f"- replay status: `{summary['a_replay_status']}`",
        f"- first latency ms: `{summary['a_first_latency_ms']}`",
        f"- replay latency ms: `{summary['a_replay_latency_ms']}`",
        f"- replay delta ms: `{summary['a_replay_latency_delta_ms']}`",
        f"- speedup ratio: `{summary['a_replay_speedup_ratio']}`",
        f"- worker kv capacity tokens: `{summary['worker_kv_capacity_tokens']}`",
        f"- worker context length: `{summary['worker_context_len']}`",
        f"- A prompt tokens: `{summary['a_first_prompt_tokens']}`",
        f"- first distractor prompt tokens: `{summary['first_distractor_prompt_tokens']}`",
        f"- kv tokens left after A: `{summary['kv_tokens_left_after_a']}`",
        f"- kv tokens left after A and first distractor: `{summary['kv_tokens_left_after_a_after_first_distractor']}`",
        f"- replay cached tokens: `{summary['a_replay_cached_tokens']}`",
        f"- replay cache reuse ratio: `{summary['a_replay_cache_reuse_ratio']}`",
        f"- replay SGLang cache events: `{summary['a_replay_sglang_cache_events']}`",
        f"- replay SGLang cache match events: `{summary['a_replay_sglang_cache_match_events']}`",
        f"- replay SGLang cache direct attribution: `{summary['a_replay_sglang_cache_direct']}`",
        f"- replay SGLang priority hint seen: `{summary['a_replay_sglang_priority_hint_seen']}`",
        f"- replay SGLang scheduler priority applied: `{summary['a_replay_sglang_scheduler_priority_applied']}`",
        f"- replay SGLang top-level priority: `{summary['a_replay_sglang_worker_top_level_priority']}`",
        f"- replay SGLang agent-hints priority: `{summary['a_replay_sglang_worker_agent_hints_priority']}`",
        f"- survived cache threshold: `{summary['a_survived_cache_threshold']}`",
        "",
        "A positive speedup ratio above 1.000 means the second A request was faster than the first A request.",
        "Replay latency, delta, speedup, and cached-token survival stay blank unless both A requests succeeded.",
        "Cache survival is inferred from response usage cached-token evidence when available.",
        "SGLang cache events are direct runtime evidence when request IDs match.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_id = args.run_id or now_run_id()
    out_root = Path(args.output_root).expanduser()
    if not out_root.is_absolute():
        out_root = REPO_ROOT / out_root
    run_dir = out_root / run_id
    requests_csv = run_dir / "retention_probe_requests.csv"
    summary_csv = run_dir / "retention_probe_summary.csv"
    summary_md = run_dir / "retention_probe_summary.md"
    matrix_path = Path(args.matrix_path).expanduser()
    if not matrix_path.is_absolute():
        matrix_path = REPO_ROOT / matrix_path
    cache_event_log = Path(args.cache_event_log).expanduser()
    if not cache_event_log.is_absolute():
        cache_event_log = REPO_ROOT / cache_event_log
    worker_runtime_log = Path(args.worker_runtime_log).expanduser() if args.worker_runtime_log else None
    if isinstance(worker_runtime_log, Path) and not worker_runtime_log.is_absolute():
        worker_runtime_log = REPO_ROOT / worker_runtime_log

    if args.postprocess_only:
        rows = read_csv_rows(requests_csv)
        if not rows:
            raise SystemExit(f"No existing request rows found for postprocess-only mode: {requests_csv}")
    else:
        protected_prompt = make_prompt(role="protected_A", target_len=args.protected_input_len, seed=args.seed)
        rows: list[dict[str, Any]] = []

        sequence: list[tuple[str, str, str]] = [
            ("a_first", protected_prompt, args.protected_hint_profile),
        ]
        for idx in range(args.distractor_count):
            distractor = make_prompt(
                role=f"distractor_{idx:04d}",
                target_len=args.distractor_input_len,
                seed=args.seed,
            )
            sequence.append((f"distractor_{idx:04d}", distractor, args.distractor_hint_profile))
        sequence.append(("a_replay", protected_prompt, args.protected_hint_profile))

        print(f"KV retention probe run_id={run_id}")
        print(f"model={args.model}")
        print(f"prompt_generator_version={PROMPT_GENERATOR_VERSION}")
        print(f"requests={len(sequence)} protected_hint_profile={args.protected_hint_profile}")

        for sequence_index, (request_role, prompt, hint_profile) in enumerate(sequence):
            print(f"[{sequence_index + 1}/{len(sequence)}] {request_role} hint_profile={hint_profile}", flush=True)
            row = send_probe_request(
                args=args,
                run_id=run_id,
                sequence_index=sequence_index,
                request_role=request_role,
                prompt=prompt,
                hint_profile=hint_profile,
            )
            rows.append(row)
            if row["error"]:
                print(f"  error status={row['status']} {row['error'][:200]}", file=sys.stderr, flush=True)
                if args.stop_on_error:
                    break
            else:
                print(
                    f"  status={row['status']} latency_ms={row['latency_ms']} "
                    f"cached={row['cached_prompt_tokens']} reuse={row['cache_reuse_ratio']}",
                    flush=True,
                )

    attach_cache_events(rows, cache_event_log, worker_runtime_log)
    write_csv(requests_csv, rows, REQUEST_COLUMNS)
    summary = build_summary(
        args=args,
        run_id=run_id,
        rows=rows,
        requests_csv=requests_csv,
        cache_event_log=cache_event_log,
        worker_runtime_log=worker_runtime_log,
    )
    write_csv(summary_csv, [summary], SUMMARY_COLUMNS)
    if not args.skip_matrix_write:
        if args.append_matrix:
            append_matrix(matrix_path, summary, SUMMARY_COLUMNS)
        else:
            write_csv(matrix_path, [summary], SUMMARY_COLUMNS)
    write_summary_md(summary_md, summary)

    print(f"Request rows: {requests_csv}")
    print(f"Run summary:  {summary_csv}")
    print(f"Summary md:   {summary_md}")
    print(f"Matrix:       {matrix_path}")
    return 1 if summary["failed_requests"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
