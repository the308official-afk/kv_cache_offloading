# Run Report: agentbench-nodebb_20260601_192108

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260601_192108`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_001506_43231.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 28964.853 | 9420.612000000001 | worker_runtime.request_to_first_decode | 10324 | 617 | False | 0 | 10324 | 0.0000 |
| execution | 3679.211 | 1601.5459999999998 | worker_runtime.request_to_first_decode | 10958 | 82 | True | 8512 | 2446 | 0.7768 |
| patch_generation | 17925.823 | 994.2990000000001 | worker_runtime.request_to_first_decode | 11864 | 6 | True | 11072 | 792 | 0.9332 |
| review | 17956.16 | 1596.2069999999999 | worker_runtime.request_to_first_decode | 11867 | 6 | True | 11072 | 795 | 0.9330 |

## Transfers

- Events: `20`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `1151.500`
- CUDA sync timing ms: `1005.089`
- Unique semantic token hashes: `20`

