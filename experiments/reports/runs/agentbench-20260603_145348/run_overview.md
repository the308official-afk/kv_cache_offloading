# Run Report: agentbench-20260603_145348

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_145348`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `future-architect/vuls`
- Instance id: `instance_future-architect__vuls-407407d306e9431d6aa0ab566baa6e44e5ba2904`
- Base commit: `dccdd8a091bc57785341d911b7d8c7867d522e9a`
- Task source: `n/a`
- Summary: trivy-to-vuls generates duplicate objects in cveContents and splits Debian severities into separate records
- Expected action: refactor code organization
- Validation expectation: no explicit validation command provided
- Problem preview: 1. Created the following Dockerfile to build a vulnerable test image (affected by CVE-2013-1629): FROM debian:10 RUN apt-get update && apt-get install -y openssh-server wget Install vulnerable versions of python-pip a...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 10718.205 | 1121.158 | runtime_events.latency.ttft_ms | 10238 | 303 | True | 8640 | 1598 | 0.8439 |
| execution | 3701.738 | 1773.816 | runtime_events.latency.ttft_ms | 10558 | 92 | True | 8640 | 1918 | 0.8183 |
| execution | 3721.607 | 1390.395 | runtime_events.latency.ttft_ms | 10675 | 92 | True | 8640 | 2035 | 0.8094 |
| execution | 3725.079 | 988.517 | runtime_events.latency.ttft_ms | 10780 | 92 | True | 8768 | 2012 | 0.8134 |
| patch_generation | 11177.237 | 1566.095 | runtime_events.latency.ttft_ms | 9737 | 8 | True | 9344 | 393 | 0.9596 |
| review | 10626.715 | 803.004 | runtime_events.latency.ttft_ms | 9715 | 6 | True | 9344 | 371 | 0.9618 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

