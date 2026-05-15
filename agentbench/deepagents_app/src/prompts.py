"""Prompt surfaces for the upstream-aligned Deep Agents app."""

from __future__ import annotations

import json

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

Workspace:
{workspace_notes}

Solve the issue in the workspace if you can.

Expectations:
- Inspect the real repo before deciding on changes.
- Use the available tools to read files, edit code, and run focused commands or tests when useful.
- Do not stop at a plan if you can make progress on the fix.
- Report only what you actually changed and actually validated.
- If you are blocked, explain the specific blocker briefly."""
