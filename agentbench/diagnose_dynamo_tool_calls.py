#!/usr/bin/env python3
"""Probe Dynamo's OpenAI-compatible tool-calling behavior directly.

This bypasses AgentBench and Deep Agents and asks the frontend to produce
structured OpenAI-style tool calls for a very small synthetic tool schema.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[1]

DEFAULT_FRONTEND_URL = "http://127.0.0.1:8000/v1/chat/completions"
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_TIMEOUT = 300

TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "echo_status",
            "description": "Return a short status string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Short status word to echo back.",
                    }
                },
                "required": ["status"],
                "additionalProperties": False,
            },
        },
    }
]

TEST_CASES = {
    "auto": {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Call the tool echo_status with status set to 'ready'. "
                    "Do not answer in plain text if a tool call is possible."
                ),
            }
        ],
        "tools": TOOL_SCHEMA,
        "tool_choice": "auto",
    },
    "required": {
        "messages": [
            {
                "role": "user",
                "content": "You must call echo_status with status set to 'ready'.",
            }
        ],
        "tools": TOOL_SCHEMA,
        "tool_choice": "required",
    },
    "named": {
        "messages": [
            {
                "role": "user",
                "content": "Use the required tool for status 'ready'.",
            }
        ],
        "tools": TOOL_SCHEMA,
        "tool_choice": {
            "type": "function",
            "function": {"name": "echo_status"},
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose OpenAI-style tool-calling support on a Dynamo frontend.",
    )
    parser.add_argument(
        "--frontend-url",
        default=DEFAULT_FRONTEND_URL,
        help=f"Chat completions URL. Defaults to {DEFAULT_FRONTEND_URL}.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model name. Defaults to {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--cases",
        default="auto,required,named",
        help="Comma-separated test cases from: auto, required, named",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="max_tokens for each diagnostic request.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write diagnostic artifacts into.",
    )
    return parser.parse_args()


def make_output_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        explicit.mkdir(parents=True, exist_ok=True)
        return explicit
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = REPO_ROOT / "experiments" / "raw" / "agentbench" / "diagnostics" / f"dynamo_tool_calls_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer dummy",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc


def extract_choice(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return {}
    choice = choices[0]
    return choice if isinstance(choice, dict) else {}


def extract_message(choice: dict[str, Any]) -> dict[str, Any]:
    message = choice.get("message")
    return message if isinstance(message, dict) else {}


def summarize_response(case_name: str, response: dict[str, Any]) -> dict[str, Any]:
    choice = extract_choice(response)
    message = extract_message(choice)
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list):
        tool_calls = []
    content = message.get("content")
    return {
        "case": case_name,
        "finish_reason": choice.get("finish_reason"),
        "tool_call_count": len(tool_calls),
        "tool_calls": tool_calls,
        "content": content,
        "usage": response.get("usage"),
    }


def main() -> None:
    args = parse_args()
    cases = [item.strip() for item in args.cases.split(",") if item.strip()]
    unknown = [name for name in cases if name not in TEST_CASES]
    if unknown:
        raise SystemExit(f"Unknown test case(s): {', '.join(unknown)}")

    output_dir = make_output_dir(args.output_dir)
    summary_rows: list[dict[str, Any]] = []

    for case_name in cases:
        payload = dict(TEST_CASES[case_name])
        payload["model"] = args.model
        payload["max_tokens"] = args.max_tokens
        payload["stream"] = False
        response = post_json(args.frontend_url, payload, args.timeout)

        (output_dir / f"{case_name}_request.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        (output_dir / f"{case_name}_response.json").write_text(
            json.dumps(response, indent=2),
            encoding="utf-8",
        )

        row = summarize_response(case_name, response)
        summary_rows.append(row)

        tool_call_count = row["tool_call_count"]
        finish_reason = row["finish_reason"]
        content = row["content"]
        content_preview = ""
        if isinstance(content, str):
            content_preview = content[:160]
        elif content is not None:
            content_preview = json.dumps(content)[:160]
        print(
            f"[{case_name}] finish_reason={finish_reason!r} "
            f"tool_calls={tool_call_count} content_preview={content_preview!r}"
        )

    summary = {
        "frontend_url": args.frontend_url,
        "model": args.model,
        "cases": summary_rows,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(f"Diagnostic output: {output_dir}")


if __name__ == "__main__":
    main()
