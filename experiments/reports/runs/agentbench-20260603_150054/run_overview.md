# Run Report: agentbench-20260603_150054

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_150054`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `qutebrowser/qutebrowser`
- Instance id: `instance_qutebrowser__qutebrowser-fd6790fe8c02b144ab2464f1fc8ab3d02ce3c476-v2ef375ac784985212b1805e1d0431dc8f1b3c171`
- Base commit: `487f90443cd1bf66bf2368b7a5c004f4e1b27777`
- Task source: `n/a`
- Summary: The :buffer command was deprecated in favor of :tab-select as part of qutebrowser's 2.0.0 settings update, but the deprecation remains incomplete.
- Expected action: fix validation logic
- Validation expectation: no explicit validation command provided
- Problem preview: The :buffer command was deprecated in favor of :tab-select as part of qutebrowser's 2.0.0 settings update, but the deprecation remains incomplete. Despite :tab-select being the intended replacement, :buffer still appe...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 16662.576 | 578.877 | runtime_events.latency.ttft_ms | 9857 | 484 | True | 8640 | 1217 | 0.8765 |
| execution | 6505.816 | 573.284 | runtime_events.latency.ttft_ms | 11747 | 55 | True | 10368 | 1379 | 0.8826 |
| execution | 14524.832 | 885.417 | runtime_events.latency.ttft_ms | 14605 | 63 | True | 13248 | 1357 | 0.9071 |
| execution | 10535.691 | 1885.991 | runtime_events.latency.ttft_ms | 13295 | 64 | True | 11904 | 1391 | 0.8954 |
| patch_generation | 1823.793 | 887.34 | runtime_events.latency.ttft_ms | 9418 | 6 | True | 10432 | 0 | 1.0000 |
| review | 4247.757 | 1647.58 | runtime_events.latency.ttft_ms | 9552 | 6 | True | 11840 | 0 | 1.0000 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

