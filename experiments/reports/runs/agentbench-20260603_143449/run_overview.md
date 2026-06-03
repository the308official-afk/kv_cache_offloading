# Run Report: agentbench-20260603_143449

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_143449`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `gravitational/teleport`
- Instance id: `instance_gravitational__teleport-3fa6904377c006497169945428e8197158667910-v626ec2a48416b10a88641359a169d99e935ff037`
- Base commit: `481158d6310e36e3c1115e25ab3fdf1c1ed45e60`
- Task source: `n/a`
- Summary: kubectl exec interactive sessions fail due to missing session uploader initialization in Kubernetes service
- Expected action: modify routing/controller logic
- Validation expectation: no explicit validation command provided
- Problem preview: kubectl exec interactive sessions fail due to missing session uploader initialization in Kubernetes service **Expected behavior:** When using the Kubernetes integration in Teleport, executing `kubectl exec` against a ...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 16053.294 | 785.462 | worker_runtime.request_to_first_decode | 10829 | 456 | True | 8640 | 2189 | 0.7979 |
| execution | 4951.058 | -15292.645 | runtime_events.latency.ttft_ms | 11302 | 122 | True | 8640 | 2662 | 0.7645 |
| execution | 3991.019 | 1722.205 | worker_runtime.request_to_first_decode | 11448 | 92 | True | 8640 | 2808 | 0.7547 |
| execution | 3993.655 | -7253.802 | runtime_events.latency.ttft_ms | 11553 | 92 | True | 8768 | 2785 | 0.7589 |
| patch_generation | 5723.319 | 335.718 | worker_runtime.request_to_first_decode | 9592 | 100 | True | 9408 | 184 | 0.9808 |
| review | 7313.238 | -8570.761 | runtime_events.latency.ttft_ms | 9853 | 6 | True | 9600 | 253 | 0.9743 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

