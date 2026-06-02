# Run Report: agentbench-qutebrowser_20260602_170812

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-qutebrowser_20260602_170812`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_220109_38058.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 17313.018 | 459.381 | worker_runtime_json.request_received_to_attached | 9914 | 500 | True | 8512 | 1402 | 0.8586 |
| execution | 3361.385 | 568.528 | worker_runtime_json.request_received_to_attached | 10431 | 80 | True | 8640 | 1791 | 0.8283 |
| execution | 3447.738 | 656.655 | worker_runtime_json.request_received_to_attached | 10536 | 80 | True | 8512 | 2024 | 0.8079 |
| execution | 3442.716 | 650.555 | worker_runtime_json.request_received_to_attached | 10629 | 80 | True | 8704 | 1925 | 0.8189 |
| patch_generation | 29692.681 | 338.55 | worker_runtime_json.request_received_to_attached | 12319 | 10 | True | 11392 | 927 | 0.9248 |
| review | 39938.526 | 338.822 | worker_runtime_json.request_received_to_attached | 11135 | 871 | True | 10560 | 575 | 0.9484 |

## Transfers

- Events: `75`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `3265.500`
- CUDA sync timing ms: `3241.451`
- Unique semantic token hashes: `75`

## Worker Subrequests

- Subrequests: `11`
- Transfer request-id matches: `11`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 459.381 | 9914 | 8512 | 0.8586 | 59de291736d0424287bb417b17e882e7 | True | n/a |
| execution | 0 | 568.528 | 10431 | 8640 | 0.8283 | abba708a0fbe44379774e6884914c126 | True | n/a |
| execution | 0 | 656.655 | 10536 | 8512 | 0.8079 | fc07ac13b0fa4d27ba306ea74da25b0b | True | n/a |
| execution | 0 | 650.555 | 10629 | 8704 | 0.8189 | 2d89ed7b4bbc491b934fb4931d9e5bf8 | True | n/a |
| patch_generation | 0 | 338.55 | 9416 | 8512 | 0.9040 | 81f08ab5a31b4ccb9b149832eb2ad57d | True | n/a |
| patch_generation | 1 | 605.78 | 10598 | 9408 | 0.8877 | 7ca1cfceb00d4f65bb366e7956e4ade3 | True | n/a |
| patch_generation | 2 | 334.029 | 11438 | 10560 | 0.9232 | 7b037628414747f68edfe3cc5e614524 | True | n/a |
| patch_generation | 3 | 360.09999999999997 | 12319 | 11392 | 0.9248 | 59335d88d5c2420fa66d64e60dc5c87c | True | n/a |
| review | 0 | 338.822 | 9422 | 8512 | 0.9034 | 3f3675aea716477eb35d1ad6a65866f1 | True | n/a |
| review | 1 | 442.928 | 10604 | 9408 | 0.8872 | 657ad0b89aed4b5f938e4efb71e1f686 | True | n/a |
| review | 2 | 250.834 | 11135 | 10560 | 0.9484 | 1fdf1c3b30d848088c7e7ccf4e715186 | True | n/a |

