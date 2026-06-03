# Run Report: agentbench-20260603_145438

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_145438`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `internetarchive/openlibrary`
- Instance id: `instance_internetarchive__openlibrary-111347e9583372e8ef91c82e0612ea437ae3a9c9-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59`
- Base commit: `c9795319b19c60e884f34df3eaf7e3e7f2bfd58c`
- Task source: `n/a`
- Summary: The MARC parsers (XML and Binary) do not correctly handle fields linked with `$6`, which prevents alternate script data, such as additional titles and names in other alphabets, ...
- Expected action: edit repo code
- Validation expectation: no explicit validation command provided
- Problem preview: The MARC parsers (XML and Binary) do not correctly handle fields linked with `$6`, which prevents alternate script data, such as additional titles and names in other alphabets, from being included in the processed out...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 31551.368 | 1164.678 | runtime_events.latency.ttft_ms | 9774 | 928 | True | 8640 | 1134 | 0.8840 |
| execution | 3458.332 | 1159.47 | worker_runtime.request_to_first_decode | 10719 | 83 | True | 8640 | 2079 | 0.8060 |
| execution | 3487.675 | -2322.467 | runtime_events.latency.ttft_ms | 10827 | 83 | True | 8640 | 2187 | 0.7980 |
| execution | 3489.568 | 989.01 | worker_runtime.request_to_first_decode | 10923 | 83 | True | 8704 | 2219 | 0.7969 |
| patch_generation | 2832.441 | -5938.063 | runtime_events.latency.ttft_ms | 10363 | 8 | True | 9856 | 507 | 0.9511 |
| review | 2875.485 | 1662.105 | worker_runtime.request_to_first_decode | 10369 | 8 | True | 9856 | 513 | 0.9505 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

