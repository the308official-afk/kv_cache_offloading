# Runtime Hint Alignment Analysis

## Summary
| Field | Value |
| --- | --- |
| Hint rows | 8 |
| Hints present in request wrapper events | 8 |
| Hints directly observed in Dynamo frontend logs | 0 |
| Hints directly observed in SGLang worker logs | 8 |
| Hints with behavior-supported evidence | 1 |
| Metadata hints that matched trace context | 1 |
| Metadata-only hints | 2 |
| Hints not proven to affect runtime behavior | 0 |
| Direct SGLang hint evidence | True |
| Hint probe id | agentbench-nodebb_20260519_231144::hint_probe |
| Probe status | observed_by_worker |
| Probe seen in request wrapper | True |
| Probe seen in Dynamo frontend logs | False |
| Probe seen in SGLang worker logs | True |
| Dynamo frontend hint sources | - |
| SGLang worker hint sources | - |
| Worker log events with null agent_hints | 0 |
| Worker log events with non-null agent_hints | 6 |

## Notes
- This report checks whether AgentBench hints were sent, observed by runtime logs, and supported by behavior evidence.
- Propagation is not the same as proof that SGLang used a hint.
- Worker-side proof requires SGLang logs to show non-null agent_hints or explicit runtime fields derived from the hints.

## Probe Layer Check

| Layer | Did the probe appear? |
| --- | --- |
| AgentBench / Request Wrapper | True |
| Dynamo Frontend Logs | False |
| SGLang Worker Logs | True |

## Hint Table

| Phase | Hint | Value sent | Request wrapper | Dynamo frontend | SGLang worker | Expected effect | Observed effect | Claim level | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_execution | agent_phase | baseline_execution | True | not_logged | observed | The phase label should match the request/run phase for traceability. | The phase label matched the runtime event phase. | observed_by_worker_plus_metadata_matched | metadata_matched | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=observed; event_phase=baseline_execution; hint_agent_phase=baseline_execution. |
| baseline_execution | context_type | software_engineering_long_horizon | True | not_logged | observed | The workload label should be retained as observability metadata. | This hint is treated as trace metadata, not a worker behavior instruction. | observed_by_worker_plus_metadata_only | metadata_only | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=observed; metadata-only hint; no runtime effect expected unless a component explicitly consumes it. |
| baseline_execution | expected_output_tokens | 2048 | True | not_logged | observed | The runtime should use a generation budget consistent with this value. | Completion token count was recorded, but it did not prove the hint controlled generation. | observed_by_worker | observed_by_worker | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=observed; completion_tokens=1892; finish_reason=stop. |
| baseline_execution | hint_probe_id | agentbench-nodebb_20260519_231144::hint_probe | True | not_logged | observed | The probe marker should appear in every layer that receives the hint payload. | The probe marker was available for layer-by-layer propagation checks. | probe_observed_by_worker | observed_by_worker | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=observed; hint_probe_id=agentbench-nodebb_20260519_231144::hint_probe. |
| baseline_execution | latency_sensitivity | 0.7000 | True | not_logged | observed | Routing or scheduling should prefer lower latency when there is a real choice. | Latency was measured, but no latency policy decision was logged. | observed_by_worker | observed_by_worker | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=observed; ttft_ms=-; end_to_end_ms=109458.095. Latency sensitivity needs routing or queue-policy evidence to prove it was respected. |
| baseline_execution | priority | 5 | True | not_logged | observed | A scheduler should be able to prefer this request when there is contention. | No scheduler evidence was available to evaluate priority. | observed_by_worker | observed_by_worker | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=observed; scheduler=-. |
| baseline_execution | program_id | agentbench.deepagents_app | True | not_logged | observed | The program label should be retained as observability metadata. | This hint is treated as trace metadata, not a worker behavior instruction. | observed_by_worker_plus_metadata_only | metadata_only | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=observed; metadata-only hint; no runtime effect expected unless a component explicitly consumes it. |
| baseline_execution | reuse_likelihood | 0.9000 | True | not_logged | observed | Cache/routing behavior should show reuse when useful context is available. | Cache reuse was observed for the request. | observed_by_worker_plus_behavior_supported | behavior_supported | request_wrapper_observed=True; dynamo_frontend_state=not_logged; sglang_worker_state=observed; cached_token_count=8576; recomputed_prefix_tokens=17999. This is consistent with the reuse hint, but not causal proof by itself. |
