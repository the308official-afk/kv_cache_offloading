# Run Report: agentbench-nodebb_20260602_153851

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_153851`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 38302.254 | 17422.666 | worker_runtime_json.request_received_to_attached | 10324 | 619 | False | 0 | 10324 | 0.0000 |
| execution | 4447.517 | 844.8090000000001 | worker_runtime_json.request_received_to_attached | 10960 | 104 | True | 8512 | 2448 | 0.7766 |
| patch_generation | 4844.179 | 318.29600000000005 | worker_runtime_json.request_received_to_attached | 10624 | 6 | True | 9408 | 1216 | 0.8855 |
| review | 2485.093 | 318.317 | worker_runtime_json.request_received_to_attached | 9442 | 6 | True | 9344 | 98 | 0.9896 |

## Transfers

- Events: `17`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `899.500`
- CUDA sync timing ms: `681.411`
- Unique semantic token hashes: `17`

## Worker Subrequests

- Subrequests: `7`
- Transfer request-id matches: `7`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 17422.666 | 10324 | 0 | 0.0000 | 2d90f644852e4a6e85f1ee740d808dd8 | True | n/a |
| execution | 0 | 844.8090000000001 | 10960 | 8512 | 0.7766 | 4e6fcaf627c44a5399f234a38df91692 | True | n/a |
| patch_generation | 0 | 318.29600000000005 | 9342 | 8512 | 0.9112 | 2697e2c30c3541afaaf2b5d07c7e7a70 | True | n/a |
| patch_generation | 1 | 87.197 | 9439 | 9344 | 0.9899 | 8404ee55894a4a5a8c0f6e1e5003ed35 | True | n/a |
| patch_generation | 2 | 444.295 | 10624 | 9408 | 0.8855 | 74eb0a436a774b36b248bc821f4f6f57 | True | n/a |
| review | 0 | 318.317 | 9345 | 8512 | 0.9109 | aefb3880f9c740aabeb5c28f801521cd | True | n/a |
| review | 1 | 87.122 | 9442 | 9344 | 0.9896 | 94e0858903fe4816b328cab85b57061e | True | n/a |

