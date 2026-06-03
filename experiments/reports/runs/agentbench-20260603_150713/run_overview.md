# Run Report: agentbench-20260603_150713

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_150713`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `element-hq/element-web`
- Instance id: `instance_element-hq__element-web-5dfde12c1c1c0b6e48f17e3405468593e39d9492-vnan`
- Base commit: `f97cef80aed8ee6011543f08bee8b1745a33a7db`
- Task source: `n/a`
- Summary: Sessions hygiene & Voice Broadcast reliability: prune stale client info, block offline start, and consistent chunk sequencing
- Expected action: edit repo code
- Validation expectation: no explicit validation command provided
- Problem preview: Users are seeing multiple problems that affect sessions and voice broadcast: Stale session metadata, After signing out other sessions or when the device list changes, “client information” account-data for removed devi...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 39798.864 | 512.808 | runtime_events.latency.ttft_ms | 10301 | 1168 | True | 8640 | 1661 | 0.8388 |
| execution | 4749.913 | 1973.505 | worker_runtime.request_to_first_decode | 11486 | 114 | True | 8640 | 2846 | 0.7522 |
| execution | 4130.016 | -2803.12 | runtime_events.latency.ttft_ms | 11624 | 95 | True | 8640 | 2984 | 0.7433 |
| execution | 4142.929 | 1692.8129999999999 | worker_runtime.request_to_first_decode | 11732 | 95 | True | 8768 | 2964 | 0.7474 |
| patch_generation | 17799.017 | -6128.754 | runtime_events.latency.ttft_ms | 12046 | 6 | True | 11264 | 782 | 0.9351 |
| review | 16740.169 | 1535.921 | worker_runtime.request_to_first_decode | 11990 | 6 | True | 11328 | 662 | 0.9448 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

