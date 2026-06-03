# Run Report: agentbench-20260603_151318

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_151318`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `flipt-io/flipt`
- Instance id: `instance_flipt-io__flipt-3b2c25ee8a3ac247c3fad13ad8d64ace34ec8ee7`
- Base commit: `8d72418bf67cec833da7f59beeecb5abfd48cb05`
- Task source: `n/a`
- Summary: OFREP Bulk Evaluation Fails When `flags` Context Key Is Missing
- Expected action: modify routing/controller logic
- Validation expectation: no explicit validation command provided
- Problem preview: I tried to use the OFREP client provider with flipt. The implementation of OFREP in flipt looks great, but there is one thing that does not fit how we intended the bulk evaluation endpoint to be used. When the request...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 13641.542 | 818.932 | runtime_events.latency.ttft_ms | 10242 | 390 | True | 8640 | 1602 | 0.8436 |
| execution | 7183.712 | 1254.858 | runtime_events.latency.ttft_ms | 10649 | 195 | True | 8640 | 2009 | 0.8113 |
| execution | 3657.591 | 1493.07 | worker_runtime.request_to_first_decode | 10868 | 88 | True | 8640 | 2228 | 0.7950 |
| execution | 3645.842 | -2197.089 | runtime_events.latency.ttft_ms | 10969 | 88 | True | 8832 | 2137 | 0.8052 |
| patch_generation | 5165.607 | 569.059 | worker_runtime.request_to_first_decode | 11473 | 8 | True | 10688 | 785 | 0.9316 |
| review | 5153.007 | -4680.582 | runtime_events.latency.ttft_ms | 11479 | 8 | True | 10688 | 791 | 0.9311 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

