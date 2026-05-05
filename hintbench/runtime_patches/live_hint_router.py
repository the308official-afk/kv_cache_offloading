#!/usr/bin/env python3

"""Lightweight live hint-aware routing shim.

This is a small HTTP proxy that:

- accepts OpenAI-style chat completion requests
- reads `nvext.agent_hints`
- scores configured upstream targets with the local hint router policy
- forwards the request to the chosen upstream
- records a structured routing decision log

Important:
- if you configure only one upstream, this shim cannot change worker choice
  inside the stock Dynamo frontend; it can only log the intended decision
- to affect live routing, you need multiple upstream targets or a deeper custom
  frontend/runtime integration
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hintbench.runtime_patches.hint_router_policy import (
    WorkerSnapshot,
    choose_worker,
)


def load_upstreams(raw: str) -> list[dict[str, str]]:
    payload = json.loads(raw)
    if not isinstance(payload, list) or not payload:
        raise ValueError("HINTBENCH_UPSTREAMS_JSON must be a non-empty JSON list.")
    normalized = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each upstream entry must be a JSON object.")
        worker_id = item.get("worker_id")
        url = item.get("url")
        if not worker_id or not url:
            raise ValueError("Each upstream entry needs worker_id and url.")
        normalized.append({"worker_id": str(worker_id), "url": str(url)})
    return normalized


def post_json(url: str, payload: dict[str, Any], timeout_s: int) -> tuple[int | None, bytes, dict[str, str]]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read()
            return resp.status, body, dict(resp.headers.items())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items())
    except Exception as exc:  # noqa: BLE001
        return None, json.dumps({"error": repr(exc)}).encode("utf-8"), {"Content-Type": "application/json"}


@dataclass
class UpstreamState:
    worker_id: str
    url: str
    queue_depth: float = 0.0
    recent_kv_hit_rate: float = 0.0
    cached_prefix_tokens: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.cached_prefix_tokens is None:
            self.cached_prefix_tokens = {}


class RouterState:
    def __init__(self, upstreams: list[dict[str, str]], log_file: Path, timeout_s: int) -> None:
        self.upstreams = {
            item["worker_id"]: UpstreamState(worker_id=item["worker_id"], url=item["url"])
            for item in upstreams
        }
        self.backend_workers: dict[str, UpstreamState] = {}
        self.log_file = log_file
        self.timeout_s = timeout_s
        self.lock = threading.Lock()
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def snapshots_for_group(self, shared_prefix_group: str) -> list[WorkerSnapshot]:
        return [
            WorkerSnapshot(
                worker_id=state.worker_id,
                queue_depth=state.queue_depth,
                cached_prefix_tokens=state.cached_prefix_tokens.get(shared_prefix_group, 0),
                recent_kv_hit_rate=state.recent_kv_hit_rate,
            )
            for state in self.upstreams.values()
        ]

    def backend_snapshots_for_group(self, shared_prefix_group: str) -> list[WorkerSnapshot]:
        return [
            WorkerSnapshot(
                worker_id=state.worker_id,
                queue_depth=state.queue_depth,
                cached_prefix_tokens=state.cached_prefix_tokens.get(shared_prefix_group, 0),
                recent_kv_hit_rate=state.recent_kv_hit_rate,
            )
            for state in self.backend_workers.values()
        ]

    def update_backend_worker(
        self,
        worker_id: str | None,
        shared_prefix_group: str,
        observed_cached_tokens: int | None,
    ) -> None:
        if not worker_id:
            return
        state = self.backend_workers.get(worker_id)
        if state is None:
            state = UpstreamState(worker_id=worker_id, url="")
            self.backend_workers[worker_id] = state
        if observed_cached_tokens is not None:
            state.cached_prefix_tokens[shared_prefix_group] = max(
                state.cached_prefix_tokens.get(shared_prefix_group, 0),
                int(observed_cached_tokens),
            )
            state.recent_kv_hit_rate = 1.0 if observed_cached_tokens > 0 else 0.0

    def complete_request(
        self,
        worker_id: str,
        shared_prefix_group: str,
        observed_cached_tokens: int | None,
    ) -> None:
        state = self.upstreams[worker_id]
        state.queue_depth = max(state.queue_depth - 1.0, 0.0)
        if observed_cached_tokens is not None:
            state.cached_prefix_tokens[shared_prefix_group] = max(
                state.cached_prefix_tokens.get(shared_prefix_group, 0),
                int(observed_cached_tokens),
            )
            state.recent_kv_hit_rate = 1.0 if observed_cached_tokens > 0 else 0.0

    def write_log(self, row: dict[str, Any]) -> None:
        with self.log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")


class HintRouterHandler(BaseHTTPRequestHandler):
    router_state: RouterState

    def _send_json(self, status_code: int, body: bytes, headers: dict[str, str]) -> None:
        self.send_response(status_code)
        content_type = headers.get("Content-Type", "application/json")
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            payload = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
            return

        if self.path == "/upstreams":
            payload = json.dumps(
                {
                    "upstreams": [
                        {
                            "worker_id": state.worker_id,
                            "url": state.url,
                            "queue_depth": state.queue_depth,
                            "recent_kv_hit_rate": state.recent_kv_hit_rate,
                            "cached_prefix_groups": state.cached_prefix_tokens,
                        }
                        for state in self.router_state.upstreams.values()
                    ]
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_error(404, "Not Found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        request_obj = json.loads(raw.decode("utf-8"))
        hint_payload = ((request_obj.get("nvext") or {}).get("agent_hints") or {})
        shared_prefix_group = str(
            hint_payload.get("shared_prefix_group")
            or request_obj.get("shared_prefix_group")
            or "default"
        )

        shadow_decision = None
        with self.router_state.lock:
            snapshots = self.router_state.snapshots_for_group(shared_prefix_group)
            decision = choose_worker(snapshots, hint_payload)
            chosen = self.router_state.upstreams[decision.worker_id]
            chosen.queue_depth += 1.0
            backend_snapshots = self.router_state.backend_snapshots_for_group(shared_prefix_group)
            if backend_snapshots:
                shadow_decision = choose_worker(backend_snapshots, hint_payload)

        start = time.time()
        status_code, body, headers = post_json(chosen.url, request_obj, self.router_state.timeout_s)
        latency_ms = round((time.time() - start) * 1000.0, 3)

        cached_tokens = None
        response_id = None
        actual_worker_id = None
        actual_prefill_worker_id = None
        actual_decode_worker_id = None
        try:
            parsed = json.loads(body.decode("utf-8"))
            usage = parsed.get("usage", {})
            prompt_details = usage.get("prompt_tokens_details", {}) if usage else {}
            cached_tokens = prompt_details.get("cached_tokens")
            response_id = parsed.get("id")
            nvext = parsed.get("nvext", {}) if parsed else {}
            worker_id = nvext.get("worker_id", {}) if nvext else {}
            if worker_id:
                actual_worker_id = worker_id
                actual_prefill_worker_id = worker_id.get("prefill_worker_id")
                actual_decode_worker_id = worker_id.get("decode_worker_id")
        except Exception:  # noqa: BLE001
            parsed = None

        with self.router_state.lock:
            self.router_state.complete_request(
                chosen.worker_id,
                shared_prefix_group,
                observed_cached_tokens=cached_tokens,
            )
            self.router_state.update_backend_worker(
                actual_prefill_worker_id,
                shared_prefix_group,
                observed_cached_tokens=cached_tokens,
            )
            if actual_decode_worker_id != actual_prefill_worker_id:
                self.router_state.update_backend_worker(
                    actual_decode_worker_id,
                    shared_prefix_group,
                    observed_cached_tokens=cached_tokens,
                )
            self.router_state.write_log(
                {
                    "timestamp": time.time(),
                    "path": self.path,
                    "shared_prefix_group": shared_prefix_group,
                    "hint_payload": hint_payload,
                    "chosen_worker_id": chosen.worker_id,
                    "upstream_url": chosen.url,
                    "score": round(decision.score, 4),
                    "cache_score": round(decision.cache_score, 4),
                    "load_score": round(decision.load_score, 4),
                    "priority_score": round(decision.priority_score, 4),
                    "explanation": decision.explanation,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "cached_tokens": cached_tokens,
                    "response_id": response_id,
                    "shadow_preferred_backend_worker_id": (
                        shadow_decision.worker_id if shadow_decision else None
                    ),
                    "shadow_score": round(shadow_decision.score, 4) if shadow_decision else None,
                    "shadow_cache_score": (
                        round(shadow_decision.cache_score, 4) if shadow_decision else None
                    ),
                    "shadow_load_score": (
                        round(shadow_decision.load_score, 4) if shadow_decision else None
                    ),
                    "shadow_priority_score": (
                        round(shadow_decision.priority_score, 4) if shadow_decision else None
                    ),
                    "shadow_explanation": shadow_decision.explanation if shadow_decision else None,
                    "actual_worker_id": actual_worker_id,
                    "actual_prefill_worker_id": actual_prefill_worker_id,
                    "actual_decode_worker_id": actual_decode_worker_id,
                }
            )

        if status_code is None:
            body = json.dumps({"error": "Upstream request failed"}).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            status_code = 502

        self._send_json(status_code, body, headers)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument(
        "--upstreams-json",
        default=None,
        help="Optional JSON list of upstreams. Defaults to HINTBENCH_UPSTREAMS_JSON env var.",
    )
    parser.add_argument(
        "--log-file",
        default="hintbench/results/live_hint_router/decisions.jsonl",
        help="Where to write routing decisions.",
    )
    parser.add_argument("--request-timeout-s", type=int, default=120)
    args = parser.parse_args()

    raw_upstreams = args.upstreams_json or os.environ.get("HINTBENCH_UPSTREAMS_JSON")
    if not raw_upstreams:
        raise SystemExit(
            "Provide upstreams with --upstreams-json or HINTBENCH_UPSTREAMS_JSON. "
            'Example: [{"worker_id":"frontend-a","url":"http://127.0.0.1:8000/v1/chat/completions"}]'
        )

    upstreams = load_upstreams(raw_upstreams)
    state = RouterState(
        upstreams=upstreams,
        log_file=Path(args.log_file),
        timeout_s=args.request_timeout_s,
    )
    HintRouterHandler.router_state = state

    server = ThreadingHTTPServer((args.host, args.port), HintRouterHandler)
    print(f"Live hint router listening on http://{args.host}:{args.port}")
    print(f"Upstreams: {json.dumps(upstreams)}")
    print(f"Decision log: {args.log_file}")
    server.serve_forever()


if __name__ == "__main__":
    main()
