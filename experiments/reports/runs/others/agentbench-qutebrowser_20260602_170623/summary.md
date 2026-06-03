# Run Report: agentbench-qutebrowser_20260602_170623

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-qutebrowser_20260602_170623`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_220109_38058.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 10068.886 | 434.195 | worker_runtime_json.request_received_to_attached | 9706 | 285 | True | 8512 | 1194 | 0.8770 |
| execution | 6650.437 | 526.872 | worker_runtime_json.request_received_to_attached | 10008 | 180 | True | 8512 | 1496 | 0.8505 |
| execution | 3065.573 | 547.205 | worker_runtime_json.request_received_to_attached | 10213 | 72 | True | 8640 | 1573 | 0.8460 |
| execution | 3050.593 | 528.682 | worker_runtime_json.request_received_to_attached | 10298 | 72 | True | 8832 | 1466 | 0.8576 |
| patch_generation | 3012.593 | 317.25100000000003 | worker_runtime_json.request_received_to_attached | 10584 | 6 | True | 9280 | 1304 | 0.8768 |
| review | 5531.354 | 317.898 | worker_runtime_json.request_received_to_attached | 11801 | 8 | True | 10560 | 1241 | 0.8948 |

## Transfers

- Events: `39`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `1858.500`
- CUDA sync timing ms: `1648.849`
- Unique semantic token hashes: `39`

## Worker Subrequests

- Subrequests: `9`
- Transfer request-id matches: `9`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 434.195 | 9706 | 8512 | 0.8770 | c4b43f33b9f546b3983787c8f6b2e58c | True | n/a |
| execution | 0 | 526.872 | 10008 | 8512 | 0.8505 | 4cd4ed2972fc4c5b8f3a13cd6dc79f26 | True | n/a |
| execution | 0 | 547.205 | 10213 | 8640 | 0.8460 | 8fd7232acf834b12907d76e659935ba8 | True | n/a |
| execution | 0 | 528.682 | 10298 | 8832 | 0.8576 | e5f8e46e4f6c48ab93853e288cfb21e5 | True | n/a |
| patch_generation | 0 | 317.25100000000003 | 9285 | 8512 | 0.9167 | cc34327dc4b043889d34ba8be085bfdc | True | n/a |
| patch_generation | 1 | 462.406 | 10584 | 9280 | 0.8768 | 4366a92cc554471b9ed6237f5e0804c6 | True | n/a |
| review | 0 | 317.898 | 9289 | 8512 | 0.9164 | 2340c77182314e37911414a0f0d02f45 | True | n/a |
| review | 1 | 462.096 | 10588 | 9280 | 0.8765 | 094b2bfabcb94c8bb05e0f75d700636d | True | n/a |
| review | 2 | 456.434 | 11801 | 10560 | 0.8948 | 60546f01ca6349f3baa05f36de218ffe | True | n/a |

