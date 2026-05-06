"""Deep Agents app wiring for local Dynamo-backed coding runs.

This is the target location for moving model construction and hint-aware
phase logic out of the repo-local runner and into a source-level Deep Agents app.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

from .prompts import (
    DYNAMO_HINT_NOTES,
    PLANNING_NOTES,
    SYSTEM_PROMPT,
    format_swebench_task_prompt,
)

APP_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = APP_ROOT / "skills"
AGENTS_FILE = APP_ROOT / "AGENTS.md"

DEFAULT_DYNAMO_HINTS: dict[str, Any] = {
    "priority": 5,
    "reuse_likelihood": 0.9,
    "agent_phase": "execution",
    "latency_sensitivity": 0.7,
    "program_id": "agentbench.deepagents_app",
    "context_type": "software_engineering_long_horizon",
    "expected_output_tokens": 512,
}


def load_agent_instructions() -> str:
    """Load the app-level instructions from AGENTS.md and skill docs.

    This makes `deepagents_app/` the active configuration surface instead of
    keeping the main workflow guidance embedded in the outer runner.
    """

    parts = [SYSTEM_PROMPT, PLANNING_NOTES, DYNAMO_HINT_NOTES]
    if AGENTS_FILE.exists():
        parts.append(AGENTS_FILE.read_text(encoding="utf-8").strip())

    if SKILLS_DIR.exists():
        for skill_path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
            skill_text = skill_path.read_text(encoding="utf-8").strip()
            if skill_text:
                parts.append(f"Skill reference: {skill_path.parent.name}\n{skill_text}")

    return "\n\n".join(part for part in parts if part)


def frontend_base_url(frontend_url: str) -> str:
    if "/v1/chat/completions" in frontend_url:
        return frontend_url.replace("/v1/chat/completions", "/v1")
    return frontend_url.rstrip("/")


def build_phase_hints(base_hints: dict[str, Any] | None = None, *, phase: str = "execution") -> dict[str, Any]:
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
):
    """Create the Deep Agents coding harness backed by a local Dynamo endpoint.
    """

    llm = build_dynamo_chat_model(
        frontend_url=frontend_url,
        model=model,
        hint_payload=build_phase_hints(base_hints, phase=phase),
    )
    return create_deep_agent(
        model=llm,
        system_prompt=load_agent_instructions(),
    )


def response_text(response) -> str:
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
    return str(content if content is not None else response)


def parse_decomposition_plan(raw_text: str, *, fallback_count: int) -> list[dict]:
    try:
        parsed = json.loads(raw_text)
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

    lines = [line.strip(" -0123456789.") for line in raw_text.splitlines() if line.strip()]
    fallback = []
    for idx, line in enumerate(lines[:fallback_count], start=1):
        fallback.append({"step_id": idx, "title": line, "goal": line, "deliverable": ""})
    return fallback


def generate_decomposition_plan(
    *,
    frontend_url: str,
    model: str,
    base_hints: dict[str, Any],
    prompt: str,
    step_limit: int,
) -> dict:
    # [CHECK_POINT] The harness explicitly decomposes the hard task into steps here.
    # [CHECK_POINT] Planning phase happens here.
    planning_hints = build_phase_hints(base_hints, phase="planning")
    planning_hints["latency_sensitivity"] = 0.4
    planning_hints["expected_output_tokens"] = 512
    llm = build_dynamo_chat_model(
        frontend_url=frontend_url,
        model=model,
        hint_payload=planning_hints,
        max_tokens=1024,
    )
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

Keep it to at most {step_limit} steps."""
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
) -> list[dict]:
    # [CHECK_POINT] The harness sends explicit step-level requests to the frontend here.
    # [CHECK_POINT] Step-by-step execution happens here.
    step_results: list[dict] = []
    prior_step_summaries: list[str] = []
    original_cwd = Path.cwd()

    try:
        if workspace_dir is not None:
            os.chdir(workspace_dir)

        for idx, step in enumerate(plan_steps, start=1):
            step_hints = build_phase_hints(base_hints, phase=f"step_{idx}_execution")
            step_hints["expected_output_tokens"] = 768
            agent = build_coding_agent(
                frontend_url=frontend_url,
                model=model,
                base_hints=step_hints,
                phase=f"step_{idx}_execution",
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
) -> dict:
    # [CHECK_POINT] The harness synthesizes the multi-step results into a final answer here.
    # [CHECK_POINT] Final synthesis happens here.
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
) -> dict:
    """Run the active multi-step Deep Agents workflow for one task."""

    prompt = format_swebench_task_prompt(task)
    resolved_hints = dict(DEFAULT_DYNAMO_HINTS)
    if base_hints:
        resolved_hints.update(base_hints)

    decomposition_plan = generate_decomposition_plan(
        frontend_url=frontend_url,
        model=model,
        base_hints=resolved_hints,
        prompt=prompt,
        step_limit=step_limit,
    )
    step_results = execute_plan_steps(
        frontend_url=frontend_url,
        model=model,
        base_hints=resolved_hints,
        task_prompt=prompt,
        plan_steps=decomposition_plan["steps"],
        workspace_dir=workspace_dir,
    )
    result = synthesize_final_summary(
        frontend_url=frontend_url,
        model=model,
        base_hints=resolved_hints,
        task_prompt=prompt,
        plan_steps=decomposition_plan["steps"],
        step_results=step_results,
    )
    return {
        "prompt": prompt,
        "resolved_hints": resolved_hints,
        "decomposition_plan": decomposition_plan,
        "step_results": step_results,
        "result": result,
    }
