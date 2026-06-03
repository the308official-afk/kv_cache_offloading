# Run Report: agentbench-20260603_150153

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_150153`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `gravitational/teleport`
- Instance id: `instance_gravitational__teleport-e6d86299a855687b21970504fbf06f52a8f80c74-vce94f93ad1030e3136852817f2423c1b3ac37bc4`
- Base commit: `ea02952f53663a6a068ac70088ad5a044f54a094`
- Task source: `n/a`
- Summary: Update user traits when renewing session
- Expected action: modify routing/controller logic
- Validation expectation: no explicit validation command provided
- Problem preview: Bug When a user updates their traits (such as logins or database users) through the web UI, the changes are not applied to the currently active web session. The session continues to use stale certificate data from bef...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 10988.783 | 1320.6180000000002 | worker_runtime.request_to_first_decode | 11652 | 298 | True | 8640 | 3012 | 0.7415 |
| execution | 4163.48 | -9681.648 | runtime_events.latency.ttft_ms | 11967 | 93 | True | 8640 | 3327 | 0.7220 |
| execution | 3541.057 | 1739.006 | worker_runtime.request_to_first_decode | 12084 | 74 | True | 8640 | 3444 | 0.7150 |
| execution | 3545.16 | -5597.426 | runtime_events.latency.ttft_ms | 12171 | 74 | True | 8768 | 3403 | 0.7204 |
| patch_generation | 6210.164 | 1337.395 | worker_runtime.request_to_first_decode | 9456 | 8 | True | 9280 | 176 | 0.9814 |
| review | 6239.143 | -7350.136 | runtime_events.latency.ttft_ms | 9462 | 8 | True | 9280 | 182 | 0.9808 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

