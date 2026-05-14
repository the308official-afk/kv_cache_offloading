#!/usr/bin/env python3
"""Replay a saved AgentBench prompt through multiple client layers.

This utility helps isolate where a Dynamo/OpenAI-compatible response becomes
corrupted by comparing four paths:
1. Raw HTTP to /v1/chat/completions
2. Python OpenAI client
3. LangChain ChatOpenAI
4. Deep Agents baseline agent.invoke(...)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections.abc import Mapping

THIS_FILE = Path(__file__).resolve()
AGENTBENCH_ROOT = THIS_FILE.parent
REPO_ROOT = AGENTBENCH_ROOT.parent
UPSTREAM_ROOT = AGENTBENCH_ROOT / "upstream" / "deepagents"
CLONED_DEEPAGENTS_LIB_ROOT = UPSTREAM_ROOT / "libs" / "deepagents"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if CLONED_DEEPAGENTS_LIB_ROOT.exists() and str(CLONED_DEEPAGENTS_LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(CLONED_DEEPAGENTS_LIB_ROOT))

from agentbench.deepagents_app.src.prompts import (  # noqa: E402
    DYNAMO_HINT_NOTES,
    PLANNING_NOTES,
    SYSTEM_PROMPT,
)

DEFAULT_FRONTEND_URL = "http://127.0.0.1:8000/v1/chat/completions"
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_APP_VARIANT = "upstream_deploy_coding_agent"
DEFAULT_LAYERS = ("raw_http", "openai", "chat_openai", "deepagents")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay a saved AgentBench prompt through multiple client layers.",
    )
    parser.add_argument(
        "--result-json",
        type=Path,
        help="Saved AgentBench result.json file or its containing run directory.",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="Plain-text prompt file to use instead of loading from result.json.",
    )
    parser.add_argument(
        "--frontend-url",
        default=None,
        help=f"Chat completions URL. Defaults to {DEFAULT_FRONTEND_URL}.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Model name. Defaults to {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--app-variant",
        default=None,
        help=f"Instruction surface to load. Defaults to {DEFAULT_APP_VARIANT}.",
    )
    parser.add_argument(
        "--layers",
        default=",".join(DEFAULT_LAYERS),
        help="Comma-separated list from: raw_http,openai,chat_openai,deepagents",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=2048,
        help="max_tokens to request from each layer.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Request timeout in seconds.",
    )
    parser.add_argument(
        "--no-system-prompt",
        action="store_true",
        help="Send only the saved user prompt without app instructions.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write diagnostic artifacts into.",
    )
    return parser.parse_args()


def normalize_result_json_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    if path.is_dir():
        return path / "result.json"
    return path


def read_result_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    resolved = normalize_result_json_path(path)
    if resolved is None or not resolved.exists():
        raise FileNotFoundError(f"result.json not found: {resolved}")
    return json.loads(resolved.read_text(encoding="utf-8"))


def resolve_app_root(app_variant: str) -> Path:
    if app_variant == "local":
        return AGENTBENCH_ROOT / "deepagents_app"
    if app_variant == "upstream_deploy_coding_agent":
        return UPSTREAM_ROOT / "examples" / "deploy-coding-agent"
    raise ValueError(f"Unsupported app_variant: {app_variant}")


def load_agent_instructions(app_variant: str) -> str:
    app_root = resolve_app_root(app_variant)
    agents_file = app_root / "AGENTS.md"
    skills_dir = app_root / "skills"

    parts = [SYSTEM_PROMPT, PLANNING_NOTES, DYNAMO_HINT_NOTES]
    if agents_file.exists():
        parts.append(agents_file.read_text(encoding="utf-8").strip())

    if skills_dir.exists():
        for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
            skill_text = skill_path.read_text(encoding="utf-8").strip()
            if skill_text:
                parts.append(f"Skill reference: {skill_path.parent.name}\n{skill_text}")

    return "\n\n".join(part for part in parts if part)


def frontend_base_url(frontend_url: str) -> str:
    if "/v1/chat/completions" in frontend_url:
        return frontend_url.replace("/v1/chat/completions", "/v1")
    return frontend_url.rstrip("/")


def choose_value(primary: Any, fallback: Any, default: Any) -> Any:
    if primary not in (None, ""):
        return primary
    if fallback not in (None, ""):
        return fallback
    return default


def extract_prompt_from_saved_run(payload: dict[str, Any]) -> str:
    result = payload.get("result", {})
    baseline_prompt = result.get("baseline_prompt")
    if isinstance(baseline_prompt, str) and baseline_prompt.strip():
        return baseline_prompt

    prompt = payload.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt

    messages = result.get("response", {}).get("messages", [])
    if isinstance(messages, list):
        for message in messages:
            if isinstance(message, dict) and message.get("type") == "human":
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content

    raise ValueError("Could not extract a saved user prompt from result.json")


def extract_saved_hints(payload: dict[str, Any], *, max_tokens: int) -> dict[str, Any]:
    result = payload.get("result", {})
    hints = result.get("baseline_hints")
    if isinstance(hints, dict) and hints:
        copied = dict(hints)
        copied.pop("_provenance", None)
        return copied
    return {
        "priority": 5,
        "reuse_likelihood": 0.9,
        "agent_phase": "baseline_execution",
        "latency_sensitivity": 0.7,
        "program_id": "agentbench.deepagents_app.diagnostic",
        "context_type": "software_engineering_long_horizon",
        "expected_output_tokens": max_tokens,
    }


def build_request_context(
    *,
    source_payload: dict[str, Any],
    app_variant: str,
    layer: str,
) -> dict[str, Any]:
    task = source_payload.get("task", {}) if isinstance(source_payload.get("task"), dict) else {}
    parent_run_id = source_payload.get("parent_run_id")
    source_run_id = None
    result_path = source_payload.get("__result_json_path")
    if isinstance(result_path, str):
        source_run_id = Path(result_path).parent.name
    return {
        "request_id": f"diagnose::{layer}::{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "parent_run_id": parent_run_id,
        "task_instance_id": task.get("instance_id"),
        "phase": f"diagnostic_{layer}",
        "step_index": None,
        "step_title": None,
        "app_variant": app_variant,
        "source_run_id": source_run_id,
    }


def build_messages(*, system_prompt: str | None, user_prompt: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    return messages


def preview(text: str, limit: int = 240) -> str:
    collapsed = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


def extract_last_ai_message(response: Any) -> Any:
    messages = None
    if isinstance(response, Mapping):
        messages = response.get("messages")
    elif hasattr(response, "messages"):
        messages = getattr(response, "messages", None)

    if isinstance(messages, list):
        for message in reversed(messages):
            message_type = None
            if isinstance(message, Mapping):
                message_type = message.get("type")
            if message_type is None:
                message_type = getattr(message, "type", None)
            if message_type == "ai":
                return message
    return response


def extract_text(value: Any) -> str:
    if isinstance(value, Mapping):
        message = extract_last_ai_message(value)
        if message is not value:
            return extract_text(message)
        content = value.get("content")
        if content is not None:
            return extract_text(content)
    content = getattr(value, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, Mapping):
                text = item.get("text")
                if text is not None:
                    parts.append(str(text))
                    continue
            parts.append(str(item))
        return "\n".join(parts)
    if isinstance(value, str):
        return value
    return str(content if content is not None else value)


def extract_usage_bundle(response: Any) -> dict[str, Any]:
    if isinstance(response, Mapping):
        if "choices" in response:
            return {
                "usage": response.get("usage"),
                "finish_reason": _extract_finish_reason_from_openai_dict(response),
            }
        message = extract_last_ai_message(response)
        if message is not response:
            return extract_usage_bundle(message)

    usage_metadata = getattr(response, "usage_metadata", None)
    response_metadata = getattr(response, "response_metadata", None)
    if isinstance(response, Mapping):
        usage_metadata = response.get("usage_metadata", usage_metadata)
        response_metadata = response.get("response_metadata", response_metadata)

    bundle: dict[str, Any] = {}
    if isinstance(usage_metadata, dict):
        bundle["usage_metadata"] = usage_metadata
    if isinstance(response_metadata, dict):
        bundle["response_metadata"] = response_metadata
        token_usage = response_metadata.get("token_usage")
        if token_usage is not None:
            bundle["token_usage"] = token_usage
        finish_reason = response_metadata.get("finish_reason")
        if finish_reason is not None:
            bundle["finish_reason"] = finish_reason
    return bundle


def _extract_finish_reason_from_openai_dict(response: Mapping[str, Any]) -> Any:
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, Mapping):
            return choice.get("finish_reason")
    return None


def _openai_like_text(response: Mapping[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice = choices[0]
    if not isinstance(choice, Mapping):
        return ""
    message = choice.get("message")
    if not isinstance(message, Mapping):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return extract_text(content)
    return str(content or "")


def to_jsonable(value: Any, *, depth: int = 0, max_depth: int = 8) -> Any:
    if depth >= max_depth:
        return repr(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item, depth=depth + 1, max_depth=max_depth) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item, depth=depth + 1, max_depth=max_depth) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump(mode="json")
        except TypeError:
            dumped = model_dump()
        return to_jsonable(dumped, depth=depth + 1, max_depth=max_depth)
    if hasattr(value, "__dict__"):
        public = {key: item for key, item in vars(value).items() if not key.startswith("_")}
        return to_jsonable(public, depth=depth + 1, max_depth=max_depth)
    return repr(value)


def write_layer_output(*, output_dir: Path, layer: str, text: str, payload: dict[str, Any]) -> None:
    (output_dir / f"{layer}.txt").write_text(text, encoding="utf-8")
    (output_dir / f"{layer}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def run_raw_http(
    *,
    frontend_url: str,
    request_payload: dict[str, Any],
    timeout: int,
) -> tuple[str, dict[str, Any]]:
    import requests

    response = requests.post(
        frontend_url,
        json=request_payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer dummy"},
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    text = _openai_like_text(body)
    return text, {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "response": body,
        "usage_bundle": extract_usage_bundle(body),
    }


def run_openai_client(
    *,
    frontend_url: str,
    model: str,
    messages: list[dict[str, str]],
    extra_body: dict[str, Any],
    max_tokens: int,
    timeout: int,
) -> tuple[str, dict[str, Any]]:
    from openai import OpenAI

    client = OpenAI(
        api_key="dummy",
        base_url=frontend_base_url(frontend_url),
        timeout=timeout,
    )
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
        max_tokens=max_tokens,
        extra_body=extra_body,
    )
    dumped = response.model_dump(mode="json")
    text = _openai_like_text(dumped)
    return text, {
        "response": dumped,
        "usage_bundle": extract_usage_bundle(dumped),
    }


def run_chat_openai(
    *,
    frontend_url: str,
    model: str,
    messages: list[dict[str, str]],
    extra_body: dict[str, Any],
    max_tokens: int,
    timeout: int,
) -> tuple[str, dict[str, Any]]:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    lc_messages = []
    for message in messages:
        role = message["role"]
        content = message["content"]
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "user":
            lc_messages.append(HumanMessage(content=content))
        else:
            raise ValueError(f"Unsupported role for ChatOpenAI replay: {role}")

    llm = ChatOpenAI(
        model=model,
        base_url=frontend_base_url(frontend_url),
        api_key="dummy",
        temperature=0.0,
        max_tokens=max_tokens,
        timeout=timeout,
        extra_body=extra_body,
    )
    response = llm.invoke(lc_messages)
    dumped = to_jsonable(response)
    text = extract_text(response)
    return text, {
        "response": dumped,
        "usage_bundle": extract_usage_bundle(response),
    }


def run_deepagents(
    *,
    frontend_url: str,
    model: str,
    app_variant: str,
    system_prompt: str,
    user_prompt: str,
    extra_body: dict[str, Any],
    max_tokens: int,
    timeout: int,
) -> tuple[str, dict[str, Any]]:
    from deepagents import create_deep_agent
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=model,
        base_url=frontend_base_url(frontend_url),
        api_key="dummy",
        temperature=0.0,
        max_tokens=max_tokens,
        timeout=timeout,
        extra_body=extra_body,
    )
    agent = create_deep_agent(
        model=llm,
        system_prompt=system_prompt,
    )
    response = agent.invoke({"messages": [{"role": "user", "content": user_prompt}]})
    dumped = to_jsonable(response)
    text = extract_text(response)
    return text, {
        "app_variant": app_variant,
        "response": dumped,
        "usage_bundle": extract_usage_bundle(response),
    }


def summarize_layer(*, layer: str, text: str, payload: dict[str, Any]) -> dict[str, Any]:
    usage_bundle = payload.get("usage_bundle", {})
    return {
        "layer": layer,
        "text_chars": len(text),
        "text_preview": preview(text),
        "usage_bundle": usage_bundle,
        "error": payload.get("error"),
    }


def ensure_output_dir(path: Path | None) -> Path:
    if path is not None:
        path.mkdir(parents=True, exist_ok=True)
        return path
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    auto = AGENTBENCH_ROOT / "diagnostics" / f"dynamo_response_{timestamp}"
    auto.mkdir(parents=True, exist_ok=True)
    return auto


def main() -> None:
    args = parse_args()
    if not args.result_json and not args.prompt_file:
        raise SystemExit("Provide either --result-json or --prompt-file.")

    source_payload = read_result_json(args.result_json)
    if args.result_json is not None:
        source_payload["__result_json_path"] = str(normalize_result_json_path(args.result_json))

    frontend_url = choose_value(args.frontend_url, source_payload.get("frontend_url"), DEFAULT_FRONTEND_URL)
    model = choose_value(args.model, source_payload.get("model"), DEFAULT_MODEL)
    app_variant = choose_value(args.app_variant, source_payload.get("app_variant"), DEFAULT_APP_VARIANT)

    if args.prompt_file:
        user_prompt = args.prompt_file.read_text(encoding="utf-8")
    else:
        user_prompt = extract_prompt_from_saved_run(source_payload)

    system_prompt = None if args.no_system_prompt else load_agent_instructions(app_variant)
    hints = extract_saved_hints(source_payload, max_tokens=args.max_tokens)
    messages = build_messages(system_prompt=system_prompt, user_prompt=user_prompt)

    output_dir = ensure_output_dir(args.output_dir)
    requested_layers = [item.strip() for item in args.layers.split(",") if item.strip()]
    valid_layers = set(DEFAULT_LAYERS)
    unknown_layers = [item for item in requested_layers if item not in valid_layers]
    if unknown_layers:
        raise SystemExit(f"Unsupported layers: {', '.join(unknown_layers)}")

    request_payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": args.max_tokens,
    }
    saved_request_payload = {
        "model": model,
        "app_variant": app_variant,
        "frontend_url": frontend_url,
        "max_tokens": args.max_tokens,
        "messages": messages,
        "source_result_json": source_payload.get("__result_json_path"),
        "layers": requested_layers,
    }

    layer_runners = {
        "raw_http": lambda extra_body: run_raw_http(
            frontend_url=frontend_url,
            request_payload={**request_payload, **extra_body},
            timeout=args.timeout,
        ),
        "openai": lambda extra_body: run_openai_client(
            frontend_url=frontend_url,
            model=model,
            messages=messages,
            extra_body=extra_body,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
        ),
        "chat_openai": lambda extra_body: run_chat_openai(
            frontend_url=frontend_url,
            model=model,
            messages=messages,
            extra_body=extra_body,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
        ),
        "deepagents": lambda extra_body: run_deepagents(
            frontend_url=frontend_url,
            model=model,
            app_variant=app_variant,
            system_prompt=system_prompt or "",
            user_prompt=user_prompt,
            extra_body=extra_body,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
        ),
    }

    summaries: list[dict[str, Any]] = []

    for layer in requested_layers:
        request_context = build_request_context(
            source_payload=source_payload,
            app_variant=app_variant,
            layer=layer,
        )
        extra_body = {
            "nvext": {
                "agent_hints": hints,
                "request_context": request_context,
            }
        }
        saved_request_payload[f"{layer}_extra_body"] = extra_body

        try:
            text, payload = layer_runners[layer](extra_body)
        except Exception as exc:  # noqa: BLE001
            text = ""
            payload = {
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            }

        layer_output = {
            "layer": layer,
            "request_context": request_context,
            "payload": payload,
        }
        write_layer_output(
            output_dir=output_dir,
            layer=layer,
            text=text,
            payload=layer_output,
        )
        summaries.append(summarize_layer(layer=layer, text=text, payload=payload))

    (output_dir / "request_payload.json").write_text(
        json.dumps(saved_request_payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summaries, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print(f"Diagnostic output: {output_dir}")
    for item in summaries:
        layer = item["layer"]
        error = item.get("error")
        if error:
            print(f"[{layer}] ERROR {error['type']}: {error['message']}")
            continue
        print(
            f"[{layer}] chars={item['text_chars']} "
            f"preview={item['text_preview']!r}"
        )


if __name__ == "__main__":
    main()
