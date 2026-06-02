# Run Report: agentbench-nodebb_20260601_184042

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260601_184042`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260601_233421_38235.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 28837.472 | n/a | 10324 | 617 | False | 0 | 10324 | 0.0000 |
| execution | 3675.161 | n/a | 10958 | 82 | False | 0 | 10958 | 0.0000 |
| patch_generation | 17912.748 | n/a | 11864 | 6 | False | 0 | 11864 | 0.0000 |
| review | 17899.874 | n/a | 11867 | 6 | False | 0 | 11867 | 0.0000 |

## Transfers

- Events: `20`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `1151.500`
- CUDA sync timing ms: `1004.319`
- Unique semantic token hashes: `20`

