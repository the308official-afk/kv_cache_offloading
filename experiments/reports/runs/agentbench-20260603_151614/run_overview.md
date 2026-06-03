# Run Report: agentbench-20260603_151614

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_151614`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `gravitational/teleport`
- Instance id: `instance_gravitational__teleport-eefac60a350930e5f295f94a2d55b94c1988c04e-vee9b09fb20c43af7e520f57e9239bbcf46b7113d`
- Base commit: `eca1d01746c031f95e8df1ef3eea36d31416633d`
- Task source: `n/a`
- Summary: Lack of utility functions for extracting system metadata
- Expected action: refactor code organization
- Validation expectation: no explicit validation command provided
- Problem preview: Teleport should provide utility functions to programmatically retrieve system metadata from the Linux DMI interface (`/sys/class/dmi/id`) and from the `/etc/os-release` file. Functions should extract known fields from...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `True`
- Git diff nonempty: `True`
- Workspace patch bytes: `3516`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 39298.702 | 565.365 | runtime_events.latency.ttft_ms | 10109 | 1154 | True | 8640 | 1469 | 0.8547 |
| execution | 8549.666 | 1091.428 | worker_runtime.request_to_first_decode | 11409 | 110 | True | 11328 | 81 | 0.9929 |
| execution | 38968.806 | -3651.302 | runtime_events.latency.ttft_ms | 12626 | 10 | True | 12032 | 594 | 0.9530 |
| execution | 22436.282 | -3337.458 | runtime_events.latency.ttft_ms | 12874 | 10 | True | 12032 | 842 | 0.9346 |
| patch_generation | 36272.603 | 916.2360000000001 | worker_runtime.request_to_first_decode | 11102 | 10 | True | 11392 | 0 | 1.0000 |
| review | 17841.074 | -36732.829 | runtime_events.latency.ttft_ms | 10526 | 6 | True | 12032 | 0 | 1.0000 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

