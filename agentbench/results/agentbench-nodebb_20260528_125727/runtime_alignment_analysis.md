# Runtime Alignment Analysis

## Summary
| Field | Value |
| --- | --- |
| Decision rows | 5 |
| Observed worker count | 1 |
| Observed workers | 7587895149794289712 |
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
| baseline_execution | request_dispatch | deepagents_app | frontend_dynamo | Sent one baseline model request for the task. | Frontend observed the request and routed it to worker 7587895149794289712. | frontend_event_found=True; worker_observation_found=True; request_id=agentbench-nodebb_20260528_125727::baseline_execution; worker_id=7587895149794289712 | Request dispatch aligned with runtime routing evidence. | agreed | 7587895149794289712 | - | - | 58395.3980 |
| baseline_execution | tool_availability | deepagents_app | frontend_dynamo | Expected a tool-capable execution path for coding work. | Frontend/runtime reported tool parser(s): hermes. | tool_parser_observed=True; parsers=hermes; tool_call_count=15 | Runtime exposed a tool-capable path consistent with agent expectations. | agreed | 7587895149794289712 | - | - | 58395.3980 |
| baseline_execution | tool_use | deepagents_app | frontend_dynamo | Chose tool calls: edit_file, execute, ls, read_file. | Runtime returned tool results for: edit_file, execute, ls, read_file. | tool_call_count=15; tool_calls=edit_file, execute, ls, read_file; tool_results=edit_file, execute, ls, read_file | Agent tool-use decisions aligned with runtime tool execution. | agreed | 7587895149794289712 | - | - | 58395.3980 |
| baseline_execution | runtime_execution | deepagents_app | sglang_worker | Expected the request to execute on a routed worker. | Worker showed prefill activity only. | prefill_seen=True; decode_seen=False; cached_token_count=0; recomputed_prefix_tokens=18336 | Worker execution evidence aligned with the model request. | agreed | 7587895149794289712 | - | - | 58395.3980 |
| baseline_execution | stop_behavior | deepagents_app | frontend_dynamo/sglang_worker | Produced a final response and ended the run. | Runtime/tool outcome included execute failure: [stderr] node:internal/modules/cjs/loader:1433 [stderr] throw err; [stderr] ^ [stderr] [stderr] Error: Cannot find module 'nconf' [stderr] Require stack: [stderr] - /home/ec2-user/kv_cache_offloading/agentbench/repos/... | finish_reason=stop; response_preview=It appears that the `nconf` module is still missing from the project, which is causing the tests to fail. We need to install the `nconf` ... | Agent stopped in a way that is consistent with runtime/tool outcomes. | agreed | 7587895149794289712 | - | - | 58395.3980 |
