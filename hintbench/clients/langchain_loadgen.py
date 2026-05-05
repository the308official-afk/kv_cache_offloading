#!/usr/bin/env python3

"""Optional LangChain-based load generator for OpenAI-compatible frontends."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hintbench.constants import REQUEST_LOG_ENABLED, REQUEST_LOG_EVERY, REQUEST_LOG_MODE
from hintbench.constants import (
    CONVERTED_MESSAGE_LOG_ENABLED,
    CONVERTED_MESSAGE_LOG_EVERY,
    CONVERTED_MESSAGE_LOG_MODE,
)
from hintbench.constants import (
    HINT_INJECTION_LOG_ENABLED,
    HINT_INJECTION_LOG_EVERY,
    HINT_INJECTION_LOG_MODE,
)
from hintbench.constants import (
    REQUEST_DISPATCH_LOG_ENABLED,
    REQUEST_DISPATCH_LOG_EVERY,
    REQUEST_DISPATCH_LOG_MODE,
)

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "LangChain support requires 'langchain-openai' and 'langchain-core'. "
        "Install them with: python3 -m pip install -U langchain-openai langchain-core"
    ) from exc


def frontend_base_url(frontend_url: str) -> str:
    if "/v1/chat/completions" in frontend_url:
        return frontend_url.replace("/v1/chat/completions", "/v1")
    return frontend_url.rstrip("/")


def should_log_request(request_index: int) -> bool:
    if not REQUEST_LOG_ENABLED:
        return False
    if REQUEST_LOG_EVERY <= 0:
        return False
    return request_index % REQUEST_LOG_EVERY == 0


def should_log_converted_messages(request_index: int) -> bool:
    if not CONVERTED_MESSAGE_LOG_ENABLED:
        return False
    if CONVERTED_MESSAGE_LOG_EVERY <= 0:
        return False
    return request_index % CONVERTED_MESSAGE_LOG_EVERY == 0


def should_log_hint_injection(request_index: int) -> bool:
    if not HINT_INJECTION_LOG_ENABLED:
        return False
    if HINT_INJECTION_LOG_EVERY <= 0:
        return False
    return request_index % HINT_INJECTION_LOG_EVERY == 0


def should_log_request_dispatch(request_index: int) -> bool:
    if not REQUEST_DISPATCH_LOG_ENABLED:
        return False
    if REQUEST_DISPATCH_LOG_EVERY <= 0:
        return False
    return request_index % REQUEST_DISPATCH_LOG_EVERY == 0


def summarize_request_one_line(request_index: int, request_obj: dict) -> str:
    hint_payload = request_obj.get("hint_payload", {})
    return (
        "# [CHECK_POINT] LangChain request received | "
        f"idx={request_index} "
        f"request_id={request_obj.get('request_id')} "
        f"prompt_id={request_obj.get('prompt_id')} "
        f"group={request_obj.get('shared_prefix_group')} "
        f"messages={len(request_obj.get('messages', []))} "
        f"phase={hint_payload.get('agent_phase')} "
        f"priority={hint_payload.get('priority')} "
        f"reuse={hint_payload.get('reuse_likelihood')} "
        f"latency_sensitivity={hint_payload.get('latency_sensitivity')} "
        f"context_type={hint_payload.get('context_type')}"
    )


def summarize_request_compact(request_index: int, request_obj: dict) -> str:
    messages = request_obj.get("messages", [])
    preview_messages = []
    for item in messages[:2]:
        preview_messages.append(
            {
                "role": item.get("role"),
                "content_preview": item.get("content", "")[:120],
            }
        )
    payload = {
        "check_point": "LangChain request received",
        "request_index": request_index,
        "request_id": request_obj.get("request_id"),
        "prompt_id": request_obj.get("prompt_id"),
        "shared_prefix_group": request_obj.get("shared_prefix_group"),
        "message_count": len(messages),
        "messages_preview": preview_messages,
        "hint_payload": request_obj.get("hint_payload", {}),
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def summarize_request_full(request_index: int, request_obj: dict) -> str:
    payload = {
        "check_point": "LangChain request received",
        "request_index": request_index,
        "request": request_obj,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def log___request_checkpoint(request_index: int, request_obj: dict) -> None:
    if not should_log_request(request_index):
        return
    mode = REQUEST_LOG_MODE.strip().lower()
    if mode == "single_line":
        print(summarize_request_one_line(request_index, request_obj), flush=True)
        return
    if mode == "full":
        print("# [CHECK_POINT] LangChain request received", flush=True)
        print(summarize_request_full(request_index, request_obj), flush=True)
        return
    print("# [CHECK_POINT] LangChain request received", flush=True)
    print(summarize_request_compact(request_index, request_obj), flush=True)


def normalize_langchain_messages(messages: list) -> list[dict[str, str]]:
    normalized = []
    for item in messages:
        normalized.append(
            {
                "type": item.__class__.__name__,
                "content": getattr(item, "content", ""),
            }
        )
    return normalized


def summarize_converted_messages_one_line(request_index: int, messages: list) -> str:
    message_types = ",".join(item.__class__.__name__ for item in messages)
    return (
        "# [CHECK_POINT] LangChain messages converted | "
        f"idx={request_index} "
        f"count={len(messages)} "
        f"types=[{message_types}]"
    )


def summarize_converted_messages_compact(request_index: int, messages: list) -> str:
    normalized = normalize_langchain_messages(messages)
    preview = []
    for item in normalized[:2]:
        preview.append(
            {
                "type": item["type"],
                "content_preview": item["content"][:120],
            }
        )
    payload = {
        "check_point": "LangChain messages converted",
        "request_index": request_index,
        "message_count": len(normalized),
        "message_types": [item["type"] for item in normalized],
        "messages_preview": preview,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def summarize_converted_messages_full(request_index: int, messages: list) -> str:
    payload = {
        "check_point": "LangChain messages converted",
        "request_index": request_index,
        "messages": normalize_langchain_messages(messages),
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def log___converted_message_checkpoint(request_index: int, messages: list) -> None:
    if not should_log_converted_messages(request_index):
        return
    mode = CONVERTED_MESSAGE_LOG_MODE.strip().lower()
    if mode == "single_line":
        print(summarize_converted_messages_one_line(request_index, messages), flush=True)
        return
    if mode == "full":
        print("# [CHECK_POINT] LangChain messages converted", flush=True)
        print(summarize_converted_messages_full(request_index, messages), flush=True)
        return
    print("# [CHECK_POINT] LangChain messages converted", flush=True)
    print(summarize_converted_messages_compact(request_index, messages), flush=True)


def summarize_hint_injection_one_line(request_index: int, request_obj: dict, extra_body: dict) -> str:
    hint_payload = request_obj.get("hint_payload", {})
    return (
        "# [CHECK_POINT] LangChain hints injected | "
        f"idx={request_index} "
        f"request_id={request_obj.get('request_id')} "
        f"keys={sorted(hint_payload.keys())} "
        f"nvext_keys={sorted(extra_body.keys())}"
    )


def summarize_hint_injection_compact(request_index: int, request_obj: dict, extra_body: dict) -> str:
    payload = {
        "check_point": "LangChain hints injected",
        "request_index": request_index,
        "request_id": request_obj.get("request_id"),
        "prompt_id": request_obj.get("prompt_id"),
        "hint_payload": request_obj.get("hint_payload", {}),
        "extra_body": extra_body,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def summarize_hint_injection_full(request_index: int, request_obj: dict, extra_body: dict) -> str:
    payload = {
        "check_point": "LangChain hints injected",
        "request_index": request_index,
        "request_id": request_obj.get("request_id"),
        "prompt_id": request_obj.get("prompt_id"),
        "request": request_obj,
        "extra_body": extra_body,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def log___hint_injection_checkpoint(request_index: int, request_obj: dict, extra_body: dict) -> None:
    if not should_log_hint_injection(request_index):
        return
    mode = HINT_INJECTION_LOG_MODE.strip().lower()
    if mode == "single_line":
        print(summarize_hint_injection_one_line(request_index, request_obj, extra_body), flush=True)
        return
    if mode == "full":
        print("# [CHECK_POINT] LangChain hints injected", flush=True)
        print(summarize_hint_injection_full(request_index, request_obj, extra_body), flush=True)
        return
    print("# [CHECK_POINT] LangChain hints injected", flush=True)
    print(summarize_hint_injection_compact(request_index, request_obj, extra_body), flush=True)


def summarize_request_dispatch_one_line(
    request_index: int,
    request_obj: dict,
    converted_messages: list,
    extra_body: dict,
    frontend_url: str,
    model: str,
) -> str:
    return (
        "# [CHECK_POINT] LangChain request dispatched | "
        f"idx={request_index} "
        f"request_id={request_obj.get('request_id')} "
        f"model={model} "
        f"frontend={frontend_url} "
        f"message_count={len(converted_messages)} "
        f"hint_keys={sorted(request_obj.get('hint_payload', {}).keys())}"
    )


def summarize_request_dispatch_compact(
    request_index: int,
    request_obj: dict,
    converted_messages: list,
    extra_body: dict,
    frontend_url: str,
    model: str,
) -> str:
    payload = {
        "check_point": "LangChain request dispatched",
        "request_index": request_index,
        "request_id": request_obj.get("request_id"),
        "prompt_id": request_obj.get("prompt_id"),
        "frontend_url": frontend_url,
        "model": model,
        "message_count": len(converted_messages),
        "message_types": [item.__class__.__name__ for item in converted_messages],
        "extra_body": extra_body,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def summarize_request_dispatch_full(
    request_index: int,
    request_obj: dict,
    converted_messages: list,
    extra_body: dict,
    frontend_url: str,
    model: str,
) -> str:
    payload = {
        "check_point": "LangChain request dispatched",
        "request_index": request_index,
        "request_id": request_obj.get("request_id"),
        "prompt_id": request_obj.get("prompt_id"),
        "frontend_url": frontend_url,
        "model": model,
        "converted_messages": normalize_langchain_messages(converted_messages),
        "extra_body": extra_body,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def log___request_dispatch_checkpoint(
    request_index: int,
    request_obj: dict,
    converted_messages: list,
    extra_body: dict,
    frontend_url: str,
    model: str,
) -> None:
    if not should_log_request_dispatch(request_index):
        return
    mode = REQUEST_DISPATCH_LOG_MODE.strip().lower()
    if mode == "single_line":
        print(
            summarize_request_dispatch_one_line(
                request_index,
                request_obj,
                converted_messages,
                extra_body,
                frontend_url,
                model,
            ),
            flush=True,
        )
        return
    if mode == "full":
        print("# [CHECK_POINT] LangChain request dispatched", flush=True)
        print(
            summarize_request_dispatch_full(
                request_index,
                request_obj,
                converted_messages,
                extra_body,
                frontend_url,
                model,
            ),
            flush=True,
        )
        return
    print("# [CHECK_POINT] LangChain request dispatched", flush=True)
    print(
        summarize_request_dispatch_compact(
            request_index,
            request_obj,
            converted_messages,
            extra_body,
            frontend_url,
            model,
        ),
        flush=True,
    )


def to_langchain_messages(messages: list[dict[str, str]]) -> list:
    # [CHECK_POINT] Raw request messages are converted into LangChain message
    # objects here.
    converted = []
    for item in messages:
        role = item["role"]
        content = item["content"]
        if role == "system":
            converted.append(SystemMessage(content=content))
        elif role == "user":
            converted.append(HumanMessage(content=content))
        elif role == "assistant":
            converted.append(AIMessage(content=content))
        else:
            raise ValueError(f"Unsupported message role for LangChain client: {role}")
    return converted


async def one_request(
    frontend_url: str,
    model: str,
    request_obj: dict,
    *,
    request_index: int,
    experiment_name: str,
    router_mode: str,
    max_tokens: int,
    temperature: float,
    request_timeout_s: int,
) -> dict:
    # [CHECK_POINT] Generated HintBench request rows are printed here before
    # LangChain converts messages or sends the request onward.
    log___request_checkpoint(request_index, request_obj)

    # [CHECK_POINT] LangChain message objects are logged here immediately after
    # conversion so they can be compared against the incoming raw messages.
    converted_messages = to_langchain_messages(request_obj["messages"])
    log___converted_message_checkpoint(request_index, converted_messages)

    # [CHECK_POINT] Hints are injected into the outgoing request here under
    # nvext.agent_hints via LangChain's extra_body.
    extra_body = {"nvext": {"agent_hints": request_obj.get("hint_payload", {})}}
    log___hint_injection_checkpoint(request_index, request_obj, extra_body)
    llm = ChatOpenAI(
        model=model,
        base_url=frontend_base_url(frontend_url),
        api_key="dummy",
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=request_timeout_s,
        extra_body=extra_body,
    )

    started_at = datetime.now(timezone.utc)
    try:
        # [CHECK_POINT] LangChain sends the request to the frontend here.
        log___request_dispatch_checkpoint(
            request_index,
            request_obj,
            converted_messages,
            extra_body,
            frontend_url,
            model,
        )
        response = await llm.ainvoke(converted_messages)
        response_metadata = getattr(response, "response_metadata", {}) or {}
        usage_metadata = getattr(response, "usage_metadata", {}) or {}
        token_usage = response_metadata.get("token_usage", {}) if isinstance(response_metadata, dict) else {}
        latency_ms = None
        if started_at:
            latency_ms = round((datetime.now(timezone.utc) - started_at).total_seconds() * 1000.0, 3)
        return {
            "timestamp": started_at.isoformat(),
            "experiment_name": experiment_name,
            "router_mode": router_mode,
            "model": model,
            "request_id": request_obj["request_id"],
            "prompt_id": request_obj["prompt_id"],
            "workload_name": request_obj["workload_name"],
            "shared_prefix_group": request_obj["shared_prefix_group"],
            "hint_payload": request_obj["hint_payload"],
            "status_code": 200,
            "success": True,
            "error": None,
            "latency_ms": latency_ms,
            "ttft_ms": None,
            "kv_hit_rate": None,
            "prompt_tokens": usage_metadata.get("input_tokens") or token_usage.get("prompt_tokens"),
            "completion_tokens": usage_metadata.get("output_tokens") or token_usage.get("completion_tokens"),
            "cached_tokens": None,
            "worker_id": None,
            "response_id": response_metadata.get("id"),
            "raw_response": {
                "content": response.content,
                "response_metadata": response_metadata,
                "usage_metadata": usage_metadata,
            },
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = round((datetime.now(timezone.utc) - started_at).total_seconds() * 1000.0, 3)
        return {
            "timestamp": started_at.isoformat(),
            "experiment_name": experiment_name,
            "router_mode": router_mode,
            "model": model,
            "request_id": request_obj["request_id"],
            "prompt_id": request_obj["prompt_id"],
            "workload_name": request_obj["workload_name"],
            "shared_prefix_group": request_obj["shared_prefix_group"],
            "hint_payload": request_obj["hint_payload"],
            "status_code": None,
            "success": False,
            "error": repr(exc),
            "latency_ms": latency_ms,
            "ttft_ms": None,
            "kv_hit_rate": None,
            "prompt_tokens": None,
            "completion_tokens": None,
            "cached_tokens": None,
            "worker_id": None,
            "response_id": None,
            "raw_response": None,
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

    # [CHECK_POINT] Generated HintBench request rows enter the LangChain client
    # here from workload.jsonl.
    requests = [json.loads(line) for line in Path(args.workload_file).read_text().splitlines() if line.strip()]
    semaphore = asyncio.Semaphore(args.concurrency)

    async def guarded(request_index: int, req: dict) -> dict:
        async with semaphore:
            return await one_request(
                args.frontend_url,
                args.model,
                req,
                request_index=request_index,
                experiment_name=args.experiment_name,
                router_mode=args.router_mode,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                request_timeout_s=args.request_timeout_s,
            )

    results = await asyncio.gather(*(guarded(idx, req) for idx, req in enumerate(requests, start=1)))
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for item in results:
            fh.write(json.dumps(item, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
