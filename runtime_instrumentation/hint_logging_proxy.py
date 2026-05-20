#!/usr/bin/env python3
"""Small HTTP proxy that logs AgentBench hint payloads before Dynamo receives them."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

RUNTIME_JSON_PREFIX = "[RUNTIME_JSON]"


def sanitize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): sanitize(item) for key, item in value.items() if key is not None}
    if isinstance(value, (list, tuple, set)):
        return [sanitize(item) for item in value]
    return str(value)


def extract_agent_hints_with_source(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    nvext = payload.get("nvext")
    if isinstance(nvext, dict):
        agent_hints = nvext.get("agent_hints")
        if isinstance(agent_hints, dict):
            return sanitize(agent_hints), "nvext.agent_hints"

    extra_args = payload.get("extra_args")
    if isinstance(extra_args, dict):
        runtime_observability = extra_args.get("runtime_observability")
        if isinstance(runtime_observability, dict):
            agent_hints = runtime_observability.get("agent_hints")
            if isinstance(agent_hints, dict):
                return sanitize(agent_hints), "extra_args.runtime_observability.agent_hints"
            nested_nvext = runtime_observability.get("nvext")
            if isinstance(nested_nvext, dict):
                agent_hints = nested_nvext.get("agent_hints")
                if isinstance(agent_hints, dict):
                    return (
                        sanitize(agent_hints),
                        "extra_args.runtime_observability.nvext.agent_hints",
                    )

    return None, "missing"


def agent_hint_log_fields(payload: dict[str, Any]) -> dict[str, Any]:
    agent_hints, source = extract_agent_hints_with_source(payload)
    if not isinstance(agent_hints, dict):
        return {
            "agent_hints": None,
            "agent_hints_source": source,
            "agent_hints_keys": [],
            "hint_probe_id": None,
        }
    return {
        "agent_hints": agent_hints,
        "agent_hints_source": source,
        "agent_hints_keys": sorted(str(key) for key in agent_hints),
        "hint_probe_id": agent_hints.get("hint_probe_id"),
    }


class RuntimeLogger:
    def __init__(self, log_file: Path | None) -> None:
        self.log_file = log_file
        self._lock = threading.Lock()
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            self.log_file.write_text("", encoding="utf-8")

    def emit(self, event: dict[str, Any]) -> None:
        line = f"{RUNTIME_JSON_PREFIX} {json.dumps(sanitize(event), sort_keys=True, separators=(',', ':'))}"
        with self._lock:
            print(line, flush=True)
            if self.log_file:
                with self.log_file.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")


def build_handler(target_base: str, logger: RuntimeLogger) -> type[BaseHTTPRequestHandler]:
    class HintLoggingProxyHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: object) -> None:
            print(f"[hint-proxy] {self.address_string()} - {format % args}", file=sys.stderr)

        def do_GET(self) -> None:
            self._forward()

        def do_POST(self) -> None:
            self._forward()

        def _forward(self) -> None:
            started = time.time()
            raw_body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            request_payload: dict[str, Any] = {}
            if raw_body:
                try:
                    parsed = json.loads(raw_body.decode("utf-8"))
                    if isinstance(parsed, dict):
                        request_payload = parsed
                except json.JSONDecodeError:
                    request_payload = {}

            event: dict[str, Any] = {
                "event_type": "frontend.boundary.request_received",
                "component": "hint_logging_proxy",
                "method": self.command,
                "path": self.path,
                "model": request_payload.get("model"),
                "request_keys": sorted(str(key) for key in request_payload),
                **agent_hint_log_fields(request_payload),
            }
            logger.emit(event)

            target_url = urljoin(target_base.rstrip("/") + "/", self.path.lstrip("/"))
            headers = {
                key: value
                for key, value in self.headers.items()
                if key.lower()
                not in {
                    "connection",
                    "content-length",
                    "host",
                    "keep-alive",
                    "proxy-authenticate",
                    "proxy-authorization",
                    "te",
                    "trailers",
                    "transfer-encoding",
                    "upgrade",
                }
            }
            request = urllib.request.Request(
                target_url,
                data=raw_body if self.command not in {"GET", "HEAD"} else None,
                headers=headers,
                method=self.command,
            )

            try:
                with urllib.request.urlopen(request, timeout=self.server.forward_timeout) as response:  # type: ignore[attr-defined]
                    response_body = response.read()
                    self.send_response(response.status)
                    for key, value in response.headers.items():
                        if key.lower() in {"connection", "content-length", "transfer-encoding"}:
                            continue
                        self.send_header(key, value)
                    self.send_header("Content-Length", str(len(response_body)))
                    self.end_headers()
                    self.wfile.write(response_body)
                    status = response.status
            except urllib.error.HTTPError as exc:
                response_body = exc.read()
                self.send_response(exc.code)
                for key, value in exc.headers.items():
                    if key.lower() in {"connection", "content-length", "transfer-encoding"}:
                        continue
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
                status = exc.code
            except Exception as exc:  # pragma: no cover - defensive runtime path
                response_body = json.dumps({"error": str(exc)}).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
                status = 502

            logger.emit(
                {
                    "event_type": "frontend.boundary.request_completed",
                    "component": "hint_logging_proxy",
                    "method": self.command,
                    "path": self.path,
                    "status": status,
                    "elapsed_ms": round((time.time() - started) * 1000, 3),
                    "model": request_payload.get("model"),
                    **agent_hint_log_fields(request_payload),
                }
            )

    return HintLoggingProxyHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=8001)
    parser.add_argument("--target-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--log-file", default="/tmp/dynamo_hint_proxy_runtime.log")
    parser.add_argument("--forward-timeout", type=float, default=600.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_file = Path(args.log_file) if args.log_file else None
    logger = RuntimeLogger(log_file)
    handler = build_handler(args.target_base_url, logger)
    server = ThreadingHTTPServer((args.listen_host, args.listen_port), handler)
    server.forward_timeout = args.forward_timeout  # type: ignore[attr-defined]
    print(
        f"[hint-proxy] listening on http://{args.listen_host}:{args.listen_port}; "
        f"forwarding to {args.target_base_url}; log_file={log_file}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[hint-proxy] shutting down", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
