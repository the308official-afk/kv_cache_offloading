#!/usr/bin/env python3
"""Run a synthetic speculative-prefill probe against an OpenAI-compatible endpoint."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_ROOT = REPO_ROOT / "experiments" / "reports" / "speculative_prefill"
RUNTIME_JSON_PREFIX = "[RUNTIME_JSON]"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

REQUEST_COLUMNS = [
    "run_id",
    "arm",
    "request",
    "spec_prefill",
    "request_id",
    "hint_probe_id",
    "latency_ms",
    "status",
    "error",
    "prompt_tokens",
    "cached_tokens",
    "reuse_ratio",
    "worker_hint",
    "runtime_match",
    "worker_req_ts",
    "worker_attach_ts",
    "worker_done_ts",
    "worker_queue_ms",
    "worker_service_ms",
    "worker_total_ms",
]

MATRIX_COLUMNS = [
    "run_id",
    "arm",
    "spec_prefill",
    "turn_a_ms",
    "turn_b_ms",
    "turn_b_latency_gain_ms",
    "turn_b_cached",
    "turn_b_reuse",
    "hint_status",
    "prefill_evidence_status",
    "prefill_wrap",
    "prefill_spawned",
    "prefill_sent",
    "prefill_done",
    "prefill_failed",
    "prefill_target_seen",
    "anonymous_warmup_seen",
    "prefill_tokens",
    "effect_status",
]

SUMMARY_COLUMNS = [
    "run_id",
    "model",
    "mode",
    "turn_a_words",
    "turn_b_words",
    "output_tokens",
    "warmup_wait_ms",
    "control_turn_b_ms",
    "protected_turn_b_ms",
    "turn_b_latency_delta_ms",
    "control_turn_b_cached",
    "protected_turn_b_cached",
    "turn_b_cached_delta",
    "protected_prefill_evidence_status",
    "protected_prefill_done",
    "protected_prefill_target_seen",
    "protected_anonymous_warmup_seen",
    "effect_status",
]


@dataclass(frozen=True)
class ArmSpec:
    arm: str
    spec_prefill: bool


def now_run_id() -> str:
    return f"speculative_prefill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frontend-url",
        default=f"http://127.0.0.1:{os.environ.get('DYNAMO_FRONTEND_PORT', '8000')}/v1/chat/completions",
    )
    parser.add_argument("--model", default=os.environ.get("MODEL_NAME", ""))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--worker-runtime-log", default="")
    parser.add_argument("--postprocess-only", action="store_true")
    parser.add_argument(
        "--attribution-mode",
        default=os.environ.get("SPEC_PREFILL_ATTRIBUTION_MODE", "precise"),
        choices=("light", "precise"),
    )
    parser.add_argument(
        "--request-context-mode",
        default=os.environ.get("SPEC_PREFILL_REQUEST_CONTEXT_MODE", "auto"),
        choices=("auto", "force", "disable"),
    )
    parser.add_argument(
        "--turn-a-words",
        type=int,
        default=int(os.environ.get("SPEC_PREFILL_TURN_A_WORDS", "4000")),
    )
    parser.add_argument(
        "--turn-b-words",
        type=int,
        default=int(os.environ.get("SPEC_PREFILL_TURN_B_WORDS", "512")),
    )
    parser.add_argument(
        "--output-len-tokens",
        type=int,
        default=int(os.environ.get("SPEC_PREFILL_OUTPUT_TOKENS", "64")),
    )
    parser.add_argument(
        "--warmup-wait-ms",
        type=int,
        default=int(os.environ.get("SPEC_PREFILL_WARMUP_WAIT_MS", "500")),
    )
    parser.add_argument("--seed", type=int, default=int(os.environ.get("SPEC_PREFILL_SEED", "42")))
    parser.add_argument("--request-timeout", type=float, default=float(os.environ.get("REQUEST_TIMEOUT", "600")))
    args = parser.parse_args()
    if not args.model:
        parser.error("--model is required or MODEL_NAME must be set")
    return args


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def round_ms(value: float | None) -> int | str:
    if value is None:
        return ""
    return int(round(value))


def round_ratio(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}"


def maybe_int(value: Any) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


def request_context_unsupported(status: int, error: str) -> bool:
    if status != 400 or not error:
        return False
    normalized = error.lower()
    return "request_context" in normalized and "unknown field" in normalized


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
    line_ts = None
    prefix = prefix.strip()
    if prefix:
        first = prefix.split(" ", 1)[0]
        if "T" in first:
            line_ts = first
    return parsed if isinstance(parsed, dict) else None, line_ts


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
    return {}


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


def usage_prompt_tokens(usage: dict[str, Any]) -> tuple[int | None, int | None]:
    prompt_tokens = maybe_int(
        usage.get("prompt_tokens") if "prompt_tokens" in usage else usage.get("input_tokens")
    )
    cached_tokens = None
    for path in (
        ("prompt_tokens_details", "cached_tokens"),
        ("prompt_token_details", "cached_tokens"),
        ("input_tokens_details", "cached_tokens"),
    ):
        current: Any = usage
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        cached_tokens = maybe_int(current)
        if cached_tokens is not None:
            break
    if cached_tokens is None:
        cached_tokens = maybe_int(usage.get("cached_prompt_tokens") or usage.get("cached_tokens"))
    return prompt_tokens, cached_tokens


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


def response_text_from_chat_completion(response_json: dict[str, Any] | None) -> str:
    if not isinstance(response_json, dict):
        return ""
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "".join(parts)
    return ""


def make_turn_a_prompt(*, arm: str, target_len: int, seed: int) -> str:
    marker = short_hash(f"turn_a:{arm}:{seed}:{target_len}")
    header = (
        f"Speculative prefill probe arm {arm}. "
        f"Marker {marker}. "
        "Reply in one short sentence. "
        "The repeated words below are just to create a long prefix. "
    )
    words = [f"{arm}_prefix"] * target_len
    for idx in range(0, target_len, 256):
        words[idx] = f"{arm}_marker_{idx}"
    return header + " ".join(words)


def make_turn_b_user_prompt(*, arm: str, target_len: int, seed: int) -> str:
    marker = short_hash(f"turn_b:{arm}:{seed}:{target_len}")
    header = (
        f"Follow-up request for arm {arm}. "
        f"Marker {marker}. "
        "Answer briefly. "
    )
    words = [f"{arm}_followup"] * target_len
    for idx in range(0, target_len, 128):
        words[idx] = f"{arm}_followup_marker_{idx}"
    return header + " ".join(words)


def request_context(*, run_id: str, arm: str, request_role: str, step_index: int, prompt_hash: str) -> dict[str, Any]:
    return {
        "request_id": f"{run_id}::{arm}::{request_role}",
        "parent_run_id": run_id,
        "task_instance_id": "synthetic_speculative_prefill_probe",
        "phase": "speculative_prefill_probe",
        "step_index": step_index,
        "step_title": request_role,
        "app_variant": "synthetic_speculative_prefill_probe",
        "arm": arm,
        "prompt_hash": prompt_hash,
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
        "arm",
        "prompt_hash",
    ):
        value = context.get(key)
        if value in (None, ""):
            continue
        annotations.append(f"{key}:{value}")
    return annotations


def build_agent_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_type_id": "synthetic_speculative_prefill_probe:v1",
        "session_id": str(context.get("parent_run_id") or "speculative_prefill_probe"),
        "trajectory_id": str(context.get("request_id") or ""),
        "parent_trajectory_id": str(context.get("parent_run_id") or ""),
    }


def build_agent_hints(
    *,
    spec_prefill: bool,
    hint_probe_id: str,
    target_request_id: str,
    target_hint_probe_id: str,
) -> dict[str, Any]:
    return {
        "speculative_prefill": spec_prefill,
        "hint_probe_id": hint_probe_id,
        "spec_prefill_target_request_id": target_request_id,
        "spec_prefill_target_hint_probe_id": target_hint_probe_id,
    }


def send_request(
    *,
    args: argparse.Namespace,
    run_id: str,
    arm: str,
    request_name: str,
    messages: list[dict[str, str]],
    step_index: int,
    spec_prefill: bool,
    target_request_id: str,
    target_hint_probe_id: str,
) -> dict[str, Any]:
    prompt_hash = short_hash(json.dumps(messages, sort_keys=True))
    context = request_context(
        run_id=run_id,
        arm=arm,
        request_role=request_name,
        step_index=step_index,
        prompt_hash=prompt_hash,
    )
    hint_probe_id = f"{run_id}::{arm}::{request_name}"
    hints = build_agent_hints(
        spec_prefill=spec_prefill,
        hint_probe_id=hint_probe_id,
        target_request_id=target_request_id,
        target_hint_probe_id=target_hint_probe_id,
    )
    payload: dict[str, Any] = {
        "model": args.model,
        "messages": messages,
        "max_tokens": args.output_len_tokens,
        "temperature": 0,
        "nvext": {
            "agent_context": build_agent_context(context),
            "annotations": build_annotations(context),
            "agent_hints": hints,
        },
    }

    request_context_sent = args.request_context_mode != "disable"
    if request_context_sent:
        payload["nvext"]["request_context"] = context

    start_dt = utc_now()
    start = time.perf_counter()
    status, response_json, error = post_json(args.frontend_url, payload, timeout=args.request_timeout)
    latency_ms = (time.perf_counter() - start) * 1000
    end_dt = utc_now()
    request_context_fallback_used = False
    if (
        request_context_sent
        and args.request_context_mode == "auto"
        and request_context_unsupported(status, error)
    ):
        payload["nvext"].pop("request_context", None)
        request_context_sent = False
        request_context_fallback_used = True
        start_dt = utc_now()
        start = time.perf_counter()
        status, response_json, error = post_json(args.frontend_url, payload, timeout=args.request_timeout)
        latency_ms = (time.perf_counter() - start) * 1000
        end_dt = utc_now()

    usage = response_json.get("usage", {}) if isinstance(response_json, dict) else {}
    prompt_tokens, cached_tokens = usage_prompt_tokens(usage if isinstance(usage, dict) else {})
    reuse_ratio = None
    if prompt_tokens and cached_tokens is not None:
        reuse_ratio = cached_tokens / prompt_tokens

    return {
        "run_id": run_id,
        "arm": arm,
        "request": request_name,
        "spec_prefill": spec_prefill,
        "request_id": context["request_id"],
        "hint_probe_id": hint_probe_id,
        "latency_ms": round_ms(latency_ms),
        "status": status,
        "error": error,
        "prompt_tokens": prompt_tokens if prompt_tokens is not None else "",
        "cached_tokens": cached_tokens if cached_tokens is not None else "",
        "reuse_ratio": round_ratio(reuse_ratio),
        "response_text": response_text_from_chat_completion(response_json),
        "request_context_sent": request_context_sent,
        "request_context_fallback_used": request_context_fallback_used,
        "worker_hint": "",
        "runtime_match": False,
        "worker_req_ts": "",
        "worker_attach_ts": "",
        "worker_done_ts": "",
        "worker_queue_ms": "",
        "worker_service_ms": "",
        "worker_total_ms": "",
        "client_send_ts": start_dt.isoformat(),
        "client_done_ts": end_dt.isoformat(),
    }


def run_probe(args: argparse.Namespace, run_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    arms = [ArmSpec("control", False), ArmSpec("protected", True)]
    for idx, arm in enumerate(arms):
        turn_a_prompt = make_turn_a_prompt(arm=arm.arm, target_len=args.turn_a_words, seed=args.seed + idx)
        turn_b_user_prompt = make_turn_b_user_prompt(arm=arm.arm, target_len=args.turn_b_words, seed=args.seed + 100 + idx)
        target_request_id = f"{run_id}::{arm.arm}::turn_b"
        target_hint_probe_id = f"{run_id}::{arm.arm}::turn_b"
        turn_a = send_request(
            args=args,
            run_id=run_id,
            arm=arm.arm,
            request_name="turn_a",
            messages=[{"role": "user", "content": turn_a_prompt}],
            step_index=0,
            spec_prefill=arm.spec_prefill,
            target_request_id=target_request_id,
            target_hint_probe_id=target_hint_probe_id,
        )
        rows.append(turn_a)
        if int(turn_a.get("status") or 0) < 200 or int(turn_a.get("status") or 0) >= 300:
            rows.append(
                {
                    "run_id": run_id,
                    "arm": arm.arm,
                    "request": "turn_b",
                    "spec_prefill": arm.spec_prefill,
                    "request_id": target_request_id,
                    "hint_probe_id": target_hint_probe_id,
                    "latency_ms": "",
                    "status": 0,
                    "error": "skipped_because_turn_a_failed",
                    "prompt_tokens": "",
                    "cached_tokens": "",
                    "reuse_ratio": "",
                    "response_text": "",
                    "request_context_sent": turn_a["request_context_sent"],
                    "request_context_fallback_used": turn_a["request_context_fallback_used"],
                    "worker_hint": "",
                    "runtime_match": False,
                    "worker_req_ts": "",
                    "worker_attach_ts": "",
                    "worker_done_ts": "",
                    "worker_queue_ms": "",
                    "worker_service_ms": "",
                    "worker_total_ms": "",
                    "client_send_ts": "",
                    "client_done_ts": "",
                }
            )
            continue

        if args.warmup_wait_ms > 0:
            time.sleep(args.warmup_wait_ms / 1000.0)

        turn_b = send_request(
            args=args,
            run_id=run_id,
            arm=arm.arm,
            request_name="turn_b",
            messages=[
                {"role": "user", "content": turn_a_prompt},
                {"role": "assistant", "content": turn_a.get("response_text") or ""},
                {"role": "user", "content": turn_b_user_prompt},
            ],
            step_index=1,
            spec_prefill=arm.spec_prefill,
            target_request_id=target_request_id,
            target_hint_probe_id=target_hint_probe_id,
        )
        rows.append(turn_b)
    return rows


def extract_runtime_records(worker_runtime_log: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    request_records: dict[str, dict[str, Any]] = {}
    spec_events: list[dict[str, Any]] = []
    if not worker_runtime_log.exists():
        return request_records, spec_events
    for raw_line in worker_runtime_log.read_text(encoding="utf-8", errors="replace").splitlines():
        record, line_ts = parse_runtime_json_payload(clean_log_line(raw_line))
        if not isinstance(record, dict):
            continue
        event_type = str(record.get("event_type") or "")
        if event_type.startswith("worker.decode.") or event_type.startswith("worker.prefill."):
            request_context = runtime_request_context(record)
            request_id = request_context.get("request_id") or record.get("external_request_id")
            if not isinstance(request_id, str) or not request_id:
                continue
            info = request_records.setdefault(
                request_id,
                {
                    "request_id": request_id,
                    "received_dt": None,
                    "attached_dt": None,
                    "completed_dt": None,
                    "spec_prefill_hint": None,
                    "hint_probe_id": "",
                    "has_request_context": False,
                    "prompt_tokens": None,
                    "cached_tokens": None,
                },
            )
            ts = parse_dt(str(record.get("timestamp") or line_ts or ""))
            if event_type.endswith("request_received") and info["received_dt"] is None:
                info["received_dt"] = ts
            elif event_type.endswith("request_attached") and info["attached_dt"] is None:
                info["attached_dt"] = ts
            elif event_type.endswith("request_completed"):
                info["completed_dt"] = ts
            hints = runtime_agent_hints(record)
            hint_value = hints.get("speculative_prefill")
            if isinstance(hint_value, bool):
                info["spec_prefill_hint"] = hint_value
            hint_probe_id = record.get("hint_probe_id") or hints.get("hint_probe_id")
            if isinstance(hint_probe_id, str) and hint_probe_id:
                info["hint_probe_id"] = hint_probe_id
            request_context_present = bool(runtime_request_context(record))
            if request_context_present:
                info["has_request_context"] = True
            if event_type.endswith("request_completed"):
                usage = record.get("completion_usage")
                if isinstance(usage, dict):
                    prompt_tokens, cached_tokens = usage_prompt_tokens(usage)
                    if prompt_tokens is not None:
                        info["prompt_tokens"] = prompt_tokens
                    if cached_tokens is not None:
                        info["cached_tokens"] = cached_tokens
        elif event_type.startswith("worker.spec_prefill."):
            if line_ts and "timestamp" not in record:
                record["timestamp"] = line_ts
            spec_events.append(record)
    return request_records, spec_events


def attach_worker_runtime(rows: list[dict[str, Any]], request_records: dict[str, dict[str, Any]]) -> None:
    for row in rows:
        info = request_records.get(str(row.get("request_id")))
        if not info:
            continue
        row["runtime_match"] = True
        row["worker_hint"] = info.get("spec_prefill_hint", "")
        received_dt = info.get("received_dt")
        attached_dt = info.get("attached_dt")
        completed_dt = info.get("completed_dt")
        row["worker_req_ts"] = received_dt.isoformat() if isinstance(received_dt, datetime) else ""
        row["worker_attach_ts"] = attached_dt.isoformat() if isinstance(attached_dt, datetime) else ""
        row["worker_done_ts"] = completed_dt.isoformat() if isinstance(completed_dt, datetime) else ""
        row["worker_queue_ms"] = ms_between(received_dt, attached_dt)
        row["worker_service_ms"] = ms_between(attached_dt, completed_dt)
        row["worker_total_ms"] = ms_between(received_dt, completed_dt)


def infer_anonymous_warmup(
    request_records: dict[str, dict[str, Any]],
    *,
    turn_a: dict[str, Any],
    turn_b: dict[str, Any],
) -> dict[str, Any]:
    turn_a_done = parse_dt(str(turn_a.get("worker_done_ts") or ""))
    turn_b_req = parse_dt(str(turn_b.get("worker_req_ts") or ""))
    turn_a_prompt_tokens = maybe_int(turn_a.get("prompt_tokens"))
    turn_a_id = str(turn_a.get("request_id") or "")
    turn_b_id = str(turn_b.get("request_id") or "")

    if turn_a_done is None or turn_b_req is None:
        return {"seen": False, "count": 0}

    candidates: list[dict[str, Any]] = []
    for info in request_records.values():
        request_id = str(info.get("request_id") or "")
        if not request_id or request_id in {turn_a_id, turn_b_id}:
            continue
        if info.get("has_request_context"):
            continue
        if info.get("hint_probe_id"):
            continue
        if info.get("spec_prefill_hint") is not None:
            continue
        received_dt = info.get("received_dt")
        completed_dt = info.get("completed_dt")
        if not isinstance(received_dt, datetime) or not isinstance(completed_dt, datetime):
            continue
        if received_dt < turn_a_done or completed_dt > turn_b_req:
            continue
        prompt_tokens = maybe_int(info.get("prompt_tokens"))
        cached_tokens = maybe_int(info.get("cached_tokens"))
        if prompt_tokens is None or cached_tokens is None or cached_tokens <= 0:
            continue
        if turn_a_prompt_tokens is not None and prompt_tokens + 256 < turn_a_prompt_tokens:
            continue
        candidates.append(info)

    return {"seen": bool(candidates), "count": len(candidates)}


def arm_prefill_status(
    events: list[dict[str, Any]],
    request_records: dict[str, dict[str, Any]],
    *,
    turn_a: dict[str, Any],
    turn_b: dict[str, Any],
) -> dict[str, Any]:
    turn_a_id = str(turn_a.get("request_id") or "")
    turn_b_id = str(turn_b.get("request_id") or "")
    matching = [
        event
        for event in events
        if event.get("request_id") == turn_a_id
        or event.get("spec_prefill_target_request_id") == turn_b_id
    ]
    event_types = {str(event.get("event_type") or "") for event in matching}
    prompt_tokens = ""
    for event in matching:
        value = maybe_int(event.get("prefill_prompt_tokens"))
        if value is not None:
            prompt_tokens = value
            break
    wrap_event = next(
        (event for event in matching if str(event.get("event_type") or "") == "worker.spec_prefill.wrap_checked"),
        None,
    )
    wrap_status = "missing"
    if isinstance(wrap_event, dict):
        wrap_status = "on" if truthy(wrap_event.get("enabled")) else "off"
    anonymous_warmup = infer_anonymous_warmup(
        request_records,
        turn_a=turn_a,
        turn_b=turn_b,
    )
    evidence_status = "hint_missing"
    if "worker.spec_prefill.prefill_failed" in event_types:
        evidence_status = "prefill_failed"
    elif (
        "worker.spec_prefill.prefill_completed" in event_types
        or "worker.spec_prefill.prefill_sent" in event_types
        or "worker.spec_prefill.task_spawned" in event_types
    ):
        evidence_status = "direct_prefill_seen"
    elif anonymous_warmup["seen"]:
        evidence_status = "inferred_prefill_seen"
    elif truthy(turn_a.get("worker_hint")) or truthy(turn_b.get("worker_hint")):
        evidence_status = "hint_seen_no_prefill_evidence"
    return {
        "prefill_evidence_status": evidence_status,
        "prefill_wrap": wrap_status,
        "prefill_spawned": "worker.spec_prefill.task_spawned" in event_types,
        "prefill_sent": "worker.spec_prefill.prefill_sent" in event_types,
        "prefill_done": "worker.spec_prefill.prefill_completed" in event_types,
        "prefill_failed": "worker.spec_prefill.prefill_failed" in event_types,
        "prefill_target_seen": any(
            str(event.get("spec_prefill_target_request_id") or "") == turn_b_id for event in matching
        ),
        "anonymous_warmup_seen": anonymous_warmup["seen"],
        "prefill_tokens": prompt_tokens,
    }


def build_matrix_rows(
    rows: list[dict[str, Any]],
    request_records: dict[str, dict[str, Any]],
    spec_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matrix_rows: list[dict[str, Any]] = []
    control_turn_b = next(
        (row for row in rows if row.get("arm") == "control" and row.get("request") == "turn_b"),
        {},
    )
    control_turn_b_ms = maybe_int(control_turn_b.get("latency_ms"))
    for arm in ("control", "protected"):
        arm_rows = [row for row in rows if row.get("arm") == arm]
        turn_a = next((row for row in arm_rows if row.get("request") == "turn_a"), {})
        turn_b = next((row for row in arm_rows if row.get("request") == "turn_b"), {})
        prefill = arm_prefill_status(
            spec_events,
            request_records,
            turn_a=turn_a,
            turn_b=turn_b,
        )
        hint_value = turn_a.get("worker_hint")
        if hint_value is True:
            hint_status = "on"
        elif hint_value is False:
            hint_status = "off"
        elif turn_a.get("runtime_match"):
            hint_status = "missing"
        else:
            hint_status = "no_runtime"
        turn_b_cached = maybe_int(turn_b.get("cached_tokens"))
        turn_b_ms = maybe_int(turn_b.get("latency_ms"))
        latency_gain_ms = (
            control_turn_b_ms - turn_b_ms
            if control_turn_b_ms is not None and turn_b_ms is not None
            else None
        )
        effect_status = "baseline_off"
        prefill_evidence_status = prefill["prefill_evidence_status"]
        if arm == "protected":
            if prefill["prefill_evidence_status"] == "prefill_failed":
                effect_status = "prefill_failed"
            elif prefill["prefill_evidence_status"] == "direct_prefill_seen" and (latency_gain_ms or 0) > 0:
                effect_status = "faster_direct"
            elif prefill["prefill_evidence_status"] == "inferred_prefill_seen" and (latency_gain_ms or 0) > 0:
                effect_status = "faster_inferred"
            elif prefill["prefill_evidence_status"] == "direct_prefill_seen":
                effect_status = "direct_no_visible_gain"
            elif prefill["prefill_evidence_status"] == "inferred_prefill_seen":
                effect_status = "inferred_no_visible_gain"
            elif prefill["prefill_evidence_status"] == "hint_seen_no_prefill_evidence":
                effect_status = "hint_seen_no_prefill_evidence"
            elif hint_status == "missing":
                effect_status = "hint_missing"
            elif hint_status == "no_runtime":
                effect_status = "no_runtime"
            elif prefill["prefill_sent"]:
                effect_status = "sent_no_visible_gain"
            elif prefill["prefill_failed"]:
                effect_status = "prefill_failed"
            else:
                effect_status = "no_prefill_seen"
        else:
            prefill_evidence_status = "baseline_off"
        matrix_rows.append(
            {
                "run_id": turn_a.get("run_id") or turn_b.get("run_id") or "",
                "arm": arm,
                "spec_prefill": turn_a.get("spec_prefill", turn_b.get("spec_prefill", "")),
                "turn_a_ms": turn_a.get("latency_ms", ""),
                "turn_b_ms": turn_b.get("latency_ms", ""),
                "turn_b_latency_gain_ms": latency_gain_ms if latency_gain_ms is not None else "",
                "turn_b_cached": turn_b.get("cached_tokens", ""),
                "turn_b_reuse": turn_b.get("reuse_ratio", ""),
                "hint_status": hint_status,
                "prefill_evidence_status": prefill_evidence_status,
                "prefill_wrap": prefill["prefill_wrap"],
                "prefill_spawned": prefill["prefill_spawned"],
                "prefill_sent": prefill["prefill_sent"],
                "prefill_done": prefill["prefill_done"],
                "prefill_failed": prefill["prefill_failed"],
                "prefill_target_seen": prefill["prefill_target_seen"],
                "anonymous_warmup_seen": prefill["anonymous_warmup_seen"],
                "prefill_tokens": prefill["prefill_tokens"],
                "effect_status": effect_status,
            }
        )
    return matrix_rows


def build_summary(args: argparse.Namespace, run_id: str, matrix_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_arm = {str(row.get("arm")): row for row in matrix_rows}
    control = by_arm.get("control", {})
    protected = by_arm.get("protected", {})
    control_turn_b_ms = maybe_int(control.get("turn_b_ms"))
    protected_turn_b_ms = maybe_int(protected.get("turn_b_ms"))
    control_turn_b_cached = maybe_int(control.get("turn_b_cached"))
    protected_turn_b_cached = maybe_int(protected.get("turn_b_cached"))
    latency_delta = (
        control_turn_b_ms - protected_turn_b_ms
        if control_turn_b_ms is not None and protected_turn_b_ms is not None
        else None
    )
    cached_delta = (
        protected_turn_b_cached - control_turn_b_cached
        if control_turn_b_cached is not None and protected_turn_b_cached is not None
        else None
    )
    effect_status = str(protected.get("effect_status") or "no")
    return {
        "run_id": run_id,
        "model": args.model,
        "mode": args.attribution_mode,
        "turn_a_words": args.turn_a_words,
        "turn_b_words": args.turn_b_words,
        "output_tokens": args.output_len_tokens,
        "warmup_wait_ms": args.warmup_wait_ms,
        "control_turn_b_ms": control.get("turn_b_ms", ""),
        "protected_turn_b_ms": protected.get("turn_b_ms", ""),
        "turn_b_latency_delta_ms": latency_delta if latency_delta is not None else "",
        "control_turn_b_cached": control.get("turn_b_cached", ""),
        "protected_turn_b_cached": protected.get("turn_b_cached", ""),
        "turn_b_cached_delta": cached_delta if cached_delta is not None else "",
        "protected_prefill_evidence_status": protected.get("prefill_evidence_status", ""),
        "protected_prefill_done": protected.get("prefill_done", ""),
        "protected_prefill_target_seen": protected.get("prefill_target_seen", ""),
        "protected_anonymous_warmup_seen": protected.get("anonymous_warmup_seen", ""),
        "effect_status": effect_status,
    }


def build_summary_md(summary: dict[str, Any]) -> str:
    lines = [
        f"# Speculative Prefill Probe: {summary['run_id']}",
        "",
        f"- Model: `{summary['model']}`",
        f"- Attribution mode: `{summary['mode']}`",
        f"- Turn A words: `{summary['turn_a_words']}`",
        f"- Turn B words: `{summary['turn_b_words']}`",
        f"- Output tokens: `{summary['output_tokens']}`",
        f"- Warmup wait ms: `{summary['warmup_wait_ms']}`",
        "",
        "## Result",
        "",
        f"- Control turn B latency ms: `{summary['control_turn_b_ms']}`",
        f"- Protected turn B latency ms: `{summary['protected_turn_b_ms']}`",
        f"- Turn B latency delta ms (control - protected): `{summary['turn_b_latency_delta_ms']}`",
        f"- Control turn B cached tokens: `{summary['control_turn_b_cached']}`",
        f"- Protected turn B cached tokens: `{summary['protected_turn_b_cached']}`",
        f"- Turn B cached-token delta (protected - control): `{summary['turn_b_cached_delta']}`",
        f"- Protected prefill evidence status: `{summary['protected_prefill_evidence_status']}`",
        f"- Protected prefill completed: `{summary['protected_prefill_done']}`",
        f"- Protected target seen in prefill events: `{summary['protected_prefill_target_seen']}`",
        f"- Protected anonymous warmup seen: `{summary['protected_anonymous_warmup_seen']}`",
        f"- Overall effect verdict: `{summary['effect_status']}`",
        "",
    ]
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def output_paths(root: Path, run_id: str) -> dict[str, Path]:
    run_dir = root / run_id
    return {
        "run_dir": run_dir,
        "requests_csv": run_dir / "speculative_prefill_requests.csv",
        "matrix_csv": run_dir / "speculative_prefill_matrix.csv",
        "summary_csv": run_dir / "speculative_prefill_summary.csv",
        "summary_md": run_dir / "speculative_prefill_summary.md",
        "latest_requests_csv": root.parent / "speculative_prefill_requests.csv",
        "latest_matrix_csv": root.parent / "speculative_prefill_matrix.csv",
        "latest_summary_csv": root.parent / "speculative_prefill_summary.csv",
        "latest_summary_md": root.parent / "speculative_prefill_summary.md",
        "latest_named_requests_csv": root.parent / "latest_speculative_prefill_requests.csv",
        "latest_named_matrix_csv": root.parent / "latest_speculative_prefill_matrix.csv",
        "latest_named_summary_csv": root.parent / "latest_speculative_prefill_summary.csv",
        "latest_named_summary_md": root.parent / "latest_speculative_prefill_summary.md",
        "latest_named_run_txt": root.parent / "latest_speculative_prefill_run.txt",
    }


def save_outputs(paths: dict[str, Path], request_rows: list[dict[str, Any]], matrix_rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    write_csv(paths["requests_csv"], request_rows, REQUEST_COLUMNS)
    write_csv(paths["matrix_csv"], matrix_rows, MATRIX_COLUMNS)
    write_csv(paths["summary_csv"], [summary], SUMMARY_COLUMNS)
    paths["summary_md"].write_text(build_summary_md(summary), encoding="utf-8")

    for source_key, latest_key in (
        ("requests_csv", "latest_requests_csv"),
        ("matrix_csv", "latest_matrix_csv"),
        ("summary_csv", "latest_summary_csv"),
        ("summary_md", "latest_summary_md"),
        ("requests_csv", "latest_named_requests_csv"),
        ("matrix_csv", "latest_named_matrix_csv"),
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
                f"matrix_csv={paths['matrix_csv']}",
                f"summary_csv={paths['summary_csv']}",
                f"summary_md={paths['summary_md']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def load_rows_for_postprocess(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            row["spec_prefill"] = str(row.get("spec_prefill", "")).lower() == "true"
            row["runtime_match"] = str(row.get("runtime_match", "")).lower() == "true"
            rows.append(row)
    return rows


def main() -> int:
    args = parse_args()
    run_id = args.run_id or now_run_id()
    out_root = Path(args.output_root).resolve()
    paths = output_paths(out_root, run_id)
    worker_runtime_log = Path(args.worker_runtime_log).resolve() if args.worker_runtime_log else None

    if args.postprocess_only:
        request_rows = load_rows_for_postprocess(paths["requests_csv"])
    else:
        request_rows = run_probe(args, run_id)
        write_csv(paths["requests_csv"], request_rows, REQUEST_COLUMNS)

    request_records: dict[str, dict[str, Any]] = {}
    spec_events: list[dict[str, Any]] = []
    if isinstance(worker_runtime_log, Path) and worker_runtime_log.exists():
        request_records, spec_events = extract_runtime_records(worker_runtime_log)
        attach_worker_runtime(request_rows, request_records)

    matrix_rows = build_matrix_rows(request_rows, request_records, spec_events)
    summary = build_summary(args, run_id, matrix_rows)
    save_outputs(paths, request_rows, matrix_rows, summary)

    print(f"Run dir: {paths['run_dir']}")
    print(f"Requests CSV: {paths['requests_csv']}")
    print(f"Matrix CSV: {paths['matrix_csv']}")
    print(f"Summary CSV: {paths['summary_csv']}")
    print(f"Summary MD: {paths['summary_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
