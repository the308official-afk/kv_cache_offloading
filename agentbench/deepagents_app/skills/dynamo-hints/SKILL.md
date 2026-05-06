# Dynamo Hints

This skill explains the hint vocabulary currently used by the local Dynamo-backed AgentBench setup.

## Current Hints

- `priority`
- `reuse_likelihood`
- `agent_phase`
- `latency_sensitivity`
- `program_id`
- `context_type`
- `expected_output_tokens`

## Guidance

- use `agent_phase` to distinguish planning, execution, and synthesis
- keep `program_id` stable for the app
- use `expected_output_tokens` conservatively
- do not invent unsupported NVIDIA hints and assume they are active end to end
