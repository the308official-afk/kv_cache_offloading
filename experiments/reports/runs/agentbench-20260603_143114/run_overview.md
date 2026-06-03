# Run Report: agentbench-20260603_143114

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_143114`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `qutebrowser/qutebrowser`
- Instance id: `instance_qutebrowser__qutebrowser-f631cd4422744160d9dcf7a0455da532ce973315-v35616345bb8052ea303186706cec663146f0f184`
- Base commit: `5ee28105ad972dd635fcdc0ea56e5f82de478fb1`
- Task source: `n/a`
- Summary: The application is currently configured to display the changelog after any upgrade, including patch and minor updates.
- Expected action: edit repo code
- Validation expectation: no explicit validation command provided
- Problem preview: The application is currently configured to display the changelog after any upgrade, including patch and minor updates. This behavior lacks flexibility and does not allow users to control when the changelog should be s...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 26901.89 | 444.285 | runtime_events.latency.ttft_ms | 9822 | 789 | True | 8640 | 1182 | 0.8797 |
| execution | 39793.06 | 1019.354 | runtime_events.latency.ttft_ms | 10628 | 1164 | True | 8640 | 1988 | 0.8129 |
| execution | 19007.202 | 1026.2910000000002 | worker_runtime.request_to_first_decode | 11037 | 542 | True | 8640 | 2397 | 0.7828 |
| execution | 34060.894 | -18006.337 | runtime_events.latency.ttft_ms | 11457 | 986 | True | 9024 | 2433 | 0.7876 |
| patch_generation | 19657.408 | 1100.5990000000002 | worker_runtime.request_to_first_decode | 12155 | 549 | True | 9024 | 3131 | 0.7424 |
| review | 70753.852 | -52092.004 | runtime_events.latency.ttft_ms | 12701 | 2048 | True | 8576 | 4125 | 0.6752 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

