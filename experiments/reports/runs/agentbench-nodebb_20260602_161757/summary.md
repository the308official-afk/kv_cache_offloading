# Run Report: agentbench-nodebb_20260602_161757

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_161757`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 12993.024 | 494.869 | worker_runtime_json.request_received_to_attached | 10062 | 370 | True | 8640 | 1422 | 0.8587 |
| execution | 5904.35 | 612.0100000000001 | worker_runtime_json.request_received_to_attached | 10643 | 23 | True | 10496 | 147 | 0.9862 |
| patch_generation | 24991.328 | 215.718 | worker_runtime_json.request_received_to_attached | 9511 | 509 | True | 9024 | 487 | 0.9488 |
| review | 29115.762 | 340.14 | worker_runtime_json.request_received_to_attached | 10549 | 176 | True | 10240 | 309 | 0.9707 |

## Transfers

- Events: `193`
- Device to host present: `True`
- Host to device present: `True`
- Estimated KV MB: `5484.500`
- CUDA sync timing ms: `6807.803`
- Unique semantic token hashes: `128`

## Worker Subrequests

- Subrequests: `10`
- Transfer request-id matches: `10`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 494.869 | 10062 | 8640 | 0.8587 | 752a43336dee4f82870e0ca0a408747c | True | n/a |
| execution | 0 | 612.0100000000001 | 10449 | 8640 | 0.8269 | 5a130441b3e94c0d9f563e62ccdebc39 | True | n/a |
| execution | 1 | 108.792 | 10643 | 10496 | 0.9862 | e14ec7bc129c4f6fb41b49518a19fb3a | True | n/a |
| patch_generation | 0 | 215.718 | 9010 | 8576 | 0.9518 | 39c89943835749a7a2f628ed30cf36ae | True | n/a |
| patch_generation | 1 | 88.703 | 9071 | 8960 | 0.9878 | 61d43410800f4aa6bc35345882110627 | True | n/a |
| patch_generation | 2 | 221.195 | 9511 | 9024 | 0.9488 | 22583099e63f488981ce411ba456b665 | True | n/a |
| review | 0 | 340.14 | 9516 | 8576 | 0.9012 | 84e6d798e22b4fdcbb369147f20424ae | True | n/a |
| review | 1 | 223.054 | 9969 | 9472 | 0.9501 | c90fc90afb334c528b791a276950a19c | True | n/a |
| review | 2 | 47.300000000000004 | 10108 | 10048 | 0.9941 | e11de4b4d80a41e999cef61241e47db9 | True | n/a |
| review | 3 | 181.064 | 10549 | 10240 | 0.9707 | e77a4e61e2a542cdb858bced9a7370f8 | True | n/a |

