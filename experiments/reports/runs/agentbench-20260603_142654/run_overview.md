# Run Report: agentbench-20260603_142654

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_142654`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `ansible/ansible`
- Instance id: `instance_ansible__ansible-a26c325bd8f6e2822d9d7e62f77a424c1db4fbf6-v0f01c69f1e2528b935359cfe578530722bca2c59`
- Base commit: `79f67ed56116be11b1c992fade04acf06d9208d1`
- Task source: `n/a`
- Summary: uri module uses .netrc to overwrite Authorization header even if specified
- Expected action: modify routing/controller logic
- Validation expectation: no explicit validation command provided
- Problem preview: When using the `uri` module, the presence of a `.netrc` file for a specific host unintentionally overrides a user-specified `Authorization` header. This causes issues when endpoints expect a different authentication s...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `True`
- Git diff nonempty: `True`
- Workspace patch bytes: `183`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 16595.939 | 1369.145 | runtime_events.latency.ttft_ms | 10015 | 481 | True | 8640 | 1375 | 0.8627 |
| execution | 23707.617 | 1504.577 | runtime_events.latency.ttft_ms | 11834 | 75 | True | 11136 | 698 | 0.9410 |
| execution | 27806.995 | 486.64 | runtime_events.latency.ttft_ms | 11512 | 66 | True | 11392 | 120 | 0.9896 |
| execution | 9491.756 | 1321.272 | runtime_events.latency.ttft_ms | 10996 | 70 | True | 11136 | 0 | 1.0000 |
| patch_generation | 1780.039 | 1872.0220000000002 | worker_runtime.request_to_first_decode | 9459 | 6 | True | 9344 | 115 | 0.9878 |
| review | 19281.732 | -16684.167 | runtime_events.latency.ttft_ms | 9471 | 6 | True | 11072 | 0 | 1.0000 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

