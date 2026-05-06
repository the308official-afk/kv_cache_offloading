# Upstream Deep Agents Adoption Map

This file maps the active local `agentbench` app to the cloned upstream Deep Agents source.

Local upstream clone:

- [agentbench/upstream/deepagents](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents)

## Primary Upstream Bases

### 1. Main workflow base

- [examples/deploy-coding-agent/README.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents/examples/deploy-coding-agent/README.md)
- [examples/deploy-coding-agent/AGENTS.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents/examples/deploy-coding-agent/AGENTS.md)
- [examples/deploy-coding-agent/deepagents.toml](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents/examples/deploy-coding-agent/deepagents.toml)
- [examples/deploy-coding-agent/mcp.json](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents/examples/deploy-coding-agent/mcp.json)

Why:

- closest workflow match for SWE-bench-style coding tasks
- already organized around `Plan -> Implement -> Review -> Deliver`

### 2. Main source-level customization reference

- [examples/nvidia_deep_agent/README.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents/examples/nvidia_deep_agent/README.md)

Why:

- best architectural reference for custom model wiring and deeper source-level changes
- closest spirit to Dynamo / NVIDIA-backed specialization

### 3. Future eval / optimization reference

- [examples/better-harness/README.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents/examples/better-harness/README.md)
- [examples/better-harness/better_harness_plugin.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents/examples/better-harness/better_harness_plugin.py)

Why:

- best future reference for benchmark-driven harness tuning

## Local Active Files vs Upstream Targets

### Agent instructions

Local:

- [agentbench/deepagents_app/AGENTS.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/AGENTS.md)

Upstream target:

- [examples/deploy-coding-agent/AGENTS.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents/examples/deploy-coding-agent/AGENTS.md)

### App config

Local:

- [agentbench/deepagents_app/deepagents.toml](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/deepagents.toml)
- [agentbench/deepagents_app/mcp.json](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/mcp.json)

Upstream target:

- [examples/deploy-coding-agent/deepagents.toml](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents/examples/deploy-coding-agent/deepagents.toml)
- [examples/deploy-coding-agent/mcp.json](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents/examples/deploy-coding-agent/mcp.json)

### Prompt and model wiring

Local:

- [agentbench/deepagents_app/src/prompts.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/src/prompts.py)
- [agentbench/deepagents_app/src/agent.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/src/agent.py)

Upstream target:

- `deploy-coding-agent` gives the workflow shape
- `nvidia_deep_agent` gives the best customization reference for source-level agent wiring

### Skills

Local:

- [agentbench/deepagents_app/skills/code-review/SKILL.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/skills/code-review/SKILL.md)
- [agentbench/deepagents_app/skills/coding-prefs/SKILL.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/skills/coding-prefs/SKILL.md)
- [agentbench/deepagents_app/skills/planning/SKILL.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/skills/planning/SKILL.md)
- [agentbench/deepagents_app/skills/dynamo-hints/SKILL.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/skills/dynamo-hints/SKILL.md)
- [agentbench/deepagents_app/skills/swebench-coding/SKILL.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/skills/swebench-coding/SKILL.md)

Upstream target:

- `deploy-coding-agent` skill layout
- `better-harness` as future editable optimization surfaces

## Current Reality

Right now:

- the active app is still your local `agentbench/deepagents_app/`
- it uses the installed `deepagents` package
- but you now also have the full upstream source in the workspace for:
  - direct comparison
  - source-level debugging
  - future patching

## Recommended Next Upstream-Facing Step

Start aligning local files more directly with the cloned upstream `deploy-coding-agent` files:

1. compare and tighten `AGENTS.md`
2. tighten `deepagents.toml`
3. add upstream-style skills layout
4. begin patching the cloned source when you want behavior that the package API does not expose
