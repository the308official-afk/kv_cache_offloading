# Run Report: agentbench-20260603_010402

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_010402`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_010402/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 10514.524 | 641.968 | runtime_events.latency.ttft_ms | 9706 | 302 | True | 8640 | 1066 | 0.8902 |
| execution | 5606.056 | 1302.845 | runtime_events.latency.ttft_ms | 10025 | 154 | True | 8640 | 1385 | 0.8618 |
| execution | 3803.174 | 1540.319 | runtime_events.latency.ttft_ms | 10204 | 99 | True | 8768 | 1436 | 0.8593 |
| execution | 3855.494 | 953.311 | runtime_events.latency.ttft_ms | 10316 | 99 | True | 8768 | 1548 | 0.8499 |
| patch_generation | 2897.756 | 1421.646 | runtime_events.latency.ttft_ms | 10629 | 8 | True | 9280 | 1349 | 0.8731 |
| review | 5033.288 | 1369.863 | worker_runtime.request_to_first_decode | 11309 | 6 | True | 10624 | 685 | 0.9394 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

