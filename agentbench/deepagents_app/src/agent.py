"""Deep Agents app wiring for local Dynamo-backed coding runs.

This is the target location for moving model construction and hint-aware
phase logic out of the repo-local runner and into a source-level Deep Agents app.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from agentbench.log_utils import log_checkpoint

THIS_FILE = Path(__file__).resolve()
APP_ROOT = THIS_FILE.parents[1]
AGENTBENCH_ROOT = APP_ROOT.parents[1]
UPSTREAM_ROOT = AGENTBENCH_ROOT / "upstream" / "deepagents"
CLONED_DEEPAGENTS_LIB_ROOT = UPSTREAM_ROOT / "libs" / "deepagents"
if CLONED_DEEPAGENTS_LIB_ROOT.exists() and str(CLONED_DEEPAGENTS_LIB_ROOT) not in sys.path:
    # Debugging note: this is the "use the downloaded GitHub repo first" hook.
    sys.path.insert(0, str(CLONED_DEEPAGENTS_LIB_ROOT))

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from .prompts import (
    DYNAMO_HINT_NOTES,
    PLANNING_NOTES,
    SYSTEM_PROMPT,
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

DEEPAGENTS_RUNTIME_SOURCE = (
    str(CLONED_DEEPAGENTS_LIB_ROOT)
    if CLONED_DEEPAGENTS_LIB_ROOT.exists()
    else "python_environment"
)


def _prompt_preview(prompt: str) -> str:
    lines = [line.strip() for line in prompt.splitlines() if line.strip()]
    if not lines:
        return ""
    return " ".join(lines[:3])


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


def resolve_app_root(app_variant: str = "local") -> Path:
    # Debugging note: this selects which instruction/skill surface the run uses.
    # "local" = our adapted app; "upstream_deploy_coding_agent" = cloned upstream example content.
    if app_variant == "local":
        return APP_ROOT
    if app_variant == "upstream_deploy_coding_agent":
        return UPSTREAM_DEPLOY_CODING_AGENT_ROOT
    raise ValueError(f"Unsupported app_variant: {app_variant}")


def load_agent_instructions(app_variant: str = "local") -> str:
    """Load the app-level instructions from AGENTS.md and skill docs.

    This makes `deepagents_app/` the active configuration surface instead of
    keeping the main workflow guidance embedded in the outer runner.
    """
    # Debugging note: this is where AGENTS.md and skills are folded into the live agent prompt.

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
    # Debugging note: AgentBench receives a chat-completions URL,
    # but the OpenAI-compatible client wants the /v1 base URL.
    if "/v1/chat/completions" in frontend_url:
        return frontend_url.replace("/v1/chat/completions", "/v1")
    return frontend_url.rstrip("/")


def build_phase_hints(base_hints: dict[str, Any] | None = None, *, phase: str = "execution") -> dict[str, Any]:
    # Debugging note: this is the hint adaptation hook for Dynamo.
    # Every planning/step/synthesis request gets its own phase-tagged hint payload.
    hints = dict(DEFAULT_DYNAMO_HINTS)
    if base_hints:
        hints.update(base_hints)
    hints["agent_phase"] = phase
    return hints


def build_dynamo_chat_model(
    *,
    frontend_url: str,
    model: str,
    hint_payload: dict[str, Any] | None = None,
    max_tokens: int = 2048,
) -> ChatOpenAI:
    # Debugging note: this is the Deep Agents -> Dynamo adaptation hook.
    # Instead of sending requests to a cloud model endpoint, the app points ChatOpenAI at local Dynamo.
    payload = hint_payload or dict(DEFAULT_DYNAMO_HINTS)
    extra_body = {"nvext": {"agent_hints": payload}}
    return ChatOpenAI(
        model=model,
        base_url=frontend_base_url(frontend_url),
        api_key="dummy",
        temperature=0.0,
        max_tokens=max_tokens,
        timeout=300,
        extra_body=extra_body,
    )


def build_coding_agent(
    *,
    frontend_url: str,
    model: str,
    base_hints: dict[str, Any] | None = None,
    phase: str = "execution",
    app_variant: str = "local",
):
    """Create the Deep Agents coding harness backed by a local Dynamo endpoint.
    """
    # Debugging note: this is the Deep Agents harness construction point.
    # The returned agent is powered by create_deep_agent(...) but wired to local Dynamo.

    llm = build_dynamo_chat_model(
        frontend_url=frontend_url,
        model=model,
        hint_payload=build_phase_hints(base_hints, phase=phase),
    )
    return create_deep_agent(
        model=llm,
        system_prompt=load_agent_instructions(app_variant),
    )


def response_text(response) -> str:
    if isinstance(response, dict):
        messages = response.get("messages")
        if isinstance(messages, list):
            for message in reversed(messages):
                message_type = getattr(message, "type", None) or message.get("type") if isinstance(message, dict) else None
                if message_type == "ai":
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


def parse_decomposition_plan(raw_text: str, *, fallback_count: int) -> list[dict]:
    # Debugging note: this parser lets the workflow survive weak planning output.
    # It prefers JSON, but falls back to extracting step-like lines from plain prose.
    json_match = re.search(r"\{[\s\S]*\}", raw_text)
    candidate_texts = [raw_text]
    if json_match:
        candidate_texts.insert(0, json_match.group(0))

    for candidate in candidate_texts:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                parsed = parsed.get("steps", [])
            if isinstance(parsed, list):
                normalized = []
                for idx, item in enumerate(parsed, start=1):
                    if isinstance(item, str):
                        normalized.append({"step_id": idx, "title": item, "goal": item})
                    elif isinstance(item, dict):
                        normalized.append(
                            {
                                "step_id": item.get("step_id", idx),
                                "title": str(item.get("title", f"Step {idx}")),
                                "goal": str(item.get("goal", item.get("title", f"Step {idx}"))),
                                "deliverable": str(item.get("deliverable", "")),
                            }
                        )
                if normalized:
                    return normalized[:fallback_count]
        except Exception:  # noqa: BLE001
            pass

    candidate_lines = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip(" -0123456789.")
        if not line:
            continue
        if line.lower().startswith(("sure,", "example json", "summary")):
            continue
        if line.startswith("### Step"):
            continue
        if ":" in line:
            title, _, remainder = line.partition(":")
            if len(title.split()) <= 8 and remainder.strip():
                line = title.strip("*# ") + ": " + remainder.strip()
        candidate_lines.append(line)

    filtered = []
    seen = set()
    for line in candidate_lines:
        normalized_line = line.strip()
        if normalized_line in seen:
            continue
        seen.add(normalized_line)
        if any(
            keyword in normalized_line.lower()
            for keyword in ("inspect", "identify", "propose", "check", "review", "trace")
        ):
            filtered.append(normalized_line)

    lines = filtered or candidate_lines
    fallback = []
    for idx, line in enumerate(lines[:fallback_count], start=1):
        title = line.strip("*# ")
        fallback.append({"step_id": idx, "title": title, "goal": title, "deliverable": ""})
    return fallback


def generate_decomposition_plan(
    *,
    frontend_url: str,
    model: str,
    base_hints: dict[str, Any],
    prompt: str,
    step_limit: int,
    task_index: int | None = None,
    task_source: str | None = None,
    task_metadata: dict[str, Any] | None = None,
) -> dict:
    # [CHECK_POINT 3] The harness explicitly decomposes the hard task into steps here.
    # [CHECK_POINT 3] Planning phase happens here.
    # Debugging note: this is the planning-stage model request.
    # It turns one task prompt into a decomposition plan before any step execution happens.
    planning_hints = build_phase_hints(base_hints, phase="planning")
    planning_hints["latency_sensitivity"] = 0.4
    planning_hints["expected_output_tokens"] = 512
    llm = build_dynamo_chat_model(
        frontend_url=frontend_url,
        model=model,
        hint_payload=planning_hints,
        max_tokens=1024,
    )
    preferred_step_guidance = ""
    if "--dry-run" in prompt or "temporary working directory" in prompt or "temporary directories" in prompt:
        preferred_step_guidance = f"""

Prefer task-specific steps over generic planning language.
For this kind of CLI dry-run bug, prefer up to {step_limit} steps like:
1. inspect argument parsing for `--dry-run`
2. inspect the dispatch or command execution flow
3. inspect the helper that creates temporary directories
4. propose a safe high-level fix strategy

Use concrete titles such as:
- "Inspect argument parsing for --dry-run"
- "Inspect dispatch flow for dry-run handling"
- "Inspect temporary-directory helper"
- "Propose safe fix strategy"

Do not use placeholder titles like:
- "Short title"
- "Step 1"
- "Break the task into concrete steps"
- "What this step should accomplish"
"""
    planning_prompt = f"""{prompt}

Return only valid JSON in this exact shape:
{{
  "steps": [
    {{
      "step_id": 1,
      "title": "short title",
      "goal": "what this step should accomplish",
      "deliverable": "what artifact or answer this step should produce"
    }}
  ]
}}

Keep it to at most {step_limit} steps.{preferred_step_guidance}"""

    planning_prompt += "\n\nDo not include markdown, bullet points, commentary, or code fences.\nStart with `{` and end with `}`."
    # [CHECK_POINT 3] Planning request leaving the Deep Agents harness for Dynamo.
    log_outbound_harness_request(
        check_point="3. Planning request leaving Deep Agents harness",
        task_index=task_index,
        payload={
            "task_source": task_source,
            "task_metadata": task_metadata or {},
            "phase": "planning",
            "prompt_preview": _prompt_preview(planning_prompt),
            "prompt": planning_prompt,
            "hints": planning_hints,
            "step_limit": step_limit,
            "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
        },
    )
    response = llm.invoke(planning_prompt)
    raw_text = response_text(response)
    steps = parse_decomposition_plan(raw_text, fallback_count=step_limit)
    return {
        "planning_hints": planning_hints,
        "planning_prompt": planning_prompt,
        "planning_response_text": raw_text,
        "steps": steps,
    }


def execute_plan_steps(
    *,
    frontend_url: str,
    model: str,
    base_hints: dict[str, Any],
    task_prompt: str,
    plan_steps: list[dict],
    workspace_dir: Path | None,
    app_variant: str = "local",
    task_index: int | None = None,
    task_source: str | None = None,
    task_metadata: dict[str, Any] | None = None,
) -> list[dict]:
    # [CHECK_POINT 4] The harness sends explicit step-level requests to the frontend here.
    # [CHECK_POINT 4] Step-by-step execution happens here.
    # Debugging note: this is the step-execution loop.
    # The app sends one Deep Agents request per planned step and optionally operates inside the repo workspace.
    step_results: list[dict] = []
    prior_step_summaries: list[str] = []
    original_cwd = Path.cwd()

    try:
        if workspace_dir is not None:
            os.chdir(workspace_dir)

        for idx, step in enumerate(plan_steps, start=1):
            # Debugging note: each iteration here becomes one Checkpoint 4 payload.
            step_hints = build_phase_hints(base_hints, phase=f"step_{idx}_execution")
            step_hints["expected_output_tokens"] = 768
            agent = build_coding_agent(
                frontend_url=frontend_url,
                model=model,
                base_hints=step_hints,
                phase=f"step_{idx}_execution",
                app_variant=app_variant,
            )
            prior_context = "\n".join(
                f"- Step {i + 1} summary: {summary}" for i, summary in enumerate(prior_step_summaries)
            ) or "None yet."
            step_prompt = f"""{task_prompt}

Approved decomposition plan:
{json.dumps(plan_steps, indent=2)}

Current step:
{json.dumps(step, indent=2)}

Completed step summaries so far:
{prior_context}

Your job for this step:
1. Focus only on the current step.
2. Inspect or modify the workspace if it is available and needed.
3. Produce a concise step summary.
4. Say exactly what files or code locations mattered for this step.
5. Do not invent test runs or edits you did not perform."""
            # [CHECK_POINT 4] Step execution request leaving the Deep Agents harness for Dynamo.
            log_outbound_harness_request(
                check_point="4. Step execution request leaving Deep Agents harness",
                task_index=task_index,
                payload={
                    "task_source": task_source,
                    "task_metadata": task_metadata or {},
                    "phase": f"step_{idx}_execution",
                    "app_variant": app_variant,
                    "step_index": idx,
                    "step_title": step.get("title"),
                    "prompt_preview": _prompt_preview(step_prompt),
                    "prompt": step_prompt,
                    "hints": step_hints,
                    "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
                },
            )
            response = agent.invoke({"messages": [{"role": "user", "content": step_prompt}]})
            summary = response_text(response)
            prior_step_summaries.append(summary[:1200])
            step_results.append(
                {
                    "step_index": idx,
                    "step": step,
                    "step_hints": step_hints,
                    "step_prompt": step_prompt,
                    "response": response,
                    "response_text": summary,
                }
            )
    finally:
        os.chdir(original_cwd)

    return step_results


def synthesize_final_summary(
    *,
    frontend_url: str,
    model: str,
    base_hints: dict[str, Any],
    task_prompt: str,
    plan_steps: list[dict],
    step_results: list[dict],
    task_index: int | None = None,
    task_source: str | None = None,
    task_metadata: dict[str, Any] | None = None,
) -> dict:
    # [CHECK_POINT 5] The harness synthesizes the multi-step results into a final answer here.
    # [CHECK_POINT 5] Final synthesis happens here.
    # Debugging note: this is the final merge stage.
    # It collects all prior step outputs and asks the model for one combined answer.
    synthesis_hints = build_phase_hints(base_hints, phase="synthesis")
    synthesis_hints["expected_output_tokens"] = 768
    llm = build_dynamo_chat_model(
        frontend_url=frontend_url,
        model=model,
        hint_payload=synthesis_hints,
        max_tokens=1024,
    )
    step_summaries = "\n\n".join(
        f"Step {item['step_index']} ({item['step']['title']}):\n{item['response_text']}"
        for item in step_results
    )
    synthesis_prompt = f"""{task_prompt}

Plan used:
{json.dumps(plan_steps, indent=2)}

Step results:
{step_summaries}

Produce a final summary with these sections:
1. Overall diagnosis
2. Proposed fix strategy
3. Files or code areas that matter most
4. Validation steps still needed
5. What actually changed in the workspace, if anything"""
    # [CHECK_POINT 5] Final synthesis request leaving the Deep Agents harness for Dynamo.
    log_outbound_harness_request(
        check_point="5. Final synthesis request leaving Deep Agents harness",
        task_index=task_index,
        payload={
            "task_source": task_source,
            "task_metadata": task_metadata or {},
            "phase": "synthesis",
            "prompt_preview": _prompt_preview(synthesis_prompt),
            "prompt": synthesis_prompt,
            "hints": synthesis_hints,
            "step_count": len(step_results),
            "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
        },
    )
    response = llm.invoke(synthesis_prompt)
    return {
        "synthesis_hints": synthesis_hints,
        "synthesis_prompt": synthesis_prompt,
        "response": response,
        "response_text": response_text(response),
    }


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
) -> dict:
    """Run the active multi-step Deep Agents workflow for one task."""
    # Debugging note: this is the app-layer orchestration entry point.
    # The wrapper calls this once per run, and this function owns:
    # prompt building, planning, step execution, synthesis, and returned artifacts.

    prompt = format_swebench_task_prompt(task)
    resolved_hints = dict(DEFAULT_DYNAMO_HINTS)
    if base_hints:
        resolved_hints.update(base_hints)
    task_metadata = {
        "instance_id": task.get("instance_id"),
        "repo": task.get("repo"),
        "app_variant": app_variant,
    }

    decomposition_plan = generate_decomposition_plan(
        frontend_url=frontend_url,
        model=model,
        base_hints=resolved_hints,
        prompt=prompt,
        step_limit=step_limit,
        task_index=task_index,
        task_source=task_source,
        task_metadata=task_metadata,
    )
    step_results = execute_plan_steps(
        frontend_url=frontend_url,
        model=model,
        base_hints=resolved_hints,
        task_prompt=prompt,
        plan_steps=decomposition_plan["steps"],
        workspace_dir=workspace_dir,
        app_variant=app_variant,
        task_index=task_index,
        task_source=task_source,
        task_metadata=task_metadata,
    )
    result = synthesize_final_summary(
        frontend_url=frontend_url,
        model=model,
        base_hints=resolved_hints,
        task_prompt=prompt,
        plan_steps=decomposition_plan["steps"],
        step_results=step_results,
        task_index=task_index,
        task_source=task_source,
        task_metadata=task_metadata,
    )
    return {
        "prompt": prompt,
        "resolved_hints": resolved_hints,
        "app_variant": app_variant,
        "deepagents_runtime_source": DEEPAGENTS_RUNTIME_SOURCE,
        "decomposition_plan": decomposition_plan,
        "step_results": step_results,
        "result": result,
    }
