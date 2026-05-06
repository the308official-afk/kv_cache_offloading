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
    │   ├── code-review/SKILL.md
    │   ├── coding-prefs/SKILL.md
    │   ├── dynamo-hints/SKILL.md
    │   ├── planning/SKILL.md
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
4. preferring the cloned upstream `deepagents` source at runtime when it is present

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

The app now prepends the cloned upstream package path at runtime:

- [agentbench/upstream/deepagents/libs/deepagents](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/upstream/deepagents/libs/deepagents)

So calls to `deepagents` now prefer the downloaded GitHub source over a separately installed package copy when that cloned path exists.

The outer runner can now also target the cloned upstream example variant:

- `--app-variant upstream_deploy_coding_agent`
- or [run_upstream_deploy_coding_agent_single_host.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_upstream_deploy_coding_agent_single_host.sh)

## Recommended Migration Order

1. Keep SWE-bench task loading in the outer `agentbench/` wrapper.
2. Keep aligning local instructions and skill layout with `deploy-coding-agent`.
3. Move more workflow behavior from the runner into native Deep Agents surfaces.
4. Reduce explicit repo-local orchestration over time.
5. Add middleware and eval surfaces inspired by `better-harness`.
6. Eventually patch/debug the real Deep Agents source and examples directly.
