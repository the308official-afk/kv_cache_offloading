# Run Report: agentbench-nodebb_20260602_132159

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_132159`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_180217_9267.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 12992.903 | 494.244 | worker_runtime_json.request_received_to_attached | 10062 | 370 | True | 8640 | 1422 | 0.8587 |
| execution | 66624.291 | 611.25 | worker_runtime_json.request_received_to_attached | 13872 | 87 | True | 10624 | 3248 | 0.7659 |
| patch_generation | 2107.083 | 240.034 | worker_runtime_json.request_received_to_attached | 9138 | 6 | True | 9024 | 114 | 0.9875 |
| review | 2155.417 | 239.965 | worker_runtime_json.request_received_to_attached | 9151 | 6 | True | 9024 | 127 | 0.9861 |

## Transfers

- Events: `56`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `2320.500`
- CUDA sync timing ms: `2406.306`
- Unique semantic token hashes: `56`

## Worker Subrequests

- Subrequests: `8`
- Transfer request-id matches: `0`
- Transfer time-window matches: `8`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 494.244 | 10062 | 8640 | 0.8587 | 8bfab2e2909844f280a5f5a0878c648d | False | True |
| execution | 0 | 611.25 | 10449 | 8640 | 0.8269 | 5726ba47843841d989f870aab31a1793 | False | True |
| execution | 1 | 90.594 | 10620 | 10496 | 0.9883 | 802e86f4484b473d94ef26144b697c49 | False | True |
| execution | 2 | 1124.922 | 13872 | 10624 | 0.7659 | 9d9225a373f641918774ad75c2308589 | False | True |
| patch_generation | 0 | 240.034 | 9076 | 8512 | 0.9379 | 10ca4c7e05904fb4ac52570c6458b8d0 | False | True |
| patch_generation | 1 | 88.193 | 9138 | 9024 | 0.9875 | 0590d3b24b5d44ccab83aecf436d318a | False | True |
| review | 0 | 239.965 | 9079 | 8512 | 0.9375 | c1be66a72b8e4de381fc79f5629a82d7 | False | True |
| review | 1 | 88.674 | 9151 | 9024 | 0.9861 | 00a5ab615cbc4167bfe4c40e21c54360 | False | True |

