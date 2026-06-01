"""Prompt surfaces for the upstream-aligned Deep Agents app."""

from __future__ import annotations

import json
import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK_OVERRIDES_FILE = APP_ROOT / "prompts" / "task_overrides.txt"
PROMPT_OVERRIDES_ENV = "AGENTBENCH_PROMPT_OVERRIDES"
PROMPT_OVERRIDES_FILE_ENV = "AGENTBENCH_PROMPT_OVERRIDES_FILE"
PROMPT_OVERRIDES_DISABLED_VALUES = {"0", "false", "no", "off", "none", "disabled"}

SYSTEM_PROMPT = (
    "You are a careful software engineering agent. "
    "Plan first, inspect real files when available, keep changes minimal, "
    "and summarize what still needs validation."
)

PLANNING_NOTES = (
    "Break the task into explicit steps before implementation. "
    "Prefer a small number of meaningful steps over a long checklist."
)

DYNAMO_HINT_NOTES = (
    "Requests may be tagged with phase-aware agent hints. "
    "Treat planning, execution, and synthesis as separate phases."
)


def _decode_task_field(value: object) -> object:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return ""
    if text[:1] in {'"', "[", "{"}:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


def _normalize_text(value: object, *, fallback: str) -> str:
    decoded = _decode_task_field(value)
    if decoded is None:
        return fallback
    if isinstance(decoded, list):
        lines = [str(item).strip() for item in decoded if str(item).strip()]
        return "\n".join(f"- {line}" for line in lines) or fallback
    text = str(decoded).strip()
    return text or fallback


def _normalize_list(value: object) -> list[str]:
    decoded = _decode_task_field(value)
    if isinstance(decoded, list):
        return [str(item).strip() for item in decoded if str(item).strip()]
    if isinstance(decoded, str):
        return [line.strip() for line in decoded.splitlines() if line.strip()]
    if decoded:
        return [str(decoded).strip()]
    return []


def build_validation_command(task: dict) -> str:
    """Build an explicit validation command for known selected-test shapes."""

    selected_tests = _normalize_list(task.get("selected_test_files_to_run", ""))
    if selected_tests and all(test.endswith(".js") for test in selected_tests):
        return "npx mocha --timeout 30000 " + " ".join(selected_tests)
    return ""


class _PromptOverrideValues(dict):
    def __missing__(self, key: str) -> str:
        return ""


def prompt_overrides_enabled() -> bool:
    value = os.environ.get(PROMPT_OVERRIDES_ENV, "1").strip().lower()
    return value not in PROMPT_OVERRIDES_DISABLED_VALUES


def prompt_overrides_path() -> Path:
    configured_path = os.environ.get(PROMPT_OVERRIDES_FILE_ENV, "").strip()
    if configured_path:
        return Path(configured_path).expanduser()
    return DEFAULT_TASK_OVERRIDES_FILE


def load_prompt_overrides_template() -> str:
    if not prompt_overrides_enabled():
        return ""
    path = prompt_overrides_path()
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def render_task_prompt_overrides(task: dict) -> str:
    template = load_prompt_overrides_template()
    if not template:
        return ""
    values = _PromptOverrideValues(
        validation_command=build_validation_command(task) or "Not provided.",
        selected_tests=_normalize_text(
            task.get("selected_test_files_to_run", ""),
            fallback="Not provided.",
        ),
        repo=str(task.get("repo", "unknown_repo")),
        instance_id=str(task.get("instance_id", "unknown_instance")),
        workspace_path=str(task.get("workspace_path", "")).strip(),
    )
    return template.format_map(values).strip()


def format_swebench_task_prompt(task: dict) -> str:
    """Build the main SWE-bench-style task prompt for the Deep Agents app."""

    repo = task.get("repo", "unknown_repo")
    instance_id = task.get("instance_id", "unknown_instance")
    problem_statement = _normalize_text(
        task.get("problem_statement", ""),
        fallback="None provided.",
    )
    requirements = _normalize_text(
        task.get("requirements", ""),
        fallback="None provided.",
    )
    interface = _normalize_text(
        task.get("interface", ""),
        fallback="None provided.",
    )
    selected_tests = _normalize_text(
        task.get("selected_test_files_to_run", ""),
        fallback="Not provided.",
    )
    prompt_overrides = render_task_prompt_overrides(task)
    prompt_overrides_section = f"\n{prompt_overrides}\n" if prompt_overrides else ""

    workspace_path = str(task.get("workspace_path", "")).strip()
    workspace_notes = (
        f"You have a writable local workspace at:\n{workspace_path}\n\n"
        "Use the available filesystem and shell tools to inspect the repo, edit files when needed, "
        "run focused validation, and leave the workspace in a state where a git diff can be captured."
        if workspace_path
        else "No local repo workspace was provided for this run."
    )

    return f"""You are working on one SWE-bench Pro software engineering task.

Task metadata:
- instance_id: {instance_id}
- repo: {repo}

Problem statement:
{problem_statement}

Requirements:
{requirements}

Interface / environment notes:
{interface}

Selected tests to run:
{selected_tests}
{prompt_overrides_section}

Workspace:
{workspace_notes}

Solve the issue in the workspace if you can.

Expectations:
- Inspect the real repo before deciding on changes.
- Use the available tools to read files, edit code, and run focused commands or tests when useful.
- Do not stop at a plan if you can make progress on the fix.
- Report only what you actually changed and actually validated.
- If you are blocked, explain the specific blocker briefly."""
