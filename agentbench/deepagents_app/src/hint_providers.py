"""Hint-provider adapters for AgentBench / Deep Agents runs.

Deep Agents does not natively define Dynamo/SGLang cache hints. This module
keeps the research-specific mapping small and easy to disable.
"""

from __future__ import annotations

from typing import Any


HINT_PROVIDER_AGENTBENCH = "agentbench"
HINT_PROVIDER_DEEPAGENTS = "deepagents"
HINT_PROVIDER_NONE = "none"
HINT_PROVIDERS = (
    HINT_PROVIDER_AGENTBENCH,
    HINT_PROVIDER_DEEPAGENTS,
    HINT_PROVIDER_NONE,
)


DEEPAGENTS_PHASE_POLICIES: dict[str, dict[str, Any]] = {
    "baseline_execution": {
        "priority": 6,
        "reuse_likelihood": 0.85,
        "latency_sensitivity": 0.6,
        "expected_output_tokens": 2048,
        "hint_decision_reason": "baseline execution expects long repository context and direct code work",
    },
    "planning": {
        "priority": 4,
        "reuse_likelihood": 0.8,
        "latency_sensitivity": 0.4,
        "expected_output_tokens": 768,
        "hint_decision_reason": "planning usually reuses the task and repository context but is less latency critical",
    },
    "execution": {
        "priority": 8,
        "reuse_likelihood": 0.95,
        "latency_sensitivity": 0.5,
        "expected_output_tokens": 2048,
        "hint_decision_reason": "execution is most likely to reuse repository context and call tools repeatedly",
    },
    "patch_generation": {
        "priority": 6,
        "reuse_likelihood": 0.9,
        "latency_sensitivity": 0.4,
        "expected_output_tokens": 1024,
        "hint_decision_reason": "patch generation reuses prior phase context and should preserve cached prefixes",
    },
    "review": {
        "priority": 5,
        "reuse_likelihood": 0.75,
        "latency_sensitivity": 0.8,
        "expected_output_tokens": 1024,
        "hint_decision_reason": "review is shorter and more latency sensitive while still sharing patch context",
    },
}


def normalize_hint_provider(value: str | None) -> str:
    provider = (value or HINT_PROVIDER_AGENTBENCH).strip().lower().replace("_", "-")
    if provider not in HINT_PROVIDERS:
        raise ValueError(
            f"Unknown hint provider {value!r}. Choose one of: {', '.join(HINT_PROVIDERS)}"
        )
    return provider


def build_hint_payload(
    *,
    provider: str,
    default_hints: dict[str, Any],
    base_hints: dict[str, Any] | None,
    phase: str,
    request_context: dict[str, Any] | None = None,
    expected_output_tokens: int | None = None,
    sequence_index: int | None = None,
) -> dict[str, Any]:
    """Return the hint payload to send as ``nvext.agent_hints``.

    ``none`` deliberately returns an empty dict so callers can omit
    ``agent_hints`` from the request while still sending request context.
    """

    provider = normalize_hint_provider(provider)
    if provider == HINT_PROVIDER_NONE:
        return {}

    hints = dict(default_hints)
    if base_hints:
        hints.update(base_hints)

    if provider == HINT_PROVIDER_DEEPAGENTS:
        policy = DEEPAGENTS_PHASE_POLICIES.get(phase, DEEPAGENTS_PHASE_POLICIES["execution"])
        if hints.get("hint_profile"):
            hints["agentbench_hint_profile_seed"] = hints["hint_profile"]
        hints.update(policy)
        hints["hint_source"] = "deepagents_app.runtime_state"
        hints["hint_profile"] = "deepagents-derived"
    else:
        hints["hint_source"] = "agentbench.request_wrapper"

    if expected_output_tokens is not None:
        hints["expected_output_tokens"] = expected_output_tokens
    if sequence_index is not None:
        hints["phase_sequence_index"] = sequence_index

    hints["hint_provider"] = provider
    hints["agent_phase"] = phase
    context = request_context or {}
    if context.get("request_id"):
        hints["request_id"] = context["request_id"]
    return hints
