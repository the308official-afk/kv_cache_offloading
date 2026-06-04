# Run Report: agentbench-20260604_151332

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260604_151332`
- SGLang transfer log: `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260604_195847_17361.jsonl`

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

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 34516.748 | 17191.821 | worker_runtime_json.request_received_to_attached | 10449 | 506 | False | 0 | 10449 | 0.0000 |
| execution | 5028.091 | 762.544 | worker_runtime_json.request_received_to_attached | 10972 | 122 | True | 8512 | 2460 | 0.7758 |
| execution | 5071.949 | 785.064 | worker_runtime_json.request_received_to_attached | 11118 | 122 | True | 8512 | 2606 | 0.7656 |
| execution | 4031.444 | 768.9820000000001 | worker_runtime_json.request_received_to_attached | 11252 | 92 | True | 8768 | 2484 | 0.7792 |
| patch_generation | 2673.166 | 292.97200000000004 | worker_runtime_json.request_received_to_attached | 9617 | 8 | True | 9472 | 145 | 0.9849 |
| review | 4916.244 | 293.279 | worker_runtime_json.request_received_to_attached | 10752 | 6 | True | 9600 | 1152 | 0.8929 |

## Transfers

- Events: `24`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `1218.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

## Worker Subrequests

- Subrequests: `9`
- Transfer request-id matches: `9`
- Transfer time-window matches: `0`

| Phase | Subrequest | TTFT ms | Prompt tokens | Cached tokens | Reuse ratio | SGLang request id | Transfer ID match | Transfer time match |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | 0 | 17191.821 | 10449 | 0 | 0.0000 | 6d49d47b27b744039f97045a88262574 | True | n/a |
| execution | 0 | 762.544 | 10972 | 8512 | 0.7758 | acdad27e04f64dcea5e4fb68e4f5d6d3 | True | n/a |
| execution | 0 | 785.064 | 11118 | 8512 | 0.7656 | 45264a0659d540b0a1f802abf014aaa2 | True | n/a |
| execution | 0 | 768.9820000000001 | 11252 | 8768 | 0.7792 | ee2672e0a47741f898f0d7b9429fa0d0 | True | n/a |
| patch_generation | 0 | 292.97200000000004 | 9516 | 8512 | 0.8945 | 428cdd537b314a7184996b6f0855370e | True | n/a |
| patch_generation | 1 | 71.634 | 9617 | 9472 | 0.9849 | 9272b1d6d0b54dc0b8d0127078be3d24 | True | n/a |
| review | 0 | 293.279 | 9520 | 8512 | 0.8941 | f5a7b85bda27496f8ec7f498d64a76da | True | n/a |
| review | 1 | 72.13 | 9621 | 9472 | 0.9845 | 6ec68573b634428aa98d874a67c780a6 | True | n/a |
| review | 2 | 373.31199999999995 | 10752 | 9600 | 0.8929 | 78a1fc25038141f08f6689bb1dd7b270 | True | n/a |

