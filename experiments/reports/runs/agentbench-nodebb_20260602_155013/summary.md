# Run Report: agentbench-nodebb_20260602_155013

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_155013`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 11506.347 | 545.284 | worker_runtime_json.request_received_to_attached | 10062 | 324 | True | 8512 | 1550 | 0.8460 |
| execution | 10984.103 | 633.904 | worker_runtime_json.request_received_to_attached | 11951 | 24 | True | 10752 | 1199 | 0.8997 |
| patch_generation | 9658.027 | 216.46699999999998 | worker_runtime_json.request_received_to_attached | 9369 | 6 | True | 8960 | 409 | 0.9563 |
| review | 3796.456 | 213.76600000000002 | worker_runtime_json.request_received_to_attached | 9108 | 6 | True | 9024 | 84 | 0.9908 |

## Transfers

- Events: `46`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `1830.500`
- CUDA sync timing ms: `1916.690`
- Unique semantic token hashes: `46`

## Worker Subrequests

- Subrequests: `11`
- Transfer request-id matches: `11`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 545.284 | 10062 | 8512 | 0.8460 | 1b7ecbdfe81a480f996cf0bd5d91b0ed | True | n/a |
| execution | 0 | 633.904 | 10403 | 8512 | 0.8182 | e959976770d24ee4b0595ca510c54432 | True | n/a |
| execution | 1 | 108.958 | 10597 | 10432 | 0.9844 | 3b0532ade83d4af78c58825435952539 | True | n/a |
| execution | 2 | 134.92299999999997 | 10760 | 10560 | 0.9814 | 876f2467063c4685a191fe09c6fb6c6b | True | n/a |
| execution | 3 | 455.927 | 11951 | 10752 | 0.8997 | 4b12fc6aa15d42818101ad787b5ef9a5 | True | n/a |
| patch_generation | 0 | 216.46699999999998 | 8965 | 8512 | 0.9495 | 968aa5b10db543249b1a0dfdd5ce0807 | True | n/a |
| patch_generation | 1 | 46.522 | 9020 | 8960 | 0.9933 | e5023dfbc2d34e598747f4f24a42462a | True | n/a |
| patch_generation | 2 | 215.98899999999998 | 9369 | 8960 | 0.9563 | 69258d8afd074024af78cc880d2faf34 | True | n/a |
| review | 0 | 213.76600000000002 | 8968 | 8576 | 0.9563 | b015e2f6dc504b7ebfb51d80363b2f3c | True | n/a |
| review | 1 | 46.504 | 9023 | 8960 | 0.9930 | eb2a571143fa4f7eac04fdfa1124c621 | True | n/a |
| review | 2 | 83.475 | 9108 | 9024 | 0.9908 | b82932fcd208470ba30f7a83b8e0fbe5 | True | n/a |

