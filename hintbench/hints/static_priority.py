#!/usr/bin/env python3

"""Simple deterministic hint policy used for early experiments."""

from __future__ import annotations


def build_hint(
    priority: int = 5,
    reuse_likelihood: float = 0.9,
    agent_phase: str = "execution",
    latency_sensitivity: float = 0.7,
    program_id: str = "hintbench.shared_prefix",
    context_type: str = "multi_turn_shared_prefix",
) -> dict:
    return {
        "priority": priority,
        "reuse_likelihood": reuse_likelihood,
        "agent_phase": agent_phase,
        "latency_sensitivity": latency_sensitivity,
        "program_id": program_id,
        "context_type": context_type,
        "expected_output_tokens": 128,
    }


if __name__ == "__main__":
    print(build_hint())
