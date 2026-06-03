# Run Report: agentbench-20260603_010608

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_010608`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_010608/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 26245.004 | 1083.34 | runtime_events.latency.ttft_ms | 9914 | 769 | True | 8640 | 1274 | 0.8715 |
| execution | 45500.565 | 1024.073 | worker_runtime.request_to_first_decode | 10700 | 1332 | True | 8640 | 2060 | 0.8075 |
| execution | 48234.56 | -44500.557 | runtime_events.latency.ttft_ms | 11119 | 1407 | True | 8640 | 2479 | 0.7770 |
| execution | 70036.181 | 1881.811 | worker_runtime.request_to_first_decode | 11526 | 2048 | True | 9024 | 2502 | 0.7829 |
| patch_generation | 64732.618 | -116218.826 | runtime_events.latency.ttft_ms | 14890 | 1381 | True | 14208 | 682 | 0.9542 |
| review | 12811.173 | 563.149 | worker_runtime.request_to_first_decode | 15710 | 255 | True | 15552 | 158 | 0.9899 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

