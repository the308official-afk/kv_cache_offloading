# Run Report: agentbench-nodebb_20260602_130553

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `baseline`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_130553`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_180217_9267.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 38244.995 | 17365.876 | worker_runtime_json.request_received_to_attached | 10324 | 619 | False | 0 | 10324 | 0.0000 |
| execution | 4461.137 | 844.88 | worker_runtime_json.request_received_to_attached | 10960 | 104 | True | 8512 | 2448 | 0.7766 |
| patch_generation | 4821.794 | 317.847 | worker_runtime_json.request_received_to_attached | 10624 | 6 | True | 9408 | 1216 | 0.8855 |
| review | 2482.563 | 317.959 | worker_runtime_json.request_received_to_attached | 9442 | 6 | True | 9344 | 98 | 0.9896 |

## Transfers

- Events: `17`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `899.500`
- CUDA sync timing ms: `687.282`
- Unique semantic token hashes: `17`

## Worker Subrequests

- Subrequests: `7`
- Transfer request-id matches: `0`
- Transfer time-window matches: `7`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 17365.876 | 10324 | 0 | 0.0000 | b66fed899579418d90b164b396529771 | False | True |
| execution | 0 | 844.88 | 10960 | 8512 | 0.7766 | db7adeebc90d42cdb7fb9fca8d5f8c68 | False | True |
| patch_generation | 0 | 317.847 | 9342 | 8512 | 0.9112 | 3de64cc54ed54a40a44e470eadacdd3d | False | True |
| patch_generation | 1 | 86.769 | 9439 | 9344 | 0.9899 | a5a16b01cceb4037babb2cb2650a61fa | False | True |
| patch_generation | 2 | 443.03 | 10624 | 9408 | 0.8855 | 5b775d66682e461f97a01ac291f48768 | False | True |
| review | 0 | 317.959 | 9345 | 8512 | 0.9109 | 82ba03eee5264c8aa76b912ff5477c46 | False | True |
| review | 1 | 86.79299999999999 | 9442 | 9344 | 0.9896 | 0a66e600e5614e3cace9b93e3f258820 | False | True |

