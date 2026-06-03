# Run Report: agentbench-20260603_142838

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_142838`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `internetarchive/openlibrary`
- Instance id: `instance_internetarchive__openlibrary-4a5d2a7d24c9e4c11d3069220c0685b736d5ecde-v13642507b4fc1f8d234172bf8129942da2c2ca26`
- Base commit: `90475fb6c168e8317e22bd5fbe057d98e570a715`
- Task source: `n/a`
- Summary: Incomplete Retrieval of Property Statement Values in Wikidata Entities.
- Expected action: fix validation logic
- Validation expectation: no explicit validation command provided
- Problem preview: Incomplete Retrieval of Property Statement Values in Wikidata Entities. Wikidata entities currently store property statements, but the code does not provide a mechanism to access all the values associated with a speci...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `True`
- Git diff nonempty: `True`
- Workspace patch bytes: `2272268`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 20785.197 | 1010.304 | runtime_events.latency.ttft_ms | 9720 | 608 | True | 8640 | 1080 | 0.8889 |
| execution | 2795.044 | 911.919 | runtime_events.latency.ttft_ms | 11611 | 6 | True | 10304 | 1307 | 0.8874 |
| execution | 92795.834 | 580.446 | runtime_events.latency.ttft_ms | 11533 | 2048 | True | 10944 | 589 | 0.9489 |
| patch_generation | 18540.887 | 1808.228 | runtime_events.latency.ttft_ms | 11672 | 277 | True | 11328 | 344 | 0.9705 |
| review | 10498.246 | 1318.001 | runtime_events.latency.ttft_ms | 11604 | 284 | True | 10368 | 1236 | 0.8935 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

