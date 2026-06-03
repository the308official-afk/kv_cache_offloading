# Run Report: agentbench-20260603_130247

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_130247`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `ansible/ansible`
- Instance id: `instance_ansible__ansible-f327e65d11bb905ed9f15996024f857a95592629-vba6da65a0f3baefda7a058ebbd0a8dcafb8512f5`
- Base commit: `f533d46572113655a0a698beab4b38671744a458`
- Task source: `n/a`
- Summary: Collection Name Validation Accepts Python Keywords
- Expected action: fix validation logic
- Validation expectation: no explicit validation command provided
- Problem preview: Collection Name Validation Accepts Python Keywords The current validation system for Fully Qualified Collection Names (FQCN) in ansible-galaxy incorrectly accepts collection names that contain Python reserved keywords...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 14813.297 | 1539.25 | runtime_events.latency.ttft_ms | 10430 | 6 | True | 9920 | 510 | 0.9511 |
| execution | 3935.391 | 1418.886 | runtime_events.latency.ttft_ms | 9519 | 108 | True | 9472 | 47 | 0.9951 |
| execution | 3517.127 | 1362.708 | worker_runtime.request_to_first_decode | 9651 | 95 | True | 9920 | 0 | 1.0000 |
| execution | 3518.303 | 904.357 | runtime_events.latency.ttft_ms | 9759 | 95 | True | 8768 | 991 | 0.8985 |
| patch_generation | 2350.068 | 1330.537 | runtime_events.latency.ttft_ms | 9076 | 8 | True | 8960 | 116 | 0.9872 |
| review | 2284.097 | 827.391 | runtime_events.latency.ttft_ms | 9082 | 6 | True | 8960 | 122 | 0.9866 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

