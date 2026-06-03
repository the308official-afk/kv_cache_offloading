# Run Report: agentbench-nodebb_20260602_161622

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_161622`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 18988.83 | 613.004 | worker_runtime_json.request_received_to_attached | 10324 | 545 | True | 8512 | 1812 | 0.8245 |
| execution | 5446.424 | 804.971 | worker_runtime_json.request_received_to_attached | 10886 | 135 | True | 8512 | 2374 | 0.7819 |
| patch_generation | 17475.427 | 317.043 | worker_runtime_json.request_received_to_attached | 11170 | 6 | True | 10432 | 738 | 0.9339 |
| review | 17579.007 | 455.075 | worker_runtime_json.request_received_to_attached | 11173 | 6 | True | 10432 | 741 | 0.9337 |

## Transfers

- Events: `165`
- Device to host present: `True`
- Host to device present: `True`
- Estimated KV MB: `4721.500`
- CUDA sync timing ms: `5664.348`
- Unique semantic token hashes: `127`

## Worker Subrequests

- Subrequests: `8`
- Transfer request-id matches: `8`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 613.004 | 10324 | 8512 | 0.8245 | 3c0d6d6aecb94222b7da8b3b2638d4b6 | True | n/a |
| execution | 0 | 804.971 | 10886 | 8512 | 0.7819 | 111a374ceddb45a4ac128a74aee1ca8a | True | n/a |
| patch_generation | 0 | 317.043 | 9299 | 8512 | 0.9154 | 8d4ea34020674098bfe71b124b7aabde | True | n/a |
| patch_generation | 1 | 441.29 | 10484 | 9280 | 0.8852 | 97bc30f8aa4a417cac6da400730edb31 | True | n/a |
| patch_generation | 2 | 313.77 | 11170 | 10432 | 0.9339 | 253eaa979451424aad6383e4da72bc15 | True | n/a |
| review | 0 | 455.075 | 9302 | 8576 | 0.9220 | 7f001f66f3b24bd0b5254444c4733033 | True | n/a |
| review | 1 | 441.459 | 10487 | 9280 | 0.8849 | 4ceb39a74f8e466497369cd60f01d8e4 | True | n/a |
| review | 2 | 314.29699999999997 | 11173 | 10432 | 0.9337 | 0b0ea9cdade446f9a7404f321b10881c | True | n/a |

