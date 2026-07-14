#!/usr/bin/env python3
"""Probe whether Deep Agents can execute a real multi-tool loop via Dynamo."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

THIS_FILE = Path(__file__).resolve()
AGENTBENCH_ROOT = THIS_FILE.parent
REPO_ROOT = AGENTBENCH_ROOT.parent
CLONED_DEEPAGENTS_LIB_ROOT = REPO_ROOT / "upstream" / "deepagents" / "libs" / "deepagents"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if CLONED_DEEPAGENTS_LIB_ROOT.exists() and str(CLONED_DEEPAGENTS_LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(CLONED_DEEPAGENTS_LIB_ROOT))


DEFAULT_FRONTEND_URL = "http://127.0.0.1:8000/v1/chat/completions"
DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
DEFAULT_APP_VARIANT = "upstream_deploy_coding_agent"

PROMPTS = {
    "ls-read-execute": """You are running a tool-call smoke test.

Use the available tools. Do not describe tool calls as text.

Required actions:
1. Use ls to list the current workspace.
2. Use read_file to read /tool_probe.txt.
3. Use execute to run: pwd
4. Then give a short final answer that includes the exact probe text.

The exact probe text is only available from the file. If you cannot use tools,
say TOOL_CALL_FAILED.""",
    "edit-validate": """You are running a coding tool-call smoke test.

Use the available tools. Do not describe tool calls as text.

Required actions:
1. Use write_file or edit_file to create /tool_probe_result.txt containing exactly:
   tool-loop-ok
2. Use execute to run: test -f tool_probe_result.txt && cat tool_probe_result.txt
3. Then give a short final answer.

If you cannot use tools, say TOOL_CALL_FAILED.""",
}

EXPECTED_CASE_TOOLS = {
    "ls-read-execute": {"ls", "read_file", "execute"},
    "edit-validate": {"execute"},
}

EXPECTED_CASE_TOOL_GROUPS = {
    "edit-validate": [{"write_file", "edit_file"}],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose Deep Agents multi-tool execution through local Dynamo.",
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
        "--app-variant",
        default=DEFAULT_APP_VARIANT,
        help=f"Agent instruction surface. Defaults to {DEFAULT_APP_VARIANT}.",
    )
    parser.add_argument(
        "--case",
        choices=sorted(PROMPTS),
        default="ls-read-execute",
        help="Diagnostic case to run.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for diagnostic artifacts.",
    )
    parser.add_argument(
        "--recursion-limit",
        type=int,
        default=int(os.environ.get("AGENTBENCH_TOOL_LOOP_RECURSION_LIMIT", "30")),
        help="LangGraph recursion limit for this diagnostic. Defaults to 30.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=int(os.environ.get("AGENTBENCH_TOOL_LOOP_TIMEOUT_SECONDS", "180")),
        help="Hard timeout for this diagnostic. Defaults to 180 seconds.",
    )
    return parser.parse_args()


def make_output_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        explicit.mkdir(parents=True, exist_ok=True)
        return explicit
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = REPO_ROOT / "experiments" / "raw" / "agentbench" / "diagnostics" / f"deepagents_tool_loop_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def prepare_workspace(output_dir: Path) -> Path:
    workspace = output_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "tool_probe.txt").write_text("probe-text-123\n", encoding="utf-8")
    (workspace / "README.md").write_text(
        "# Tool Loop Diagnostic\n\nThis workspace is safe for tool-call probing.\n",
        encoding="utf-8",
    )
    return workspace


def message_to_dict(message: Any) -> dict[str, Any]:
    if isinstance(message, dict):
        raw = dict(message)
    else:
        raw = {
            "type": getattr(message, "type", None),
            "content": getattr(message, "content", None),
            "name": getattr(message, "name", None),
            "tool_call_id": getattr(message, "tool_call_id", None),
        }
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls is not None:
            raw["tool_calls"] = tool_calls
        invalid_tool_calls = getattr(message, "invalid_tool_calls", None)
        if invalid_tool_calls is not None:
            raw["invalid_tool_calls"] = invalid_tool_calls
    return json.loads(json.dumps(raw, default=str))


def extract_messages(response: Any) -> list[dict[str, Any]]:
    messages = None
    if isinstance(response, dict):
        messages = response.get("messages")
    else:
        messages = getattr(response, "messages", None)
    if not isinstance(messages, list):
        return [message_to_dict(response)]
    return [message_to_dict(message) for message in messages]


def tool_call_name(call: dict[str, Any]) -> str:
    name = call.get("name")
    if name:
        return str(name)
    function = call.get("function")
    if isinstance(function, dict) and function.get("name"):
        return str(function["name"])
    return ""


def summarize_messages(
    messages: list[dict[str, Any]],
    workspace: Path,
    *,
    case: str,
) -> dict[str, Any]:
    ai_tool_call_count = 0
    tool_message_count = 0
    tool_names: list[str] = []
    invalid_tool_call_count = 0
    message_rows: list[dict[str, Any]] = []

    for index, message in enumerate(messages):
        message_type = message.get("type") or message.get("role") or type(message).__name__
        content = message.get("content")
        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list):
            tool_calls = []
        invalid_tool_calls = message.get("invalid_tool_calls")
        if not isinstance(invalid_tool_calls, list):
            invalid_tool_calls = []

        if tool_calls:
            ai_tool_call_count += len(tool_calls)
            for call in tool_calls:
                if isinstance(call, dict):
                    name = tool_call_name(call)
                    if name:
                        tool_names.append(name)
        invalid_tool_call_count += len(invalid_tool_calls)
        if message_type == "tool" or message.get("tool_call_id"):
            tool_message_count += 1

        preview = content if isinstance(content, str) else json.dumps(content, default=str)
        message_rows.append(
            {
                "index": index,
                "type": message_type,
                "tool_call_count": len(tool_calls),
                "invalid_tool_call_count": len(invalid_tool_calls),
                "tool_call_names": [
                    tool_call_name(call)
                    for call in tool_calls
                    if isinstance(call, dict)
                ],
                "content_preview": preview[:240] if isinstance(preview, str) else "",
            }
        )

    unique_tool_names = sorted(set(tool_names))
    required_tools = sorted(EXPECTED_CASE_TOOLS.get(case, set()))
    missing_required_tools = [
        tool_name for tool_name in required_tools if tool_name not in unique_tool_names
    ]
    missing_required_tool_groups: list[list[str]] = []
    for group in EXPECTED_CASE_TOOL_GROUPS.get(case, []):
        if not any(tool_name in unique_tool_names for tool_name in group):
            missing_required_tool_groups.append(sorted(group))

    result_file = workspace / "tool_probe_result.txt"
    result_file_text = result_file.read_text(encoding="utf-8").strip() if result_file.exists() else None
    required_tools_observed = not missing_required_tools and not missing_required_tool_groups
    edit_validation_observed = case != "edit-validate" or result_file_text == "tool-loop-ok"
    return {
        "message_count": len(messages),
        "ai_tool_call_count": ai_tool_call_count,
        "tool_message_count": tool_message_count,
        "invalid_tool_call_count": invalid_tool_call_count,
        "tool_names": tool_names,
        "unique_tool_names": unique_tool_names,
        "required_tools": required_tools,
        "missing_required_tools": missing_required_tools,
        "missing_required_tool_groups": missing_required_tool_groups,
        "required_tools_observed": required_tools_observed,
        "multi_tool_loop_observed": ai_tool_call_count >= 2 and tool_message_count >= 2,
        "result_file_exists": result_file.exists(),
        "result_file_text": result_file_text,
        "edit_validation_observed": edit_validation_observed,
        "case_success": required_tools_observed
        and ai_tool_call_count >= 2
        and tool_message_count >= 2
        and edit_validation_observed,
        "messages": message_rows,
    }


def main() -> None:
    args = parse_args()
    if args.timeout_seconds > 0:
        def _timeout_handler(signum, frame):  # noqa: ARG001
            raise TimeoutError(
                f"Deep Agents tool-loop diagnostic timed out after {args.timeout_seconds}s"
            )

        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(args.timeout_seconds)

    try:
        from agentbench.deepagents_app.src.agent import (  # noqa: PLC0415
            build_coding_agent,
            response_text,
        )
    except ImportError as exc:
        raise SystemExit(
            "Deep Agents dependencies could not be imported. Install the AgentBench "
            "Python environment first, for example: python3.11 -m pip install -r "
            f"agentbench/requirements.txt. Original import error: {exc}"
        ) from exc

    output_dir = make_output_dir(args.output_dir)
    workspace = prepare_workspace(output_dir)

    hints = {
        "priority": 5,
        "reuse_likelihood": 0.2,
        "agent_phase": "tool_diagnostic",
        "latency_sensitivity": 1.0,
        "program_id": "agentbench.deepagents_tool_loop_diagnostic",
        "context_type": "tool_call_smoke_test",
        "expected_output_tokens": 512,
        "hint_profile": "tool-diagnostic",
    }
    request_context = {
        "request_id": f"diagnose-deepagents-tool-loop::{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "parent_run_id": output_dir.name,
        "task_instance_id": "tool-loop-diagnostic",
        "phase": "tool_diagnostic",
        "step_index": 0,
        "step_title": args.case,
        "app_variant": args.app_variant,
    }
    prompt = PROMPTS[args.case]

    agent = build_coding_agent(
        frontend_url=args.frontend_url,
        model=args.model,
        workspace_dir=workspace,
        base_hints=hints,
        phase="tool_diagnostic",
        app_variant=args.app_variant,
        request_context=request_context,
        prompt_stage="tool_diagnostic_agent_system_prompt_loaded",
    )
    response = None
    invoke_error: BaseException | None = None
    try:
        response = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"recursion_limit": args.recursion_limit},
        )
    except BaseException as exc:
        invoke_error = exc
    finally:
        if args.timeout_seconds > 0:
            signal.alarm(0)

    messages = extract_messages(response) if response is not None else []
    summary = {
        "frontend_url": args.frontend_url,
        "model": args.model,
        "app_variant": args.app_variant,
        "case": args.case,
        "recursion_limit": args.recursion_limit,
        "timeout_seconds": args.timeout_seconds,
        "workspace": str(workspace),
        "prompt": prompt,
        "request_context": request_context,
        "hints": hints,
        "final_text": response_text(response) if response is not None else "",
        "invoke_error_type": type(invoke_error).__name__ if invoke_error else "",
        "invoke_error": str(invoke_error) if invoke_error else "",
        **summarize_messages(messages, workspace, case=args.case),
    }

    (output_dir / "request.json").write_text(
        json.dumps(
            {
                "frontend_url": args.frontend_url,
                "model": args.model,
                "app_variant": args.app_variant,
                "case": args.case,
                "prompt": prompt,
                "request_context": request_context,
                "hints": hints,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / "messages.json").write_text(json.dumps(messages, indent=2), encoding="utf-8")
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Diagnostic output: {output_dir}")
    print(f"tool_calls={summary['ai_tool_call_count']}")
    print(f"tool_messages={summary['tool_message_count']}")
    print(f"invalid_tool_calls={summary['invalid_tool_call_count']}")
    print(f"unique_tools={','.join(summary['unique_tool_names']) or '(none)'}")
    print(f"required_tools_observed={summary['required_tools_observed']}")
    if summary["missing_required_tools"]:
        print(f"missing_required_tools={','.join(summary['missing_required_tools'])}")
    if summary["missing_required_tool_groups"]:
        print(f"missing_required_tool_groups={summary['missing_required_tool_groups']}")
    print(f"multi_tool_loop_observed={summary['multi_tool_loop_observed']}")
    print(f"result_file_exists={summary['result_file_exists']}")
    print(f"edit_validation_observed={summary['edit_validation_observed']}")
    if invoke_error is not None:
        print(f"invoke_error_type={summary['invoke_error_type']}")
        print(f"invoke_error={summary['invoke_error']}")
    print(f"case_success={summary['case_success']}")
    if invoke_error is not None:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
