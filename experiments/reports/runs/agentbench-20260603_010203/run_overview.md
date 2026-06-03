# Run Report: agentbench-20260603_010203

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_010203`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_010203/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 17907.738 | 576.356 | runtime_events.latency.ttft_ms | 10449 | 515 | True | 8640 | 1809 | 0.8269 |
| execution | 8759.325 | 924.173 | worker_runtime.request_to_first_decode | 13320 | 24 | True | 12160 | 1160 | 0.9129 |
| execution | 4362.542 | -4019.031 | runtime_events.latency.ttft_ms | 12170 | 27 | True | 11008 | 1162 | 0.9045 |
| execution | 4380.736 | -2077.672 | runtime_events.latency.ttft_ms | 12210 | 25 | True | 12160 | 50 | 0.9959 |
| patch_generation | 75272.058 | -210.634 | runtime_events.latency.ttft_ms | 9611 | 2048 | True | 12160 | 0 | 1.0000 |
| review | 4389.756 | 635.697 | worker_runtime.request_to_first_decode | 11467 | 6 | True | 11328 | 139 | 0.9879 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

