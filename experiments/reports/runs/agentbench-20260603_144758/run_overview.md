# Run Report: agentbench-20260603_144758

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_144758`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `element-hq/element-web`
- Instance id: `instance_element-hq__element-web-33e8edb3d508d6eefb354819ca693b7accc695e7`
- Base commit: `83612dd4adeb2a4dad77655ec8969fcb1c555e6f`
- Task source: `n/a`
- Summary: Inconsistent and inflexible keyboard shortcut handling
- Expected action: edit repo code
- Validation expectation: no explicit validation command provided
- Problem preview: Inconsistent and inflexible keyboard shortcut handling The current keyboard shortcut system is fragmented and hardcoded across different components, which makes it difficult to extend, override, or maintain. Because t...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 10289.928 | 948.411 | runtime_events.latency.ttft_ms | 9866 | 294 | True | 8640 | 1226 | 0.8757 |
| execution | 36183.74 | 581.58 | runtime_events.latency.ttft_ms | 10177 | 1061 | True | 8640 | 1537 | 0.8490 |
| execution | 32719.939 | 1359.247 | worker_runtime.request_to_first_decode | 10690 | 953 | True | 8640 | 2050 | 0.8082 |
| execution | 58556.05 | -31388.41 | runtime_events.latency.ttft_ms | 11189 | 1717 | True | 9152 | 2037 | 0.8179 |
| patch_generation | 95443.109 | -57017.604 | runtime_events.latency.ttft_ms | 14072 | 2048 | True | 13952 | 120 | 0.9915 |
| review | 82256.791 | 1208.112 | worker_runtime.request_to_first_decode | 15482 | 2048 | True | 15168 | 314 | 0.9797 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

