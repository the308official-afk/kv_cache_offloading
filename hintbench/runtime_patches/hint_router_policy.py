#!/usr/bin/env python3

"""First hint-aware routing policy scaffold.

This module does not patch Dynamo directly yet. Instead, it defines:

- a normalized hint schema
- a worker snapshot format
- a transparent scoring function for worker selection

The goal is to make the first routing policy concrete and testable before
integrating it into a custom frontend image.
"""

from __future__ import annotations

from dataclasses import dataclass


PHASE_WEIGHTS = {
    "planning": {"cache_bias": 0.2, "load_bias": 0.8},
    "execution": {"cache_bias": 0.7, "load_bias": 0.3},
    "decode": {"cache_bias": 0.85, "load_bias": 0.15},
    "prefill": {"cache_bias": 0.75, "load_bias": 0.25},
}


@dataclass(frozen=True)
class NormalizedHints:
    priority: int
    reuse_likelihood: float
    agent_phase: str
    expected_output_tokens: int
    latency_sla_ms: int | None = None


@dataclass(frozen=True)
class WorkerSnapshot:
    worker_id: str
    queue_depth: float
    cached_prefix_tokens: int
    recent_kv_hit_rate: float


@dataclass(frozen=True)
class RoutingDecision:
    worker_id: str
    score: float
    cache_score: float
    load_score: float
    priority_score: float
    explanation: str


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_hints(hints: dict | None) -> NormalizedHints:
    hints = hints or {}
    priority = int(hints.get("priority", 0) or 0)
    reuse_likelihood = clamp(float(hints.get("reuse_likelihood", 0.5) or 0.5), 0.0, 1.0)
    agent_phase = str(hints.get("agent_phase", "execution") or "execution").lower()
    expected_output_tokens = int(hints.get("expected_output_tokens", 128) or 128)
    latency_sla_ms = hints.get("latency_sla_ms")
    if latency_sla_ms is not None:
        latency_sla_ms = int(latency_sla_ms)

    return NormalizedHints(
        priority=priority,
        reuse_likelihood=reuse_likelihood,
        agent_phase=agent_phase,
        expected_output_tokens=expected_output_tokens,
        latency_sla_ms=latency_sla_ms,
    )


def phase_weights(agent_phase: str) -> dict[str, float]:
    return PHASE_WEIGHTS.get(agent_phase, PHASE_WEIGHTS["execution"])


def compute_worker_score(worker: WorkerSnapshot, hints: NormalizedHints) -> RoutingDecision:
    weights = phase_weights(hints.agent_phase)

    cache_tokens = max(worker.cached_prefix_tokens, 0)
    cache_score = hints.reuse_likelihood * (
        (cache_tokens / max(cache_tokens, 128)) * 0.7 + worker.recent_kv_hit_rate * 0.3
    )
    cache_score = clamp(cache_score, 0.0, 1.0)

    load_score = 1.0 / (1.0 + max(worker.queue_depth, 0.0))
    priority_score = clamp(hints.priority / 10.0, 0.0, 1.0)

    score = (
        weights["cache_bias"] * cache_score
        + weights["load_bias"] * load_score
        + 0.15 * priority_score
    )

    explanation = (
        f"phase={hints.agent_phase} cache={cache_score:.3f} "
        f"load={load_score:.3f} priority={priority_score:.3f}"
    )

    return RoutingDecision(
        worker_id=worker.worker_id,
        score=score,
        cache_score=cache_score,
        load_score=load_score,
        priority_score=priority_score,
        explanation=explanation,
    )


def choose_worker(workers: list[WorkerSnapshot], hint_payload: dict | None) -> RoutingDecision:
    if not workers:
        raise ValueError("At least one worker snapshot is required.")

    hints = normalize_hints(hint_payload)
    decisions = [compute_worker_score(worker, hints) for worker in workers]
    decisions.sort(key=lambda d: (d.score, d.cache_score, d.load_score), reverse=True)
    return decisions[0]
