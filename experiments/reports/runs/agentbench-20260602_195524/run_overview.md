# Run Report: agentbench-20260602_195524

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_195524`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_195524/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 11620.542 | n/a | n/a | 10187 | 329 | True | 8640 | 1547 | 0.8481 |
| execution | 6049.02 | n/a | n/a | 10701 | 31 | True | 10560 | 141 | 0.9868 |
| execution | 48659.486 | n/a | n/a | 11848 | 1274 | True | 10624 | 1224 | 0.8967 |
| execution | 60870.619 | n/a | n/a | 12699 | 1376 | True | 11520 | 1179 | 0.9072 |
| patch_generation | 48447.164 | n/a | n/a | 11700 | 1408 | True | 8576 | 3124 | 0.7330 |
| review | 13494.337 | n/a | n/a | 14933 | 140 | True | 14400 | 533 | 0.9643 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

