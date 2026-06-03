# Run Report: agentbench-20260603_141735

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_141735`
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
| planning | 20577.404 | 7360.33 | worker_runtime.request_to_first_decode | 10449 | 431 | False | 0 | 10449 | 0.0000 |
| execution | 9062.271 | 1023.439 | worker_runtime.request_to_first_decode | 13236 | 24 | True | 12096 | 1140 | 0.9139 |
| execution | 13290.759 | 567.982 | worker_runtime.request_to_first_decode | 14940 | 45 | True | 12288 | 2652 | 0.8225 |
| patch_generation | 6582.428 | 1484.694 | worker_runtime.request_to_first_decode | 9390 | 36 | True | 12096 | 0 | 1.0000 |
| review | 70139.582 | 2069.814 | worker_runtime.request_to_first_decode | 9269 | 2048 | True | 9152 | 117 | 0.9874 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

