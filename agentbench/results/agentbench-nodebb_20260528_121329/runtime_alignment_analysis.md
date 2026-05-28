# Runtime Alignment Analysis

## Summary
| Field | Value |
| --- | --- |
| Decision rows | 5 |
| Observed worker count | 1 |
| Observed workers | 7587895149164876591 |
| Agreed rows | 5 |
| Partially-agreed rows | 0 |
| Diverged rows | 0 |
| Insufficient-evidence rows | 0 |
| Tool parser names seen | hermes |
| Observed tool call names | edit_file, execute, ls, read_file |

## Notes
- This report compares major Deep Agents decisions with the frontend and SGLang worker response observed in runtime evidence.
- Each row represents one decision point, the runtime-side reaction, the evidence we saw, and a short judgment of agreement or divergence.

## Decision Table

| Phase | Decision type | Agent component | Runtime component | Agent-side decision | Runtime-side response | Evidence | Judgment | Status | Worker | TTFT (ms) | Decode (ms) | End to end (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| baseline_execution | request_dispatch | deepagents_app | frontend_dynamo | Sent one baseline model request for the task. | Frontend observed the request and routed it to worker 7587895149164876591. | frontend_event_found=True; worker_observation_found=True; request_id=agentbench-nodebb_20260528_121329::baseline_execution; worker_id=7587895149164876591 | Request dispatch aligned with runtime routing evidence. | agreed | 7587895149164876591 | - | - | 86392.2380 |
| baseline_execution | tool_availability | deepagents_app | frontend_dynamo | Expected a tool-capable execution path for coding work. | Frontend/runtime reported tool parser(s): hermes. | tool_parser_observed=True; parsers=hermes; tool_call_count=27 | Runtime exposed a tool-capable path consistent with agent expectations. | agreed | 7587895149164876591 | - | - | 86392.2380 |
| baseline_execution | tool_use | deepagents_app | frontend_dynamo | Chose tool calls: edit_file, execute, ls, read_file. | Runtime returned tool results for: edit_file, execute, ls, read_file. | tool_call_count=27; tool_calls=edit_file, execute, ls, read_file; tool_results=edit_file, execute, ls, read_file | Agent tool-use decisions aligned with runtime tool execution. | agreed | 7587895149164876591 | - | - | 86392.2380 |
| baseline_execution | runtime_execution | deepagents_app | sglang_worker | Expected the request to execute on a routed worker. | Worker showed prefill activity only. | prefill_seen=True; decode_seen=False; cached_token_count=0; recomputed_prefix_tokens=17691 | Worker execution evidence aligned with the model request. | agreed | 7587895149164876591 | - | - | 86392.2380 |
| baseline_execution | stop_behavior | deepagents_app | frontend_dynamo/sglang_worker | Produced a final response and ended the run. | Runtime/tool outcome included execute failure: [stderr] /bin/sh: line 1: node: command not found Exit code: 127 [Command failed with exit code 127] | finish_reason=stop; response_preview=It appears that the `node` command is still not available in the current environment. This is likely because the environment does not hav... | Agent stopped in a way that is consistent with runtime/tool outcomes. | agreed | 7587895149164876591 | - | - | 86392.2380 |
