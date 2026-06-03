# Run Report: agentbench-20260603_142016

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_142016`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `NodeBB/NodeBB`
- Instance id: `instance_NodeBB__NodeBB-51d8f3b195bddb13a13ddc0de110722774d9bb1b-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e`
- Base commit: `da2441b9bd293d7188ee645be3322a7305a43a19`
- Task source: `n/a`
- Summary: Move .well-known assets to separate router file, add a basic webfinger implementation
- Expected action: modify routing/controller logic
- Validation expectation: no explicit validation command provided
- Problem preview: Federated identity discovery via the `.well-known/webfinger` endpoint is not currently supported. Additionally, the redirect logic for `.well-known/change-password` is embedded in an unrelated route file, making route...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `True`
- Git diff nonempty: `True`
- Workspace patch bytes: `1934`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 14576.83 | 1721.527 | runtime_events.latency.ttft_ms | 10187 | 418 | True | 8640 | 1547 | 0.8481 |
| execution | 5981.06 | 1220.159 | runtime_events.latency.ttft_ms | 10790 | 33 | True | 10688 | 102 | 0.9905 |
| execution | 59776.516 | 591.098 | runtime_events.latency.ttft_ms | 13940 | 84 | True | 10688 | 3252 | 0.7667 |
| patch_generation | 2270.116 | 1356.587 | runtime_events.latency.ttft_ms | 9330 | 6 | True | 9152 | 178 | 0.9809 |
| review | 2173.999 | 1294.744 | worker_runtime.request_to_first_decode | 9334 | 6 | True | 10688 | 0 | 1.0000 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

