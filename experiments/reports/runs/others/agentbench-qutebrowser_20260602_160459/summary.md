# Run Report: agentbench-qutebrowser_20260602_160459

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-qutebrowser_20260602_160459`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 16336.976 | 394.288 | worker_runtime_json.request_received_to_attached | 9581 | 474 | True | 8512 | 1069 | 0.8884 |
| execution | 7360.986 | 495.321 | worker_runtime_json.request_received_to_attached | 11500 | 67 | True | 10112 | 1388 | 0.8793 |
| patch_generation | 1919.696 | 244.567 | worker_runtime_json.request_received_to_attached | 9219 | 8 | True | 9152 | 67 | 0.9927 |
| review | 1836.114 | 244.671 | worker_runtime_json.request_received_to_attached | 9222 | 6 | True | 9152 | 70 | 0.9924 |

## Transfers

- Events: `89`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `3129.000`
- CUDA sync timing ms: `3688.128`
- Unique semantic token hashes: `89`

## Worker Subrequests

- Subrequests: `7`
- Transfer request-id matches: `7`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 394.288 | 9581 | 8512 | 0.8884 | f2b7d8db48c242919b3049faae46464a | True | n/a |
| execution | 0 | 495.321 | 10072 | 8640 | 0.8578 | ceb793074a014a7993cb8ec73dd33ca3 | True | n/a |
| execution | 1 | 473.648 | 11500 | 10112 | 0.8793 | 8911e11efd5d430fa136101d008cbb09 | True | n/a |
| patch_generation | 0 | 244.567 | 9158 | 8576 | 0.9364 | c2283f7d7f41445a8e6f9b8ad787468d | True | n/a |
| patch_generation | 1 | 85.843 | 9219 | 9152 | 0.9927 | c09446332a2448f19e5aa53012e79acb | True | n/a |
| review | 0 | 244.671 | 9161 | 8576 | 0.9361 | 0b66b615e43a42a8bc017a1140942fcf | True | n/a |
| review | 1 | 86.06400000000001 | 9222 | 9152 | 0.9924 | b9ac04d87076433b95c658c8e739daa4 | True | n/a |

