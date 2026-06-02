# Run Report: agentbench-nodebb_20260602_124555

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `baseline`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-nodebb_20260602_124555`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_174141_4478.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 38354.631 | 17458.361 | worker_runtime_json.request_received_to_attached | 10324 | 619 | False | 0 | 10324 | 0.0000 |
| execution | 4448.171 | 844.186 | worker_runtime_json.request_received_to_attached | 10960 | 104 | True | 8512 | 2448 | 0.7766 |
| patch_generation | 4809.846 | 317.87399999999997 | worker_runtime_json.request_received_to_attached | 10624 | 6 | True | 9408 | 1216 | 0.8855 |
| review | 2483.193 | 317.75100000000003 | worker_runtime_json.request_received_to_attached | 9442 | 6 | True | 9344 | 98 | 0.9896 |

## Transfers

- Events: `17`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `899.500`
- CUDA sync timing ms: `687.728`
- Unique semantic token hashes: `17`

## Worker Subrequests

- Subrequests: `7`
- Transfer request-id matches: `0`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 17458.361 | 10324 | 0 | 0.0000 | a9f7748142864bb7b67e946da5d4a57a | False | False |
| execution | 0 | 844.186 | 10960 | 8512 | 0.7766 | 508101929a404cd39975c34094109341 | False | False |
| patch_generation | 0 | 317.87399999999997 | 9342 | 8512 | 0.9112 | 62d5d642f1904e8b8593c92b4c94f73b | False | False |
| patch_generation | 1 | 86.596 | 9439 | 9344 | 0.9899 | a068bb4193d5405f93523d81106aa5d8 | False | False |
| patch_generation | 2 | 442.986 | 10624 | 9408 | 0.8855 | 85bd3378b7e44a659def3c8d0f1e12ff | False | False |
| review | 0 | 317.75100000000003 | 9345 | 8512 | 0.9109 | 26079aaf8bf24a51a4228cc8d06156d8 | False | False |
| review | 1 | 86.804 | 9442 | 9344 | 0.9896 | e2fba75c016142a8bc117ff4ced0210e | False | False |

