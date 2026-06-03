# Run Report: agentbench-20260603_144653

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_144653`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `qutebrowser/qutebrowser`
- Instance id: `instance_qutebrowser__qutebrowser-96b997802e942937e81d2b8a32d08f00d3f4bc4e-v5fc38aaf22415ab0b70567368332beee7955b367`
- Base commit: `2e65f731b1b615b5cd60417c00b6993c2295e9f8`
- Task source: `n/a`
- Summary: Bug Report: `parse_duration` accepts invalid formats and miscalculates durations
- Expected action: fix validation logic
- Validation expectation: no explicit validation command provided
- Problem preview: The helper responsible for parsing duration strings does not properly validate input or return consistent millisecond values. Inputs such as negative values (`-1s`), duplicate units (`34ss`), or fractional seconds (`6...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 22207.775 | 1503.941 | runtime_events.latency.ttft_ms | 10471 | 248 | True | 10368 | 103 | 0.9902 |
| execution | 8417.665 | 1261.873 | runtime_events.latency.ttft_ms | 10396 | 175 | True | 10368 | 28 | 0.9973 |
| execution | 16401.874 | 1418.664 | runtime_events.latency.ttft_ms | 23899 | 64 | True | 11776 | 12123 | 0.4927 |
| execution | 8513.059 | 421.834 | runtime_events.latency.ttft_ms | 10683 | 173 | True | 10560 | 123 | 0.9885 |
| patch_generation | 1613.547 | 1772.948 | runtime_events.latency.ttft_ms | 9425 | 6 | True | 9344 | 81 | 0.9914 |
| review | 2746.059 | 731.87 | runtime_events.latency.ttft_ms | 9490 | 6 | True | 10496 | 0 | 1.0000 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

