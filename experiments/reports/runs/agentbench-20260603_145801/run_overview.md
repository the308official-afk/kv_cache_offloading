# Run Report: agentbench-20260603_145801

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_145801`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `gravitational/teleport`
- Instance id: `instance_gravitational__teleport-6eaaf3a27e64f4ef4ef855bd35d7ec338cf17460-v626ec2a48416b10a88641359a169d99e935ff037`
- Base commit: `a51596d8d779935e1dfa8d0fabce39d9edd91457`
- Task source: `n/a`
- Summary: Add linear benchmark generator for progressive request rate configurations
- Expected action: edit repo code
- Validation expectation: no explicit validation command provided
- Problem preview: Introduce a linear benchmark generator that can produce a sequence of benchmark configurations. The generator should start at a defined lower bound of requests per second, increase by a fixed step size on each generat...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 15389.217 | 1149.195 | runtime_events.latency.ttft_ms | 9877 | 446 | True | 8640 | 1237 | 0.8748 |
| execution | 32671.59 | 1067.698 | runtime_events.latency.ttft_ms | 10340 | 956 | True | 8640 | 1700 | 0.8356 |
| execution | 69735.665 | 1357.645 | worker_runtime.request_to_first_decode | 10823 | 2048 | True | 8640 | 2183 | 0.7983 |
| execution | 40045.746 | -68404.969 | runtime_events.latency.ttft_ms | 11294 | 1167 | True | 9088 | 2206 | 0.8047 |
| patch_generation | 2809.828 | 1607.612 | worker_runtime.request_to_first_decode | 13293 | 40 | True | 9088 | 4205 | 0.6837 |
| review | 2836.744 | -41814.636 | runtime_events.latency.ttft_ms | 13330 | 40 | True | 8576 | 4754 | 0.6434 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

