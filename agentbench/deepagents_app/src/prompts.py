"""Prompt surfaces for the upstream-aligned Deep Agents app."""

from __future__ import annotations

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


def format_swebench_task_prompt(task: dict) -> str:
    """Build the main SWE-bench-style task prompt for the Deep Agents app."""

    repo = task.get("repo", "unknown_repo")
    instance_id = task.get("instance_id", "unknown_instance")
    problem_statement = str(task.get("problem_statement", "")).strip()
    requirements = str(task.get("requirements", "")).strip()
    interface = str(task.get("interface", "")).strip()
    selected_tests = str(task.get("selected_test_files_to_run", "")).strip()

    workspace_path = str(task.get("workspace_path", "")).strip()
    workspace_notes = (
        f"You have a writable local workspace at:\n{workspace_path}\n\n"
        "Use the available filesystem and shell tools to inspect the repo, make changes if needed, "
        "and leave the workspace in a state where a git diff can be captured."
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
{requirements if requirements else "None provided."}

Interface / environment notes:
{interface if interface else "None provided."}

Selected tests to run:
{selected_tests if selected_tests else "Not provided."}

Workspace:
{workspace_notes}

Your job:
1. Break this task into concrete steps.
2. Identify what information would be needed to solve it well.
3. Inspect the local repo if a workspace is available.
4. Produce a structured plan for solving it.
5. If the workspace is available, make a safe first-pass fix in the repo.
6. Summarize what changed and what should be validated next.

Do not claim that code was changed or tests were run unless you actually did so.
Focus on decomposition, reasoning, and a clear action plan."""
