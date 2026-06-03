# Run Report: agentbench-20260603_144037

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_144037`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `internetarchive/openlibrary`
- Instance id: `instance_internetarchive__openlibrary-dbbd9d539c6d4fd45d5be9662aa19b6d664b5137-v08d8e8889ec945ab821fb156c04c7d2e2810debb`
- Base commit: `409914bf541b32b2160200b7623060f2b5fab6c0`
- Task source: `n/a`
- Summary: When submitting a form to the /lists/add endpoint via POST, the server may return a 500 Internal Server Error.
- Expected action: modify routing/controller logic
- Validation expectation: no explicit validation command provided
- Problem preview: When submitting a form to the /lists/add endpoint via POST, the server may return a 500 Internal Server Error. This occurs when the form does not explicitly specify an action parameter and the request body contains fo...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 42773.918 | 1361.837 | runtime_events.latency.ttft_ms | 10822 | 543 | True | 9792 | 1030 | 0.9048 |
| execution | 17816.408 | 449.008 | runtime_events.latency.ttft_ms | 10498 | 244 | True | 10368 | 130 | 0.9876 |
| execution | 52982.709 | 1152.083 | runtime_events.latency.ttft_ms | 22325 | 539 | True | 10624 | 11701 | 0.4759 |
| execution | 84653.305 | 1180.035 | runtime_events.latency.ttft_ms | 13072 | 1547 | True | 11072 | 2000 | 0.8470 |
| patch_generation | 47167.879 | 1516.555 | runtime_events.latency.ttft_ms | 14562 | 548 | True | 11776 | 2786 | 0.8087 |
| review | 26015.603 | 4880.531 | worker_runtime.request_to_first_decode | 12127 | 737 | True | 10624 | 1503 | 0.8761 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

