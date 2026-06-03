# Run Report: agentbench-nodebb_20260602_160531

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_160531`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 12994.682 | 495.06600000000003 | worker_runtime_json.request_received_to_attached | 10062 | 370 | True | 8640 | 1422 | 0.8587 |
| execution | 5904.583 | 611.951 | worker_runtime_json.request_received_to_attached | 10643 | 23 | True | 10496 | 147 | 0.9862 |
| patch_generation | 24990.307 | 214.85899999999998 | worker_runtime_json.request_received_to_attached | 9511 | 509 | True | 9024 | 487 | 0.9488 |
| review | 29102.757 | 340.204 | worker_runtime_json.request_received_to_attached | 10549 | 176 | True | 10240 | 309 | 0.9707 |

## Transfers

- Events: `107`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `3570.000`
- CUDA sync timing ms: `4405.725`
- Unique semantic token hashes: `107`

## Worker Subrequests

- Subrequests: `10`
- Transfer request-id matches: `10`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 495.06600000000003 | 10062 | 8640 | 0.8587 | 36f8989d735b42cb90022c73c0dc0d79 | True | n/a |
| execution | 0 | 611.951 | 10449 | 8640 | 0.8269 | 5b436a915455439fa61a46dc54a794fb | True | n/a |
| execution | 1 | 108.329 | 10643 | 10496 | 0.9862 | 4979ed006a604b0ca2f579a31b9af8ac | True | n/a |
| patch_generation | 0 | 214.85899999999998 | 9010 | 8576 | 0.9518 | 8d353dd9a781430bac1102bf7590e767 | True | n/a |
| patch_generation | 1 | 88.461 | 9071 | 8960 | 0.9878 | 859254d2787a46828f795841f0f607d2 | True | n/a |
| patch_generation | 2 | 220.449 | 9511 | 9024 | 0.9488 | 09ab8e77becf4f78a69930a52a9bff3b | True | n/a |
| review | 0 | 340.204 | 9516 | 8576 | 0.9012 | 3a0a1049c175454c9862bca282efb9b8 | True | n/a |
| review | 1 | 222.751 | 9969 | 9472 | 0.9501 | a04c47e916404353a967d709594d60de | True | n/a |
| review | 2 | 47.281 | 10108 | 10048 | 0.9941 | 4b0ffcc8ebfb4abd87c973fb59324036 | True | n/a |
| review | 3 | 181.274 | 10549 | 10240 | 0.9707 | b05302daf11c4fa2bf596cf7fc733bb6 | True | n/a |

