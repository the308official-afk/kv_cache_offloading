# Run Report: agentbench-20260603_003149

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_003149`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_003149/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `True`
- Git diff nonempty: `True`
- Workspace patch bytes: `1934`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 14576.992 | 782.86 | runtime_events.latency.ttft_ms | 10187 | 418 | True | 8640 | 1547 | 0.8481 |
| execution | 5973.282 | 1622.937 | runtime_events.latency.ttft_ms | 10790 | 33 | True | 10688 | 102 | 0.9905 |
| execution | 59939.118 | 994.031 | runtime_events.latency.ttft_ms | 13940 | 84 | True | 10688 | 3252 | 0.7667 |
| patch_generation | 2266.562 | 1759.662 | runtime_events.latency.ttft_ms | 9330 | 6 | True | 9152 | 178 | 0.9809 |
| review | 2178.709 | 1702.321 | worker_runtime.request_to_first_decode | 9334 | 6 | True | 10688 | 0 | 1.0000 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

