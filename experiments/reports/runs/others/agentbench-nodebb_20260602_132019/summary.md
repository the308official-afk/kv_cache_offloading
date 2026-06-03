# Run Report: agentbench-nodebb_20260602_132019

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_132019`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_180217_9267.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 20246.218 | 41.730999999999995 | worker_runtime_json.request_received_to_attached | 10324 | 599 | True | 10304 | 20 | 0.9981 |
| execution | 4295.557 | 660.511 | worker_runtime_json.request_received_to_attached | 10940 | 105 | True | 8960 | 1980 | 0.8190 |
| patch_generation | 18086.277 | 317.673 | worker_runtime_json.request_received_to_attached | 11869 | 8 | True | 11072 | 797 | 0.9329 |
| review | 18005.27 | 317.716 | worker_runtime_json.request_received_to_attached | 11872 | 6 | True | 11072 | 800 | 0.9326 |

## Transfers

- Events: `30`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `1442.000`
- CUDA sync timing ms: `1294.349`
- Unique semantic token hashes: `30`

## Worker Subrequests

- Subrequests: `8`
- Transfer request-id matches: `0`
- Transfer time-window matches: `8`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 41.730999999999995 | 10324 | 10304 | 0.9981 | b205fd22c3ea47fc91039739c453d1c8 | False | True |
| execution | 0 | 660.511 | 10940 | 8960 | 0.8190 | 536eb4bfbc52442180c180601ecb3aeb | False | True |
| patch_generation | 0 | 317.673 | 9323 | 8512 | 0.9130 | 1e08f11bc8514b55bc6729e13cdf0fe0 | False | True |
| patch_generation | 1 | 640.798 | 11125 | 9280 | 0.8342 | 338dcf2aa72e4e62a5a9f87ee698d014 | False | True |
| patch_generation | 2 | 335.747 | 11869 | 11072 | 0.9329 | e0ad88fdd7504d6dad6d5938900c28a1 | False | True |
| review | 0 | 317.716 | 9326 | 8512 | 0.9127 | 4bcb5567f2a5416fbd330ee2bcfa2bec | False | True |
| review | 1 | 641.043 | 11128 | 9280 | 0.8339 | 92097cbfdc4744dba9c4b114293a80b2 | False | True |
| review | 2 | 335.78400000000005 | 11872 | 11072 | 0.9326 | 4a0589e2bc5448a79228cfa6c6699bff | False | True |

