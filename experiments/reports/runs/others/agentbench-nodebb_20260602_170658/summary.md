# Run Report: agentbench-nodebb_20260602_170658

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_170658`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_220109_38058.jsonl`

## Outcome

- Patch nonempty: `True`
- Git diff nonempty: `True`
- Workspace patch bytes: `1146`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 11529.465 | 560.627 | worker_runtime_json.request_received_to_attached | 10187 | 324 | True | 8512 | 1675 | 0.8356 |
| execution | 53779.275 | 655.385 | worker_runtime_json.request_received_to_attached | 13306 | 120 | True | 10752 | 2554 | 0.8081 |
| patch_generation | 2458.328 | 239.95 | worker_runtime_json.request_received_to_attached | 9154 | 6 | True | 9024 | 130 | 0.9858 |
| review | 2190.866 | 240.13799999999998 | worker_runtime_json.request_received_to_attached | 9154 | 6 | True | 9024 | 130 | 0.9858 |

## Transfers

- Events: `54`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `2380.000`
- CUDA sync timing ms: `2270.945`
- Unique semantic token hashes: `54`

## Worker Subrequests

- Subrequests: `8`
- Transfer request-id matches: `8`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 560.627 | 10187 | 8512 | 0.8356 | e7f2856ce22b417695f554c609051441 | True | n/a |
| execution | 0 | 655.385 | 10528 | 8512 | 0.8085 | 732135b0d0104f6c9995731936b2fd97 | True | n/a |
| execution | 1 | 108.318 | 10691 | 10560 | 0.9877 | d3df78b0281442469c2d9485a5a00062 | True | n/a |
| execution | 2 | 890.327 | 13306 | 10752 | 0.8081 | 4f4d231e52d14a8d9bde8173c2fd54da | True | n/a |
| patch_generation | 0 | 239.95 | 9061 | 8512 | 0.9394 | 5c4aa312325042049d25ef1cedfe5fcb | True | n/a |
| patch_generation | 1 | 106.40299999999999 | 9154 | 9024 | 0.9858 | 74045b5b4d654d9bb13ea1fcfe414ebd | True | n/a |
| review | 0 | 240.13799999999998 | 9064 | 8512 | 0.9391 | e8381d3479d34bd5b5f01dac7a115b50 | True | n/a |
| review | 1 | 106.41499999999999 | 9154 | 9024 | 0.9858 | d1beeb6457c740da840551c953faf119 | True | n/a |

