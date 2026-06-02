# Run Report: agentbench-nodebb_20260602_160017

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_160017`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 11061.651 | 43.403 | worker_runtime_json.request_received_to_attached | 10062 | 325 | True | 10048 | 14 | 0.9986 |
| execution | 20298.176 | 532.317 | worker_runtime_json.request_received_to_attached | 13150 | 222 | True | 11968 | 1182 | 0.9101 |
| patch_generation | 9461.566 | 275.642 | worker_runtime_json.request_received_to_attached | 9513 | 36 | True | 9152 | 361 | 0.9621 |
| review | 7979.59 | 276.02 | worker_runtime_json.request_received_to_attached | 9546 | 36 | True | 9152 | 394 | 0.9587 |

## Transfers

- Events: `64`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `2219.000`
- CUDA sync timing ms: `2614.179`
- Unique semantic token hashes: `64`

## Worker Subrequests

- Subrequests: `10`
- Transfer request-id matches: `10`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 43.403 | 10062 | 10048 | 0.9986 | 0c25e5746ccb445ebb0e7d850aa4505e | True | n/a |
| execution | 0 | 532.317 | 10404 | 8896 | 0.8551 | 0eafb572d47c4a22ac64fa3cb58d4618 | True | n/a |
| execution | 1 | 109.13000000000001 | 10598 | 10432 | 0.9843 | 63b62ab1fcbe4879bbc695eaff954044 | True | n/a |
| execution | 2 | 134.911 | 10761 | 10560 | 0.9813 | 2770d6cb1b094719abe97ba9189d7ce4 | True | n/a |
| execution | 3 | 456.061 | 11952 | 10752 | 0.8996 | 3d49b9739824428a9c0ffc343aec5d1e | True | n/a |
| execution | 4 | 467.12199999999996 | 13150 | 11968 | 0.9101 | d94f888f976342d7af8d7219054e1846 | True | n/a |
| patch_generation | 0 | 275.642 | 9166 | 8512 | 0.9286 | c481c5a9f15742aba53cf0dba477e02b | True | n/a |
| patch_generation | 1 | 180.91299999999998 | 9513 | 9152 | 0.9621 | acfcd23448454bd98974ae011335596c | True | n/a |
| review | 0 | 276.02 | 9199 | 8512 | 0.9253 | 9f5ef59578b947b992f4953595a08699 | True | n/a |
| review | 1 | 217.101 | 9546 | 9152 | 0.9587 | c18338c25c64406bb0a64f556713a76f | True | n/a |

