# Run Report: agentbench-20260603_003750

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_003750`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_003750/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 14827.581 | 1539.2 | runtime_events.latency.ttft_ms | 10430 | 6 | True | 9920 | 510 | 0.9511 |
| execution | 3928.284 | 1418.968 | runtime_events.latency.ttft_ms | 9519 | 108 | True | 9472 | 47 | 0.9951 |
| execution | 3517.82 | 1354.529 | worker_runtime.request_to_first_decode | 9651 | 95 | True | 9920 | 0 | 1.0000 |
| execution | 3517.564 | 904.496 | runtime_events.latency.ttft_ms | 9759 | 95 | True | 8768 | 991 | 0.8985 |
| patch_generation | 2350.362 | 1330.323 | runtime_events.latency.ttft_ms | 9076 | 8 | True | 8960 | 116 | 0.9872 |
| review | 2285.914 | 827.496 | runtime_events.latency.ttft_ms | 9082 | 6 | True | 8960 | 122 | 0.9866 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

