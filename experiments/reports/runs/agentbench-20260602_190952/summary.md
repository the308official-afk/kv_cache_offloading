# Run Report: agentbench-20260602_190952

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_190952`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 16671.282 | n/a | n/a | 9914 | 484 | True | 8640 | 1274 | 0.8715 |
| execution | 3287.658 | n/a | n/a | 10415 | 80 | True | 8640 | 1775 | 0.8296 |
| execution | 3363.6 | n/a | n/a | 10520 | 80 | True | 8640 | 1880 | 0.8213 |
| execution | 3368.939 | n/a | n/a | 10613 | 80 | True | 8704 | 1909 | 0.8201 |
| patch_generation | 27805.157 | n/a | n/a | 12215 | 10 | True | 11328 | 887 | 0.9274 |
| review | 39195.75 | n/a | n/a | 11119 | 855 | True | 10560 | 559 | 0.9497 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

