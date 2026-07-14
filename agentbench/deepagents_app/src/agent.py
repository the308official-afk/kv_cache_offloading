"""Deep Agents app wiring for local Dynamo-backed coding runs.

This is the target location for moving model construction and hint-aware
phase logic out of the repo-local runner and into a source-level Deep Agents app.
"""

from __future__ import annotations

import os
import json
import subprocess
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Any
from collections.abc import Mapping

from agentbench.log_utils import log_checkpoint, log_lifecycle_event

THIS_FILE = Path(__file__).resolve()
APP_ROOT = THIS_FILE.parents[1]
AGENTBENCH_ROOT = APP_ROOT.parents[1]
UPSTREAM_ROOT = AGENTBENCH_ROOT / "upstream" / "deepagents"
CLONED_DEEPAGENTS_LIB_ROOT = UPSTREAM_ROOT / "libs" / "deepagents"


def _select_deepagents_runtime_source() -> str:
    """Select which DeepAgents library implementation this run imports."""
    requested = os.environ.get("AGENTBENCH_DEEPAGENTS_SOURCE", "python_environment")
    source = requested.strip().lower().replace("-", "_")
    cloned_root = str(CLONED_DEEPAGENTS_LIB_ROOT)

    if source in {"python", "python_environment", "installed"}:
        sys.path[:] = [entry for entry in sys.path if entry != cloned_root]
        return "python_environment"

    if source in {"upstream", "cloned", "repo"}:
        if not CLONED_DEEPAGENTS_LIB_ROOT.exists():
            raise SystemExit(
                "AGENTBENCH_DEEPAGENTS_SOURCE=upstream was requested, but "
                f"{CLONED_DEEPAGENTS_LIB_ROOT} does not exist."
            )
        if cloned_root not in sys.path:
            sys.path.insert(0, cloned_root)
        return cloned_root

    if source == "auto":
        if CLONED_DEEPAGENTS_LIB_ROOT.exists() and cloned_root not in sys.path:
            sys.path.insert(0, cloned_root)
        return cloned_root if CLONED_DEEPAGENTS_LIB_ROOT.exists() else "python_environment"

    raise SystemExit(
        "Unsupported AGENTBENCH_DEEPAGENTS_SOURCE value "
        f"{requested!r}. Use python_environment, upstream, or auto."
    )


DEEPAGENTS_RUNTIME_SOURCE = _select_deepagents_runtime_source()

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, LocalShellBackend, StateBackend
from langchain_openai import ChatOpenAI

from .hint_providers import (
    HINT_PROVIDER_AGENTBENCH,
    build_agent_context,
    build_annotations,
    build_hint_payload,
    normalize_hint_provider,
    supported_agent_hints,
)
from .prompts import (
    DYNAMO_HINT_NOTES,
    PLANNING_NOTES,
    SYSTEM_PROMPT,
    build_validation_command,
    format_swebench_task_prompt,
)

SKILLS_DIR = APP_ROOT / "skills"
AGENTS_FILE = APP_ROOT / "AGENTS.md"
UPSTREAM_DEPLOY_CODING_AGENT_ROOT = UPSTREAM_ROOT / "examples" / "deploy-coding-agent"

DEFAULT_DYNAMO_HINTS: dict[str, Any] = {
    "priority": 5,
    "reuse_likelihood": 0.9,
    "agent_phase": "execution",
    "latency_sensitivity": 0.7,
    "program_id": "agentbench.deepagents_app",
    "context_type": "software_engineering_long_horizon",
    "expected_output_tokens": 512,
}


def env_flag(name: str, *, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def env_int(name: str, *, default: int) -> int:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {value!r}") from exc


def limit_text(text: str, limit: int = 3000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def load_task_overrides() -> dict[str, str | None]:
    configured_path = os.environ.get("AGENTBENCH_TASK_OVERRIDES_FILE")
    if not configured_path:
        return {"path": None, "text": ""}

    path = Path(configured_path).expanduser()
    if not path.is_absolute():
        path = AGENTBENCH_ROOT / path
    if not path.exists():
        raise SystemExit(f"AGENTBENCH_TASK_OVERRIDES_FILE does not exist: {path}")

    text = path.read_text(encoding="utf-8").strip()
    return {"path": str(path), "text": text}


def apply_task_overrides(prompt: str, task_overrides: dict[str, str | None]) -> str:
    text = str(task_overrides.get("text") or "").strip()
    if not text:
        return prompt
    path = task_overrides.get("path") or "unknown"
    return (
        f"{prompt.rstrip()}\n\n"
        "External task override instructions:\n"
        f"Source: {path}\n\n"
        f"{text}\n"
    )


# Builds the per-request tracking payload that we send through logs and Dynamo hints.
def build_request_context(
    *,
    parent_run_id: str | None,
    task_instance_id: str | None,
    phase: str,
    app_variant: str | None,
    step_index: int | None = None,
    step_title: str | None = None,
) -> dict[str, Any]:
    request_id = f"{parent_run_id or 'run'}::{phase}"
    if step_index is not None:
        request_id += f"::{step_index}"
    return {
        "request_id": request_id,
        "parent_run_id": parent_run_id,
        "task_instance_id": task_instance_id,
        "phase": phase,
        "step_index": step_index,
        "step_title": step_title,
        "app_variant": app_variant,
    }


# Pulls out the final AI message from a LangChain / Deep Agents response object.
def _extract_last_ai_message(response: Any) -> Any:
    messages = None
    if isinstance(response, Mapping):
        messages = response.get("messages")
    elif hasattr(response, "get"):
        try:
            messages = response.get("messages")
        except Exception:  # noqa: BLE001
            messages = None
    if messages is None:
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


def _response_messages(response: Any) -> list[Any]:
    messages = None
    if isinstance(response, Mapping):
        messages = response.get("messages")
    elif hasattr(response, "get"):
        try:
            messages = response.get("messages")
        except Exception:  # noqa: BLE001
            messages = None
    if messages is None:
        messages = getattr(response, "messages", None)
    return messages if isinstance(messages, list) else []


def _tool_call_name(tool_call: Any) -> str | None:
    if isinstance(tool_call, Mapping):
        name = tool_call.get("name")
        if name:
            return str(name)
        function = tool_call.get("function")
        if isinstance(function, Mapping) and function.get("name"):
            return str(function["name"])
    name = getattr(tool_call, "name", None)
    return str(name) if name else None


def _tool_call_args(tool_call: Any) -> Any:
    if isinstance(tool_call, Mapping):
        if "args" in tool_call:
            return tool_call.get("args")
        function = tool_call.get("function")
        if isinstance(function, Mapping):
            return function.get("arguments")
    return getattr(tool_call, "args", None)


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return response_text(value)


def _message_tool_call_names(message: Any) -> list[str]:
    tool_calls = None
    if isinstance(message, Mapping):
        tool_calls = message.get("tool_calls")
    if tool_calls is None:
        tool_calls = getattr(message, "tool_calls", None)
    if not isinstance(tool_calls, list):
        return []
    return [name for item in tool_calls if (name := _tool_call_name(item))]


def extract_tool_call_details(response: Any) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    call_id_to_index: dict[str, int] = {}
    call_id_to_name: dict[str, str] = {}

    for message_index, message in enumerate(_response_messages(response)):
        tool_calls = None
        if isinstance(message, Mapping):
            tool_calls = message.get("tool_calls")
        if tool_calls is None:
            tool_calls = getattr(message, "tool_calls", None)
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                name = _tool_call_name(tool_call) or "unknown"
                call_id = _tool_call_id(tool_call)
                args = _jsonable(_tool_call_args(tool_call))
                row = {
                    "message_index": message_index,
                    "tool_call_index": len(details),
                    "tool_call_id": call_id,
                    "tool_name": name,
                    "args": args,
                    "command": args.get("command") if isinstance(args, Mapping) else None,
                    "cmd": args.get("cmd") if isinstance(args, Mapping) else None,
                    "file_path": (
                        args.get("file_path")
                        or args.get("path")
                        or args.get("target_file")
                        if isinstance(args, Mapping)
                        else None
                    ),
                    "result_preview": None,
                    "source": "deepagents_response.messages.tool_calls",
                }
                if call_id:
                    call_id_to_index[call_id] = len(details)
                    call_id_to_name[call_id] = name
                details.append(row)

        if _message_type(message) != "tool":
            continue
        if isinstance(message, Mapping):
            tool_call_id = message.get("tool_call_id")
            name = message.get("name")
        else:
            tool_call_id = getattr(message, "tool_call_id", None)
            name = getattr(message, "name", None)
        resolved_name = str(name or call_id_to_name.get(str(tool_call_id)) or "unknown")
        preview = _message_text(message)[:1000]
        if tool_call_id and str(tool_call_id) in call_id_to_index:
            details[call_id_to_index[str(tool_call_id)]]["result_preview"] = preview
        else:
            details.append(
                {
                    "message_index": message_index,
                    "tool_call_index": len(details),
                    "tool_call_id": str(tool_call_id) if tool_call_id else None,
                    "tool_name": resolved_name,
                    "args": None,
                    "command": None,
                    "cmd": None,
                    "file_path": None,
                    "result_preview": preview,
                    "source": "deepagents_response.messages.tool_result",
                }
            )
    return details


def summarize_tool_progress(response: Any) -> dict[str, Any]:
    names: list[str] = []
    for message in _response_messages(response):
        names.extend(_message_tool_call_names(message))

    write_or_edit_tools = {"edit_file", "write_file"}
    unique_names = sorted(set(names))
    has_write_or_edit = any(name in write_or_edit_tools for name in names)
    has_execute = any(name == "execute" for name in names)
    return {
        "tool_call_count": len(names),
        "tool_call_names": names,
        "unique_tool_call_names": unique_names,
        "has_read_file": any(name == "read_file" for name in names),
        "has_write_or_edit": has_write_or_edit,
        "has_execute": has_execute,
        "has_edit_plus_validation": has_write_or_edit and has_execute,
    }


def execution_retry_reason(tool_progress: dict[str, Any]) -> str | None:
    if not env_flag("AGENTBENCH_EXECUTION_GUARD", default=True):
        return None

    tool_call_count = int(tool_progress.get("tool_call_count") or 0)
    unique_names = set(tool_progress.get("unique_tool_call_names") or [])
    if tool_call_count == 0:
        return "no_tool_calls"
    if unique_names <= {"read_file"}:
        return "read_only_tool_calls"
    if not tool_progress.get("has_write_or_edit"):
        return "no_edit_or_write_tool_call"
    if not tool_progress.get("has_execute"):
        return "no_validation_execute_tool_call"
    return None


def execution_loop_enabled() -> bool:
    return env_flag("AGENTBENCH_EXECUTION_LOOP", default=False)


def execution_loop_max_steps() -> int:
    return env_int("AGENTBENCH_EXECUTION_LOOP_MAX_STEPS", default=6)


def execution_loop_require_test() -> bool:
    return env_flag("AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST", default=True)


def _message_type(message: Any) -> str | None:
    if isinstance(message, Mapping):
        value = message.get("type")
        if value:
            return str(value)
    value = getattr(message, "type", None)
    return str(value) if value else None


def _message_text(message: Any) -> str:
    if isinstance(message, Mapping):
        if message.get("text") is not None:
            return response_text(message.get("text"))
        content = message.get("content")
    else:
        text = getattr(message, "text", None)
        if text is not None:
            return response_text(text)
        content = getattr(message, "content", None)
    return response_text(content if content is not None else message)


def _tool_call_id(tool_call: Any) -> str | None:
    if isinstance(tool_call, Mapping):
        value = tool_call.get("id")
    else:
        value = getattr(tool_call, "id", None)
    return str(value) if value else None


def tool_result_texts_by_name(response: Any) -> dict[str, list[str]]:
    call_id_to_name: dict[str, str] = {}
    results: dict[str, list[str]] = {}

    for message in _response_messages(response):
        tool_calls = None
        if isinstance(message, Mapping):
            tool_calls = message.get("tool_calls")
        if tool_calls is None:
            tool_calls = getattr(message, "tool_calls", None)
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                call_id = _tool_call_id(tool_call)
                name = _tool_call_name(tool_call)
                if call_id and name:
                    call_id_to_name[call_id] = name

        if _message_type(message) != "tool":
            continue
        if isinstance(message, Mapping):
            tool_call_id = message.get("tool_call_id")
            name = message.get("name")
        else:
            tool_call_id = getattr(message, "tool_call_id", None)
            name = getattr(message, "name", None)
        tool_name = str(name or call_id_to_name.get(str(tool_call_id)) or "unknown")
        results.setdefault(tool_name, []).append(_message_text(message))

    return results


def execute_output_failed(response: Any) -> bool:
    execute_outputs = "\n".join(tool_result_texts_by_name(response).get("execute", []))
    lowered = execute_outputs.lower()
    failure_markers = (
        "[stderr]",
        "exception during run",
        "traceback",
        "error:",
        "failed",
        "failing",
        "cannot find module",
        "command not found",
        "no such file or directory",
        "exit code",
    )
    return any(marker in lowered for marker in failure_markers)


def git_workspace_snapshot(workspace_dir: Path | None) -> dict[str, Any]:
    if workspace_dir is None or not (workspace_dir / ".git").exists():
        return {
            "workspace_present": workspace_dir is not None,
            "git_repo": False,
            "workspace_changed": False,
            "patch_nonempty": False,
            "git_status": "",
            "git_diff_stat": "",
            "git_untracked_files": "",
        }

    def run_git(command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(  # noqa: S603
            command,
            cwd=workspace_dir,
            check=False,
            capture_output=True,
            text=True,
        )

    status = run_git(["git", "status", "--short"])
    diff_stat = run_git(["git", "diff", "--stat"])
    untracked = run_git(["git", "ls-files", "--others", "--exclude-standard"])
    return {
        "workspace_present": True,
        "git_repo": True,
        "workspace_changed": bool(status.stdout.strip()),
        "patch_nonempty": bool(diff_stat.stdout.strip() or untracked.stdout.strip()),
        "git_status": status.stdout,
        "git_diff_stat": diff_stat.stdout,
        "git_untracked_files": untracked.stdout,
    }


def describe_execution_attempts(execution_results: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for index, result in enumerate(execution_results):
        tool_progress = result.get("tool_progress") or {}
        tool_names = tool_progress.get("tool_call_names") or []
        tool_text = ", ".join(str(name) for name in tool_names) or "none"
        response = limit_text(str(result.get("response_text") or "").strip(), 1800)
        parts.append(
            f"Attempt {index} tool calls: {tool_text}\n"
            f"Attempt {index} response:\n{response or '(empty response)'}"
        )
    return "\n\n".join(parts)


def build_execution_retry_prompt(
    *,
    task_prompt: str,
    planning_text: str,
    execution_results: list[dict[str, Any]],
    retry_reason: str,
) -> str:
    return (
        "Phase: execution_retry\n\n"
        f"The previous execution attempt stalled with guard reason: {retry_reason}.\n\n"
        "Continue the same SWE-bench task. Do not write another plan, todo list, "
        "markdown code fence, or next-steps section. Use real tool calls. If the "
        "previous reads gave enough context, call edit_file or write_file now. If one "
        "specific file is still missing, read that file and then edit/write. After "
        "editing, call execute with the validation command from the task prompt. "
        "A valid response for this retry must include edit_file or write_file and "
        "execute, unless a tool result shows a concrete blocker.\n\n"
        "Previous execution attempts:\n"
        f"{describe_execution_attempts(execution_results)}\n\n"
        "Planning output:\n"
        f"{planning_text or '(no planning output captured)'}\n\n"
        f"{task_prompt}"
    )


def combine_execution_attempt_text(execution_results: list[dict[str, Any]]) -> str:
    if len(execution_results) == 1:
        return str(execution_results[0].get("response_text") or "")
    parts: list[str] = []
    for index, result in enumerate(execution_results):
        tool_progress = result.get("tool_progress") or {}
        reason = result.get("execution_guard", {}).get("retry_reason")
        tool_names = ", ".join(str(name) for name in tool_progress.get("tool_call_names") or []) or "none"
        parts.append(
            f"### Execution attempt {index}\n\n"
            f"Tool calls: {tool_names}\n"
            f"Guard retry reason: {reason or 'none'}\n\n"
            f"{str(result.get('response_text') or '').strip() or '(empty response)'}"
        )
    return "\n\n".join(parts)


def describe_loop_steps(execution_results: list[dict[str, Any]], limit: int = 2200) -> str:
    parts: list[str] = []
    for index, result in enumerate(execution_results):
        tool_progress = result.get("tool_progress") or {}
        loop_state = result.get("execution_loop") or {}
        workspace = loop_state.get("workspace") or {}
        tool_names = ", ".join(str(name) for name in tool_progress.get("tool_call_names") or []) or "none"
        parts.append(
            f"Step {index} ({loop_state.get('step_type', 'unknown')})\n"
            f"Tools: {tool_names}\n"
            f"Workspace changed: {workspace.get('workspace_changed')}\n"
            f"Patch exists: {workspace.get('patch_nonempty')}\n"
            f"Execute failed: {loop_state.get('execute_failed')}\n"
            f"Response:\n{limit_text(str(result.get('response_text') or '').strip(), 900) or '(empty response)'}"
        )
    return limit_text("\n\n".join(parts), limit)


def next_execution_loop_step(
    *,
    execution_results: list[dict[str, Any]],
    require_test: bool,
) -> tuple[str | None, str]:
    if not execution_results:
        return "inspect", "start_with_inspection"

    last_result = execution_results[-1]
    last_loop = last_result.get("execution_loop") or {}
    last_workspace = last_loop.get("workspace") or {}
    last_progress = last_result.get("tool_progress") or {}
    any_workspace_changed = any(
        ((result.get("execution_loop") or {}).get("workspace") or {}).get("workspace_changed")
        for result in execution_results
    )
    any_patch_nonempty = any(
        ((result.get("execution_loop") or {}).get("workspace") or {}).get("patch_nonempty")
        for result in execution_results
    )
    any_execute = any((result.get("tool_progress") or {}).get("has_execute") for result in execution_results)
    any_edit = any((result.get("tool_progress") or {}).get("has_write_or_edit") for result in execution_results)
    last_has_execute = bool(last_progress.get("has_execute"))
    last_execute_failed = last_has_execute and bool(last_loop.get("execute_failed"))
    last_execute_succeeded = last_has_execute and not last_execute_failed

    if require_test and any_patch_nonempty and last_execute_succeeded:
        return None, "patch_and_validation_attempted"
    if not require_test and any_patch_nonempty:
        return None, "patch_produced"
    if require_test and any_patch_nonempty and last_execute_failed:
        return "fix", "validation_failed"
    if not any_workspace_changed and not any_edit:
        unique_names = set(last_progress.get("unique_tool_call_names") or [])
        if unique_names <= {"read_file", "grep", "glob", "ls"}:
            return "edit", "inspection_done_without_edit"
        return "edit", "no_workspace_change"
    if require_test and any_workspace_changed and not any_execute:
        return "test", "patch_needs_validation"
    if require_test and any_workspace_changed and any_execute and not last_has_execute:
        return "test", "post_fix_needs_validation"
    if any_workspace_changed and last_execute_failed:
        return "fix", "validation_failed"
    if any_workspace_changed and not last_workspace.get("patch_nonempty") and not any_patch_nonempty:
        return "edit", "workspace_changed_without_patch_signal"
    if require_test and any_workspace_changed and any_execute:
        return None, "workspace_changed_and_validation_attempted"
    if any_workspace_changed:
        return None, "workspace_changed"
    return "edit", "no_progress"


def build_execution_loop_prompt(
    *,
    step_type: str,
    task_prompt: str,
    planning_text: str,
    validation_command: str,
    execution_results: list[dict[str, Any]],
    stop_reason: str,
) -> str:
    prior_steps = describe_loop_steps(execution_results) if execution_results else "(no prior execution loop steps)"
    common = (
        f"Phase: execution_loop_{step_type}\n\n"
        f"Loop state reason: {stop_reason}.\n\n"
        "Do not write a plan, markdown code fence, or next-steps-only answer. "
        "Use the available tools now. Keep the response focused on this step.\n\n"
        "Planning output:\n"
        f"{planning_text or '(no planning output captured)'}\n\n"
        "Prior execution loop steps:\n"
        f"{prior_steps}\n\n"
    )
    if step_type == "inspect":
        instruction = (
            "This is the inspect step. Use read_file, grep, glob, or ls to inspect the "
            "specific files needed for the SWE-bench fix. Do not edit yet unless a file "
            "is clearly missing and the task explicitly requires creating it."
        )
    elif step_type == "edit":
        instruction = (
            "This is the edit step. Use the prior inspection and call edit_file or "
            "write_file now. If a required file is missing, create it with write_file. "
            "Do not stop after another read unless that read returns a concrete blocker."
        )
    elif step_type == "test":
        instruction = (
            "This is the test step. Run the validation command with execute now:\n"
            f"{validation_command}\n\n"
            "Do not edit in this step unless the validation command cannot be run without "
            "a tiny setup fix."
        )
    elif step_type == "fix":
        instruction = (
            "This is the fix step. The prior validation attempt appears to have failed. "
            "Use edit_file or write_file to fix the failure, then call execute with the "
            f"validation command: {validation_command}"
        )
    else:
        raise ValueError(f"Unsupported execution loop step: {step_type}")
    return f"{common}{instruction}\n\n{task_prompt}"


def mark_execution_loop_result(
    result: dict[str, Any],
    *,
    step_type: str,
    step_index: int,
    stop_reason: str,
    workspace_dir: Path | None,
    max_steps: int,
    require_test: bool,
) -> dict[str, Any]:
    workspace = git_workspace_snapshot(workspace_dir)
    execute_failed = execute_output_failed(result.get("response"))
    tool_results = tool_result_texts_by_name(result.get("response"))
    result["execution_loop"] = {
        "enabled": True,
        "step_index": step_index,
        "step_type": step_type,
        "input_reason": stop_reason,
        "max_steps": max_steps,
        "require_test": require_test,
        "workspace": workspace,
        "execute_failed": execute_failed,
        "tool_result_names": sorted(tool_results),
        "execute_result_preview": limit_text("\n\n".join(tool_results.get("execute", [])), 1800),
    }
    return result


def run_execution_loop(
    *,
    frontend_url: str,
    model: str,
    resolved_hints: dict[str, Any],
    task_prompt: str,
    planning_text: str,
    validation_command: str,
    workspace_dir: Path | None,
    app_variant: str,
    task_index: int | None,
    task_source: str | None,
    task_metadata: dict[str, Any],
    parent_run_id: str | None,
    hint_provider: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    max_steps = execution_loop_max_steps()
    require_test = execution_loop_require_test()
    execution_results: list[dict[str, Any]] = []
    next_step = "inspect"
    reason = "start_with_inspection"

    for step_index in range(max_steps):
        prompt = build_execution_loop_prompt(
            step_type=next_step,
            task_prompt=task_prompt,
            planning_text=planning_text,
            validation_command=validation_command,
            execution_results=execution_results,
            stop_reason=reason,
        )
        result = execute_phase_agent(
            phase="execution",
            sequence_index=step_index,
            frontend_url=frontend_url,
            model=model,
            base_hints=resolved_hints,
            prompt=prompt,
            workspace_dir=workspace_dir,
            app_variant=app_variant,
            task_index=task_index,
            task_source=task_source,
            task_metadata=task_metadata,
            parent_run_id=parent_run_id,
            step_title=f"Execution loop {step_index}: {next_step}",
            expected_output_tokens=2048,
            hint_provider=hint_provider,
        )
        mark_execution_loop_result(
            result,
            step_type=next_step,
            step_index=step_index,
            stop_reason=reason,
            workspace_dir=workspace_dir,
            max_steps=max_steps,
            require_test=require_test,
        )
        execution_results.append(result)
        next_step, reason = next_execution_loop_step(
            execution_results=execution_results,
            require_test=require_test,
        )
        log_lifecycle_event(
            stage="execution_loop_step_completed",
            payload={
                "event_kind": "execution_loop",
                "phase": "execution",
                "parent_run_id": parent_run_id,
                "step_index": step_index,
                "step_type": result["execution_loop"]["step_type"],
                "next_step_type": next_step,
                "next_reason": reason,
                "tool_progress": result.get("tool_progress"),
                "tool_call_details": result.get("tool_call_details"),
                "workspace": result["execution_loop"]["workspace"],
                "execute_failed": result["execution_loop"]["execute_failed"],
            },
        )
        if next_step is None:
            break

    final_next_step, final_reason = next_execution_loop_step(
        execution_results=execution_results,
        require_test=require_test,
    )
    if final_next_step is not None and len(execution_results) >= max_steps:
        final_reason = "max_steps_reached"

    trace = {
        "enabled": True,
        "max_steps": max_steps,
        "require_test": require_test,
        "step_count": len(execution_results),
        "final_reason": final_reason,
        "completed": final_next_step is None,
        "steps": [
            {
                "step_index": result.get("execution_loop", {}).get("step_index"),
                "step_type": result.get("execution_loop", {}).get("step_type"),
                "input_reason": result.get("execution_loop", {}).get("input_reason"),
                "tool_progress": result.get("tool_progress"),
                "tool_call_details": result.get("tool_call_details"),
                "workspace": result.get("execution_loop", {}).get("workspace"),
                "execute_failed": result.get("execution_loop", {}).get("execute_failed"),
                "execute_result_preview": result.get("execution_loop", {}).get("execute_result_preview"),
                "request_context": result.get("request_context"),
                "hints": result.get("hints"),
            }
            for result in execution_results
        ],
    }
    return execution_results, trace


# Reads provider metadata like finish reason and token usage from the final AI message.
def _response_metadata(response: Any) -> dict[str, Any]:
    message = _extract_last_ai_message(response)
    metadata = getattr(message, "response_metadata", None)
    if isinstance(metadata, dict):
        return metadata
    if isinstance(message, dict):
        raw = message.get("response_metadata")
        if isinstance(raw, dict):
            return raw
    return {}


# Reads normalized usage numbers from the final AI message when they are present.
def _usage_metadata(response: Any) -> dict[str, Any]:
    message = _extract_last_ai_message(response)
    metadata = getattr(message, "usage_metadata", None)
    if isinstance(metadata, dict):
        return metadata
    if isinstance(message, dict):
        raw = message.get("usage_metadata")
        if isinstance(raw, dict):
            return raw
    return {}


# Builds the measurement row we save for one model call.
def build_measurement_record(
    *,
    phase: str,
    model: str,
    frontend_url: str,
    prompt: str,
    hints: dict[str, Any],
    response: Any,
    started_at_perf: float,
    finished_at_perf: float,
    task_index: int | None,
    task_source: str | None,
    task_metadata: dict[str, Any] | None,
    request_context: dict[str, Any] | None = None,
    step_index: int | None = None,
    step_title: str | None = None,
    app_variant: str | None = None,
) -> dict[str, Any]:
    response_metadata = _response_metadata(response)
    usage_metadata = _usage_metadata(response)
    token_usage = response_metadata.get("token_usage", {}) if isinstance(response_metadata, dict) else {}
    prompt_token_details = token_usage.get("prompt_tokens_details", {}) if isinstance(token_usage, dict) else {}

    return {
        "task_index": task_index,
        "task_source": task_source,
        "task_metadata": task_metadata or {},
        "app_variant": app_variant,
        "request_context": request_context or {},
        "phase": phase,
        "step_index": step_index,
        "step_title": step_title,
        "frontend_url": frontend_url,
        "model": model,
        "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
        "hints": hints,
        "latency_ms": round((finished_at_perf - started_at_perf) * 1000, 3),
        "prompt_chars": len(prompt),
        "prompt_lines": len(prompt.splitlines()),
        "prompt_preview": _prompt_preview(prompt),
        "finish_reason": response_metadata.get("finish_reason"),
        "provider_response_id": response_metadata.get("id"),
        "model_name_reported": response_metadata.get("model_name"),
        "input_tokens": usage_metadata.get("input_tokens"),
        "output_tokens": usage_metadata.get("output_tokens"),
        "total_tokens": usage_metadata.get("total_tokens"),
        "cached_input_tokens": (
            usage_metadata.get("input_token_details", {}) or {}
        ).get("cache_read"),
        "prompt_tokens": token_usage.get("prompt_tokens") if isinstance(token_usage, dict) else None,
        "completion_tokens": token_usage.get("completion_tokens") if isinstance(token_usage, dict) else None,
        "total_tokens_reported": token_usage.get("total_tokens") if isinstance(token_usage, dict) else None,
        "cached_prompt_tokens": prompt_token_details.get("cached_tokens") if isinstance(prompt_token_details, dict) else None,
    }


# Stores the full prompt plus a few lightweight prompt stats for debugging.
def build_prompt_snapshot(prompt: str) -> dict[str, Any]:
    return {
        "prompt": prompt,
        "prompt_chars": len(prompt),
        "prompt_lines": len(prompt.splitlines()),
        "prompt_preview": _prompt_preview(prompt),
    }


# Stores the final response text plus the metadata we may want to inspect later.
def build_response_snapshot(response: Any) -> dict[str, Any]:
    response_metadata = _response_metadata(response)
    usage_metadata = _usage_metadata(response)
    text = response_text(response)
    return {
        "response_text": text,
        "response_preview": _prompt_preview(text),
        "response_metadata": response_metadata,
        "usage_metadata": usage_metadata,
        "tool_progress": summarize_tool_progress(response),
    }


# Creates a short one-line preview so logs stay readable.
def _prompt_preview(prompt: str) -> str:
    lines = [line.strip() for line in prompt.splitlines() if line.strip()]
    if not lines:
        return ""
    return " ".join(lines[:3])


# Writes a structured checkpoint entry for major harness events.
def log_outbound_harness_request(
    *,
    check_point: str,
    task_index: int | None,
    payload: dict[str, Any],
) -> None:
    log_checkpoint(
        check_point=check_point,
        task_index=task_index,
        payload=payload,
    )


# Chooses which instruction bundle to use: our local app or the upstream example app.
def resolve_app_root(app_variant: str = "local") -> Path:
    # Debugging note: this selects which instruction/skill surface the run uses.
    # "local" = our adapted app; "upstream_deploy_coding_agent" = cloned upstream example content.
    if app_variant == "local":
        return APP_ROOT
    if app_variant == "upstream_deploy_coding_agent":
        return UPSTREAM_DEPLOY_CODING_AGENT_ROOT
    raise ValueError(f"Unsupported app_variant: {app_variant}")


# Loads AGENTS.md and skills text into one system prompt for the selected app variant.
def load_agent_instructions(app_variant: str = "local") -> str:
    """Load the app-level instructions from AGENTS.md and skill docs.

    This makes `deepagents_app/` the active configuration surface instead of
    keeping the main workflow guidance embedded in the outer runner.
    """
    # Debugging note: this is where AGENTS.md and skills are folded into the live agent prompt.

    app_root = resolve_app_root(app_variant)
    agents_file = app_root / "AGENTS.md"
    skills_dir = app_root / "skills"

    if app_variant == "local":
        parts = [SYSTEM_PROMPT, PLANNING_NOTES, DYNAMO_HINT_NOTES]
    else:
        parts = []
    if agents_file.exists():
        parts.append(agents_file.read_text(encoding="utf-8").strip())

    if skills_dir.exists():
        for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
            skill_text = skill_path.read_text(encoding="utf-8").strip()
            if skill_text:
                parts.append(f"Skill reference: {skill_path.parent.name}\n{skill_text}")

    return "\n\n".join(part for part in parts if part)


# Converts a full chat-completions URL into the base /v1 URL expected by ChatOpenAI.
def frontend_base_url(frontend_url: str) -> str:
    # Debugging note: AgentBench receives a chat-completions URL,
    # but the OpenAI-compatible client wants the /v1 base URL.
    if "/v1/chat/completions" in frontend_url:
        return frontend_url.replace("/v1/chat/completions", "/v1")
    return frontend_url.rstrip("/")


# Merges default Dynamo hints with caller overrides and stamps the current phase on them.
def build_phase_hints(
    base_hints: dict[str, Any] | None = None,
    *,
    phase: str = "execution",
    hint_provider: str = HINT_PROVIDER_AGENTBENCH,
    request_context: dict[str, Any] | None = None,
    expected_output_tokens: int | None = None,
    sequence_index: int | None = None,
) -> dict[str, Any]:
    # Debugging note: this is the hint adaptation hook for Dynamo.
    # Every planning/step/synthesis request gets its own phase-tagged hint payload.
    return build_hint_payload(
        provider=hint_provider,
        default_hints=DEFAULT_DYNAMO_HINTS,
        base_hints=base_hints,
        phase=phase,
        request_context=request_context,
        expected_output_tokens=expected_output_tokens,
        sequence_index=sequence_index,
    )


def ensure_hint_probe_id(hints: dict[str, Any], *, parent_run_id: str | None) -> dict[str, Any]:
    """Attach a stable probe marker so hint propagation can be traced across layers."""
    resolved = dict(hints)
    if not resolved.get("hint_probe_id"):
        resolved["hint_probe_id"] = f"{parent_run_id or 'run'}::hint_probe"
    return resolved


def build_phase_probe_id(*, parent_run_id: str | None, phase: str, sequence_index: int) -> str:
    return f"{parent_run_id or 'run'}::{phase}::{sequence_index}"


# Builds the ChatOpenAI client that sends requests to the local Dynamo frontend.
def build_dynamo_chat_model(
    *,
    frontend_url: str,
    model: str,
    hint_payload: dict[str, Any] | None = None,
    request_context: dict[str, Any] | None = None,
    max_tokens: int = 2048,
) -> ChatOpenAI:
    # Debugging note: this is the Deep Agents -> Dynamo adaptation hook.
    # Instead of sending requests to a cloud model endpoint, the app points ChatOpenAI at local Dynamo.
    full_hint_payload = hint_payload or {}
    payload = supported_agent_hints(full_hint_payload)
    context = request_context or {}
    extra_body = {
        "nvext": {
            "request_context": context,
            "agent_context": build_agent_context(context),
            "annotations": build_annotations(context, full_hint_payload),
        },
    }
    if payload:
        extra_body["nvext"]["agent_hints"] = payload
    if os.environ.get("AGENTBENCH_SEND_TOP_LEVEL_EXTRA_ARGS", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        runtime_observability = {
            "agent_hints": payload or None,
            "agent_hints_source": full_hint_payload.get("hint_source") if full_hint_payload else "none",
            "agent_hints_keys": sorted(str(key) for key in payload),
            "hint_probe_id": full_hint_payload.get("hint_probe_id"),
            "request_context": context,
            "agent_context": build_agent_context(context),
            "annotations": build_annotations(context, full_hint_payload),
            "nvext": {
                "request_context": context,
                "agent_context": build_agent_context(context),
                "annotations": build_annotations(context, full_hint_payload),
            },
        }
        if payload:
            runtime_observability["nvext"]["agent_hints"] = payload
        extra_body["extra_args"] = {
            "runtime_observability": runtime_observability,
        }
    llm = ChatOpenAI(
        model=model,
        base_url=frontend_base_url(frontend_url),
        api_key="dummy",
        temperature=0.0,
        max_tokens=max_tokens,
        timeout=300,
        extra_body=extra_body,
    )
    return apply_tool_choice_override(llm)


def normalize_forced_tool_choice(value: str | None) -> str | None:
    choice = (value or "").strip()
    if not choice or choice.lower() in {"0", "false", "none", "off", "auto"}:
        return None
    return choice


def apply_tool_choice_override(llm: ChatOpenAI) -> ChatOpenAI:
    """Force LangChain-bound tools to use a specific OpenAI tool_choice.

    Dynamo/SGLang can parse tool calls when tool_choice is `required`, while
    some local models only emit text-like tool tags in auto mode. This wrapper
    keeps the normal Deep Agents flow, but changes the bound model request from
    auto to the configured tool_choice when tools are present.
    """
    forced_choice = normalize_forced_tool_choice(os.environ.get("AGENTBENCH_FORCE_TOOL_CHOICE"))
    if forced_choice is None:
        return llm

    original_bind_tools = llm.bind_tools

    @wraps(original_bind_tools)
    def bind_tools_with_forced_choice(tools, *args, **kwargs):
        existing_choice = kwargs.get("tool_choice")
        if existing_choice is None or str(existing_choice).strip().lower() == "auto":
            kwargs["tool_choice"] = forced_choice
        return original_bind_tools(tools, *args, **kwargs)

    object.__setattr__(llm, "bind_tools", bind_tools_with_forced_choice)
    log_lifecycle_event(
        stage="dynamo_chat_model_tool_choice_override",
        payload={
            "event_kind": "tool_choice_override",
            "forced_tool_choice": forced_choice,
        },
    )
    return llm


# Builds the Deep Agents filesystem/shell backend rooted at the task workspace.
def build_agent_backend(workspace_dir: Path | None):
    root_dir = str(workspace_dir or Path.cwd())
    ephemeral_backend = StateBackend()
    shell_backend = LocalShellBackend(
        root_dir=root_dir,
        inherit_env=True,
        env=os.environ.copy(),
        virtual_mode=False,
    )
    return CompositeBackend(
        default=shell_backend,
        routes={
            "/memories/": ephemeral_backend,
            "/conversation_history/": ephemeral_backend,
        },
    )


# Creates the actual Deep Agents coding agent wired to local Dynamo.
def build_coding_agent(
    *,
    frontend_url: str,
    model: str,
    workspace_dir: Path | None,
    base_hints: dict[str, Any] | None = None,
    phase: str = "execution",
    app_variant: str = "local",
    request_context: dict[str, Any] | None = None,
    prompt_stage: str = "step_agent_system_prompt_loaded",
):
    """Create the Deep Agents coding harness backed by a local Dynamo endpoint.
    """
    # Debugging note: this is the Deep Agents harness construction point.
    # The returned agent is powered by create_deep_agent(...) but wired to local Dynamo.

    system_prompt = load_agent_instructions(app_variant)
    log_lifecycle_event(
        stage=prompt_stage,
        payload={
            "event_kind": "prompt_context",
            "phase": phase,
            "app_variant": app_variant,
            "request_context": request_context or {},
            "system_prompt": system_prompt,
            "system_prompt_chars": len(system_prompt),
            "system_prompt_lines": len(system_prompt.splitlines()),
            "system_prompt_preview": _prompt_preview(system_prompt),
        },
    )
    llm = build_dynamo_chat_model(
        frontend_url=frontend_url,
        model=model,
        hint_payload=base_hints if base_hints is not None else build_phase_hints(base_hints, phase=phase),
        request_context=request_context,
    )
    backend = build_agent_backend(workspace_dir)
    return create_deep_agent(
        model=llm,
        system_prompt=system_prompt,
        backend=backend,
    )


# Extracts plain text from the final response object no matter how it is nested.
def response_text(response) -> str:
    if isinstance(response, Mapping):
        message = _extract_last_ai_message(response)
        if message is not response:
            return response_text(message)
        content = response.get("content")
        if content is not None:
            return response_text(content)
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                chunks.append(str(item["text"]))
            else:
                chunks.append(str(item))
        return "\n".join(chunks)
    if isinstance(response, str):
        return response
    return str(content if content is not None else response)


# Runs one end-to-end baseline Deep Agents call for a single SWE-bench task.
def execute_baseline_agent(
    *,
    frontend_url: str,
    model: str,
    base_hints: dict[str, Any],
    task_prompt: str,
    workspace_dir: Path | None,
    app_variant: str = "local",
    task_index: int | None = None,
    task_source: str | None = None,
    task_metadata: dict[str, Any] | None = None,
    parent_run_id: str | None = None,
    hint_provider: str = HINT_PROVIDER_AGENTBENCH,
) -> dict:
    request_context = build_request_context(
        parent_run_id=parent_run_id,
        task_instance_id=(task_metadata or {}).get("instance_id"),
        phase="baseline_execution",
        app_variant=app_variant,
    )
    baseline_hints = build_phase_hints(
        base_hints,
        phase="baseline_execution",
        hint_provider=hint_provider,
        request_context=request_context,
        expected_output_tokens=2048,
    )
    log_lifecycle_event(
        stage="baseline_agent_request_prepared",
        payload={
            "event_kind": "request_context",
            "phase": "baseline_execution",
            "task_source": task_source,
            "task_metadata": task_metadata or {},
            "frontend_url": frontend_url,
            "model": model,
            "hints": baseline_hints,
            "request_context": request_context,
            "workspace_dir": str(workspace_dir) if workspace_dir is not None else None,
        },
    )
    agent = build_coding_agent(
        frontend_url=frontend_url,
        model=model,
        workspace_dir=workspace_dir,
        base_hints=baseline_hints,
        phase="baseline_execution",
        app_variant=app_variant,
        request_context=request_context,
        prompt_stage="baseline_agent_system_prompt_loaded",
    )
    log_outbound_harness_request(
        check_point="2. Baseline Deep Agents request leaving harness",
        task_index=task_index,
        payload={
            "task_source": task_source,
            "task_metadata": task_metadata or {},
            "phase": "baseline_execution",
            "prompt_preview": _prompt_preview(task_prompt),
            "prompt": task_prompt,
            "hints": baseline_hints,
            "request_context": request_context,
            "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
        },
    )
    log_lifecycle_event(
        stage="baseline_agent_request_dispatched",
        payload={
            "event_kind": "request_dispatch",
            "phase": "baseline_execution",
            "frontend_url": frontend_url,
            "model": model,
            "hints": baseline_hints,
            "request_context": request_context,
            **build_prompt_snapshot(task_prompt),
        },
    )
    original_cwd = Path.cwd()
    try:
        if workspace_dir is not None:
            os.chdir(workspace_dir)
        started_at_perf = time.perf_counter()
        response = agent.invoke({"messages": [{"role": "user", "content": task_prompt}]})
        finished_at_perf = time.perf_counter()
    finally:
        os.chdir(original_cwd)
    measurement = build_measurement_record(
        phase="baseline_execution",
        model=model,
        frontend_url=frontend_url,
        prompt=task_prompt,
        hints=baseline_hints,
        response=response,
        started_at_perf=started_at_perf,
        finished_at_perf=finished_at_perf,
        task_index=task_index,
        task_source=task_source,
        task_metadata=task_metadata,
        request_context=request_context,
        app_variant=task_metadata.get("app_variant") if task_metadata else None,
    )
    log_lifecycle_event(
        stage="baseline_agent_response_received",
        payload={
            "event_kind": "response",
            "phase": "baseline_execution",
            "request_context": request_context,
            "measurement": measurement,
            **build_response_snapshot(response),
        },
    )
    return {
        "baseline_hints": baseline_hints,
        "baseline_prompt": task_prompt,
        "response": response,
        "response_text": response_text(response),
        "measurement": measurement,
    }


def build_phase_prompt(
    *,
    phase: str,
    task_prompt: str,
    planning_text: str = "",
    execution_text: str = "",
    patch_text: str = "",
) -> str:
    if phase == "planning":
        return (
            "Phase: planning\n\n"
            "Read the SWE-bench task and produce a concise implementation plan. "
            "Do not edit files in this phase. Do not end by telling a later phase to "
            "read a file next; instead identify the concrete files, functions, and code "
            "changes that execution should make. If the task prompt already names target "
            "files, treat those as enough to plan from. Return a short numbered edit plan, "
            "including the validation command to run after edits. Do not output empty JSON "
            "or markdown code fences.\n\n"
            f"{task_prompt}"
        )
    if phase == "execution":
        return (
            "Phase: execution\n\n"
            "Use the plan to implement the SWE-bench fix in the workspace. "
            "Make focused code changes only. If the planning output only proposes more "
            "inspection, continue with the task prompt and inspect the necessary files "
            "yourself. Do not return a prose plan or empty JSON fence. Use read_file when "
            "you need context, then use edit_file or write_file to apply the fix. After "
            "editing, run the validation command from the task prompt with execute. A final "
            "answer is valid only after an edit plus validation attempt, or after a concrete "
            "blocker from a tool result.\n\n"
            "Planning output:\n"
            f"{planning_text or '(no planning output captured)'}\n\n"
            f"{task_prompt}"
        )
    if phase == "patch_generation":
        return (
            "Phase: patch_generation\n\n"
            "Inspect the current workspace changes and consolidate the final patch. "
            "Do not start a broad refactor. Do not output an empty JSON fence. Use execute "
            "to inspect git status and git diff. If no edits exist, say explicitly that "
            "the workspace has no patch. If edits exist, return the changed files, intended "
            "behavior, and any checks run.\n\n"
            "Planning output:\n"
            f"{planning_text or '(no planning output captured)'}\n\n"
            "Execution output:\n"
            f"{execution_text or '(no execution output captured)'}"
        )
    if phase == "review":
        return (
            "Phase: review\n\n"
            "Review the current patch for bugs, missing tests, and behavioral risk. "
            "Keep the review concise and actionable. Do not undo unrelated changes. Do not "
            "output an empty JSON fence. Use execute to inspect git diff before reviewing; "
            "if there is no patch, say no patch was produced and name that as the blocker.\n\n"
            "Planning output:\n"
            f"{planning_text or '(no planning output captured)'}\n\n"
            "Execution output:\n"
            f"{execution_text or '(no execution output captured)'}\n\n"
            "Patch-generation output:\n"
            f"{patch_text or '(no patch-generation output captured)'}"
        )
    raise ValueError(f"Unsupported phase: {phase}")


def execute_phase_agent(
    *,
    phase: str,
    sequence_index: int,
    frontend_url: str,
    model: str,
    base_hints: dict[str, Any],
    prompt: str,
    workspace_dir: Path | None,
    app_variant: str = "local",
    task_index: int | None = None,
    task_source: str | None = None,
    task_metadata: dict[str, Any] | None = None,
    parent_run_id: str | None = None,
    step_title: str | None = None,
    expected_output_tokens: int = 1024,
    hint_provider: str = HINT_PROVIDER_AGENTBENCH,
) -> dict:
    request_context = build_request_context(
        parent_run_id=parent_run_id,
        task_instance_id=(task_metadata or {}).get("instance_id"),
        phase=phase,
        app_variant=app_variant,
        step_index=sequence_index,
        step_title=step_title or phase.replace("_", " ").title(),
    )
    phase_hints = build_phase_hints(
        base_hints,
        phase=phase,
        hint_provider=hint_provider,
        request_context=request_context,
        expected_output_tokens=expected_output_tokens,
        sequence_index=sequence_index,
    )
    if phase_hints:
        phase_hints["hint_probe_id"] = build_phase_probe_id(
            parent_run_id=parent_run_id,
            phase=phase,
            sequence_index=sequence_index,
        )
    log_lifecycle_event(
        stage=f"{phase}_request_prepared",
        payload={
            "event_kind": "request_context",
            "phase": phase,
            "task_source": task_source,
            "task_metadata": task_metadata or {},
            "frontend_url": frontend_url,
            "model": model,
            "hints": phase_hints,
            "request_context": request_context,
            "workspace_dir": str(workspace_dir) if workspace_dir is not None else None,
        },
    )
    agent = build_coding_agent(
        frontend_url=frontend_url,
        model=model,
        workspace_dir=workspace_dir,
        base_hints=phase_hints,
        phase=phase,
        app_variant=app_variant,
        request_context=request_context,
        prompt_stage=f"{phase}_agent_system_prompt_loaded",
    )
    log_outbound_harness_request(
        check_point=f"2. Deep Agents {phase} request leaving harness",
        task_index=task_index,
        payload={
            "task_source": task_source,
            "task_metadata": task_metadata or {},
            "phase": phase,
            "prompt_preview": _prompt_preview(prompt),
            "prompt": prompt,
            "hints": phase_hints,
            "request_context": request_context,
            "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
        },
    )
    log_lifecycle_event(
        stage=f"{phase}_request_dispatched",
        payload={
            "event_kind": "request_dispatch",
            "phase": phase,
            "frontend_url": frontend_url,
            "model": model,
            "hints": phase_hints,
            "request_context": request_context,
            **build_prompt_snapshot(prompt),
        },
    )
    original_cwd = Path.cwd()
    try:
        if workspace_dir is not None:
            os.chdir(workspace_dir)
        started_at_perf = time.perf_counter()
        response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        finished_at_perf = time.perf_counter()
    finally:
        os.chdir(original_cwd)
    measurement = build_measurement_record(
        phase=phase,
        model=model,
        frontend_url=frontend_url,
        prompt=prompt,
        hints=phase_hints,
        response=response,
        started_at_perf=started_at_perf,
        finished_at_perf=finished_at_perf,
        task_index=task_index,
        task_source=task_source,
        task_metadata=task_metadata,
        request_context=request_context,
        step_index=sequence_index,
        step_title=step_title,
        app_variant=app_variant,
    )
    log_lifecycle_event(
        stage=f"{phase}_response_received",
        payload={
            "event_kind": "response",
            "phase": phase,
            "request_context": request_context,
            "measurement": measurement,
            **build_response_snapshot(response),
        },
    )
    tool_progress = summarize_tool_progress(response)
    tool_call_details = extract_tool_call_details(response)
    return {
        "phase": phase,
        "sequence_index": sequence_index,
        "hints": phase_hints,
        "request_context": request_context,
        "prompt": prompt,
        "response": response,
        "response_text": response_text(response),
        "measurement": measurement,
        "tool_progress": tool_progress,
        "tool_call_details": tool_call_details,
    }


def combine_phase_response_text(phase_results: list[dict[str, Any]]) -> str:
    parts = ["# Phased SWE-bench Agent Run", ""]
    for phase_result in phase_results:
        phase = str(phase_result.get("phase") or "unknown")
        text = str(phase_result.get("response_text") or "").strip()
        parts.extend([f"## {phase}", "", text or "(no response text)", ""])
    return "\n".join(parts).strip() + "\n"


# Main entry point for one task: build the prompt, run phased agent calls, and package artifacts.
def run_task_workflow(
    *,
    frontend_url: str,
    model: str,
    task: dict,
    base_hints: dict[str, Any] | None = None,
    step_limit: int = 4,
    workspace_dir: Path | None = None,
    app_variant: str = "local",
    task_index: int | None = None,
    task_source: str | None = None,
    parent_run_id: str | None = None,
    hint_provider: str = HINT_PROVIDER_AGENTBENCH,
) -> dict:
    """Run the active phased Deep Agents workflow for one task."""
    # Debugging note: this is the app-layer orchestration entry point.
    # The wrapper calls this once per run, and this function owns:
    # prompt building, phase-tagged Deep Agents requests, and returned artifacts.

    validation_command = build_validation_command(task)
    task_overrides = load_task_overrides()
    prompt = apply_task_overrides(format_swebench_task_prompt(task), task_overrides)
    hint_provider = normalize_hint_provider(hint_provider)
    resolved_hints = dict(DEFAULT_DYNAMO_HINTS)
    if base_hints:
        resolved_hints.update(base_hints)
    resolved_hints = ensure_hint_probe_id(resolved_hints, parent_run_id=parent_run_id)
    task_metadata = {
        "instance_id": task.get("instance_id"),
        "repo": task.get("repo"),
        "app_variant": app_variant,
    }
    log_lifecycle_event(
        stage="task_workflow_started",
        payload={
            "event_kind": "workflow",
            "task_source": task_source,
            "task_metadata": task_metadata,
            "parent_run_id": parent_run_id,
            "frontend_url": frontend_url,
            "model": model,
            "step_limit": step_limit,
            "workspace_dir": str(workspace_dir) if workspace_dir is not None else None,
            "app_variant": app_variant,
            "task_overrides_file": task_overrides.get("path"),
            "task_overrides_applied": bool(task_overrides.get("text")),
        },
    )
    log_lifecycle_event(
        stage="task_prompt_built",
        payload={
            "event_kind": "prompt",
            "task_source": task_source,
            "task_metadata": task_metadata,
            "workspace_dir": str(workspace_dir) if workspace_dir is not None else None,
            **build_prompt_snapshot(prompt),
            "task_overrides_file": task_overrides.get("path"),
            "task_overrides_text": task_overrides.get("text"),
            "task_overrides_applied": bool(task_overrides.get("text")),
        },
    )
    log_lifecycle_event(
        stage="workflow_hints_resolved",
        payload={
            "event_kind": "hints",
            "task_source": task_source,
            "task_metadata": task_metadata,
            "resolved_hints": resolved_hints,
            "hint_provider": hint_provider,
            "step_limit": step_limit,
        },
    )
    if os.environ.get("AGENTBENCH_WORKFLOW_MODE", "phased").lower() in {"baseline", "single"}:
        result = execute_baseline_agent(
            frontend_url=frontend_url,
            model=model,
            base_hints=resolved_hints,
            task_prompt=prompt,
            workspace_dir=workspace_dir,
            app_variant=app_variant,
            task_index=task_index,
            task_source=task_source,
            task_metadata=task_metadata,
            parent_run_id=parent_run_id,
            hint_provider=hint_provider,
        )
        measurements = [result["measurement"]]
        decomposition_plan = {
            "steps": [],
            "planning_hints": None,
            "planning_prompt": None,
            "planning_response_text": None,
            "measurement": None,
        }
        step_results: list[dict] = []
        phase_results = [result]
        execution_loop_trace = {
            "enabled": False,
            "max_steps": execution_loop_max_steps(),
            "require_test": execution_loop_require_test(),
            "step_count": 0,
            "final_reason": "baseline_mode",
            "completed": False,
            "steps": [],
        }
    else:
        phase_results: list[dict[str, Any]] = []
        planning_prompt = build_phase_prompt(phase="planning", task_prompt=prompt)
        planning_result = execute_phase_agent(
            phase="planning",
            sequence_index=0,
            frontend_url=frontend_url,
            model=model,
            base_hints=resolved_hints,
            prompt=planning_prompt,
            workspace_dir=workspace_dir,
            app_variant=app_variant,
            task_index=task_index,
            task_source=task_source,
            task_metadata=task_metadata,
            parent_run_id=parent_run_id,
            step_title="Plan SWE-bench fix",
            expected_output_tokens=768,
            hint_provider=hint_provider,
        )
        phase_results.append(planning_result)

        execution_loop_trace: dict[str, Any]
        if execution_loop_enabled():
            execution_results, execution_loop_trace = run_execution_loop(
                frontend_url=frontend_url,
                model=model,
                resolved_hints=resolved_hints,
                task_prompt=prompt,
                planning_text=planning_result["response_text"],
                validation_command=validation_command,
                workspace_dir=workspace_dir,
                app_variant=app_variant,
                task_index=task_index,
                task_source=task_source,
                task_metadata=task_metadata,
                parent_run_id=parent_run_id,
                hint_provider=hint_provider,
            )
            phase_results.extend(execution_results)
            retry_limit = 0
        else:
            execution_prompt = build_phase_prompt(
                phase="execution",
                task_prompt=prompt,
                planning_text=planning_result["response_text"],
            )
            execution_result = execute_phase_agent(
                phase="execution",
                sequence_index=0,
                frontend_url=frontend_url,
                model=model,
                base_hints=resolved_hints,
                prompt=execution_prompt,
                workspace_dir=workspace_dir,
                app_variant=app_variant,
                task_index=task_index,
                task_source=task_source,
                task_metadata=task_metadata,
                parent_run_id=parent_run_id,
                step_title="Implement SWE-bench fix",
                expected_output_tokens=2048,
                hint_provider=hint_provider,
            )
            execution_result["execution_guard"] = {
                "attempt_index": 0,
                "retry_reason": execution_retry_reason(execution_result["tool_progress"]),
                "retry_limit": env_int("AGENTBENCH_EXECUTION_RETRY_LIMIT", default=2),
                "guard_enabled": env_flag("AGENTBENCH_EXECUTION_GUARD", default=True),
            }
            phase_results.append(execution_result)
            execution_results = [execution_result]

            retry_limit = env_int("AGENTBENCH_EXECUTION_RETRY_LIMIT", default=2)
            while (
                (retry_reason := execution_retry_reason(execution_results[-1]["tool_progress"]))
                and len(execution_results) <= retry_limit
            ):
                retry_index = len(execution_results)
                log_lifecycle_event(
                    stage="execution_retry_guard_triggered",
                    payload={
                        "event_kind": "guard",
                        "phase": "execution",
                        "retry_index": retry_index,
                        "retry_reason": retry_reason,
                        "retry_limit": retry_limit,
                        "parent_run_id": parent_run_id,
                        "task_source": task_source,
                        "task_metadata": task_metadata,
                        "previous_tool_progress": execution_results[-1].get("tool_progress"),
                    },
                )
                retry_prompt = build_execution_retry_prompt(
                    task_prompt=prompt,
                    planning_text=planning_result["response_text"],
                    execution_results=execution_results,
                    retry_reason=retry_reason,
                )
                retry_result = execute_phase_agent(
                    phase="execution",
                    sequence_index=retry_index,
                    frontend_url=frontend_url,
                    model=model,
                    base_hints=resolved_hints,
                    prompt=retry_prompt,
                    workspace_dir=workspace_dir,
                    app_variant=app_variant,
                    task_index=task_index,
                    task_source=task_source,
                    task_metadata=task_metadata,
                    parent_run_id=parent_run_id,
                    step_title=f"Implement SWE-bench fix retry {retry_index}",
                    expected_output_tokens=2048,
                    hint_provider=hint_provider,
                )
                retry_result["execution_guard"] = {
                    "attempt_index": retry_index,
                    "retry_reason": execution_retry_reason(retry_result["tool_progress"]),
                    "previous_retry_reason": retry_reason,
                    "retry_limit": retry_limit,
                    "guard_enabled": env_flag("AGENTBENCH_EXECUTION_GUARD", default=True),
                }
                execution_results.append(retry_result)
                phase_results.append(retry_result)
            execution_loop_trace = {
                "enabled": False,
                "max_steps": execution_loop_max_steps(),
                "require_test": execution_loop_require_test(),
                "step_count": 0,
                "final_reason": "disabled",
                "completed": False,
                "steps": [],
            }

        execution_result = execution_results[-1] if execution_results else planning_result
        execution_text = combine_execution_attempt_text(execution_results)

        patch_prompt = build_phase_prompt(
            phase="patch_generation",
            task_prompt=prompt,
            planning_text=planning_result["response_text"],
            execution_text=execution_text,
        )
        patch_result = execute_phase_agent(
            phase="patch_generation",
            sequence_index=0,
            frontend_url=frontend_url,
            model=model,
            base_hints=resolved_hints,
            prompt=patch_prompt,
            workspace_dir=workspace_dir,
            app_variant=app_variant,
            task_index=task_index,
            task_source=task_source,
            task_metadata=task_metadata,
            parent_run_id=parent_run_id,
            step_title="Consolidate patch",
            expected_output_tokens=1024,
            hint_provider=hint_provider,
        )
        phase_results.append(patch_result)

        review_prompt = build_phase_prompt(
            phase="review",
            task_prompt=prompt,
            planning_text=planning_result["response_text"],
            execution_text=execution_text,
            patch_text=patch_result["response_text"],
        )
        review_result = execute_phase_agent(
            phase="review",
            sequence_index=0,
            frontend_url=frontend_url,
            model=model,
            base_hints=resolved_hints,
            prompt=review_prompt,
            workspace_dir=workspace_dir,
            app_variant=app_variant,
            task_index=task_index,
            task_source=task_source,
            task_metadata=task_metadata,
            parent_run_id=parent_run_id,
            step_title="Review patch",
            expected_output_tokens=1024,
            hint_provider=hint_provider,
        )
        phase_results.append(review_result)

        measurements = [phase_result["measurement"] for phase_result in phase_results]
        execution_plan_steps = [
            {
                "phase": "execution",
                "title": (
                    f"Execution loop {index}: {result.get('execution_loop', {}).get('step_type')}"
                    if execution_loop_trace.get("enabled")
                    else (
                        "Implement SWE-bench fix"
                        if index == 0
                        else f"Implement SWE-bench fix retry {index}"
                    )
                ),
                "hint_probe_id": result["hints"].get("hint_probe_id"),
                "tool_progress": result.get("tool_progress"),
                "tool_call_details": result.get("tool_call_details"),
                "execution_guard": result.get("execution_guard"),
                "execution_loop": result.get("execution_loop"),
            }
            for index, result in enumerate(execution_results)
        ]
        decomposition_plan = {
            "steps": [
                {
                    "phase": "planning",
                    "title": "Plan SWE-bench fix",
                    "hint_probe_id": planning_result["hints"].get("hint_probe_id"),
                },
                *execution_plan_steps,
                {
                    "phase": "patch_generation",
                    "title": "Consolidate patch",
                    "hint_probe_id": patch_result["hints"].get("hint_probe_id"),
                },
                {
                    "phase": "review",
                    "title": "Review patch",
                    "hint_probe_id": review_result["hints"].get("hint_probe_id"),
                },
            ],
            "planning_hints": planning_result["hints"],
            "planning_prompt": planning_result["prompt"],
            "planning_response_text": planning_result["response_text"],
            "measurement": planning_result["measurement"],
        }
        step_results = [
            {
                "phase": phase_result["phase"],
                "sequence_index": phase_result["sequence_index"],
                "request_context": phase_result["request_context"],
                "hints": phase_result["hints"],
                "response_text": phase_result["response_text"],
                "measurement": phase_result["measurement"],
                "tool_progress": phase_result.get("tool_progress"),
                "tool_call_details": phase_result.get("tool_call_details"),
                "execution_guard": phase_result.get("execution_guard"),
                "execution_loop": phase_result.get("execution_loop"),
            }
            for phase_result in phase_results
        ]
        primary_result = execution_result
        result = {
            **primary_result,
            "baseline_hints": primary_result["hints"],
            "baseline_prompt": primary_result["prompt"],
            "response_text": combine_phase_response_text(phase_results),
            "execution_guard": {
                "guard_enabled": env_flag("AGENTBENCH_EXECUTION_GUARD", default=True),
                "retry_limit": retry_limit,
                "attempt_count": len(execution_results),
                "final_tool_progress": execution_result.get("tool_progress"),
                "final_retry_reason": execution_retry_reason(execution_result.get("tool_progress") or {}),
            },
            "execution_loop": execution_loop_trace,
            "phase_results": [
                {
                    "phase": phase_result["phase"],
                    "sequence_index": phase_result["sequence_index"],
                    "request_context": phase_result["request_context"],
                    "hints": phase_result["hints"],
                    "prompt": phase_result["prompt"],
                    "response_text": phase_result["response_text"],
                    "measurement": phase_result["measurement"],
                    "tool_progress": phase_result.get("tool_progress"),
                    "tool_call_details": phase_result.get("tool_call_details"),
                    "execution_guard": phase_result.get("execution_guard"),
                    "execution_loop": phase_result.get("execution_loop"),
                }
                for phase_result in phase_results
            ],
        }
    phase_names = [str(phase_result.get("phase") or "") for phase_result in phase_results]
    log_lifecycle_event(
        stage="phased_requests_completed",
        payload={
            "event_kind": "workflow",
            "task_source": task_source,
            "task_metadata": task_metadata,
            "parent_run_id": parent_run_id,
            "phases": phase_names,
            "phase_count": len(phase_names),
            "measurement_count": len(measurements),
        },
    )
    log_lifecycle_event(
        stage="task_workflow_completed",
        payload={
            "event_kind": "workflow",
            "task_source": task_source,
            "task_metadata": task_metadata,
            "parent_run_id": parent_run_id,
            "step_count": len(step_results),
            "measurement_count": len(measurements),
            "plan_steps": decomposition_plan.get("steps", []),
            "final_response_preview": _prompt_preview(result["response_text"]),
        },
    )
    return {
        "prompt": prompt,
        "validation_command": validation_command,
        "task_overrides": task_overrides,
        "resolved_hints": resolved_hints,
        "hint_provider": hint_provider,
        "app_variant": app_variant,
        "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
        "decomposition_plan": decomposition_plan,
        "step_results": step_results,
        "phase_results": phase_results,
        "execution_loop_trace": execution_loop_trace,
        "result": result,
        "measurements": measurements,
    }
