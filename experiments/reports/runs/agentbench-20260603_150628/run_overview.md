# Run Report: agentbench-20260603_150628

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_150628`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `internetarchive/openlibrary`
- Instance id: `instance_internetarchive__openlibrary-25858f9f0c165df25742acf8309ce909773f0cdd-v13642507b4fc1f8d234172bf8129942da2c2ca26`
- Base commit: `322d7a46cdc965bfabbf9500e98fde098c9d95b2`
- Task source: `n/a`
- Summary: Currently, Solr-related utility functions, configuration, and shared state are mixed directly into main modules like `openlibrary/solr/update_work.py`.
- Expected action: refactor code organization
- Validation expectation: no explicit validation command provided
- Problem preview: Currently, Solr-related utility functions, configuration, and shared state are mixed directly into main modules like `openlibrary/solr/update_work.py`. This creates tight coupling and cyclic import issues, making it d...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 14234.145 | 1035.417 | runtime_events.latency.ttft_ms | 10556 | 405 | True | 8640 | 1916 | 0.8185 |
| execution | 8540.019 | 1025.558 | worker_runtime.request_to_first_decode | 10978 | 231 | True | 8640 | 2338 | 0.7870 |
| execution | 4095.47 | -7538.02 | runtime_events.latency.ttft_ms | 11233 | 97 | True | 8640 | 2593 | 0.7692 |
| execution | 4080.076 | 800.489 | worker_runtime.request_to_first_decode | 11343 | 97 | True | 8896 | 2447 | 0.7843 |
| patch_generation | 2841.094 | -6835.809 | runtime_events.latency.ttft_ms | 10643 | 6 | True | 9472 | 1171 | 0.8900 |
| review | 5269.009 | 1011.8119999999999 | worker_runtime.request_to_first_decode | 11860 | 8 | True | 10624 | 1236 | 0.8958 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

