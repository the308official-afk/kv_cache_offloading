# Run Report: agentbench-qutebrowser_20260602_161915

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-qutebrowser_20260602_161915`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 15140.533 | 418.235 | worker_runtime_json.request_received_to_attached | 9789 | 437 | True | 8640 | 1149 | 0.8826 |
| execution | 5014.606 | 550.192 | worker_runtime_json.request_received_to_attached | 10243 | 130 | True | 8640 | 1603 | 0.8435 |
| patch_generation | 5360.262 | 246.149 | worker_runtime_json.request_received_to_attached | 9292 | 87 | True | 9152 | 140 | 0.9849 |
| review | 9331.621 | 277.709 | worker_runtime_json.request_received_to_attached | 14295 | 8 | True | 13952 | 343 | 0.9760 |

## Transfers

- Events: `208`
- Device to host present: `True`
- Host to device present: `True`
- Estimated KV MB: `6030.500`
- CUDA sync timing ms: `7412.337`
- Unique semantic token hashes: `128`

## Worker Subrequests

- Subrequests: `7`
- Transfer request-id matches: `7`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 418.235 | 9789 | 8640 | 0.8826 | 35e484e171964846ab872f15b12c5984 | True | n/a |
| execution | 0 | 550.192 | 10243 | 8640 | 0.8435 | 40a4d51fc0b54367b1f9d66cf8565761 | True | n/a |
| patch_generation | 0 | 246.149 | 9186 | 8576 | 0.9336 | 71b5f1d902ef4caf81aa3791bafbac01 | True | n/a |
| patch_generation | 1 | 107.24499999999999 | 9292 | 9152 | 0.9849 | 280bb4c009d848bf8b385b5a52f02f52 | True | n/a |
| review | 0 | 277.709 | 9270 | 8576 | 0.9251 | c89438582e5349cc9b6683a7d8dd73d4 | True | n/a |
| review | 1 | 1561.791 | 13949 | 9216 | 0.6607 | 8799c545a1624fceb6c6568e15b94963 | True | n/a |
| review | 2 | 193.89000000000001 | 14295 | 13952 | 0.9760 | 255f324447be4a90b6a80432ea0ad622 | True | n/a |

