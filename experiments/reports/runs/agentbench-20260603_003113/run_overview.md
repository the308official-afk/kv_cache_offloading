# Run Report: agentbench-20260603_003113

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_003113`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_003113/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 10514.642 | 541.546 | runtime_events.latency.ttft_ms | 9706 | 302 | True | 8640 | 1066 | 0.8902 |
| execution | 5605.454 | 1201.818 | runtime_events.latency.ttft_ms | 10025 | 154 | True | 8640 | 1385 | 0.8618 |
| execution | 3863.608 | 1500.076 | runtime_events.latency.ttft_ms | 10204 | 99 | True | 8512 | 1692 | 0.8342 |
| execution | 3855.318 | 852.266 | runtime_events.latency.ttft_ms | 10316 | 99 | True | 8768 | 1548 | 0.8499 |
| patch_generation | 2890.599 | 1321.297 | runtime_events.latency.ttft_ms | 10629 | 8 | True | 9280 | 1349 | 0.8731 |
| review | 5021.302 | 1258.564 | worker_runtime.request_to_first_decode | 11309 | 6 | True | 10624 | 685 | 0.9394 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

