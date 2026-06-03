# Run Report: agentbench-nodebb_20260602_170521

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_170521`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_220109_38058.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 34644.557 | 17545.943000000003 | worker_runtime_json.request_received_to_attached | 10449 | 506 | False | 0 | 10449 | 0.0000 |
| execution | 5069.043 | 844.7620000000001 | worker_runtime_json.request_received_to_attached | 10972 | 122 | True | 8512 | 2460 | 0.7758 |
| execution | 5080.314 | 870.119 | worker_runtime_json.request_received_to_attached | 11118 | 122 | True | 8512 | 2606 | 0.7656 |
| execution | 4053.609 | 849.792 | worker_runtime_json.request_received_to_attached | 11252 | 92 | True | 8768 | 2484 | 0.7792 |
| patch_generation | 2700.432 | 343.928 | worker_runtime_json.request_received_to_attached | 9617 | 8 | True | 9472 | 145 | 0.9849 |
| review | 4999.448 | 344.32800000000003 | worker_runtime_json.request_received_to_attached | 10752 | 6 | True | 9600 | 1152 | 0.8929 |

## Transfers

- Events: `24`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `1218.000`
- CUDA sync timing ms: `951.002`
- Unique semantic token hashes: `24`

## Worker Subrequests

- Subrequests: `9`
- Transfer request-id matches: `9`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 17545.943000000003 | 10449 | 0 | 0.0000 | a324140f0d5c4e5991a60ecd18fba993 | True | n/a |
| execution | 0 | 844.7620000000001 | 10972 | 8512 | 0.7758 | bf3a266a79804839aae334d2a7ee796b | True | n/a |
| execution | 0 | 870.119 | 11118 | 8512 | 0.7656 | 67e1c903c0fd4556bafdea5de3a58264 | True | n/a |
| execution | 0 | 849.792 | 11252 | 8768 | 0.7792 | 6f511ab2733f4512b477525897d50897 | True | n/a |
| patch_generation | 0 | 343.928 | 9516 | 8512 | 0.8945 | 906a8833dd3f4ec5b8eeb0f1b4389472 | True | n/a |
| patch_generation | 1 | 104.84 | 9617 | 9472 | 0.9849 | d93a59c41e5e4fd68669d0a60586e818 | True | n/a |
| review | 0 | 344.32800000000003 | 9520 | 8512 | 0.8941 | c6a2df68155941d78d4fa0764c84ac9d | True | n/a |
| review | 1 | 106.786 | 9621 | 9472 | 0.9845 | c64d6fc75a1d4cd39bf057d2743a99ff | True | n/a |
| review | 2 | 428.902 | 10752 | 9600 | 0.8929 | 7b4329f9a2af4c9baae740074db84873 | True | n/a |

