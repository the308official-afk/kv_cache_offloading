# Run Report: agentbench-20260603_003009

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_003009`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_003009/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `True`
- Git diff nonempty: `True`
- Workspace patch bytes: `412`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 21962.755 | 8735.577 | worker_runtime.request_to_first_decode | 10449 | 431 | False | 0 | 10449 | 0.0000 |
| execution | 9065.462 | 1023.576 | worker_runtime.request_to_first_decode | 13236 | 24 | True | 12096 | 1140 | 0.9139 |
| execution | 14785.365 | 567.141 | worker_runtime.request_to_first_decode | 14940 | 45 | True | 12288 | 2652 | 0.8225 |
| patch_generation | 8691.585 | 1487.044 | worker_runtime.request_to_first_decode | 9371 | 99 | True | 12096 | 0 | 1.0000 |
| review | 4572.099 | 2069.804 | worker_runtime.request_to_first_decode | 9323 | 90 | True | 9216 | 107 | 0.9885 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

