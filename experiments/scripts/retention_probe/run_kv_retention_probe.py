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
PROMPT_GENERATOR_VERSION = "cache-word-v4"
SGLANG_EVENT_PREFIX = "[SGLANG_TRANSFER_JSON] "
RUNTIME_JSON_PREFIX = "[RUNTIME_JSON]"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
DEFAULT_PROBE_INPUT_LEN = 14000
DEFAULT_MAX_CONTEXT_TOKENS = 17146
DEFAULT_CACHE_CONTROL_EPHEMERAL_TTL = os.environ.get("CACHE_CONTROL_EPHEMERAL_TTL", "1h")

#
# Important: the synthetic retention probe keeps runtime-control hints intentionally
# minimal for cross-machine compatibility. Request attribution metadata travels via
# request_context / agent_context / annotations, while nvext.agent_hints only carries
# the Dynamo-safe priority signal we want the runtime to act on.
#
DEFAULT_HINTS: dict[str, Any] = {
    "priority": 5,
}

HINT_PROFILES: dict[str, dict[str, Any]] = {
    "baseline": {"priority": 5},
    "high-reuse": {"priority": 5},
    "low-reuse": {"priority": 5},
    "high-priority": {"priority": 10},
    "low-priority": {"priority": 1},
    "long-output": {"priority": 5},
    "short-output": {"priority": 5},
}

NO_HINT_PROFILES = {"", "none", "off", "no-hints", "no_hints"}
CACHE_CONTROL_OFF_PROFILES = {"", "none", "off", "disable", "disabled", "no-cache-control", "no_cache_control"}

# Tokenizer-friendly common words used to build highly divergent distractor
# prompts. The goal is to make distractor prefixes differ early so they do not
# accidentally enjoy KV reuse from one another.
DISTRACTOR_WORD_BANK = [
    "amber", "anchor", "apple", "arch", "ash", "aster", "atlas", "autumn",
    "bamboo", "barley", "bay", "beacon", "berry", "birch", "blossom", "brook",
    "cabin", "cactus", "canal", "canyon", "cedar", "chalk", "cinder", "clay",
    "cliff", "cloud", "cobalt", "comet", "coral", "cove", "crater", "creek",
    "crystal", "dawn", "delta", "desert", "dove", "drift", "dune", "echo",
    "elm", "ember", "falcon", "field", "finch", "fjord", "flint", "flora",
    "foam", "forest", "fossil", "fox", "frost", "garden", "glacier", "glade",
    "grain", "granite", "grove", "harbor", "harvest", "hazel", "heather", "heron",
    "hollow", "horizon", "iceberg", "iris", "island", "ivy", "jade", "juniper",
    "lagoon", "lake", "laurel", "lava", "leaf", "lilac", "linen", "lotus",
    "lumen", "magnet", "maple", "marble", "marsh", "meadow", "mercury", "mesa",
    "meteor", "mint", "mist", "monsoon", "moon", "moss", "mountain", "nectar",
    "night", "north", "oasis", "oak", "ocean", "onyx", "opal", "orchard",
    "otter", "owl", "palm", "pearl", "pebble", "petal", "pine", "planet",
    "plaza", "plum", "pond", "prairie", "quartz", "quill", "rain", "raven",
    "reed", "reef", "ridge", "river", "robin", "saffron", "sage", "sand",
    "satin", "scarlet", "sea", "shadow", "shell", "shore", "silver", "sky",
    "slate", "snow", "solstice", "sparrow", "spruce", "spring", "star", "stone",
    "storm", "stream", "summer", "sun", "surf", "swift", "terra", "thistle",
    "thunder", "tide", "timber", "topaz", "trail", "trellis", "tulip", "valley",
    "velvet", "violet", "water", "wave", "willow", "wind", "winter", "wren",
]


REQUEST_COLUMNS = [
    "run_id",
    "sequence_index",
    "request_role",
    "request_id",
    "hint_profile",
    "hints_enabled",
    "agent_hints_priority",
    "cache_control_profile",
    "cache_control_type",
    "cache_control_ttl",
    "request_context_mode",
    "request_context_sent",
    "request_context_fallback_used",
    "request_context_unsupported",
    "agent_context_sent",
    "annotations_sent",
    "top_level_priority_mode",
    "top_level_priority_attempted",
    "top_level_priority_sent",
    "top_level_priority_value",
    "top_level_priority_fallback_used",
    "top_level_priority_unsupported",
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
    "protected_cache_control_profile",
    "distractor_cache_control_profile",
    "cache_control_doc_mode",
    "cache_control_frontend_flag_status",
    "cache_control_pin_path_status",
    "cache_control_pinned_ratio",
    "cache_control_write_policy",
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
    "a_first_top_level_priority_mode",
    "a_first_top_level_priority_attempted",
    "a_first_top_level_priority_sent",
    "a_first_top_level_priority_value",
    "a_first_top_level_priority_fallback_used",
    "a_first_top_level_priority_unsupported",
    "a_first_cached_tokens",
    "a_replay_agent_hints_priority",
    "a_replay_top_level_priority_mode",
    "a_replay_top_level_priority_attempted",
    "a_replay_top_level_priority_sent",
    "a_replay_top_level_priority_value",
    "a_replay_top_level_priority_fallback_used",
    "a_replay_top_level_priority_unsupported",
    "a_replay_cached_tokens",
    "a_replay_cache_reuse_ratio",
    "a_replay_prompt_tokens",
    "a_first_sglang_cache_events",
    "a_replay_sglang_cache_events",
    "a_replay_sglang_cache_match_events",
    "a_replay_sglang_cache_evict_events",
    "a_replay_sglang_cache_semantic_tokens",
    "a_replay_sglang_cache_direct",
    "a_replay_sglang_evict_cache_control_values",
    "a_replay_sglang_evict_hint_profiles",
    "a_replay_sglang_evict_cache_control_match",
    "a_replay_sglang_evict_hint_profile_match",
    "a_replay_sglang_evict_identity_status",
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

PUBLIC_SUMMARY_COLUMNS = [
    "run_id",
    "model",
    "kv_tier",
    "hint_profile",
    "protected_cache",
    "doc_mode",
    "frontend_cc_flag",
    "pin_path",
    "pinned_ratio",
    "write_policy",
    "distractors",
    "first_status",
    "replay_status",
    "first_ms",
    "replay_ms",
    "replay_delta_ms",
    "replay_speedup",
    "kv_cap",
    "ctx_len",
    "a_tokens",
    "d1_tokens",
    "kv_left_after_a",
    "replay_cached",
    "replay_reuse",
    "survived",
    "survival_source",
    "req_prio_status",
    "req_prio_values",
    "worker_prio_status",
    "worker_prio_values",
    "replay_evicts",
    "replay_evict_cache",
    "replay_evict_cache_match",
    "replay_evict_hint_match",
    "replay_evict_status",
    "effect_status",
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
    parser.add_argument(
        "--prompt-isolation-mode",
        default=os.environ.get("RETENTION_PROMPT_ISOLATION_MODE", "disjoint"),
        choices=("standard", "strict", "disjoint"),
        help=(
            "How strongly to isolate protected prompts across sweep cells. "
            "'standard' keeps the older mostly-uniform protected prompt template. "
            "'strict' makes protected prompts diverge early across different seeds "
            "while still keeping a_first and a_replay identical within each cell. "
            "'disjoint' makes sweep cells use radically different early prompt families "
            "while still keeping a_first and a_replay identical within each cell."
        ),
    )
    parser.add_argument("--protected-hint-profile", default="high-priority")
    parser.add_argument("--distractor-hint-profile", default="none")
    parser.add_argument(
        "--protected-cache-control-profile",
        default=os.environ.get("PROTECTED_CACHE_CONTROL_PROFILE", "off"),
        help="Cache-control profile for protected A requests. Examples: off, ephemeral, ephemeral:1h",
    )
    parser.add_argument(
        "--distractor-cache-control-profile",
        default=os.environ.get("DISTRACTOR_CACHE_CONTROL_PROFILE", "off"),
        help="Cache-control profile for distractor requests. Examples: off, ephemeral, ephemeral:1h",
    )
    parser.add_argument(
        "--default-cache-control-ttl",
        default=os.environ.get("CACHE_CONTROL_EPHEMERAL_TTL", DEFAULT_CACHE_CONTROL_EPHEMERAL_TTL),
        help="Default TTL used when cache-control profile is 'ephemeral' without an explicit ':ttl' suffix.",
    )
    parser.add_argument("--cache-control-doc-mode", default=os.environ.get("CACHE_CONTROL_DOC_MODE", "0"))
    parser.add_argument("--cache-control-frontend-flag-status", default=os.environ.get("CACHE_CONTROL_DOC_FRONTEND_FLAG_STATUS", ""))
    parser.add_argument("--cache-control-pin-path-status", default=os.environ.get("CACHE_CONTROL_DOC_PIN_PATH_STATUS", ""))
    parser.add_argument("--cache-control-pinned-ratio", default=os.environ.get("SGLANG_HICACHE_MAX_PINNED_RATIO", ""))
    parser.add_argument("--cache-control-write-policy", default=os.environ.get("HICACHE_WRITE_POLICY", ""))
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
    parser.add_argument(
        "--top-level-priority-mode",
        default=os.environ.get("RETENTION_TOP_LEVEL_PRIORITY_MODE", "auto"),
        choices=("auto", "force", "disable"),
        help=(
            "How to handle top-level request priority. "
            "'auto' tries it and retries once without it if the frontend rejects "
            "priority, 'force' always sends it, and 'disable' never sends it."
        ),
    )
    parser.add_argument(
        "--request-context-mode",
        default=os.environ.get("RETENTION_REQUEST_CONTEXT_MODE", "auto"),
        choices=("auto", "force", "disable"),
        help=(
            "How to handle nvext.request_context. "
            "'auto' tries it and retries once without it if the frontend rejects "
            "request_context, 'force' always sends it, and 'disable' never sends it."
        ),
    )
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


def make_distractor_prompt(*, role: str, target_len: int, seed: int) -> str:
    rng = random.Random(f"{role}:{seed}:{target_len}:distractor")
    vocab = list(DISTRACTOR_WORD_BANK)
    rng.shuffle(vocab)

    # Force early divergence across distractors. This is more important for KV
    # pressure than changing only tail words, because prefix overlap is what the
    # cache matches first.
    prefix_len = min(48, target_len)
    prefix_words = vocab[:prefix_len]
    cycle_words = vocab[prefix_len:] or vocab
    stride = (rng.randrange(5, len(cycle_words), 2) if len(cycle_words) > 5 else 1)
    offset = rng.randrange(len(cycle_words)) if cycle_words else 0

    body_words: list[str] = []
    for idx in range(target_len):
        if idx < prefix_len:
            body_words.append(prefix_words[idx])
            continue
        cycle_idx = (offset + (idx - prefix_len) * stride) % len(cycle_words)
        body_words.append(cycle_words[cycle_idx])

    nonce_words = prefix_words[: min(8, len(prefix_words))]
    header = (
        f"{role} " +
        " ".join(nonce_words) + ". "
        "Return exactly one short answer token. "
        "This distractor uses a role-specific word stream so its prefix diverges early. "
    )
    return header + " ".join(body_words)


def make_prompt(*, role: str, target_len: int, seed: int, isolation_mode: str = "strict") -> str:
    if role.startswith("distractor_"):
        return make_distractor_prompt(role=role, target_len=target_len, seed=seed)

    return make_protected_prompt(
        role=role,
        target_len=target_len,
        seed=seed,
        isolation_mode=isolation_mode,
    )


def make_disjoint_prompt(*, role: str, target_len: int, seed: int) -> str:
    family_key = f"{role}:{seed}:{target_len}:disjoint"
    family_id = short_hash(family_key)
    rng = random.Random(family_key)
    vocab = list(DISTRACTOR_WORD_BANK)
    rng.shuffle(vocab)

    prefix_len = min(64, target_len, len(vocab))
    prefix_words = [f"{word}{family_id[:4]}" for word in vocab[:prefix_len]]
    cycle_words = prefix_words or [f"cache{family_id[:4]}"]

    body_words: list[str] = []
    for idx in range(target_len):
        if idx < prefix_len:
            body_words.append(prefix_words[idx])
            continue
        cycle_idx = (idx - prefix_len) % len(cycle_words)
        body_words.append(cycle_words[cycle_idx])

    nonce_words = prefix_words[: min(10, len(prefix_words))]
    header = (
        f"{role} "
        + " ".join(nonce_words)
        + ". "
        + "KV cache retention probe prompt. "
        + f"family marker {family_id[:8]}. "
        + "Return exactly one short answer token. "
        + "This protected prompt uses a disjoint early family so different sweep cells stay clearly separated. "
    )
    return header + " ".join(body_words)


def make_protected_prompt(*, role: str, target_len: int, seed: int, isolation_mode: str) -> str:
    if isolation_mode == "standard":
        return make_standard_prompt(role=role, target_len=target_len, seed=seed)
    if isolation_mode == "disjoint":
        return make_disjoint_prompt(role=role, target_len=target_len, seed=seed)
    if isolation_mode != "strict":
        raise ValueError(f"Unknown prompt isolation mode: {isolation_mode}")

    rng = random.Random(f"{role}:{seed}:{target_len}:strict")
    vocab = list(DISTRACTOR_WORD_BANK)
    rng.shuffle(vocab)

    # For protected prompts, make different sweep cells diverge early too.
    # This preserves within-cell comparability because a_first and a_replay
    # still use the same seed and therefore the same prompt text.
    prefix_len = min(64, target_len)
    prefix_words = vocab[:prefix_len]
    cycle_words = vocab[prefix_len:] or vocab
    stride = (rng.randrange(5, len(cycle_words), 2) if len(cycle_words) > 5 else 1)
    offset = rng.randrange(len(cycle_words)) if cycle_words else 0

    body_words: list[str] = []
    for idx in range(target_len):
        if idx < prefix_len:
            body_words.append(prefix_words[idx])
            continue
        cycle_idx = (offset + (idx - prefix_len) * stride) % len(cycle_words)
        body_words.append(cycle_words[cycle_idx])

    nonce_words = prefix_words[: min(10, len(prefix_words))]
    header = (
        f"{role} "
        + " ".join(nonce_words)
        + ". "
        + "KV cache retention probe prompt. "
        f"seed marker {rng.randrange(1_000_000):06d}. "
        "Return exactly one short answer token. "
        "This protected prompt uses a seed-specific early prefix so different sweep cells do not overlap too much. "
    )
    return header + " ".join(body_words)


def make_standard_prompt(*, role: str, target_len: int, seed: int) -> str:
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
    cache_control_profile: str,
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
        "cache_control_profile": cache_control_profile,
    }


def build_agent_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_type_id": "synthetic_kv_retention_probe:v1",
        "session_id": str(context.get("parent_run_id") or "retention_probe"),
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
        "prompt_hash",
        "hint_profile",
        "cache_control_profile",
    ):
        value = context.get(key)
        if value in (None, ""):
            continue
        annotations.append(f"{key}:{value}")
    return annotations


def build_cache_control(
    profile: str,
    *,
    default_ttl: str,
) -> tuple[dict[str, Any] | None, str, str, str]:
    normalized = profile.strip()
    lowered = normalized.lower()
    if lowered in CACHE_CONTROL_OFF_PROFILES:
        return None, "off", "", ""
    if lowered == "ephemeral":
        ttl = default_ttl.strip()
        if not ttl:
            raise SystemExit("CACHE_CONTROL_EPHEMERAL_TTL / --default-cache-control-ttl must be non-empty")
        return {"type": "ephemeral", "ttl": ttl}, f"ephemeral:{ttl}", "ephemeral", ttl
    if lowered.startswith("ephemeral:"):
        ttl = normalized.split(":", 1)[1].strip()
        if not ttl:
            raise SystemExit(f"Invalid cache-control profile {profile!r}; expected ephemeral:<ttl>")
        return {"type": "ephemeral", "ttl": ttl}, f"ephemeral:{ttl}", "ephemeral", ttl
    raise SystemExit(
        f"Unknown cache-control profile {profile!r}. Use one of: off, ephemeral, ephemeral:<ttl>"
    )


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
    cache_control_profile: str,
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
        cache_control_profile=cache_control_profile,
    )
    cache_control, normalized_cache_control_profile, cache_control_type, cache_control_ttl = build_cache_control(
        cache_control_profile,
        default_ttl=args.default_cache_control_ttl,
    )
    payload: dict[str, Any] = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": args.random_output_len,
        "temperature": 0,
        "nvext": {
            "agent_context": build_agent_context(context),
            "annotations": build_annotations(context),
        },
    }
    should_attempt_request_context = args.request_context_mode != "disable"
    if should_attempt_request_context:
        payload["nvext"]["request_context"] = context
    if hints is not None:
        payload["nvext"]["agent_hints"] = hints
    if cache_control is not None:
        payload["nvext"]["cache_control"] = cache_control
    priority = top_level_priority_from_hints(hints)
    should_attempt_top_level_priority = (
        priority is not None and args.top_level_priority_mode != "disable"
    )
    if should_attempt_top_level_priority:
        payload["priority"] = priority
    if args.ignore_eos:
        payload["ignore_eos"] = True

    start = time.perf_counter()
    status, response_json, error = post_json(args.frontend_url, payload, timeout=args.request_timeout)
    latency_ms = (time.perf_counter() - start) * 1000
    fallback_used = False
    top_level_priority_unsupported = False
    request_context_fallback_used = False
    request_context_unsupported_flag = False

    if (
        should_attempt_top_level_priority
        and args.top_level_priority_mode == "auto"
        and priority_unsupported(status, error)
    ):
        fallback_used = True
        top_level_priority_unsupported = True
        payload.pop("priority", None)
        start = time.perf_counter()
        status, response_json, error = post_json(args.frontend_url, payload, timeout=args.request_timeout)
        latency_ms = (time.perf_counter() - start) * 1000

    if (
        should_attempt_request_context
        and args.request_context_mode == "auto"
        and request_context_unsupported(status, error)
    ):
        request_context_fallback_used = True
        request_context_unsupported_flag = True
        payload["nvext"].pop("request_context", None)
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
        "cache_control_profile": normalized_cache_control_profile,
        "cache_control_type": cache_control_type,
        "cache_control_ttl": cache_control_ttl,
        "request_context_mode": args.request_context_mode,
        "request_context_sent": should_attempt_request_context and not request_context_fallback_used,
        "request_context_fallback_used": request_context_fallback_used,
        "request_context_unsupported": request_context_unsupported_flag,
        "agent_context_sent": True,
        "annotations_sent": True,
        "top_level_priority_mode": args.top_level_priority_mode,
        "top_level_priority_attempted": should_attempt_top_level_priority,
        "top_level_priority_sent": should_attempt_top_level_priority and not fallback_used,
        "top_level_priority_value": priority if priority is not None else "",
        "top_level_priority_fallback_used": fallback_used,
        "top_level_priority_unsupported": top_level_priority_unsupported,
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


def annotations_from_record(record: dict[str, Any]) -> list[str]:
    nvext = record.get("nvext")
    if isinstance(nvext, dict) and isinstance(nvext.get("annotations"), list):
        return [str(item) for item in nvext["annotations"] if item not in (None, "")]

    runtime_observability = record.get("runtime_observability")
    if isinstance(runtime_observability, dict):
        annotations = runtime_observability.get("annotations")
        if isinstance(annotations, list):
            return [str(item) for item in annotations if item not in (None, "")]
        nested_nvext = runtime_observability.get("nvext")
        if isinstance(nested_nvext, dict) and isinstance(nested_nvext.get("annotations"), list):
            return [str(item) for item in nested_nvext["annotations"] if item not in (None, "")]
    return []


def annotation_map_from_record(record: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in annotations_from_record(record):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key and value and key not in values:
            values[key] = value
    return values


def agent_context_from_record(record: dict[str, Any]) -> dict[str, Any]:
    nvext = record.get("nvext")
    if isinstance(nvext, dict) and isinstance(nvext.get("agent_context"), dict):
        return nvext["agent_context"]

    runtime_observability = record.get("runtime_observability")
    if isinstance(runtime_observability, dict):
        agent_context = runtime_observability.get("agent_context")
        if isinstance(agent_context, dict):
            return agent_context
        nested_nvext = runtime_observability.get("nvext")
        if isinstance(nested_nvext, dict) and isinstance(nested_nvext.get("agent_context"), dict):
            return nested_nvext["agent_context"]
    return {}


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

    annotation_map = annotation_map_from_record(record)
    agent_context = agent_context_from_record(record)
    hint_probe_id = record.get("hint_probe_id")
    request_id = annotation_map.get("request_id")
    if not request_id and isinstance(hint_probe_id, str) and hint_probe_id:
        request_id = hint_probe_id
    if not request_id and isinstance(agent_context.get("trajectory_id"), str):
        request_id = agent_context.get("trajectory_id")

    parent_run_id = annotation_map.get("parent_run_id")
    if not parent_run_id and isinstance(agent_context.get("session_id"), str):
        parent_run_id = agent_context.get("session_id")

    if not request_id and not parent_run_id and not annotation_map:
        return {}

    return {
        "request_id": request_id or "",
        "parent_run_id": parent_run_id or "",
        "task_instance_id": annotation_map.get("task_instance_id", ""),
        "phase": annotation_map.get("phase", record.get("phase", "")),
        "step_index": annotation_map.get("step_index", ""),
        "step_title": annotation_map.get("step_title", ""),
        "app_variant": annotation_map.get("app_variant", ""),
        "prompt_hash": annotation_map.get("prompt_hash", ""),
        "hint_profile": annotation_map.get("hint_profile", ""),
        "cache_control_profile": annotation_map.get("cache_control_profile", ""),
    }


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


def cache_control_label_from_event(event: dict[str, Any]) -> str:
    cache_control = event.get("cache_control")
    cache_type = event.get("cache_control_type")
    cache_ttl = event.get("cache_control_ttl")
    cache_profile = event.get("cache_control_profile")
    if isinstance(cache_control, dict):
        if cache_type in (None, ""):
            cache_type = cache_control.get("type")
        if cache_ttl in (None, ""):
            cache_ttl = cache_control.get("ttl")
    if cache_type not in (None, "") and cache_ttl not in (None, ""):
        return f"{cache_type}:{cache_ttl}"
    if cache_type not in (None, ""):
        return str(cache_type)
    if cache_profile not in (None, ""):
        return str(cache_profile)
    return ""


def hint_profile_from_event(event: dict[str, Any]) -> str:
    for key in ("worker_hint_profile_seen", "hint_profile"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    request_context = event.get("request_context")
    if isinstance(request_context, dict):
        value = request_context.get("hint_profile")
        if isinstance(value, str) and value:
            return value
    return ""


def split_pipe_values(value: Any) -> set[str]:
    if value in (None, ""):
        return set()
    return {part.strip() for part in str(value).split("|") if part.strip()}


def expected_hint_profile(value: Any) -> str:
    normalized = str(value or "").strip()
    return "" if normalized.lower() in NO_HINT_PROFILES else normalized


def expected_cache_control_profile(value: Any) -> str:
    normalized = str(value or "").strip()
    return "" if normalized.lower() in CACHE_CONTROL_OFF_PROFILES else normalized


def evict_identity_evidence(
    *,
    replay: dict[str, Any],
    protected_hint_profile_value: Any,
    protected_cache_control_profile_value: Any,
) -> tuple[str, str, str]:
    evict_events = maybe_int(replay.get("sglang_cache_evict_events")) or 0
    observed_cache_controls = split_pipe_values(replay.get("sglang_evict_cache_control_values"))
    observed_hint_profiles = split_pipe_values(replay.get("sglang_evict_hint_profiles"))
    expected_cache_control = expected_cache_control_profile(protected_cache_control_profile_value)
    expected_hint = expected_hint_profile(protected_hint_profile_value)
    cache_control_match = bool(expected_cache_control) and expected_cache_control in observed_cache_controls
    hint_profile_match = bool(expected_hint) and expected_hint in observed_hint_profiles

    if evict_events <= 0:
        status = "no_evict_seen"
    elif not expected_cache_control and not expected_hint:
        status = "no_expected_identity"
    elif cache_control_match and hint_profile_match:
        status = "matched_cache_control_and_hint"
    elif cache_control_match:
        status = "matched_cache_control_only"
    elif hint_profile_match:
        status = "matched_hint_only"
    else:
        status = "evict_seen_no_identity"

    return status, str(cache_control_match).lower(), str(hint_profile_match).lower()


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
    evict_cache_controls: dict[str, set[str]] = {}
    evict_hint_profiles: dict[str, set[str]] = {}

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
                cache_control_label = cache_control_label_from_event(event)
                if cache_control_label:
                    evict_cache_controls.setdefault(request_id, set()).add(cache_control_label)
                hint_profile = hint_profile_from_event(event)
                if hint_profile:
                    evict_hint_profiles.setdefault(request_id, set()).add(hint_profile)

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
        row["sglang_evict_cache_control_values"] = "|".join(sorted(evict_cache_controls.get(request_id, set())))
        row["sglang_evict_hint_profiles"] = "|".join(sorted(evict_hint_profiles.get(request_id, set())))


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


def compact_priority_values(*pairs: tuple[str, Any]) -> str:
    parts: list[str] = []
    for role, value in pairs:
        parsed = maybe_int(value)
        if parsed is None:
            continue
        parts.append(f"{role}:{parsed}")
    return "|".join(parts)


def compact_priority_status(*values: Any) -> str:
    parsed_values = [maybe_int(value) for value in values]
    present = [value for value in parsed_values if value is not None]
    if not present:
        return "none"
    if len(present) == len(parsed_values):
        return "full"
    return "partial"


def worker_priority_status(summary: dict[str, Any]) -> str:
    if truthy(summary.get("a_first_sglang_scheduler_priority_applied")) or truthy(
        summary.get("a_replay_sglang_scheduler_priority_applied")
    ):
        return "applied"
    if truthy(summary.get("a_first_sglang_priority_hint_seen")) or truthy(
        summary.get("a_replay_sglang_priority_hint_seen")
    ):
        return "seen"
    if maybe_int(summary.get("a_first_sglang_worker_agent_hints_priority")) is not None or maybe_int(
        summary.get("a_replay_sglang_worker_agent_hints_priority")
    ) is not None:
        return "worker_value_only"
    return "none"


def public_effect_status(summary: dict[str, Any]) -> str:
    survived = str(summary.get("a_survived_cache_threshold", "")).strip().lower()
    if survived == "true":
        return "survived"
    if survived == "false":
        return "not_survived"
    return "unknown"


def build_public_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": summary.get("run_id", ""),
        "model": summary.get("model", ""),
        "kv_tier": summary.get("kv_tier_mode", ""),
        "hint_profile": summary.get("protected_hint_profile", ""),
        "protected_cache": summary.get("protected_cache_control_profile", ""),
        "doc_mode": summary.get("cache_control_doc_mode", ""),
        "frontend_cc_flag": summary.get("cache_control_frontend_flag_status", ""),
        "pin_path": summary.get("cache_control_pin_path_status", ""),
        "pinned_ratio": summary.get("cache_control_pinned_ratio", ""),
        "write_policy": summary.get("cache_control_write_policy", ""),
        "distractors": summary.get("distractor_count", ""),
        "first_status": summary.get("a_first_status", ""),
        "replay_status": summary.get("a_replay_status", ""),
        "first_ms": summary.get("a_first_latency_ms", ""),
        "replay_ms": summary.get("a_replay_latency_ms", ""),
        "replay_delta_ms": summary.get("a_replay_latency_delta_ms", ""),
        "replay_speedup": summary.get("a_replay_speedup_ratio", ""),
        "kv_cap": summary.get("worker_kv_capacity_tokens", ""),
        "ctx_len": summary.get("worker_context_len", ""),
        "a_tokens": summary.get("a_first_prompt_tokens", ""),
        "d1_tokens": summary.get("first_distractor_prompt_tokens", ""),
        "kv_left_after_a": summary.get("kv_tokens_left_after_a", ""),
        "replay_cached": summary.get("a_replay_cached_tokens", ""),
        "replay_reuse": summary.get("a_replay_cache_reuse_ratio", ""),
        "survived": summary.get("a_survived_cache_threshold", ""),
        "survival_source": summary.get("cache_survival_source", ""),
        "req_prio_status": compact_priority_status(
            summary.get("a_first_agent_hints_priority"),
            summary.get("a_replay_agent_hints_priority"),
        ),
        "req_prio_values": compact_priority_values(
            ("a_first", summary.get("a_first_agent_hints_priority")),
            ("a_replay", summary.get("a_replay_agent_hints_priority")),
        ),
        "worker_prio_status": worker_priority_status(summary),
        "worker_prio_values": compact_priority_values(
            ("a_first", summary.get("a_first_sglang_worker_agent_hints_priority")),
            ("a_replay", summary.get("a_replay_sglang_worker_agent_hints_priority")),
        ),
        "replay_evicts": summary.get("a_replay_sglang_cache_evict_events", ""),
        "replay_evict_cache": summary.get("a_replay_sglang_evict_cache_control_values", ""),
        "replay_evict_cache_match": summary.get("a_replay_sglang_evict_cache_control_match", ""),
        "replay_evict_hint_match": summary.get("a_replay_sglang_evict_hint_profile_match", ""),
        "replay_evict_status": summary.get("a_replay_sglang_evict_identity_status", ""),
        "effect_status": public_effect_status(summary),
    }


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
    evict_identity_status, evict_cache_control_match, evict_hint_profile_match = evict_identity_evidence(
        replay=replay,
        protected_hint_profile_value=first.get("hint_profile", args.protected_hint_profile),
        protected_cache_control_profile_value=first.get("cache_control_profile", args.protected_cache_control_profile),
    )

    failed = [row for row in rows if str(row.get("status")) not in {"200", "201"}]
    summary = {
        "run_id": run_id,
        "model": args.model,
        "kv_tier_mode": args.kv_tier_mode,
        "protected_hint_profile": args.protected_hint_profile,
        "distractor_hint_profile": args.distractor_hint_profile,
        "protected_cache_control_profile": first.get("cache_control_profile", ""),
        "distractor_cache_control_profile": first_distractor.get("cache_control_profile", ""),
        "cache_control_doc_mode": args.cache_control_doc_mode,
        "cache_control_frontend_flag_status": args.cache_control_frontend_flag_status,
        "cache_control_pin_path_status": args.cache_control_pin_path_status,
        "cache_control_pinned_ratio": args.cache_control_pinned_ratio,
        "cache_control_write_policy": args.cache_control_write_policy,
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
        "a_first_top_level_priority_mode": first.get("top_level_priority_mode", ""),
        "a_first_top_level_priority_attempted": truthy(first.get("top_level_priority_attempted")),
        "a_first_top_level_priority_sent": truthy(first.get("top_level_priority_sent")),
        "a_first_top_level_priority_value": int_or_empty(first.get("top_level_priority_value")),
        "a_first_top_level_priority_fallback_used": truthy(first.get("top_level_priority_fallback_used")),
        "a_first_top_level_priority_unsupported": truthy(first.get("top_level_priority_unsupported")),
        "a_first_cached_tokens": int_or_empty(first.get("cached_prompt_tokens")),
        "a_replay_agent_hints_priority": int_or_empty(replay.get("agent_hints_priority")),
        "a_replay_top_level_priority_mode": replay.get("top_level_priority_mode", ""),
        "a_replay_top_level_priority_attempted": truthy(replay.get("top_level_priority_attempted")),
        "a_replay_top_level_priority_sent": truthy(replay.get("top_level_priority_sent")),
        "a_replay_top_level_priority_value": int_or_empty(replay.get("top_level_priority_value")),
        "a_replay_top_level_priority_fallback_used": truthy(replay.get("top_level_priority_fallback_used")),
        "a_replay_top_level_priority_unsupported": truthy(replay.get("top_level_priority_unsupported")),
        "a_replay_cached_tokens": int_or_empty(replay.get("cached_prompt_tokens")),
        "a_replay_cache_reuse_ratio": round_ratio(replay_ratio),
        "a_replay_prompt_tokens": int_or_empty(replay.get("prompt_tokens")),
        "a_first_sglang_cache_events": int_or_empty(first.get("sglang_cache_events")),
        "a_replay_sglang_cache_events": int_or_empty(replay.get("sglang_cache_events")),
        "a_replay_sglang_cache_match_events": int_or_empty(replay.get("sglang_cache_match_events")),
        "a_replay_sglang_cache_evict_events": int_or_empty(replay.get("sglang_cache_evict_events")),
        "a_replay_sglang_cache_semantic_tokens": int_or_empty(replay.get("sglang_cache_semantic_tokens")),
        "a_replay_sglang_cache_direct": truthy(replay.get("sglang_cache_direct")),
        "a_replay_sglang_evict_cache_control_values": replay.get("sglang_evict_cache_control_values", ""),
        "a_replay_sglang_evict_hint_profiles": replay.get("sglang_evict_hint_profiles", ""),
        "a_replay_sglang_evict_cache_control_match": evict_cache_control_match,
        "a_replay_sglang_evict_hint_profile_match": evict_hint_profile_match,
        "a_replay_sglang_evict_identity_status": evict_identity_status,
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
        f"- protected_cache_control_profile: `{summary['protected_cache_control_profile']}`",
        f"- distractor_cache_control_profile: `{summary['distractor_cache_control_profile']}`",
        f"- cache_control_doc_mode: `{summary['cache_control_doc_mode']}`",
        f"- cache_control_frontend_flag_status: `{summary['cache_control_frontend_flag_status']}`",
        f"- cache_control_pin_path_status: `{summary['cache_control_pin_path_status']}`",
        f"- cache_control_pinned_ratio: `{summary['cache_control_pinned_ratio']}`",
        f"- cache_control_write_policy: `{summary['cache_control_write_policy']}`",
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
        f"- replay top-level priority mode: `{summary['a_replay_top_level_priority_mode']}`",
        f"- replay top-level priority attempted: `{summary['a_replay_top_level_priority_attempted']}`",
        f"- replay top-level priority fallback used: `{summary['a_replay_top_level_priority_fallback_used']}`",
        f"- replay top-level priority unsupported: `{summary['a_replay_top_level_priority_unsupported']}`",
        f"- replay cached tokens: `{summary['a_replay_cached_tokens']}`",
        f"- replay cache reuse ratio: `{summary['a_replay_cache_reuse_ratio']}`",
        f"- replay SGLang cache events: `{summary['a_replay_sglang_cache_events']}`",
        f"- replay SGLang cache match events: `{summary['a_replay_sglang_cache_match_events']}`",
        f"- replay SGLang evict events: `{summary['a_replay_sglang_cache_evict_events']}`",
        f"- replay SGLang cache direct attribution: `{summary['a_replay_sglang_cache_direct']}`",
        f"- replay SGLang evict cache-control values: `{summary['a_replay_sglang_evict_cache_control_values']}`",
        f"- replay SGLang evict hint profiles: `{summary['a_replay_sglang_evict_hint_profiles']}`",
        f"- replay SGLang evict cache-control match: `{summary['a_replay_sglang_evict_cache_control_match']}`",
        f"- replay SGLang evict hint-profile match: `{summary['a_replay_sglang_evict_hint_profile_match']}`",
        f"- replay SGLang evict identity status: `{summary['a_replay_sglang_evict_identity_status']}`",
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
    public_summary_csv = run_dir / "retention_probe_public_summary.csv"
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
        protected_prompt = make_protected_prompt(
            role="protected_A",
            target_len=args.protected_input_len,
            seed=args.seed,
            isolation_mode=args.prompt_isolation_mode,
        )
        rows: list[dict[str, Any]] = []

        sequence: list[tuple[str, str, str, str]] = [
            ("a_first", protected_prompt, args.protected_hint_profile, args.protected_cache_control_profile),
        ]
        for idx in range(args.distractor_count):
            distractor = make_prompt(
                role=f"distractor_{idx:04d}",
                target_len=args.distractor_input_len,
                seed=args.seed,
            )
            sequence.append(
                (
                    f"distractor_{idx:04d}",
                    distractor,
                    args.distractor_hint_profile,
                    args.distractor_cache_control_profile,
                )
            )
        sequence.append(("a_replay", protected_prompt, args.protected_hint_profile, args.protected_cache_control_profile))

        print(f"KV retention probe run_id={run_id}")
        print(f"model={args.model}")
        print(f"prompt_generator_version={PROMPT_GENERATOR_VERSION}")
        print(f"prompt_isolation_mode={args.prompt_isolation_mode}")
        print(
            "requests="
            f"{len(sequence)} protected_hint_profile={args.protected_hint_profile} "
            f"protected_cache_control_profile={args.protected_cache_control_profile}"
        )

        for sequence_index, (request_role, prompt, hint_profile, cache_control_profile) in enumerate(sequence):
            print(
                f"[{sequence_index + 1}/{len(sequence)}] {request_role} "
                f"hint_profile={hint_profile} cache_control_profile={cache_control_profile}",
                flush=True,
            )
            row = send_probe_request(
                args=args,
                run_id=run_id,
                sequence_index=sequence_index,
                request_role=request_role,
                prompt=prompt,
                hint_profile=hint_profile,
                cache_control_profile=cache_control_profile,
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
    write_csv(public_summary_csv, [build_public_summary(summary)], PUBLIC_SUMMARY_COLUMNS)
    if not args.skip_matrix_write:
        if args.append_matrix:
            append_matrix(matrix_path, summary, SUMMARY_COLUMNS)
        else:
            write_csv(matrix_path, [summary], SUMMARY_COLUMNS)
    write_summary_md(summary_md, summary)

    print(f"Request rows: {requests_csv}")
    print(f"Run summary:  {summary_csv}")
    print(f"Public CSV:   {public_summary_csv}")
    print(f"Summary md:   {summary_md}")
    print(f"Matrix:       {matrix_path}")
    return 1 if summary["failed_requests"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
