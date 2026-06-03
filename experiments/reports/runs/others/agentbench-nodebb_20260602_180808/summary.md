# Run Report: agentbench-nodebb_20260602_180808

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_180808`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_180808/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 17100.016 | n/a | n/a | 10449 | 506 | True | 10432 | 17 | 0.9984 |
| execution | 8741.143 | n/a | n/a | 12183 | 85 | True | 11008 | 1175 | 0.9036 |
| execution | 8597.573 | n/a | n/a | 12289 | 83 | True | 11136 | 1153 | 0.9062 |
| execution | 8583.409 | n/a | n/a | 12385 | 83 | True | 11200 | 1185 | 0.9043 |
| patch_generation | 1908.866 | n/a | n/a | 9495 | 6 | True | 9408 | 87 | 0.9908 |
| review | 3292.339 | n/a | n/a | 9560 | 8 | True | 9472 | 88 | 0.9908 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

