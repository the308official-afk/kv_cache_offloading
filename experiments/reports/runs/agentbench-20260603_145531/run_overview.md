# Run Report: agentbench-20260603_145531

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_145531`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `future-architect/vuls`
- Instance id: `instance_future-architect__vuls-e6c0da61324a0c04026ffd1c031436ee2be9503a`
- Base commit: `98cbe6ed837ce5983ddcb138f5c1577b9b7cf2bf`
- Task source: `n/a`
- Summary: The current Alpine Linux package scanner doesn't properly differentiate between binary and source packages during vulnerability detection.
- Expected action: edit repo code
- Validation expectation: no explicit validation command provided
- Problem preview: The current Alpine Linux package scanner doesn't properly differentiate between binary and source packages during vulnerability detection. This leads to missed vulnerabilities because the OVAL detection logic doesn't ...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 45072.121 | 1964.998 | worker_runtime.request_to_first_decode | 12011 | 574 | True | 11136 | 875 | 0.9272 |
| execution | 19818.068 | -23385.674 | runtime_events.latency.ttft_ms | 11542 | 561 | True | 11136 | 406 | 0.9648 |
| execution | 19977.261 | -18503.707 | runtime_events.latency.ttft_ms | 11977 | 561 | True | 11136 | 841 | 0.9298 |
| execution | 20022.782 | 1431.9679999999998 | worker_runtime.request_to_first_decode | 12400 | 561 | True | 9024 | 3376 | 0.7277 |
| patch_generation | 20076.159 | -38513.711 | runtime_events.latency.ttft_ms | 10931 | 574 | True | 9024 | 1907 | 0.8255 |
| review | 20253.198 | 1091.074 | worker_runtime.request_to_first_decode | 11502 | 574 | True | 8640 | 2862 | 0.7512 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

