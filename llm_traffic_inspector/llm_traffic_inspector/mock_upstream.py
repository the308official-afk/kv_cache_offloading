from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .inspection import parse_json_body, request_metrics
from .redaction import safe_headers


def create_mock_app() -> FastAPI:
    app = FastAPI(title="Mock LLM Upstream")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def mock(path: str, request: Request):
        body = await request.body()
        payload, _ = parse_json_body(body, request.headers.get("content-type", ""))
        if isinstance(payload, dict) and payload.get("simulate_error"):
            return JSONResponse({"error": {"message": "simulated provider error"}}, status_code=429)

        metrics = request_metrics(payload)
        if isinstance(payload, dict) and payload.get("stream"):
            return StreamingResponse(
                stream_response(payload, metrics),
                media_type="text/event-stream",
                headers={"x-mock-request-id": str(uuid.uuid4())},
            )

        return JSONResponse(
            {
                "id": "mock-" + uuid.uuid4().hex[:12],
                "object": "chat.completion",
                "created": int(time.time()),
                "model": metrics["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "mock response"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": metrics["total_message_content_chars"] // 4,
                    "completion_tokens": 2,
                    "total_tokens": metrics["total_message_content_chars"] // 4 + 2,
                    "prompt_tokens_details": {"cached_tokens": 0},
                },
                "service_tier": payload.get("service_tier") if isinstance(payload, dict) else None,
                "mock_echo": {
                    "path": "/" + path.lstrip("/"),
                    "query": request.scope.get("query_string", b"").decode("utf-8", errors="replace"),
                    "safe_headers": safe_headers(dict(request.headers)),
                },
            }
        )

    return app


async def stream_response(payload: Any, metrics: dict[str, Any]):
    model = metrics.get("model")
    first = {
        "id": "mock-stream-" + uuid.uuid4().hex[:12],
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [{"index": 0, "delta": {"content": "hello"}, "finish_reason": None}],
    }
    yield "data: " + json.dumps(first) + "\n\n"
    await asyncio.sleep(0.25)
    second = {
        "id": first["id"],
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [{"index": 0, "delta": {"content": " world"}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": metrics["total_message_content_chars"] // 4,
            "completion_tokens": 2,
            "total_tokens": metrics["total_message_content_chars"] // 4 + 2,
            "prompt_tokens_details": {"cached_tokens": 0},
        },
    }
    yield "data: " + json.dumps(second) + "\n\n"
    await asyncio.sleep(0.05)
    yield "data: [DONE]\n\n"

