# Run Report: agentbench-20260603_151402

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_151402`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `NodeBB/NodeBB`
- Instance id: `instance_NodeBB__NodeBB-a5afad27e52fd336163063ba40dcadc80233ae10-vd59a5728dfc977f44533186ace531248c2917516`
- Base commit: `7800016f2f1b89d2d3cfea6a7da7c77096b7b927`
- Task source: `n/a`
- Summary: Chat Allow/Deny List
- Expected action: fix validation logic
- Validation expectation: no explicit validation command provided
- Problem preview: Users who want to control who can send them direct messages must currently enable “Only allow chat messages from users I follow” and then curate their follow list. This coupling makes it cumbersome to simply block spe...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 12261.796 | 631.93 | runtime_events.latency.ttft_ms | 9990 | 352 | True | 8640 | 1350 | 0.8649 |
| execution | 7896.828 | 1009.463 | runtime_events.latency.ttft_ms | 10627 | 41 | True | 10496 | 131 | 0.9877 |
| execution | 72004.904 | 223.272 | runtime_events.latency.ttft_ms | 10542 | 2048 | True | 10432 | 110 | 0.9896 |
| execution | 27116.244 | 205.719 | runtime_events.latency.ttft_ms | 19324 | 66 | True | 19200 | 124 | 0.9936 |
| patch_generation | 2921.263 | 664.645 | runtime_events.latency.ttft_ms | 11302 | 6 | True | 11200 | 102 | 0.9910 |
| review | 2922.945 | 525.362 | runtime_events.latency.ttft_ms | 11306 | 6 | True | 11200 | 106 | 0.9906 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

