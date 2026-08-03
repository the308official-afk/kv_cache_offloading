from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

from .config import ConfigError, ProxyConfig, build_upstream_url
from .inspection import inspect_request, parse_json_body, response_usage_metadata
from .jsonl_logger import JsonlLogger
from .redaction import safe_headers


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "accept-encoding",
    "content-encoding",
}


def create_app(config: ProxyConfig | None = None) -> FastAPI:
    config = config or ProxyConfig.from_env()
    logger = JsonlLogger(config.log_directory, config.capture_mode)
    app = FastAPI(title="Local LLM Traffic Inspector")
    app.state.proxy_config = config
    app.state.jsonl_logger = logger

    if config.capture_mode == "full":
        print(
            "\nWARNING: LLM_PROXY_CAPTURE_MODE=full is enabled.\n"
            "Full mode can store prompts, source code, tool outputs, file contents,\n"
            "environment details, and accidental secrets. Logs are local only and\n"
            "authentication headers are still redacted.\n",
            flush=True,
        )

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def proxy(path: str, request: Request) -> Response:
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()
        body = await request.body()
        upstream_url = build_upstream_url(config.upstream_base_url, path, request.scope.get("query_string", b""))
        incoming_headers = {str(k): str(v) for k, v in request.headers.items()}
        client_host = request.client.host if request.client else ""

        record: dict[str, Any] = {
            "timestamp": timestamp,
            "proxy_request_id": request_id,
            "provider": config.provider,
            "capture_mode": config.capture_mode,
        }
        record.update(
            inspect_request(
                method=request.method,
                path=path,
                query_string=request.scope.get("query_string", b""),
                client_host=client_host,
                headers=incoming_headers,
                body=body,
                capture_mode=config.capture_mode,
                upstream_url=upstream_url,
            )
        )
        try:
            upstream_headers = prepare_upstream_headers(incoming_headers, config)
        except ConfigError as exc:
            record.update(
                {
                    "configuration_error": str(exc),
                    "total_duration_ms": elapsed_ms(started),
                }
            )
            logger.write(record)
            print_terminal_summary(record)
            return Response(
                content=json.dumps({"error": "proxy_configuration_error", "message": str(exc)}),
                status_code=500,
                media_type="application/json",
            )

        timeout = httpx.Timeout(
            config.request_timeout_seconds,
            connect=config.connect_timeout_seconds,
        )
        client = httpx.AsyncClient(timeout=timeout, verify=True)

        try:
            stream_context = client.stream(
                request.method,
                upstream_url,
                headers=upstream_headers,
                content=body,
            )
            upstream_response = await stream_context.__aenter__()
        except Exception as exc:  # noqa: BLE001 - proxy should log forwarding failures.
            await client.aclose()
            record.update(
                {
                    "upstream_error": f"{type(exc).__name__}: {exc}",
                    "total_duration_ms": elapsed_ms(started),
                }
            )
            logger.write(record)
            print_terminal_summary(record)
            return Response(
                content=json.dumps({"error": "upstream_request_failed", "proxy_request_id": request_id}),
                status_code=502,
                media_type="application/json",
            )

        headers_ms = elapsed_ms(started)
        response_headers = dict(upstream_response.headers)
        response_media_type = upstream_response.headers.get("content-type")
        record.update(
            {
                "time_until_upstream_response_headers_ms": headers_ms,
                "upstream_response_status": upstream_response.status_code,
                "safe_response_headers": safe_headers(response_headers),
            }
        )

        is_stream = should_stream(record, upstream_response)
        if is_stream:
            return StreamingResponse(
                stream_and_log(
                    upstream_response=upstream_response,
                    stream_context=stream_context,
                    client=client,
                    record=record,
                    logger=logger,
                    started=started,
                ),
                status_code=upstream_response.status_code,
                media_type=response_media_type,
                headers=response_headers_for_client(response_headers),
            )

        try:
            content = await upstream_response.aread()
            record.update(response_body_summary(content, response_headers))
            record["total_duration_ms"] = elapsed_ms(started)
            logger.write(record)
            print_terminal_summary(record)
            return Response(
                content=content,
                status_code=upstream_response.status_code,
                media_type=response_media_type,
                headers=response_headers_for_client(response_headers),
            )
        finally:
            await stream_context.__aexit__(None, None, None)
            await client.aclose()

    return app


def prepare_upstream_headers(incoming_headers: dict[str, str], config: ProxyConfig) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in incoming_headers.items():
        lower = name.lower()
        if lower in HOP_BY_HOP_HEADERS:
            continue
        if lower in {"authorization", "x-api-key", "api-key", "cookie", "set-cookie"}:
            continue
        headers[name] = value

    mode = config.upstream_auth_mode
    key = config.auth_key_for_mode()
    if mode in {"openai", "bearer"}:
        if not key:
            raise ConfigError(f"Auth mode {mode} requires LLM_PROXY_OPENAI_API_KEY or LLM_PROXY_UPSTREAM_API_KEY.")
        headers["Authorization"] = f"Bearer {key}"
    elif mode in {"anthropic", "x_api_key"}:
        if not key:
            raise ConfigError(
                f"Auth mode {mode} requires LLM_PROXY_ANTHROPIC_API_KEY or LLM_PROXY_UPSTREAM_API_KEY."
            )
        headers["x-api-key"] = key
    elif mode == "pass_through":
        for name, value in incoming_headers.items():
            if name.lower() in {"authorization", "x-api-key", "api-key"}:
                headers[name] = value
    return headers


def response_headers_for_client(headers: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}


def should_stream(record: dict[str, Any], upstream_response: httpx.Response) -> bool:
    content_type = upstream_response.headers.get("content-type", "").lower()
    return bool(record.get("stream_requested")) or "text/event-stream" in content_type


async def stream_and_log(
    *,
    upstream_response: httpx.Response,
    stream_context: Any,
    client: httpx.AsyncClient,
    record: dict[str, Any],
    logger: JsonlLogger,
    started: float,
):
    first_event_ms: int | None = None
    byte_count = 0
    sse_buffer = ""
    stream_events = 0
    response_metadata: dict[str, Any] = {}
    cancelled = False
    try:
        async for chunk in upstream_response.aiter_raw():
            if chunk:
                if first_event_ms is None:
                    first_event_ms = elapsed_ms(started)
                byte_count += len(chunk)
                stream_events += count_sse_events(chunk)
                sse_buffer = update_sse_metadata(sse_buffer, chunk, response_metadata)
                yield chunk
    except asyncio.CancelledError:
        cancelled = True
        raise
    finally:
        record.update(
            {
                "time_to_first_streamed_event_ms": first_event_ms,
                "stream_event_count_estimate": stream_events,
                "response_body_size_bytes": byte_count,
                "client_cancelled": cancelled,
                "total_duration_ms": elapsed_ms(started),
            }
        )
        record.update(response_metadata)
        logger.write(record)
        print_terminal_summary(record)
        await stream_context.__aexit__(None, None, None)
        await client.aclose()


def response_body_summary(content: bytes, headers: dict[str, str]) -> dict[str, Any]:
    content_type = headers.get("content-type", "")
    payload, error = parse_json_body(content, content_type)
    out: dict[str, Any] = {
        "response_body_size_bytes": len(content),
        "response_json_parse_status": "ok" if error is None and payload is not None else (error or "empty"),
    }
    if payload is not None:
        out.update(response_usage_metadata(payload))
    return out


def update_sse_metadata(buffer: str, chunk: bytes, metadata: dict[str, Any]) -> str:
    text = chunk.decode("utf-8", errors="ignore")
    buffer += text
    while "\n\n" in buffer:
        event, buffer = buffer.split("\n\n", 1)
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            data = line.removeprefix("data:").strip()
            if not data or data == "[DONE]":
                continue
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue
            usage = response_usage_metadata(payload)
            for key, value in usage.items():
                if value:
                    metadata[key] = value
    return buffer[-10000:]


def count_sse_events(chunk: bytes) -> int:
    return chunk.count(b"\n\n") + chunk.count(b"\r\n\r\n")


def elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def print_terminal_summary(record: dict[str, Any]) -> None:
    hints = record.get("candidate_hint_fields") or []
    hint_paths = ",".join(item.get("path", "") for item in hints[:6]) if isinstance(hints, list) else ""
    print(
        "[{rid}] {method} {endpoint} provider={provider} model={model} "
        "stream={stream} status={status} duration_ms={duration} hints={hints}".format(
            rid=record.get("proxy_request_id"),
            method=record.get("method"),
            endpoint=record.get("endpoint"),
            provider=record.get("provider"),
            model=record.get("model"),
            stream=record.get("stream_requested"),
            status=record.get("upstream_response_status", "ERR"),
            duration=record.get("total_duration_ms"),
            hints=hint_paths or "none",
        ),
        flush=True,
    )
