#!/usr/bin/env python3

"""Minimal async load generator for OpenAI-style chat requests."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def post_json(
    url: str, payload: dict, timeout_s: int
) -> tuple[int | None, dict | None, str | None, float]:
    start = time.time()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
            latency_ms = (time.time() - start) * 1000.0
            return resp.status, json.loads(body), None, latency_ms
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        latency_ms = (time.time() - start) * 1000.0
        return exc.code, None, body, latency_ms
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.time() - start) * 1000.0
        return None, None, repr(exc), latency_ms


async def one_request(
    frontend_url: str,
    model: str,
    request_obj: dict,
    *,
    experiment_name: str,
    router_mode: str,
    max_tokens: int,
    temperature: float,
    request_timeout_s: int,
) -> dict:
    payload = {
        "model": model,
        "messages": request_obj["messages"],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "nvext": {"agent_hints": request_obj.get("hint_payload", {})},
    }
    status, body, error, latency_ms = await asyncio.to_thread(
        post_json, frontend_url, payload, request_timeout_s
    )
    usage = body.get("usage", {}) if body else {}
    prompt_details = usage.get("prompt_tokens_details", {}) if usage else {}
    nvext = body.get("nvext", {}) if body else {}
    timing = nvext.get("timing", {}) if nvext else {}
    worker_id = nvext.get("worker_id", {}) if nvext else {}
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment_name": experiment_name,
        "router_mode": router_mode,
        "model": model,
        "request_id": request_obj["request_id"],
        "prompt_id": request_obj["prompt_id"],
        "workload_name": request_obj["workload_name"],
        "shared_prefix_group": request_obj["shared_prefix_group"],
        "hint_payload": request_obj["hint_payload"],
        "status_code": status,
        "success": body is not None and status == 200,
        "error": error,
        "latency_ms": round(latency_ms, 3),
        "ttft_ms": timing.get("ttft_ms"),
        "kv_hit_rate": timing.get("kv_hit_rate"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cached_tokens": prompt_details.get("cached_tokens"),
        "worker_id": worker_id or None,
        "response_id": body.get("id") if body else None,
        "raw_response": body,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-url", default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B")
    parser.add_argument("--workload-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--experiment-name", default="unnamed_experiment")
    parser.add_argument("--router-mode", default="unknown")
    parser.add_argument("--request-timeout-s", type=int, default=120)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args()

    requests = [json.loads(line) for line in Path(args.workload_file).read_text().splitlines() if line.strip()]
    semaphore = asyncio.Semaphore(args.concurrency)

    async def guarded(req: dict) -> dict:
        async with semaphore:
            return await one_request(
                args.frontend_url,
                args.model,
                req,
                experiment_name=args.experiment_name,
                router_mode=args.router_mode,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                request_timeout_s=args.request_timeout_s,
            )

    results = await asyncio.gather(*(guarded(req) for req in requests))
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for item in results:
            fh.write(json.dumps(item, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
