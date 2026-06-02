# Run Report: agentbench-nodebb_20260601_184042

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `baseline`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260601_184042`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260601_233421_38235.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 28837.472 | 9261.505 | worker_runtime.request_to_first_decode | 10324 | 617 | False | 0 | 10324 | 0.0000 |
| execution | 3675.161 | 1601.915 | worker_runtime.request_to_first_decode | 10958 | 82 | True | 8512 | 2446 | 0.7768 |
| patch_generation | 17912.748 | 992.933 | worker_runtime.request_to_first_decode | 11864 | 6 | True | 11072 | 792 | 0.9332 |
| review | 17899.874 | 1595.3120000000001 | worker_runtime.request_to_first_decode | 11867 | 6 | True | 11072 | 795 | 0.9330 |

## Transfers

- Events: `20`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `1151.500`
- CUDA sync timing ms: `1004.319`
- Unique semantic token hashes: `20`

