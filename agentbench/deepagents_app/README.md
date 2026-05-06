# Deep Agents App

This folder is the **active upstream-aligned Deep Agents app structure** for `agentbench/`.

Primary upstream references:

- `examples/deploy-coding-agent`
- `examples/nvidia_deep_agent`
- `examples/better-harness`

Cloned upstream source in this workspace:

- [agentbench/upstream/deepagents](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents)
- [agentbench/UPSTREAM_DEEPAGENTS_ADOPTION_MAP.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/UPSTREAM_DEEPAGENTS_ADOPTION_MAP.md)

## Purpose

Use this scaffold to split responsibilities cleanly:

- `agentbench/` outer layer
  - SWE-bench task loading
  - repo / commit materialization
  - result collection
  - benchmark-facing CLI
- `deepagents_app/` inner layer
  - Deep Agents workflow
  - AGENTS instructions
  - skills
  - Dynamo model wiring
  - future middleware and source-level customization

## Target Structure

```text
agentbench/
├── deepagents_swebench_single_host.py   # current transitional runner
├── DEEPAGENTS_MIGRATION_MAP.md          # mapping from current runner to target app
└── deepagents_app/
    ├── README.md
    ├── AGENTS.md
    ├── deepagents.toml
    ├── mcp.json
    ├── skills/
    │   ├── planning/SKILL.md
    │   ├── dynamo-hints/SKILL.md
    │   └── swebench-coding/SKILL.md
    └── src/
        ├── __init__.py
        ├── agent.py
        └── prompts.py
```

## Current Status

This folder is now the **active harness path** for:

1. system prompts and workflow guidance
2. skill surfaces
3. Dynamo-specific model wiring

The outer runner still exists:

- [deepagents_swebench_single_host.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_swebench_single_host.py)

but it now acts mainly as the benchmark/task wrapper:

- task loading
- workspace preparation
- explicit step orchestration
- result capture

The runner now imports the app-layer code from:

- [src/agent.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/src/agent.py)
- [src/prompts.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/src/prompts.py)
- [AGENTS.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/AGENTS.md)
- [skills/](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/skills)

## Recommended Migration Order

1. Keep SWE-bench task loading in the outer `agentbench/` wrapper.
2. Move more workflow behavior from the runner into native Deep Agents surfaces.
3. Reduce explicit repo-local orchestration over time.
4. Add middleware and eval surfaces inspired by `better-harness`.
5. Eventually patch/debug the real Deep Agents source and examples directly.
