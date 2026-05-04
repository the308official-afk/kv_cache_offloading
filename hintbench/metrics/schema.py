#!/usr/bin/env python3

"""Minimal result schema notes for Phase 1."""

REQUEST_FIELDS = [
    "request_id",
    "experiment_name",
    "workload_name",
    "router_mode",
    "model",
    "prompt_id",
    "shared_prefix_group",
    "hint_payload",
]

RESULT_FIELDS = [
    "success",
    "status_code",
    "error",
    "latency_ms",
    "ttft_ms",
    "completion_tokens",
    "prompt_tokens",
    "cached_tokens",
    "worker_id",
    "timestamp",
]


if __name__ == "__main__":
    print("REQUEST_FIELDS =", REQUEST_FIELDS)
    print("RESULT_FIELDS =", RESULT_FIELDS)

