from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .redaction import REDACTED, sha256_short


@dataclass(frozen=True)
class HintFinding:
    path: str
    category: str
    example_safe_value: str


EXACT_HINT_CATEGORIES = {
    "nvext": "Unknown candidate field",
    "nvext.agent_hints": "Agent/workflow context",
    "nvext.agent_hints.priority": "Infrastructure scheduling hint",
    "nvext.agent_hints.latency_sensitivity": "Infrastructure scheduling hint",
    "nvext.agent_hints.osl": "Workload-shape hint",
    "nvext.agent_hints.speculative_prefill": "Workload-shape hint",
    "nvext.agent_hints.program_id": "Routing or affinity hint",
    "nvext.agent_hints.context_type": "Agent/workflow context",
    "nvext.cache_control": "Cache-control hint",
    "nvext.agent_context": "Agent/workflow context",
    "nvext.agent_context.workflow_type_id": "Agent/workflow context",
    "nvext.agent_context.workflow_id": "Agent/workflow context",
    "nvext.agent_context.program_id": "Routing or affinity hint",
    "nvext.agent_context.parent_program_id": "Routing or affinity hint",
    "prompt_cache_key": "Cache-control hint",
    "prompt_cache_options": "Cache-control hint",
    "prompt_cache_retention": "Cache-control hint",
    "service_tier": "Service-class hint",
    "reasoning": "Model-compute hint",
    "reasoning.effort": "Model-compute hint",
    "metadata": "Observability-only metadata",
    "store": "Standard generation parameter",
    "background": "Workload-shape hint",
    "max_output_tokens": "Standard generation parameter",
    "parallel_tool_calls": "Workload-shape hint",
    "cache_control": "Cache-control hint",
    "thinking": "Model-compute hint",
    "speed": "Service-class hint",
    "reasoning_effort": "Model-compute hint",
    "user_id": "Observability-only metadata",
    "user": "Observability-only metadata",
    "priority": "Infrastructure scheduling hint",
    "cache_id": "Cache-control hint",
    "session_id": "Routing or affinity hint",
}

HEADER_HINT_CATEGORIES = {
    "anthropic-version": "Authentication or protocol metadata",
    "anthropic-beta": "Authentication or protocol metadata",
    "openai-organization": "Authentication or protocol metadata",
    "openai-project": "Authentication or protocol metadata",
    "traceparent": "Observability-only metadata",
    "x-request-id": "Observability-only metadata",
}

OPENAI_STANDARD_FIELDS = {
    "model",
    "messages",
    "input",
    "instructions",
    "tools",
    "tool_choice",
    "temperature",
    "top_p",
    "n",
    "stream",
    "stop",
    "max_tokens",
    "max_completion_tokens",
    "max_output_tokens",
    "presence_penalty",
    "frequency_penalty",
    "logit_bias",
    "user",
    "response_format",
    "seed",
    "modalities",
    "audio",
    "prediction",
    "reasoning",
    "service_tier",
    "metadata",
    "store",
    "background",
    "parallel_tool_calls",
}

ANTHROPIC_STANDARD_FIELDS = {
    "model",
    "messages",
    "system",
    "max_tokens",
    "metadata",
    "stop_sequences",
    "stream",
    "temperature",
    "tool_choice",
    "tools",
    "top_k",
    "top_p",
    "thinking",
    "service_tier",
    "cache_control",
}


def detect_hints(payload: Any, headers: dict[str, str], endpoint: str = "") -> list[HintFinding]:
    paths_with_values = flatten_with_values(payload)
    findings: list[HintFinding] = []
    seen: set[str] = set()

    for name, value in headers.items():
        lower = name.lower()
        if lower in HEADER_HINT_CATEGORIES:
            findings.append(
                HintFinding(
                    path=f"header.{lower}",
                    category=HEADER_HINT_CATEGORIES[lower],
                    example_safe_value=safe_example(value),
                )
            )

    for path, value in paths_with_values:
        normalized = normalize_path(path)
        category = category_for_path(normalized)
        if category and normalized not in seen:
            seen.add(normalized)
            findings.append(
                HintFinding(
                    path=normalized,
                    category=category,
                    example_safe_value=safe_example(value),
                )
            )

    for top_key, value in top_level_unknowns(payload, endpoint):
        if top_key not in seen:
            findings.append(
                HintFinding(
                    path=top_key,
                    category="Unknown candidate field",
                    example_safe_value=safe_example(value),
                )
            )

    return sorted(findings, key=lambda item: item.path)


def category_for_path(path: str) -> str | None:
    if path in EXACT_HINT_CATEGORIES:
        return EXACT_HINT_CATEGORIES[path]
    if path.endswith(".cache_control") or ".cache_control" in path:
        return "Cache-control hint"
    if path.startswith("nvext."):
        return EXACT_HINT_CATEGORIES.get(path, "Unknown candidate field")
    if path.endswith(".reasoning_effort"):
        return "Model-compute hint"
    if "extra_body" in path:
        return "Unknown candidate field"
    return None


def flatten_with_values(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if prefix:
        rows.append((prefix, value))
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(flatten_with_values(item, child))
    elif isinstance(value, list):
        for item in value:
            child = f"{prefix}.[]" if prefix else "[]"
            rows.extend(flatten_with_values(item, child))
    return rows


def normalize_path(path: str) -> str:
    return path.replace(".[].", ".").replace("[]", "[]")


def safe_example(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if len(value) <= 80 and not looks_secretish(value):
            return value
        return f"<string chars={len(value)} sha256_16={sha256_short(value)}>"
    if isinstance(value, list):
        return f"<array length={len(value)}>"
    if isinstance(value, dict):
        return f"<object keys={len(value)}>"
    return f"<{type(value).__name__}>"


def looks_secretish(value: str) -> bool:
    lower = value.lower()
    return (
        "bearer " in lower
        or "sk-" in lower
        or "token" in lower
        or "api_key" in lower
        or len(value) > 120
    )


def top_level_unknowns(payload: Any, endpoint: str) -> list[tuple[str, Any]]:
    if not isinstance(payload, dict):
        return []
    standard = standard_fields_for_endpoint(endpoint)
    return [(key, value) for key, value in payload.items() if key not in standard]


def standard_fields_for_endpoint(endpoint: str) -> set[str]:
    if "messages" in endpoint:
        return ANTHROPIC_STANDARD_FIELDS
    if "responses" in endpoint or "chat/completions" in endpoint:
        return OPENAI_STANDARD_FIELDS
    return OPENAI_STANDARD_FIELDS | ANTHROPIC_STANDARD_FIELDS

