#!/usr/bin/env python3
"""Verify NeMo Agent Toolkit's Dynamo client path injects nvext hints.

This diagnostic intentionally uses NeMo Agent Toolkit's Dynamo transport instead
of AgentBench's local nvext glue. It first captures the HTTP request after the
NeMo transport mutates it, then optionally sends the same style of request to a
live Dynamo OpenAI-compatible frontend.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import inspect
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-url", default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-tokens", type=int, default=16)
    parser.add_argument("--skip-live", action="store_true")
    parser.add_argument("--total-requests", type=int, default=10)
    parser.add_argument("--osl", type=int, default=512)
    parser.add_argument("--iat", type=int, default=250)
    parser.add_argument("--max-sensitivity", type=int, default=1000)
    parser.add_argument("--latency-sensitivity", type=int, default=777)
    parser.add_argument("--prefix-id", default="")
    parser.add_argument("--enable-cache-control", action="store_true")
    return parser.parse_args()


def make_output_dir(path_arg: str) -> Path:
    if path_arg:
        path = Path(path_arg)
    else:
        path = Path("experiments/reports/nemo_dynamo_debug") / f"nemo_dynamo_debug_{time.strftime('%Y%m%d_%H%M%S')}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def endpoint_parts(frontend_url: str) -> tuple[str, str]:
    parsed = urlparse(frontend_url)
    if not parsed.scheme or not parsed.netloc:
        raise SystemExit(f"Invalid frontend URL: {frontend_url}")
    path = parsed.path or "/v1/chat/completions"
    if path.endswith("/v1/chat/completions"):
        base_path = path[: -len("/v1/chat/completions")]
        post_path = f"{base_path}/chat/completions"
    elif path.endswith("/chat/completions"):
        base_path = path[: -len("/chat/completions")]
        post_path = f"{base_path}/chat/completions"
    else:
        post_path = path
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    return base_url, post_path


def request_body(model: str, max_tokens: int) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise diagnostic assistant."},
            {"role": "user", "content": "Reply with exactly: NEMO_NVEXT_OK"},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }


class CaptureTransport:
    def __init__(self, httpx_module: Any) -> None:
        self._httpx = httpx_module
        self.captured: dict[str, Any] | None = None

    async def handle_async_request(self, request: Any) -> Any:
        content = request.content
        try:
            body = json.loads(content.decode("utf-8"))
        except Exception:
            body = {"_raw": content.decode("utf-8", errors="replace")}
        self.captured = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "json": body,
        }
        response_body = {
            "id": "nemo-nvext-capture",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "captured"}, "finish_reason": "stop"}],
        }
        return self._httpx.Response(200, json=response_body, request=request)


def build_transport(
    *,
    base_transport: Any,
    dynamo_llm: Any,
    args: argparse.Namespace,
) -> Any:
    cache_pin_type = None
    cache_control_mode = None
    if args.enable_cache_control:
        cache_pin_type = getattr(dynamo_llm.CachePinType, "EPHEMERAL", None)
        cache_control_mode = getattr(dynamo_llm.CacheControlMode, "ALWAYS", None)

    return dynamo_llm._DynamoTransport(
        transport=base_transport,
        total_requests=args.total_requests,
        osl=args.osl,
        iat=args.iat,
        cache_pin_type=cache_pin_type,
        cache_control_mode=cache_control_mode,
        max_sensitivity=args.max_sensitivity,
    )


@contextlib.contextmanager
def maybe_prefix_scope(dynamo_llm: Any, prefix_id: str):
    scope = getattr(getattr(dynamo_llm, "DynamoPrefixContext", None), "scope", None)
    if scope is None:
        yield
        return
    with scope(prefix_id):
        yield


@contextlib.contextmanager
def patched_latency_context(dynamo_llm: Any, latency_sensitivity: int, prefix_id: str):
    context_cls = getattr(dynamo_llm, "Context", None)
    original_get = inspect.getattr_static(context_cls, "get", None) if context_cls is not None else None
    if context_cls is None or original_get is None:
        yield
        return

    class _DiagnosticContext:
        workflow_run_id = prefix_id
        function_path: list[str] = []
        has_manual_latency_sensitivity = True

        def __init__(self, value: int) -> None:
            self.latency_sensitivity = value

    context_value = _DiagnosticContext(latency_sensitivity)
    try:
        context_cls.get = staticmethod(lambda: context_value)
        yield
    finally:
        context_cls.get = original_get


async def capture_request(args: argparse.Namespace, output_dir: Path, dynamo_llm: Any, httpx: Any) -> dict[str, Any]:
    capture = CaptureTransport(httpx)
    transport = build_transport(base_transport=capture, dynamo_llm=dynamo_llm, args=args)
    base_url, post_path = endpoint_parts(args.frontend_url)
    async with httpx.AsyncClient(transport=transport, base_url=base_url, timeout=args.timeout) as client:
        with patched_latency_context(dynamo_llm, args.latency_sensitivity, args.prefix_id), maybe_prefix_scope(dynamo_llm, args.prefix_id):
            await client.post(post_path, json=request_body(args.model, args.max_tokens))

    if capture.captured is None:
        raise RuntimeError("NeMo capture transport did not receive a request.")

    captured_path = output_dir / "captured_request_after_nemo_transport.json"
    captured_path.write_text(json.dumps(capture.captured, indent=2, sort_keys=True), encoding="utf-8")
    return capture.captured


async def live_request(args: argparse.Namespace, output_dir: Path, dynamo_llm: Any, httpx: Any) -> dict[str, Any]:
    transport = build_transport(
        base_transport=httpx.AsyncHTTPTransport(retries=0),
        dynamo_llm=dynamo_llm,
        args=args,
    )
    base_url, post_path = endpoint_parts(args.frontend_url)
    result: dict[str, Any] = {"skipped": False}

    try:
        async with httpx.AsyncClient(transport=transport, base_url=base_url, timeout=args.timeout) as client:
            with patched_latency_context(dynamo_llm, args.latency_sensitivity, args.prefix_id), maybe_prefix_scope(dynamo_llm, args.prefix_id):
                response = await client.post(post_path, json=request_body(args.model, args.max_tokens))
        result["status_code"] = response.status_code
        result["ok"] = 200 <= response.status_code < 300
        try:
            result["json"] = response.json()
        except Exception:
            result["text"] = response.text
    except Exception as exc:  # noqa: BLE001 - this is a diagnostic report.
        result["ok"] = False
        result["error"] = repr(exc)

    (output_dir / "live_response.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def extract_hints(captured: dict[str, Any]) -> dict[str, Any]:
    body = captured.get("json") if isinstance(captured, dict) else {}
    if not isinstance(body, dict):
        return {}
    nvext = body.get("nvext") or {}
    if not isinstance(nvext, dict):
        return {}
    hints = nvext.get("agent_hints") or {}
    if not isinstance(hints, dict):
        return {}
    return hints


def write_reports(output_dir: Path, summary: dict[str, Any]) -> None:
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# NeMo Dynamo nvext Diagnostic",
        "",
        f"- result: `{summary.get('result')}`",
        f"- model: `{summary.get('model')}`",
        f"- frontend_url: `{summary.get('frontend_url')}`",
        f"- captured_agent_hints_present: `{summary.get('captured_agent_hints_present')}`",
        f"- required_hint_keys_present: `{summary.get('required_hint_keys_present')}`",
        f"- live_ok: `{summary.get('live_ok')}`",
        "",
        "## Captured Agent Hints",
        "",
        "```json",
        json.dumps(summary.get("captured_agent_hints") or {}, indent=2, sort_keys=True),
        "```",
    ]
    if summary.get("error"):
        lines.extend(["", "## Error", "", f"`{summary.get('error')}`"])
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def async_main() -> int:
    args = parse_args()
    output_dir = make_output_dir(args.output_dir)
    if not args.prefix_id:
        args.prefix_id = f"agentbench-nemo-smoke-{time.strftime('%Y%m%d-%H%M%S')}"

    try:
        import httpx
        from nat.llm import dynamo_llm
    except Exception as exc:  # noqa: BLE001 - diagnostic needs import detail.
        summary = {
            "result": "nemo_import_failed",
            "model": args.model,
            "frontend_url": args.frontend_url,
            "error": repr(exc),
        }
        write_reports(output_dir, summary)
        print(f"NeMo Agent Toolkit import failed: {exc}", file=sys.stderr)
        print(f"Diagnostic output: {output_dir}")
        return 1

    required_keys = {"latency_sensitivity", "osl", "priority", "prefix_id", "total_requests", "iat"}
    try:
        captured = await capture_request(args, output_dir, dynamo_llm, httpx)
        hints = extract_hints(captured)
        present_keys = sorted(required_keys.intersection(hints))
        live = {"skipped": True, "ok": True} if args.skip_live else await live_request(args, output_dir, dynamo_llm, httpx)

        required_hint_keys_present = required_keys.issubset(set(hints))
        captured_ok = bool(hints) and required_hint_keys_present
        live_ok = bool(live.get("ok"))
        result = "nemo_native_nvext_ready" if captured_ok and live_ok else "nemo_native_nvext_incomplete"
        summary = {
            "result": result,
            "model": args.model,
            "frontend_url": args.frontend_url,
            "prefix_id": args.prefix_id,
            "requested_latency_sensitivity": args.latency_sensitivity,
            "captured_agent_hints_present": bool(hints),
            "captured_agent_hints": hints,
            "captured_hint_keys_present": present_keys,
            "required_hint_keys": sorted(required_keys),
            "required_hint_keys_present": required_hint_keys_present,
            "live_skipped": bool(live.get("skipped")),
            "live_ok": live_ok,
            "live_status_code": live.get("status_code"),
            "live_error": live.get("error"),
        }
    except Exception as exc:  # noqa: BLE001 - diagnostic needs import detail.
        summary = {
            "result": "nemo_native_nvext_failed",
            "model": args.model,
            "frontend_url": args.frontend_url,
            "error": repr(exc),
        }

    write_reports(output_dir, summary)

    print(f"Diagnostic output: {output_dir}")
    print(f"result={summary.get('result')}")
    print(f"captured_agent_hints_present={summary.get('captured_agent_hints_present')}")
    print(f"required_hint_keys_present={summary.get('required_hint_keys_present')}")
    print(f"live_ok={summary.get('live_ok')}")
    if summary.get("captured_agent_hints"):
        print("captured_agent_hints=" + json.dumps(summary["captured_agent_hints"], sort_keys=True))
    if summary.get("error"):
        print(f"error={summary.get('error')}", file=sys.stderr)

    return 0 if summary.get("result") == "nemo_native_nvext_ready" else 1


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
