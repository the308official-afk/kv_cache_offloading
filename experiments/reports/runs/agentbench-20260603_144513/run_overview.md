# Run Report: agentbench-20260603_144513

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_144513`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `ansible/ansible`
- Instance id: `instance_ansible__ansible-395e5e20fab9cad517243372fa3c3c5d9e09ab2a-v7eee2454f617569fd6889f2211f75bc02a35f9f8`
- Base commit: `cd64e0b070f8630e1dcc021e594ed42ea7afe304`
- Task source: `n/a`
- Summary: Standardize `PlayIterator` state representation with a public type and preserve backward compatibility Right now `PlayIterator` exposes run and failure states as plain integers ...
- Expected action: edit repo code
- Validation expectation: no explicit validation command provided
- Problem preview: Standardize `PlayIterator` state representation with a public type and preserve backward compatibility Right now `PlayIterator` exposes run and failure states as plain integers like `ITERATING_TASKS` or `FAILED_SETUP`...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `True`
- Git diff nonempty: `True`
- Workspace patch bytes: `7518`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 37569.434 | 1689.085 | runtime_events.latency.ttft_ms | 10215 | 1102 | True | 8640 | 1575 | 0.8458 |
| execution | 3091.291 | 1288.4119999999998 | worker_runtime.request_to_first_decode | 12669 | 6 | True | 11328 | 1341 | 0.8942 |
| execution | 5403.943 | -1128.567 | runtime_events.latency.ttft_ms | 11584 | 10 | True | 11456 | 128 | 0.9890 |
| patch_generation | 1960.75 | 887.208 | worker_runtime.request_to_first_decode | 9841 | 6 | True | 11328 | 0 | 1.0000 |
| review | 9986.036 | 1425.975 | worker_runtime.request_to_first_decode | 9868 | 242 | True | 11456 | 0 | 1.0000 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

