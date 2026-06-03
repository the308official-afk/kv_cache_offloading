# Run Report: agentbench-20260603_125608

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260603_125608`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/sglang_transfer_logs/sglang_transfer_events_20260602_223503_45079.jsonl`

## Task Summary

- Repo: `qutebrowser/qutebrowser`
- Instance id: `instance_qutebrowser__qutebrowser-f91ace96223cac8161c16dd061907e138fe85111-v059c6fdc75567943479b23ebca7c07b5e9a7f34c`
- Base commit: `ebfe9b7aa0c4ba9d451f993e08955004aaec4345`
- Task source: `n/a`
- Summary: The `hide_qt_warning` function and its associated tests have been moved from `log.py` to `qtlog.py` to better organize Qt-specific logging functionality.
- Expected action: refactor code organization
- Validation expectation: no explicit validation command provided
- Problem preview: The `hide_qt_warning` function and its associated tests have been moved from `log.py` to `qtlog.py` to better organize Qt-specific logging functionality. The tests need to be relocated to ensure they continue validati...
- Selected tests: `n/a`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 10513.055 | 541.578 | runtime_events.latency.ttft_ms | 9706 | 302 | True | 8640 | 1066 | 0.8902 |
| execution | 5606.338 | 1201.456 | runtime_events.latency.ttft_ms | 10025 | 154 | True | 8640 | 1385 | 0.8618 |
| execution | 3862.178 | 1500.028 | runtime_events.latency.ttft_ms | 10204 | 99 | True | 8512 | 1692 | 0.8342 |
| execution | 3852.478 | 851.731 | runtime_events.latency.ttft_ms | 10316 | 99 | True | 8768 | 1548 | 0.8499 |
| patch_generation | 2889.135 | 1321.089 | runtime_events.latency.ttft_ms | 10629 | 8 | True | 9280 | 1349 | 0.8731 |
| review | 5030.457 | 1260.259 | worker_runtime.request_to_first_decode | 11309 | 6 | True | 10624 | 685 | 0.9394 |

## Transfers

- Events: `12`
- Device to host present: `True`
- Host to device present: `False`
- Estimated KV MB: `763.000`
- CUDA sync timing ms: `475.813`
- Unique semantic token hashes: `12`

