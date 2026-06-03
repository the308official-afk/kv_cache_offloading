# Run Report: agentbench-qutebrowser_20260602_132124

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-qutebrowser_20260602_132124`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_180217_9267.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 16334.868 | 394.539 | worker_runtime_json.request_received_to_attached | 9581 | 474 | True | 8512 | 1069 | 0.8884 |
| execution | 7408.923 | 544.098 | worker_runtime_json.request_received_to_attached | 11500 | 67 | True | 10112 | 1388 | 0.8793 |
| patch_generation | 1945.73 | 274.373 | worker_runtime_json.request_received_to_attached | 9219 | 8 | True | 9152 | 67 | 0.9927 |
| review | 1855.48 | 244.60899999999998 | worker_runtime_json.request_received_to_attached | 9222 | 6 | True | 9152 | 70 | 0.9924 |

## Transfers

- Events: `40`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `1767.500`
- CUDA sync timing ms: `1728.780`
- Unique semantic token hashes: `40`

## Worker Subrequests

- Subrequests: `7`
- Transfer request-id matches: `0`
- Transfer time-window matches: `7`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 394.539 | 9581 | 8512 | 0.8884 | cbcc1c2d292847b680b1f916320a9896 | False | True |
| execution | 0 | 544.098 | 10072 | 8512 | 0.8451 | fbca4fa290f841ce8722946aa37bd10d | False | True |
| execution | 1 | 473.223 | 11500 | 10112 | 0.8793 | 4d69da9f305b4b0395e2009430f5b7ed | False | True |
| patch_generation | 0 | 274.373 | 9158 | 8512 | 0.9295 | 9889119dcead46939d62f89dfc78750c | False | True |
| patch_generation | 1 | 85.505 | 9219 | 9152 | 0.9927 | ed0fd8e3972c404584bda4fbfb46c878 | False | True |
| review | 0 | 244.60899999999998 | 9161 | 8576 | 0.9361 | 943f858fac384ed8b38986d377cd4856 | False | True |
| review | 1 | 85.47399999999999 | 9222 | 9152 | 0.9924 | 08d7e36e41e24b95bb6e4af142783a71 | False | True |

