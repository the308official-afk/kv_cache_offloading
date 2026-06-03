# Run Report: agentbench-20260602_190251

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_190251`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_190251/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 17621.211 | n/a | n/a | 10449 | 506 | True | 8640 | 1809 | 0.8269 |
| execution | 83853.514 | n/a | n/a | 15666 | 2048 | True | 14464 | 1202 | 0.9233 |
| execution | 8099.483 | n/a | n/a | 13076 | 74 | True | 11840 | 1236 | 0.9055 |
| execution | 7859.201 | n/a | n/a | 13161 | 72 | True | 11968 | 1193 | 0.9094 |
| patch_generation | 3697.232 | n/a | n/a | 11502 | 6 | True | 11392 | 110 | 0.9904 |
| review | 3687.124 | n/a | n/a | 11506 | 6 | True | 11392 | 114 | 0.9901 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

