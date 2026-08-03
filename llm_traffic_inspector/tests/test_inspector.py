from __future__ import annotations

import json
import socket
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
import uvicorn

from llm_traffic_inspector.config import ProxyConfig, build_upstream_url
from llm_traffic_inspector.hints import detect_hints
from llm_traffic_inspector.inspection import inspect_request
from llm_traffic_inspector.mock_upstream import create_mock_app
from llm_traffic_inspector.proxy_app import create_app, prepare_upstream_headers
from llm_traffic_inspector.redaction import REDACTED, redact_json, safe_headers
from llm_traffic_inspector.report import build_hint_rows, build_overview, load_records


def test_header_redaction() -> None:
    headers = {
        "Authorization": "Bearer sk-testsecret",
        "x-api-key": "abc123",
        "anthropic-version": "2023-06-01",
    }
    out = safe_headers(headers)
    assert out["Authorization"] == REDACTED
    assert out["x-api-key"] == REDACTED
    assert out["anthropic-version"] == "2023-06-01"


def test_json_redaction() -> None:
    payload = {"api_key": "secret", "nested": {"session_token": "secret"}, "model": "x"}
    assert redact_json(payload)["api_key"] == REDACTED
    assert redact_json(payload)["nested"]["session_token"] == REDACTED
    assert redact_json(payload)["model"] == "x"


def test_safe_mode_records_structure_not_prompt_text() -> None:
    body = json.dumps(
        {
            "model": "mock",
            "messages": [{"role": "user", "content": "private source code here"}],
        }
    ).encode()
    record = inspect_request(
        method="POST",
        path="/v1/chat/completions",
        query_string=b"",
        client_host="127.0.0.1",
        headers={"content-type": "application/json"},
        body=body,
        capture_mode="safe",
        upstream_url="http://upstream/v1/chat/completions",
    )
    encoded = json.dumps(record)
    assert "private source code here" not in encoded
    assert record["request_body"]["json_structure"]["type"] == "object"
    assert record["model"] == "mock"


def test_full_mode_records_redacted_json() -> None:
    body = json.dumps({"model": "mock", "api_key": "secret", "messages": []}).encode()
    record = inspect_request(
        method="POST",
        path="/v1/chat/completions",
        query_string=b"",
        client_host="127.0.0.1",
        headers={"content-type": "application/json"},
        body=body,
        capture_mode="full",
        upstream_url="http://upstream/v1/chat/completions",
    )
    assert record["request_body"]["json"]["api_key"] == REDACTED
    assert record["request_body"]["json"]["model"] == "mock"


def test_hint_detection_categories() -> None:
    payload = {
        "model": "x",
        "service_tier": "priority",
        "reasoning": {"effort": "high"},
        "nvext": {"agent_hints": {"priority": 10, "latency_sensitivity": "high", "osl": 128}},
        "unknown_vendor_field": True,
    }
    findings = {item.path: item.category for item in detect_hints(payload, {}, "/v1/responses")}
    assert findings["service_tier"] == "Service-class hint"
    assert findings["reasoning"] == "Model-compute hint"
    assert findings["reasoning.effort"] == "Model-compute hint"
    assert findings["nvext.agent_hints.priority"] == "Infrastructure scheduling hint"
    assert findings["nvext.agent_hints.osl"] == "Workload-shape hint"
    assert findings["unknown_vendor_field"] == "Unknown candidate field"


def test_auth_replacement_openai() -> None:
    config = ProxyConfig(
        provider="openai",
        upstream_base_url="https://api.openai.com",
        capture_mode="safe",
        log_directory=Path("/tmp/logs"),
        upstream_auth_mode="openai",
        openai_api_key="real-key",
    )
    headers = prepare_upstream_headers(
        {
            "authorization": "Bearer local-placeholder-only",
            "content-type": "application/json",
            "cookie": "secret",
        },
        config,
    )
    assert headers["Authorization"] == "Bearer real-key"
    assert "cookie" not in {k.lower(): v for k, v in headers.items()}


def test_build_upstream_url_preserves_query() -> None:
    assert (
        build_upstream_url("http://example.com/base", "/v1/chat/completions", b"a=1&b=two")
        == "http://example.com/base/v1/chat/completions?a=1&b=two"
    )


def test_report_generation(tmp_path: Path) -> None:
    log = tmp_path / "traffic_20260101.jsonl"
    log.write_text(
        json.dumps(
            {
                "provider": "openai",
                "endpoint": "/v1/responses",
                "safe_request_headers": {"content-type": "application/json"},
                "json_field_paths": ["model", "service_tier"],
                "candidate_hint_fields": [
                    {
                        "path": "service_tier",
                        "category": "Service-class hint",
                        "example_safe_value": "priority",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    records = load_records(tmp_path)
    overview = build_overview(records)
    hints = build_hint_rows(records)
    assert overview[0]["service_tier_usage"] == "yes"
    assert hints[0]["candidate_hint_field"] == "service_tier"


def test_proxy_forwards_to_mock_and_logs(tmp_path: Path) -> None:
    mock_port = free_port()
    proxy_port = free_port()
    with run_uvicorn(create_mock_app(), mock_port), run_uvicorn(
        create_app(
            ProxyConfig(
                provider="custom",
                upstream_base_url=f"http://127.0.0.1:{mock_port}",
                capture_mode="safe",
                log_directory=tmp_path,
                port=proxy_port,
                upstream_auth_mode="none",
            )
        ),
        proxy_port,
    ):
        response = httpx.post(
            f"http://127.0.0.1:{proxy_port}/v1/chat/completions?x=1",
            json={"model": "mock", "messages": [{"role": "user", "content": "hi"}]},
            timeout=5,
        )
    assert response.status_code == 200
    assert response.json()["mock_echo"]["query"] == "x=1"
    records = load_records(tmp_path)
    assert records[0]["endpoint"] == "/v1/chat/completions"
    assert records[0]["upstream_response_status"] == 200


def test_streaming_reaches_client_before_upstream_finishes(tmp_path: Path) -> None:
    mock_port = free_port()
    proxy_port = free_port()
    with run_uvicorn(create_mock_app(), mock_port), run_uvicorn(
        create_app(
            ProxyConfig(
                provider="custom",
                upstream_base_url=f"http://127.0.0.1:{mock_port}",
                capture_mode="safe",
                log_directory=tmp_path,
                port=proxy_port,
                upstream_auth_mode="none",
            )
        ),
        proxy_port,
    ):
        started = time.perf_counter()
        with httpx.stream(
            "POST",
            f"http://127.0.0.1:{proxy_port}/v1/chat/completions",
            json={"model": "mock", "stream": True, "messages": [{"role": "user", "content": "hi"}]},
            timeout=5,
        ) as response:
            first = next(response.iter_raw())
            first_ms = (time.perf_counter() - started) * 1000
            assert response.status_code == 200
            assert b"data:" in first
            assert first_ms < 250


def test_upstream_error_is_forwarded_and_logged(tmp_path: Path) -> None:
    mock_port = free_port()
    proxy_port = free_port()
    with run_uvicorn(create_mock_app(), mock_port), run_uvicorn(
        create_app(
            ProxyConfig(
                provider="custom",
                upstream_base_url=f"http://127.0.0.1:{mock_port}",
                capture_mode="safe",
                log_directory=tmp_path,
                port=proxy_port,
                upstream_auth_mode="none",
            )
        ),
        proxy_port,
    ):
        response = httpx.post(
            f"http://127.0.0.1:{proxy_port}/v1/chat/completions",
            json={"model": "mock", "simulate_error": True},
            timeout=5,
        )
    assert response.status_code == 429
    records = load_records(tmp_path)
    assert records[0]["upstream_response_status"] == 429


def test_large_request_body_safe_mode(tmp_path: Path) -> None:
    large_text = "x" * 200_000
    record = inspect_request(
        method="POST",
        path="/v1/responses",
        query_string=b"",
        client_host="127.0.0.1",
        headers={"content-type": "application/json"},
        body=json.dumps({"model": "mock", "input": large_text}).encode(),
        capture_mode="safe",
        upstream_url="http://upstream/v1/responses",
    )
    encoded = json.dumps(record)
    assert large_text not in encoded
    assert record["request_body_size_bytes"] > 200_000


def test_stream_can_be_closed_early(tmp_path: Path) -> None:
    mock_port = free_port()
    proxy_port = free_port()
    with run_uvicorn(create_mock_app(), mock_port), run_uvicorn(
        create_app(
            ProxyConfig(
                provider="custom",
                upstream_base_url=f"http://127.0.0.1:{mock_port}",
                capture_mode="safe",
                log_directory=tmp_path,
                port=proxy_port,
                upstream_auth_mode="none",
            )
        ),
        proxy_port,
    ):
        with httpx.stream(
            "POST",
            f"http://127.0.0.1:{proxy_port}/v1/chat/completions",
            json={"model": "mock", "stream": True, "messages": [{"role": "user", "content": "hi"}]},
            timeout=5,
        ) as response:
            assert response.status_code == 200
            next(response.iter_raw())


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def run_uvicorn(app, port: int):
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    wait_for_port(port)
    try:
        yield
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def wait_for_port(port: int) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    pytest.fail(f"server on port {port} did not start")

