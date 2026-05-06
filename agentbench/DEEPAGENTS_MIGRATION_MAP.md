# Deep Agents Migration Map

This document maps the current `agentbench` runner to the target Deep Agents app structure.

## Current -> Target

### Task loading

Current:

- `deepagents_swebench_single_host.py`
  - `load_swebench_task(...)`
  - `sample_task.json`

Target:

- keep in outer `agentbench/` wrapper
- this remains benchmark-facing logic, not core agent-app logic

### Prompt construction

Current:

- `format_swebench_task_prompt(...)`

Target:

- `deepagents_app/AGENTS.md`
- `deepagents_app/skills/`
- `deepagents_app/src/prompts.py`

Status:

- active

### Dynamo model wiring

Current:

- `build_llm(...)`
- `build_agent(...)`

Target:

- `deepagents_app/src/agent.py`

Status:

- active

### Hint handling

Current:

- `DEFAULT_HINTS`
- `merge_hint_overrides(...)`
- phase-specific planning / execution / synthesis hint logic

Target:

- `deepagents_app/src/agent.py`
- later: middleware or other source-level customization surfaces

Status:

- active for current phase-aware hint wiring

### Workspace preparation and patch capture

Current:

- `prepare_workspace(...)`
- `collect_workspace_artifacts(...)`

Target:

- keep in outer `agentbench/` wrapper for now
- later decide whether sandbox / workspace lifecycle belongs in the app or wrapper

Status:

- still outer-wrapper responsibility

### Explicit orchestration

Current:

- `generate_decomposition_plan(...)`
- `execute_plan_steps(...)`
- `synthesize_final_summary(...)`

Target:

- gradually reduce repo-local orchestration
- move toward more native Deep Agents planning, file use, and delegation
- keep only the benchmark wrapper responsibilities outside the app

Status:

- still mostly outer-wrapper responsibility

## Recommended Next Migration Step

Reduce the explicit plan / step / synthesis orchestration inside
`deepagents_swebench_single_host.py` and move more of that behavior into the
Deep Agents app itself.
