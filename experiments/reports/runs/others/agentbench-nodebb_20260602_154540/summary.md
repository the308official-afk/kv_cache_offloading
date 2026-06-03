# Run Report: agentbench-nodebb_20260602_154540

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_154540`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 20246.86 | 42.809 | worker_runtime_json.request_received_to_attached | 10324 | 599 | True | 10304 | 20 | 0.9981 |
| execution | 4311.159 | 660.518 | worker_runtime_json.request_received_to_attached | 10940 | 105 | True | 8960 | 1980 | 0.8190 |
| patch_generation | 18075.526 | 318.051 | worker_runtime_json.request_received_to_attached | 11869 | 8 | True | 11072 | 797 | 0.9329 |
| review | 18007.249 | 318.808 | worker_runtime_json.request_received_to_attached | 11872 | 6 | True | 11072 | 800 | 0.9326 |

## Transfers

- Events: `30`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `1442.000`
- CUDA sync timing ms: `1280.788`
- Unique semantic token hashes: `30`

## Worker Subrequests

- Subrequests: `8`
- Transfer request-id matches: `8`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 42.809 | 10324 | 10304 | 0.9981 | c6695059a7a04a33b61b332f42635830 | True | n/a |
| execution | 0 | 660.518 | 10940 | 8960 | 0.8190 | 91c65bc28c3146339c68977a67f02e69 | True | n/a |
| patch_generation | 0 | 318.051 | 9323 | 8512 | 0.9130 | 04d5419199ac45a3963232fd5444725b | True | n/a |
| patch_generation | 1 | 641.842 | 11125 | 9280 | 0.8342 | 6a5e371d479b4394ad1ab2e687f9089a | True | n/a |
| patch_generation | 2 | 336.089 | 11869 | 11072 | 0.9329 | 0140b5d52fd94eef89e0438b572b6943 | True | n/a |
| review | 0 | 318.808 | 9326 | 8512 | 0.9127 | 1a327beda1bb468aab2a0107963b294c | True | n/a |
| review | 1 | 642.072 | 11128 | 9280 | 0.8339 | a61aee01bf314348814c3b08ce0ea3da | True | n/a |
| review | 2 | 336.223 | 11872 | 11072 | 0.9326 | 77d9ae42de874d98bdca5f294bd951ae | True | n/a |

