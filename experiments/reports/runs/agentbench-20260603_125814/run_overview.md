# Run Report: agentbench-20260603_125814

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_125814`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `qutebrowser/qutebrowser`
- Instance id: `instance_qutebrowser__qutebrowser-c580ebf0801e5a3ecabc54f327498bb753c6d5f2-v2ef375ac784985212b1805e1d0431dc8f1b3c171`
- Base commit: `0b8cc812fd0b73e296a3f93db02ce5d0b35714fc`
- Task source: `n/a`
- Summary: Host blocking does not apply to subdomains when only the parent domain is listed
- Expected action: fix host-matching logic
- Validation expectation: no explicit validation command provided
- Problem preview: Host blocking does not apply to subdomains when only the parent domain is listed In the hosts-based blocking method, requests are only blocked if the exact request hostname matches an entry in either the dynamically l...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 26241.275 | 982.629 | runtime_events.latency.ttft_ms | 9914 | 769 | True | 8640 | 1274 | 0.8715 |
| execution | 45494.107 | 922.8969999999999 | worker_runtime.request_to_first_decode | 10700 | 1332 | True | 8640 | 2060 | 0.8075 |
| execution | 48228.271 | -44595.989 | runtime_events.latency.ttft_ms | 11119 | 1407 | True | 8640 | 2479 | 0.7770 |
| execution | 70025.565 | 1780.3400000000001 | worker_runtime.request_to_first_decode | 11526 | 2048 | True | 9024 | 2502 | 0.7829 |
| patch_generation | 64721.524 | -116302.567 | runtime_events.latency.ttft_ms | 14890 | 1381 | True | 14208 | 682 | 0.9542 |
| review | 12806.445 | 460.689 | worker_runtime.request_to_first_decode | 15710 | 255 | True | 15552 | 158 | 0.9899 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

