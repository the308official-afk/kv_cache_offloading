# Runtime Alignment Analysis

## Summary
| Field | Value |
| --- | --- |
| Decision rows | 5 |
| Observed worker count | 0 |
| Observed workers | - |
| Agreed rows | 2 |
| Partially-agreed rows | 0 |
| Diverged rows | 0 |
| Insufficient-evidence rows | 3 |
| Tool parser names seen | - |
| Observed tool call names | ls, read_file |

## Notes
- This report compares major Deep Agents decisions with the frontend and SGLang worker response observed in runtime evidence.
- Each row represents one decision point, the runtime-side reaction, the evidence we saw, and a short judgment of agreement or divergence.

## Decision Table

| Phase | Decision type | Agent component | Runtime component | Agent-side decision | Runtime-side response | Evidence | Judgment | Status | Worker | TTFT (ms) | Decode (ms) | End to end (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| baseline_execution | request_dispatch | deepagents_app | frontend_dynamo | Sent one baseline model request for the task. | Frontend observation for this request was not found. | frontend_event_found=False; worker_observation_found=False; request_id=agentbench-nodebb_20260519_231144::baseline_execution; worker_id=- | Agent request was recorded, but frontend routing evidence is missing. | insufficient_evidence | - | - | - | 109458.0950 |
| baseline_execution | tool_availability | deepagents_app | frontend_dynamo | Expected a tool-capable execution path for coding work. | No tool parser observation was found in frontend runtime logs. | tool_parser_observed=False; parsers=-; tool_call_count=8 | Tool-capable execution was expected, but runtime parser evidence is missing. | insufficient_evidence | - | - | - | 109458.0950 |
| baseline_execution | tool_use | deepagents_app | frontend_dynamo | Chose tool calls: ls, read_file. | Runtime returned tool results for: ls, read_file. | tool_call_count=8; tool_calls=ls, read_file; tool_results=ls, read_file | Agent tool-use decisions aligned with runtime tool execution. | agreed | - | - | - | 109458.0950 |
| baseline_execution | runtime_execution | deepagents_app | sglang_worker | Expected the request to execute on a routed worker. | Worker activity was not observed. | prefill_seen=False; decode_seen=False; cached_token_count=8576; recomputed_prefix_tokens=17999 | Runtime execution evidence is too weak to confirm worker-side execution details. | insufficient_evidence | - | - | - | 109458.0950 |
| baseline_execution | stop_behavior | deepagents_app | frontend_dynamo/sglang_worker | Produced a final response and ended the run. | Run ended with finish_reason=stop. | finish_reason=stop; response_preview=Based on the code review, the following changes are needed to address the issue: 1. **Implement `getConfirmObjs()` in `loadUserInfo()`**:... | Agent stopped in a way that is consistent with runtime/tool outcomes. | agreed | - | - | - | 109458.0950 |
