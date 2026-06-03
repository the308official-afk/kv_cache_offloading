# Run Report: agentbench-nodebb_20260602_180934

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_180934`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_180934/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 11620.112 | n/a | n/a | 10187 | 329 | True | 8640 | 1547 | 0.8481 |
| execution | 6024.173 | n/a | n/a | 10701 | 31 | True | 10560 | 141 | 0.9868 |
| execution | 53506.722 | n/a | n/a | 11848 | 1418 | True | 10624 | 1224 | 0.8967 |
| execution | 68835.359 | n/a | n/a | 12701 | 1615 | True | 11520 | 1181 | 0.9070 |
| patch_generation | 56594.711 | n/a | n/a | 12083 | 1644 | True | 8576 | 3507 | 0.7098 |
| review | 57397.58 | n/a | n/a | 13724 | 1644 | True | 8576 | 5148 | 0.6249 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

