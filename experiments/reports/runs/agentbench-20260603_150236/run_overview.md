# Run Report: agentbench-20260603_150236

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_150236`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `internetarchive/openlibrary`
- Instance id: `instance_internetarchive__openlibrary-8a5a63af6e0be406aa6c8c9b6d5f28b2f1b6af5a-v0f5aece3601a5b4419f7ccec1dbda2071be28ee4`
- Base commit: `9d9f3a19983876522bcfd17c9079c46a17986cb3`
- Task source: `n/a`
- Summary: Background jobs (e.g., metrics collectors) should only run on a subset of application servers, but our scheduler currently registers them on every host.
- Expected action: fix host-matching logic
- Validation expectation: no explicit validation command provided
- Problem preview: Background jobs (e.g., metrics collectors) should only run on a subset of application servers, but our scheduler currently registers them on every host. This leads to duplicated work and noisy metrics. We need a host-...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 9777.801 | 916.114 | runtime_events.latency.ttft_ms | 10572 | 272 | True | 8640 | 1932 | 0.8173 |
| execution | 9238.744 | 1257.117 | worker_runtime.request_to_first_decode | 10861 | 254 | True | 8640 | 2221 | 0.7955 |
| execution | 3903.849 | -8003.433 | runtime_events.latency.ttft_ms | 11139 | 92 | True | 8640 | 2499 | 0.7757 |
| execution | 3869.021 | 1803.0720000000001 | worker_runtime.request_to_first_decode | 11244 | 92 | True | 8896 | 2348 | 0.7912 |
| patch_generation | 2602.043 | -6922.149 | runtime_events.latency.ttft_ms | 9490 | 8 | True | 9344 | 146 | 0.9846 |
| review | 4624.728 | 167.78199999999998 | worker_runtime.request_to_first_decode | 9601 | 8 | True | 9472 | 129 | 0.9866 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

