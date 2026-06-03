# Run Report: agentbench-20260602_195837

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_195837`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_195837/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 16667.773 | n/a | n/a | 9914 | 484 | True | 8640 | 1274 | 0.8715 |
| execution | 3287.705 | n/a | n/a | 10415 | 80 | True | 8640 | 1775 | 0.8296 |
| execution | 3364.144 | n/a | n/a | 10520 | 80 | True | 8640 | 1880 | 0.8213 |
| execution | 3368.722 | n/a | n/a | 10613 | 80 | True | 8704 | 1909 | 0.8201 |
| patch_generation | 27776.952 | n/a | n/a | 12215 | 10 | True | 11328 | 887 | 0.9274 |
| review | 39194.707 | n/a | n/a | 11119 | 855 | True | 10560 | 559 | 0.9497 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

