#!/usr/bin/env python3

"""Simple deterministic hint policy used for early experiments."""

from __future__ import annotations


def build_hint(priority: int = 5, reuse_likelihood: float = 0.9, agent_phase: str = "execution") -> dict:
    return {
        "priority": priority,
        "reuse_likelihood": reuse_likelihood,
        "agent_phase": agent_phase,
        "expected_output_tokens": 128,
    }


if __name__ == "__main__":
    print(build_hint())

