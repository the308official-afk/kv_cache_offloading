# Run Report: agentbench-nodebb_20260602_164353

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_164353`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_203443_19424.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 11533.462 | 563.3629999999999 | worker_runtime_json.request_received_to_attached | 10187 | 324 | True | 8512 | 1675 | 0.8356 |
| execution | 11647.737 | 655.5830000000001 | worker_runtime_json.request_received_to_attached | 12088 | 33 | True | 10880 | 1208 | 0.9001 |
| execution | 4073.687 | 695.686 | worker_runtime_json.request_received_to_attached | 11784 | 18 | True | 10560 | 1224 | 0.8961 |
| execution | 3978.628 | 638.414 | worker_runtime_json.request_received_to_attached | 11816 | 18 | True | 10624 | 1192 | 0.8991 |
| patch_generation | 1783.285 | 240.557 | worker_runtime_json.request_received_to_attached | 9133 | 6 | True | 9024 | 109 | 0.9881 |
| review | 3876.226 | 240.606 | worker_runtime_json.request_received_to_attached | 9222 | 6 | True | 9088 | 134 | 0.9855 |

## Transfers

- Events: `232`
- Device to host present: `True`
- Host to device present: `True`
- Estimated KV MB: `6776.000`
- CUDA sync timing ms: `8426.990`
- Unique semantic token hashes: `152`

## Worker Subrequests

- Subrequests: `14`
- Transfer request-id matches: `14`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 563.3629999999999 | 10187 | 8512 | 0.8356 | f157743d4c4845ce99215728225cc85e | True | n/a |
| execution | 0 | 655.5830000000001 | 10528 | 8512 | 0.8085 | 7b2d977edbb84262aaae3c40a88e8372 | True | n/a |
| execution | 1 | 108.597 | 10714 | 10560 | 0.9856 | 8d3bbc648c614526959d40ad57707665 | True | n/a |
| execution | 2 | 135.412 | 10887 | 10688 | 0.9817 | 7f42be365edc4424902f03fa19c11337 | True | n/a |
| execution | 3 | 456.856 | 12088 | 10880 | 0.9001 | be103209f00544058c88d59d42cf5fce | True | n/a |
| execution | 0 | 695.686 | 10591 | 8512 | 0.8037 | c0f9076035e6439cbdf3c6e28c89fc62 | True | n/a |
| execution | 1 | 455.597 | 11784 | 10560 | 0.8961 | 30b3d571d71b4674a7cd5f1c5a297976 | True | n/a |
| execution | 0 | 638.414 | 10623 | 8704 | 0.8194 | 552cbcc29f754c8d87607e5441e0efbe | True | n/a |
| execution | 1 | 454.287 | 11816 | 10624 | 0.8991 | b230b533e4bb4813ae3e25f91a00c8f7 | True | n/a |
| patch_generation | 0 | 240.557 | 9078 | 8512 | 0.9377 | 4c11af0725554c2697697395355dd9c4 | True | n/a |
| patch_generation | 1 | 87.37100000000001 | 9133 | 9024 | 0.9881 | 38534f3f7ac94c638e2e6c3489c573fb | True | n/a |
| review | 0 | 240.606 | 9082 | 8512 | 0.9372 | 0338206cb44d467eabafe7eb04db4a4b | True | n/a |
| review | 1 | 88.852 | 9137 | 9024 | 0.9876 | b35a39e32d8e4b0ebb236b7093787d3e | True | n/a |
| review | 2 | 106.549 | 9222 | 9088 | 0.9855 | 910a7979d4714c9aaeeaa82b18396d62 | True | n/a |

