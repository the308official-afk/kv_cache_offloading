# Run Report: agentbench-20260603_125502

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_125502`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `NodeBB/NodeBB`
- Instance id: `instance_NodeBB__NodeBB-04998908ba6721d64eba79ae3b65a351dcfbc5b5-vnan`
- Base commit: `1e137b07052bc3ea0da44ed201702c94055b8ad2`
- Task source: `n/a`
- Summary: Email Validation Status Not Handled Correctly in ACP and Confirmation Logic
- Expected action: fix validation logic
- Validation expectation: no explicit validation command provided
- Problem preview: Email Validation Status Not Handled Correctly in ACP and Confirmation Logic The Admin Control Panel (ACP) does not accurately reflect the email validation status of users. Also, validation and confirmation processes r...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `True`
- Git diff nonempty: `True`
- Workspace patch bytes: `412`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 22049.955 | 8824.1 | worker_runtime.request_to_first_decode | 10449 | 431 | False | 0 | 10449 | 0.0000 |
| execution | 9048.347 | 1023.439 | worker_runtime.request_to_first_decode | 13236 | 24 | True | 12096 | 1140 | 0.9139 |
| execution | 14593.073 | 567.342 | worker_runtime.request_to_first_decode | 14940 | 45 | True | 12288 | 2652 | 0.8225 |
| patch_generation | 8685.349 | 1484.723 | worker_runtime.request_to_first_decode | 9371 | 99 | True | 12096 | 0 | 1.0000 |
| review | 4568.703 | 2069.8430000000003 | worker_runtime.request_to_first_decode | 9323 | 90 | True | 9216 | 107 | 0.9885 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

