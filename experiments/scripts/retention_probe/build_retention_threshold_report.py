#!/usr/bin/env python3
"""Aggregate retention-probe sweep batches into eviction-threshold reports."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--progress-csv", required=True)
    parser.add_argument("--out-matrix", required=True)
    parser.add_argument("--out-comparison", required=True)
    parser.add_argument("--out-summary-md", required=True)
    parser.add_argument("--control-hint-profile", default="none")
    parser.add_argument("--match-event-min", type=int, default=1)
    parser.add_argument("--min-speedup-ratio", type=float, default=1.05)
    parser.add_argument("--min-latency-gain-ms", type=float, default=100.0)
    parser.add_argument("--sweep-status", choices=("partial", "complete"), default="partial")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    number = as_float(value)
    return int(number) if number is not None else None


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def request_succeeded(status: Any) -> bool:
    return str(status).strip() in {"200", "201"}


def round_ms(value: float | None) -> str:
    if value is None:
        return ""
    return str(int(round(value)))


def round_ratio(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}"


def clean_log_line(line: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", line)


RUNTIME_JSON_PREFIX = "[RUNTIME_JSON]"
EXPECTED_HINT_KEYS = {
    "agent_phase",
    "cache_retention_priority",
    "context_type",
    "expected_output_tokens",
    "hint_probe_id",
    "hint_profile",
    "latency_sensitivity",
    "phase_sequence_index",
    "priority",
    "program_id",
    "retention_probe_role",
    "reuse_likelihood",
}


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


def request_rows_by_role(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    rows = read_csv(path)
    return {
        row.get("request_role", ""): row
        for row in rows
        if row.get("request_role")
    }


def load_batch_summary_rows(batch_matrix: Path) -> list[dict[str, str]]:
    summaries = read_csv(batch_matrix)
    if summaries:
        return summaries

    batch_progress = batch_matrix.parent / "retention_probe_progress.csv"
    progress_rows = read_csv(batch_progress)
    fallback_rows: list[dict[str, str]] = []
    for progress in progress_rows:
        summary_path = Path(progress.get("summary_csv", ""))
        if not summary_path.is_absolute():
            summary_path = Path.cwd() / summary_path
        if not summary_path.exists():
            continue
        fallback_rows.extend(read_csv(summary_path))
    return fallback_rows


def summarize_request_priority(
    request_rows: dict[str, dict[str, str]],
    *,
    field: str,
    roles: tuple[str, ...] = ("a_first", "a_replay"),
) -> dict[str, str]:
    relevant = []
    values = []
    for role in roles:
        row = request_rows.get(role, {})
        if not row:
            continue
        relevant.append(role)
        raw = row.get(field, "")
        if str(raw).strip() == "":
            continue
        values.append(f"{role}:{raw}")
    if not relevant:
        status = "missing_requests_csv"
    elif not values:
        status = "none"
    elif len(values) == len(relevant):
        status = "full"
    else:
        status = "partial"
    return {
        "status": status,
        "values": "|".join(values),
    }


def summarize_request_flag(
    request_rows: dict[str, dict[str, str]],
    *,
    field: str,
    roles: tuple[str, ...] = ("a_first", "a_replay"),
) -> dict[str, str]:
    relevant = []
    truthy_roles = []
    for role in roles:
        row = request_rows.get(role, {})
        if not row:
            continue
        relevant.append(role)
        if truthy(row.get(field)):
            truthy_roles.append(role)
    if not relevant:
        status = "missing_requests_csv"
    elif not truthy_roles:
        status = "none"
    elif len(truthy_roles) == len(relevant):
        status = "full"
    else:
        status = "partial"
    return {
        "status": status,
        "values": "|".join(truthy_roles),
    }


def parse_worker_capacity(path: Path) -> dict[str, int | None]:
    if not path.exists():
        return {
            "worker_kv_capacity_tokens": None,
            "worker_context_len": None,
        }
    kv_capacity = None
    context_len = None
    scheduler_re = re.compile(
        r"max_total_num_tokens=(?P<kv>\d+).*context_len=(?P<context>\d+)"
    )
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = scheduler_re.search(raw_line)
        if match:
            kv_capacity = as_int(match.group("kv"))
            context_len = as_int(match.group("context"))
    return {
        "worker_kv_capacity_tokens": kv_capacity,
        "worker_context_len": context_len,
    }


def parse_worker_hint_evidence(
    worker_runtime_log: Path,
    request_rows: dict[str, dict[str, str]],
) -> dict[str, str]:
    protected_rows = [
        row
        for role, row in request_rows.items()
        if role in {"a_first", "a_replay"}
    ]
    protected_request_ids = {
        str(row.get("request_id", "")).strip()
        for row in protected_rows
        if str(row.get("request_id", "")).strip()
    }
    if not protected_request_ids:
        return {
            "worker_hint_status": "missing_runtime_json",
            "worker_hint_keys": "",
            "worker_hint_profile_seen": "",
        }
    if not worker_runtime_log.exists():
        return {
            "worker_hint_status": "missing_runtime_json",
            "worker_hint_keys": "",
            "worker_hint_profile_seen": "",
        }

    seen_request_ids: set[str] = set()
    received_hint_request_ids: set[str] = set()
    top_level_priority_request_ids: set[str] = set()
    union_keys: set[str] = set()
    profiles_seen: set[str] = set()
    top_level_priority_values: dict[str, str] = {}
    missing_expected_keys = False

    for raw_line in worker_runtime_log.read_text(encoding="utf-8", errors="replace").splitlines():
        record = parse_runtime_json_payload(clean_log_line(raw_line))
        if not isinstance(record, dict):
            continue
        request_context = request_context_from_record(record)
        request_id = request_context.get("request_id")
        if not isinstance(request_id, str) or request_id not in protected_request_ids:
            continue
        seen_request_ids.add(request_id)

        agent_hints = record.get("agent_hints")
        if not isinstance(agent_hints, dict):
            agent_hints = None
        if isinstance(agent_hints, dict):
            received_hint_request_ids.add(request_id)
            current_keys = {str(key) for key in agent_hints}
            union_keys.update(current_keys)
            if not EXPECTED_HINT_KEYS.issubset(current_keys):
                missing_expected_keys = True
            hint_profile = agent_hints.get("hint_profile")
            if isinstance(hint_profile, str) and hint_profile:
                profiles_seen.add(hint_profile)

        priority = record.get("priority")
        parsed_priority = as_int(priority)
        if parsed_priority is not None:
            top_level_priority_request_ids.add(request_id)
            top_level_priority_values.setdefault(request_id, str(parsed_priority))

    if not seen_request_ids:
        status = "missing_runtime_json"
        priority_status = "missing_runtime_json"
    elif not received_hint_request_ids:
        status = "none"
    elif received_hint_request_ids == protected_request_ids and not missing_expected_keys:
        status = "full"
    else:
        status = "partial"
    if not seen_request_ids:
        priority_status = "missing_runtime_json"
    elif not top_level_priority_request_ids:
        priority_status = "none"
    elif top_level_priority_request_ids == protected_request_ids:
        priority_status = "full"
    else:
        priority_status = "partial"

    return {
        "worker_hint_status": status,
        "worker_hint_keys": "|".join(sorted(union_keys)),
        "worker_hint_profile_seen": "|".join(sorted(profiles_seen)),
        "worker_top_level_priority_status": priority_status,
        "worker_top_level_priority_values": "|".join(
            f"{role}:{top_level_priority_values[request_rows[role]['request_id']]}"
            for role in ("a_first", "a_replay")
            if role in request_rows
            and request_rows[role].get("request_id") in top_level_priority_values
        ),
    }


def parse_worker_priority_mechanism(worker_runtime_log: Path) -> dict[str, str]:
    if not worker_runtime_log.exists():
        return {
            "worker_priority_scheduling_enabled": "",
            "worker_radix_eviction_policy": "",
            "worker_priority_mechanism_ready": "false",
        }

    scheduling_enabled: bool | None = None
    eviction_policy = ""
    scheduling_re = re.compile(r"enable_priority_scheduling=(True|False)")
    eviction_re = re.compile(r"radix_eviction_policy='([^']+)'")

    for raw_line in worker_runtime_log.read_text(encoding="utf-8", errors="replace").splitlines():
        line = clean_log_line(raw_line)
        if scheduling_enabled is None:
            match = scheduling_re.search(line)
            if match:
                scheduling_enabled = match.group(1) == "True"
        if not eviction_policy:
            match = eviction_re.search(line)
            if match:
                eviction_policy = match.group(1)
        if scheduling_enabled is not None and eviction_policy:
            break

    mechanism_ready = bool(scheduling_enabled) and eviction_policy == "priority"
    return {
        "worker_priority_scheduling_enabled": (
            "true" if scheduling_enabled is True else "false" if scheduling_enabled is False else ""
        ),
        "worker_radix_eviction_policy": eviction_policy,
        "worker_priority_mechanism_ready": "true" if mechanism_ready else "false",
    }


def derived_row(
    *,
    sweep_id: str,
    model: str,
    retention_attribution_mode: str,
    kv_tier_mode: str,
    distractor_count: int,
    retention_probe_id: str,
    summary: dict[str, str],
    control_hint_profile: str,
    match_event_min: int,
    min_speedup_ratio: float,
    min_latency_gain_ms: float,
    sweep_status: str,
) -> dict[str, Any]:
    requests_csv_path = Path(summary.get("requests_csv", ""))
    if not requests_csv_path.is_absolute():
        requests_csv_path = Path.cwd() / requests_csv_path
    request_rows = request_rows_by_role(requests_csv_path)
    sent_priority = summarize_request_priority(request_rows, field="top_level_priority_value")
    hint_priority = summarize_request_priority(request_rows, field="agent_hints_priority")
    attempted_priority = summarize_request_flag(request_rows, field="top_level_priority_attempted")
    fallback_priority = summarize_request_flag(request_rows, field="top_level_priority_fallback_used")
    unsupported_priority = summarize_request_flag(request_rows, field="top_level_priority_unsupported")

    worker_log_path = Path(summary.get("worker_runtime_log", ""))
    if not worker_log_path.is_absolute():
        worker_log_path = Path.cwd() / worker_log_path
    worker_capacity = parse_worker_capacity(worker_log_path)
    worker_hint_evidence = parse_worker_hint_evidence(worker_log_path, request_rows)
    worker_priority_mechanism = parse_worker_priority_mechanism(worker_log_path)
    sglang_priority_hint_seen = truthy(summary.get("a_replay_sglang_priority_hint_seen"))
    sglang_scheduler_priority_applied = truthy(summary.get("a_replay_sglang_scheduler_priority_applied"))
    sglang_worker_top_level_priority = as_int(summary.get("a_replay_sglang_worker_top_level_priority"))
    sglang_worker_agent_hints_priority = as_int(summary.get("a_replay_sglang_worker_agent_hints_priority"))

    hint_profile = summary.get("protected_hint_profile", "")
    replay_status = summary.get("a_replay_status", "")
    replay_ok = request_succeeded(replay_status)
    speedup_ratio = as_float(summary.get("a_replay_speedup_ratio"))
    latency_delta_ms = as_float(summary.get("a_replay_latency_delta_ms"))
    a_first_prompt_tokens = as_int(summary.get("a_first_prompt_tokens"))
    if a_first_prompt_tokens is None:
        a_first_prompt_tokens = as_int(request_rows.get("a_first", {}).get("prompt_tokens"))
    first_distractor_prompt_tokens = as_int(summary.get("first_distractor_prompt_tokens"))
    if first_distractor_prompt_tokens is None:
        first_distractor_prompt_tokens = next(
            (
                as_int(row.get("prompt_tokens"))
                for role, row in request_rows.items()
                if role.startswith("distractor_")
            ),
            None,
        )
    worker_kv_capacity_tokens = as_int(summary.get("worker_kv_capacity_tokens"))
    if worker_kv_capacity_tokens is None:
        worker_kv_capacity_tokens = worker_capacity["worker_kv_capacity_tokens"]
    worker_context_len = as_int(summary.get("worker_context_len"))
    if worker_context_len is None:
        worker_context_len = worker_capacity["worker_context_len"]
    replay_cached_tokens = as_int(summary.get("a_replay_cached_tokens"))
    replay_prompt_tokens = as_int(summary.get("a_replay_prompt_tokens"))
    if replay_prompt_tokens is None:
        replay_prompt_tokens = as_int(request_rows.get("a_replay", {}).get("prompt_tokens"))
    replay_cache_reuse_ratio = as_float(summary.get("a_replay_cache_reuse_ratio"))
    cache_match_events = as_int(summary.get("a_replay_sglang_cache_match_events")) or 0
    cache_events = as_int(summary.get("a_replay_sglang_cache_events")) or 0
    cache_direct = truthy(summary.get("a_replay_sglang_cache_direct"))
    survived_by_events = replay_ok and cache_direct and cache_match_events >= match_event_min
    survived_by_usage = replay_ok and replay_cached_tokens is not None and replay_cached_tokens > 0
    survived_by_latency = replay_ok and (
        (speedup_ratio is not None and speedup_ratio >= min_speedup_ratio)
        or (latency_delta_ms is not None and latency_delta_ms <= -abs(min_latency_gain_ms))
    )
    if replay_cached_tokens is not None:
        survived_effective = survived_by_usage and survived_by_latency
        effective_survival_source = "response_usage_cached_tokens"
    else:
        survived_effective = survived_by_events and survived_by_latency
        effective_survival_source = "sglang_cache_events_fallback"

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

    if survived_by_usage and survived_by_latency:
        reuse_signal = "true_reuse_hit"
    elif survived_by_usage:
        reuse_signal = "usage_hit_without_speedup"
    elif survived_by_events and survived_by_latency:
        reuse_signal = "event_match_with_speedup"
    elif survived_by_events:
        reuse_signal = "semantic_match_only"
    else:
        reuse_signal = "no_reuse_evidence"

    if unsupported_priority["status"] in {"full", "partial"}:
        frontend_top_level_priority_compatibility = "unsupported"
    elif attempted_priority["status"] == "none":
        frontend_top_level_priority_compatibility = "not_attempted"
    elif sent_priority["status"] in {"full", "partial"}:
        frontend_top_level_priority_compatibility = "supported"
    else:
        frontend_top_level_priority_compatibility = "unknown"

    return {
        "sweep_status": sweep_status,
        "retention_sweep_id": sweep_id,
        "model": model,
        "retention_attribution_mode": retention_attribution_mode,
        "kv_tier_mode": kv_tier_mode,
        "hint_profile": hint_profile,
        "is_control": str(hint_profile == control_hint_profile).lower(),
        "distractor_count": distractor_count,
        "retention_probe_id": retention_probe_id,
        "a_first_status": summary.get("a_first_status", ""),
        "a_replay_status": replay_status,
        "a_first_latency_ms": summary.get("a_first_latency_ms", ""),
        "a_replay_latency_ms": summary.get("a_replay_latency_ms", ""),
        "a_replay_latency_delta_ms": summary.get("a_replay_latency_delta_ms", ""),
        "a_replay_speedup_ratio": summary.get("a_replay_speedup_ratio", ""),
        "worker_kv_capacity_tokens": worker_kv_capacity_tokens if worker_kv_capacity_tokens is not None else "",
        "worker_context_len": worker_context_len if worker_context_len is not None else "",
        "a_first_prompt_tokens": a_first_prompt_tokens if a_first_prompt_tokens is not None else "",
        "first_distractor_prompt_tokens": first_distractor_prompt_tokens if first_distractor_prompt_tokens is not None else "",
        "kv_tokens_left_after_a": kv_tokens_left_after_a if kv_tokens_left_after_a is not None else "",
        "kv_tokens_left_after_a_after_first_distractor": (
            kv_tokens_left_after_a_after_first_distractor
            if kv_tokens_left_after_a_after_first_distractor is not None
            else ""
        ),
        "a_replay_cached_tokens": replay_cached_tokens if replay_cached_tokens is not None else "",
        "a_replay_prompt_tokens": replay_prompt_tokens if replay_prompt_tokens is not None else "",
        "a_replay_cache_reuse_ratio": round_ratio(replay_cache_reuse_ratio),
        "a_replay_sglang_cache_events": cache_events,
        "a_replay_sglang_cache_match_events": cache_match_events,
        "a_replay_sglang_cache_semantic_tokens": summary.get("a_replay_sglang_cache_semantic_tokens", ""),
        "a_replay_sglang_cache_direct": str(cache_direct).lower(),
        "worker_hint_status": worker_hint_evidence["worker_hint_status"],
        "worker_hint_keys": worker_hint_evidence["worker_hint_keys"],
        "worker_hint_profile_seen": worker_hint_evidence["worker_hint_profile_seen"],
        "request_agent_hints_priority_status": hint_priority["status"],
        "request_agent_hints_priority_values": hint_priority["values"],
        "request_top_level_priority_attempt_status": attempted_priority["status"],
        "request_top_level_priority_attempt_values": attempted_priority["values"],
        "request_top_level_priority_status": sent_priority["status"],
        "request_top_level_priority_values": sent_priority["values"],
        "request_top_level_priority_fallback_status": fallback_priority["status"],
        "request_top_level_priority_fallback_values": fallback_priority["values"],
        "request_top_level_priority_unsupported_status": unsupported_priority["status"],
        "request_top_level_priority_unsupported_values": unsupported_priority["values"],
        "frontend_top_level_priority_compatibility": frontend_top_level_priority_compatibility,
        "worker_top_level_priority_status": worker_hint_evidence["worker_top_level_priority_status"],
        "worker_top_level_priority_values": worker_hint_evidence["worker_top_level_priority_values"],
        "worker_priority_scheduling_enabled": worker_priority_mechanism["worker_priority_scheduling_enabled"],
        "worker_radix_eviction_policy": worker_priority_mechanism["worker_radix_eviction_policy"],
        "worker_priority_mechanism_ready": worker_priority_mechanism["worker_priority_mechanism_ready"],
        "sglang_priority_hint_seen": str(sglang_priority_hint_seen).lower(),
        "sglang_scheduler_priority_applied": str(sglang_scheduler_priority_applied).lower(),
        "sglang_worker_top_level_priority": sglang_worker_top_level_priority if sglang_worker_top_level_priority is not None else "",
        "sglang_worker_agent_hints_priority": sglang_worker_agent_hints_priority if sglang_worker_agent_hints_priority is not None else "",
        "worker_priority_path_status": (
            "applied"
            if sglang_scheduler_priority_applied
            else "seen_only"
            if sglang_priority_hint_seen
            else "not_seen"
        ),
        "survived_by_usage": str(survived_by_usage).lower(),
        "survived_by_events": str(survived_by_events).lower(),
        "survived_by_latency": str(survived_by_latency).lower(),
        "survived_effective": str(survived_effective).lower(),
        "effective_survival_source": effective_survival_source,
        "reuse_signal": reuse_signal,
        "hint_runtime_effect_status": "pending_comparison",
        "requests_csv": summary.get("requests_csv", ""),
        "worker_runtime_log": summary.get("worker_runtime_log", ""),
    }


def annotate_hint_runtime_effect(rows: list[dict[str, Any]], *, control_hint_profile: str) -> None:
    grouped: dict[tuple[str, str, str, int], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row["model"]),
            str(row["retention_attribution_mode"]),
            str(row["kv_tier_mode"]),
            int(row["distractor_count"]),
        )
        grouped.setdefault(key, {})[str(row["hint_profile"])] = row

    for row in rows:
        hint_profile = str(row["hint_profile"])
        if hint_profile == control_hint_profile:
            row["hint_runtime_effect_status"] = "control_row"
            continue

        request_hint_status = str(row.get("request_agent_hints_priority_status", ""))
        worker_hint_status = str(row.get("worker_hint_status", ""))
        mechanism_ready = str(row.get("worker_priority_mechanism_ready", "false")) == "true"

        if request_hint_status in {"missing_requests_csv", "none"}:
            row["hint_runtime_effect_status"] = "not_sent"
            continue
        if str(row.get("frontend_top_level_priority_compatibility", "")) == "unsupported":
            row["hint_runtime_effect_status"] = "frontend_priority_unsupported"
            continue
        if worker_hint_status in {"missing_runtime_json", "none"}:
            row["hint_runtime_effect_status"] = "sent_not_seen"
            continue
        if not mechanism_ready:
            row["hint_runtime_effect_status"] = "seen_but_mechanism_disabled"
            continue

        key = (
            str(row["model"]),
            str(row["retention_attribution_mode"]),
            str(row["kv_tier_mode"]),
            int(row["distractor_count"]),
        )
        control_row = grouped.get(key, {}).get(control_hint_profile)
        if control_row is None:
            row["hint_runtime_effect_status"] = "mechanism_enabled_no_control_row"
            continue

        control_survived = str(control_row.get("survived_effective", "false")) == "true"
        protected_survived = str(row.get("survived_effective", "false")) == "true"
        if protected_survived and not control_survived:
            row["hint_runtime_effect_status"] = "effect_observed"
        elif protected_survived == control_survived:
            row["hint_runtime_effect_status"] = "mechanism_enabled_no_effect"
        else:
            row["hint_runtime_effect_status"] = "protected_worse_than_control"


def build_comparison_rows(
    rows: list[dict[str, Any]],
    *,
    control_hint_profile: str,
    sweep_status: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        key = (row["model"], row["retention_attribution_mode"], row["kv_tier_mode"])
        grouped.setdefault(key, {}).setdefault(row["hint_profile"], []).append(row)

    out: list[dict[str, Any]] = []
    for (model, retention_attribution_mode, kv_tier_mode), by_profile in sorted(grouped.items()):
        control_rows = sorted(
            by_profile.get(control_hint_profile, []),
            key=lambda item: int(item["distractor_count"]),
        )
        control_first_evict = next(
            (int(row["distractor_count"]) for row in control_rows if row["survived_effective"] == "false"),
            None,
        )
        control_last_survive = next(
            (int(row["distractor_count"]) for row in reversed(control_rows) if row["survived_effective"] == "true"),
            None,
        )

        for hint_profile, profile_rows in sorted(by_profile.items()):
            if hint_profile == control_hint_profile:
                continue
            profile_rows = sorted(profile_rows, key=lambda item: int(item["distractor_count"]))
            protected_first_evict = next(
                (int(row["distractor_count"]) for row in profile_rows if row["survived_effective"] == "false"),
                None,
            )
            protected_last_survive = next(
                (int(row["distractor_count"]) for row in reversed(profile_rows) if row["survived_effective"] == "true"),
                None,
            )
            threshold_gap = (
                protected_first_evict - control_first_evict
                if protected_first_evict is not None and control_first_evict is not None
                else None
            )
            if threshold_gap is None:
                interpretation = "inconclusive"
            elif threshold_gap > 0:
                interpretation = "protected_hint_survives_longer"
            elif threshold_gap == 0:
                interpretation = "same_eviction_threshold_question_hint_respected"
            else:
                interpretation = "protected_hint_evicts_earlier"

            worker_hint_statuses = sorted({str(row.get("worker_hint_status", "")) for row in profile_rows if str(row.get("worker_hint_status", ""))})
            mechanism_states = sorted({str(row.get("worker_priority_mechanism_ready", "")) for row in profile_rows if str(row.get("worker_priority_mechanism_ready", ""))})
            effect_states = sorted({str(row.get("hint_runtime_effect_status", "")) for row in profile_rows if str(row.get("hint_runtime_effect_status", ""))})
            priority_path_states = sorted({str(row.get("worker_priority_path_status", "")) for row in profile_rows if str(row.get("worker_priority_path_status", ""))})
            frontend_compat_states = sorted({str(row.get("frontend_top_level_priority_compatibility", "")) for row in profile_rows if str(row.get("frontend_top_level_priority_compatibility", ""))})
            out.append(
                {
                    "sweep_status": sweep_status,
                    "model": model,
                    "retention_attribution_mode": retention_attribution_mode,
                    "kv_tier_mode": kv_tier_mode,
                    "control_hint_profile": control_hint_profile,
                    "protected_hint_profile": hint_profile,
                    "control_last_survived_distractor_count": control_last_survive or "",
                    "control_first_evicted_distractor_count": control_first_evict or "",
                    "protected_last_survived_distractor_count": protected_last_survive or "",
                    "protected_first_evicted_distractor_count": protected_first_evict or "",
                    "threshold_gap_distractors": threshold_gap if threshold_gap is not None else "",
                    "worker_hint_status": "|".join(worker_hint_statuses),
                    "frontend_top_level_priority_compatibility": "|".join(frontend_compat_states),
                    "worker_priority_mechanism_ready": "|".join(mechanism_states),
                    "worker_priority_path_status": "|".join(priority_path_states),
                    "hint_runtime_effect_status": "|".join(effect_states),
                    "interpretation": interpretation,
                }
            )
    return out


def write_summary_md(
    path: Path,
    matrix_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
    *,
    control_hint_profile: str,
    match_event_min: int,
    min_speedup_ratio: float,
    min_latency_gain_ms: float,
    sweep_status: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    models = sorted({row["model"] for row in matrix_rows})
    modes = sorted({row["retention_attribution_mode"] for row in matrix_rows})
    tiers = sorted({row["kv_tier_mode"] for row in matrix_rows})
    profiles = sorted({row["hint_profile"] for row in matrix_rows})
    lines = [
        "# Retention Threshold Sweep Summary",
        "",
        "## Scope",
        "",
        f"- Models: {', '.join(models) if models else 'none'}",
        f"- Attribution modes: {', '.join(modes) if modes else 'none'}",
        f"- KV tier modes: {', '.join(tiers) if tiers else 'none'}",
        f"- Hint profiles: {', '.join(profiles) if profiles else 'none'}",
        f"- Control hint profile: {control_hint_profile}",
        f"- Sweep status: {sweep_status}",
        "",
        "## Effective survival rule",
        "",
        f"- replay must succeed (`200`/`201`)",
        f"- if replay exposes cached prompt tokens, we treat that as the primary reuse signal",
        f"- otherwise we fall back to direct cache attribution plus at least `{match_event_min}` match event(s)",
        f"- replay must also show meaningful benefit: speedup ratio >= `{min_speedup_ratio}` or latency gain >= `{int(min_latency_gain_ms)}` ms",
        "",
        "## Comparison",
        "",
    ]
    if not comparison_rows:
        lines.append("- No comparison rows were generated.")
    else:
        for row in comparison_rows:
            lines.extend(
                [
                    f"- `{row['model']}` / `{row['retention_attribution_mode']}` / `{row['kv_tier_mode']}` / `{row['protected_hint_profile']}`:",
                    f"  control first evicted at `{row['control_first_evicted_distractor_count'] or 'not observed'}`, "
                    f"protected first evicted at `{row['protected_first_evicted_distractor_count'] or 'not observed'}`, "
                    f"frontend top-level priority: `{row['frontend_top_level_priority_compatibility'] or 'unknown'}`, "
                    f"mechanism ready: `{row['worker_priority_mechanism_ready'] or 'unknown'}`, "
                    f"hint status: `{row['worker_hint_status'] or 'unknown'}`, "
                    f"priority path: `{row['worker_priority_path_status'] or 'unknown'}`, "
                    f"effect status: `{row['hint_runtime_effect_status'] or 'unknown'}`, "
                    f"interpretation: `{row['interpretation']}`",
                ]
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    progress_rows = read_csv(Path(args.progress_csv))
    matrix_rows: list[dict[str, Any]] = []
    for progress in progress_rows:
        batch_matrix = Path(progress["batch_matrix"])
        if not batch_matrix.is_absolute():
            batch_matrix = Path.cwd() / batch_matrix
        summaries = load_batch_summary_rows(batch_matrix)
        if not summaries:
            continue
        for summary in summaries:
            matrix_rows.append(
                derived_row(
                    sweep_id=progress["retention_sweep_id"],
                    model=progress["model"],
                    retention_attribution_mode=progress.get("retention_attribution_mode", "precise"),
                    kv_tier_mode=progress["kv_tier_mode"],
                    distractor_count=int(progress["distractor_count"]),
                    retention_probe_id=progress["retention_probe_id"],
                    summary=summary,
                    control_hint_profile=args.control_hint_profile,
                    match_event_min=args.match_event_min,
                    min_speedup_ratio=args.min_speedup_ratio,
                    min_latency_gain_ms=args.min_latency_gain_ms,
                    sweep_status=args.sweep_status,
                )
            )

    annotate_hint_runtime_effect(matrix_rows, control_hint_profile=args.control_hint_profile)

    matrix_fields = [
        "sweep_status",
        "retention_sweep_id",
        "model",
        "retention_attribution_mode",
        "kv_tier_mode",
        "hint_profile",
        "is_control",
        "distractor_count",
        "retention_probe_id",
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
        "a_replay_cached_tokens",
        "a_replay_prompt_tokens",
        "a_replay_cache_reuse_ratio",
        "a_replay_sglang_cache_events",
        "a_replay_sglang_cache_match_events",
        "a_replay_sglang_cache_semantic_tokens",
        "a_replay_sglang_cache_direct",
        "worker_hint_status",
        "worker_hint_keys",
        "worker_hint_profile_seen",
        "request_agent_hints_priority_status",
        "request_agent_hints_priority_values",
        "request_top_level_priority_attempt_status",
        "request_top_level_priority_attempt_values",
        "request_top_level_priority_status",
        "request_top_level_priority_values",
        "request_top_level_priority_fallback_status",
        "request_top_level_priority_fallback_values",
        "request_top_level_priority_unsupported_status",
        "request_top_level_priority_unsupported_values",
        "frontend_top_level_priority_compatibility",
        "worker_top_level_priority_status",
        "worker_top_level_priority_values",
        "worker_priority_scheduling_enabled",
        "worker_radix_eviction_policy",
        "worker_priority_mechanism_ready",
        "sglang_priority_hint_seen",
        "sglang_scheduler_priority_applied",
        "sglang_worker_top_level_priority",
        "sglang_worker_agent_hints_priority",
        "worker_priority_path_status",
        "survived_by_usage",
        "survived_by_events",
        "survived_by_latency",
        "survived_effective",
        "effective_survival_source",
        "reuse_signal",
        "hint_runtime_effect_status",
        "requests_csv",
        "worker_runtime_log",
    ]
    write_csv(Path(args.out_matrix), matrix_rows, matrix_fields)

    comparison_rows = build_comparison_rows(
        matrix_rows,
        control_hint_profile=args.control_hint_profile,
        sweep_status=args.sweep_status,
    )
    comparison_fields = [
        "sweep_status",
        "model",
        "retention_attribution_mode",
        "kv_tier_mode",
        "control_hint_profile",
        "protected_hint_profile",
        "control_last_survived_distractor_count",
        "control_first_evicted_distractor_count",
        "protected_last_survived_distractor_count",
        "protected_first_evicted_distractor_count",
        "threshold_gap_distractors",
        "worker_hint_status",
        "frontend_top_level_priority_compatibility",
        "worker_priority_mechanism_ready",
        "worker_priority_path_status",
        "hint_runtime_effect_status",
        "interpretation",
    ]
    write_csv(Path(args.out_comparison), comparison_rows, comparison_fields)
    write_summary_md(
        Path(args.out_summary_md),
        matrix_rows,
        comparison_rows,
        control_hint_profile=args.control_hint_profile,
        match_event_min=args.match_event_min,
        min_speedup_ratio=args.min_speedup_ratio,
        min_latency_gain_ms=args.min_latency_gain_ms,
        sweep_status=args.sweep_status,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
