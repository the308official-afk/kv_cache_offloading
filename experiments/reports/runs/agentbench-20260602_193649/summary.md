# Run Report: agentbench-20260602_193649

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_193649`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_193649/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `True`
- Git diff nonempty: `True`
- Workspace patch bytes: `1652`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 11619.672 | n/a | n/a | 10187 | 329 | True | 8640 | 1547 | 0.8481 |
| execution | 6042.119 | n/a | n/a | 10701 | 31 | True | 10560 | 141 | 0.9868 |
| execution | 50336.436 | n/a | n/a | 11848 | 1323 | True | 10624 | 1224 | 0.8967 |
| execution | 47232.225 | n/a | n/a | 13748 | 124 | True | 11072 | 2676 | 0.8054 |
| patch_generation | 23340.576 | n/a | n/a | 13740 | 151 | True | 12672 | 1068 | 0.9223 |
| review | 12301.166 | n/a | n/a | 12627 | 113 | True | 10816 | 1811 | 0.8566 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

