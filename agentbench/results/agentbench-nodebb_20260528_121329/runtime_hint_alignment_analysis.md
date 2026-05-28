# Runtime Hint Alignment Analysis

## Summary
| Field | Value |
| --- | --- |
| Hint rows | 8 |
| Hints present in request wrapper events | 8 |
| Hints directly observed in Dynamo frontend logs | 0 |
| Hints directly observed in SGLang worker logs | 0 |
| Hints with behavior-supported evidence | 0 |
| Metadata hints that matched trace context | 1 |
| Metadata-only hints | 2 |
| Hints not proven to affect runtime behavior | 4 |
| Direct SGLang hint evidence | False |
| Hint probe id | agentbench-nodebb_20260528_121329::hint_probe |
| Probe status | request_only |
| Probe seen in request wrapper | True |
| Probe seen in Dynamo frontend logs | False |
| Probe seen in SGLang worker logs | False |
| Dynamo frontend hint sources | - |
| SGLang worker hint sources | - |
| Worker log events with null agent_hints | 0 |
| Worker log events with non-null agent_hints | 0 |

## Notes
- This report checks whether AgentBench hints were sent, observed by runtime logs, and supported by behavior evidence.
- Propagation is not the same as proof that SGLang used a hint.
- Worker-side proof requires SGLang logs to show non-null agent_hints or explicit runtime fields derived from the hints.

## Probe Layer Check

| Layer | Did the probe appear? |
| --- | --- |
| AgentBench / Request Wrapper | True |
| Dynamo Frontend Logs | False |
| SGLang Worker Logs | False |

## Hint Table

| Phase | Hint | Value sent | Request wrapper | Dynamo frontend | SGLang worker | Expected effect | Observed effect | Claim level | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_execution | agent_phase | baseline_execution | True | not_logged | not_logged | The phase label should match the request/run phase for traceability. | The phase label matched the runtime event phase. | metadata_matched | metadata_matched | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=not_logged; event_phase=baseline_execution; hint_agent_phase=baseline_execution. |
| baseline_execution | context_type | software_engineering_long_horizon | True | not_logged | not_logged | The workload label should be retained as observability metadata. | This hint is treated as trace metadata, not a worker behavior instruction. | metadata_only | metadata_only | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=not_logged; metadata-only hint; no runtime effect expected unless a component explicitly consumes it. |
| baseline_execution | expected_output_tokens | 2048 | True | not_logged | not_logged | The runtime should use a generation budget consistent with this value. | Completion token count was recorded, but it did not prove the hint controlled generation. | propagated_to_request | not_proven | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=not_logged; completion_tokens=237; finish_reason=stop. |
| baseline_execution | hint_probe_id | agentbench-nodebb_20260528_121329::hint_probe | True | not_logged | not_logged | The probe marker should appear in every layer that receives the hint payload. | The probe marker was available for layer-by-layer propagation checks. | probe_present_request_only | request_only | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=not_logged; hint_probe_id=agentbench-nodebb_20260528_121329::hint_probe. |
| baseline_execution | latency_sensitivity | 0.7000 | True | not_logged | not_logged | Routing or scheduling should prefer lower latency when there is a real choice. | Latency was measured, but no latency policy decision was logged. | propagated_to_request | not_proven | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=not_logged; ttft_ms=-; end_to_end_ms=86392.238. Latency sensitivity needs routing or queue-policy evidence to prove it was respected. |
| baseline_execution | priority | 5 | True | not_logged | not_logged | A scheduler should be able to prefer this request when there is contention. | The scheduler selected a worker, but no priority-specific decision was logged. | propagated_to_request | not_proven | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=not_logged; worker_id=7587895149164876591; dp_rank=0; logit=264.219. Priority needs queue/competition evidence to prove it was respected. |
| baseline_execution | program_id | agentbench.deepagents_app | True | not_logged | not_logged | The program label should be retained as observability metadata. | This hint is treated as trace metadata, not a worker behavior instruction. | metadata_only | metadata_only | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=not_logged; metadata-only hint; no runtime effect expected unless a component explicitly consumes it. |
| baseline_execution | reuse_likelihood | 0.9000 | True | not_logged | not_logged | Cache/routing behavior should show reuse when useful context is available. | No cache reuse evidence was observed for this request. | propagated_to_request | not_proven | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=not_logged; cached_token_count=0. |
