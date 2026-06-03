# Run Report: agentbench-qutebrowser_20260602_160648

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-qutebrowser_20260602_160648`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 15134.629 | 418.04999999999995 | worker_runtime_json.request_received_to_attached | 9789 | 437 | True | 8640 | 1149 | 0.8826 |
| execution | 5027.911 | 549.092 | worker_runtime_json.request_received_to_attached | 10243 | 130 | True | 8640 | 1603 | 0.8435 |
| patch_generation | 5371.719 | 245.14600000000002 | worker_runtime_json.request_received_to_attached | 9292 | 87 | True | 9152 | 140 | 0.9849 |
| review | 9329.066 | 277.281 | worker_runtime_json.request_received_to_attached | 14295 | 8 | True | 13952 | 343 | 0.9760 |

## Transfers

- Events: `122`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `4116.000`
- CUDA sync timing ms: `5009.309`
- Unique semantic token hashes: `122`

## Worker Subrequests

- Subrequests: `7`
- Transfer request-id matches: `7`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 418.04999999999995 | 9789 | 8640 | 0.8826 | 3c8eda9241cb4f6ba74d95cb7bd5b7d8 | True | n/a |
| execution | 0 | 549.092 | 10243 | 8640 | 0.8435 | 388b660cf38e47f19d9812cdd4528b40 | True | n/a |
| patch_generation | 0 | 245.14600000000002 | 9186 | 8576 | 0.9336 | 8076266b86e44461bf1dd542ae59813c | True | n/a |
| patch_generation | 1 | 107.07600000000001 | 9292 | 9152 | 0.9849 | 9b780a1c588445e38cd16c3b13865393 | True | n/a |
| review | 0 | 277.281 | 9270 | 8576 | 0.9251 | 96c1f5c8fbde455d9588d18ef867a203 | True | n/a |
| review | 1 | 1562.353 | 13949 | 9216 | 0.6607 | e7b10314af834522947018cef29cd61f | True | n/a |
| review | 2 | 194.08 | 14295 | 13952 | 0.9760 | ba8a1742c8774f718637d7b1f932b025 | True | n/a |

