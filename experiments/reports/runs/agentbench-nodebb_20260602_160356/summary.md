# Run Report: agentbench-nodebb_20260602_160356

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_160356`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 18989.551 | 612.1370000000001 | worker_runtime_json.request_received_to_attached | 10324 | 545 | True | 8512 | 1812 | 0.8245 |
| execution | 5399.262 | 758.9169999999999 | worker_runtime_json.request_received_to_attached | 10886 | 135 | True | 8640 | 2246 | 0.7937 |
| patch_generation | 17402.184 | 279.112 | worker_runtime_json.request_received_to_attached | 11170 | 6 | True | 10432 | 738 | 0.9339 |
| review | 17442.719 | 317.284 | worker_runtime_json.request_received_to_attached | 11173 | 6 | True | 10432 | 741 | 0.9337 |

## Transfers

- Events: `79`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `2814.000`
- CUDA sync timing ms: `3264.176`
- Unique semantic token hashes: `79`

## Worker Subrequests

- Subrequests: `8`
- Transfer request-id matches: `8`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 612.1370000000001 | 10324 | 8512 | 0.8245 | e7554852451b4f7e811dd76100f8e119 | True | n/a |
| execution | 0 | 758.9169999999999 | 10886 | 8640 | 0.7937 | 63c77143b2c041dabb350a2c0b3d3f8a | True | n/a |
| patch_generation | 0 | 279.112 | 9299 | 8576 | 0.9222 | 4f924264e15d43b988a3bc48c08fed81 | True | n/a |
| patch_generation | 1 | 442.246 | 10484 | 9280 | 0.8852 | 22b6d20ef7fc424ab1015e0755fc1d6b | True | n/a |
| patch_generation | 2 | 313.092 | 11170 | 10432 | 0.9339 | 60f34fde117447e3b7a09635b6923a67 | True | n/a |
| review | 0 | 317.284 | 9302 | 8512 | 0.9151 | 45bef0d30f84487aad9efc5786c4c11e | True | n/a |
| review | 1 | 441.28299999999996 | 10487 | 9280 | 0.8849 | 3e5aa944d40d438fa48a9ae0c8cf2824 | True | n/a |
| review | 2 | 313.842 | 11173 | 10432 | 0.9337 | acdadbf35133450d8d4dcefc4654008f | True | n/a |

