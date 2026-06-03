# Run Report: agentbench-20260603_003318

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_003318`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_003318/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 26244.76 | 982.458 | runtime_events.latency.ttft_ms | 9914 | 769 | True | 8640 | 1274 | 0.8715 |
| execution | 45500.071 | 922.7070000000001 | worker_runtime.request_to_first_decode | 10700 | 1332 | True | 8640 | 2060 | 0.8075 |
| execution | 48245.361 | -44612.383 | runtime_events.latency.ttft_ms | 11119 | 1407 | True | 8640 | 2479 | 0.7770 |
| execution | 70036.122 | 1780.144 | worker_runtime.request_to_first_decode | 11526 | 2048 | True | 9024 | 2502 | 0.7829 |
| patch_generation | 64729.5 | -116319.994 | runtime_events.latency.ttft_ms | 14890 | 1381 | True | 14208 | 682 | 0.9542 |
| review | 12813.752 | 460.672 | worker_runtime.request_to_first_decode | 15710 | 255 | True | 15552 | 158 | 0.9899 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

