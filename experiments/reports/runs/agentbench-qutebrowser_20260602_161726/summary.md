# Run Report: agentbench-qutebrowser_20260602_161726

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-qutebrowser_20260602_161726`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 16335.801 | 394.71299999999997 | worker_runtime_json.request_received_to_attached | 9581 | 474 | True | 8512 | 1069 | 0.8884 |
| execution | 7445.754 | 544.533 | worker_runtime_json.request_received_to_attached | 11500 | 67 | True | 10112 | 1388 | 0.8793 |
| patch_generation | 1925.576 | 245.279 | worker_runtime_json.request_received_to_attached | 9219 | 8 | True | 9152 | 67 | 0.9927 |
| review | 1837.098 | 245.038 | worker_runtime_json.request_received_to_attached | 9222 | 6 | True | 9152 | 70 | 0.9924 |

## Transfers

- Events: `175`
- Device to host present: `True`
- Host to device present: `True`
- Estimated KV MB: `5043.500`
- CUDA sync timing ms: `6090.319`
- Unique semantic token hashes: `128`

## Worker Subrequests

- Subrequests: `7`
- Transfer request-id matches: `7`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 394.71299999999997 | 9581 | 8512 | 0.8884 | 744e8b312bb84174b304971695136b45 | True | n/a |
| execution | 0 | 544.533 | 10072 | 8512 | 0.8451 | b723eb86c02a422587159c3b0a915136 | True | n/a |
| execution | 1 | 472.916 | 11500 | 10112 | 0.8793 | 309c2825572a49c0b73e84d1c861f797 | True | n/a |
| patch_generation | 0 | 245.279 | 9158 | 8576 | 0.9364 | 720b6c5498a54a9498ce1ad2c18e2b20 | True | n/a |
| patch_generation | 1 | 85.911 | 9219 | 9152 | 0.9927 | e49d583e8bee4d5c944a8550425add0b | True | n/a |
| review | 0 | 245.038 | 9161 | 8576 | 0.9361 | be7b554a129f4c62bc7e205fef7aa85c | True | n/a |
| review | 1 | 86.105 | 9222 | 9152 | 0.9924 | db4997ae54364746932111427d43e258 | True | n/a |

