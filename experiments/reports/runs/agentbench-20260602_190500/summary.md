# Run Report: agentbench-20260602_190500

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_190500`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_190500/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 8549.444 | n/a | n/a | 9706 | 242 | True | 8640 | 1066 | 0.8902 |
| execution | 4824.221 | n/a | n/a | 9965 | 128 | True | 8640 | 1325 | 0.8670 |
| execution | 2957.11 | n/a | n/a | 10118 | 72 | True | 8768 | 1350 | 0.8666 |
| execution | 2965.472 | n/a | n/a | 10203 | 72 | True | 8768 | 1435 | 0.8594 |
| patch_generation | 5279.467 | n/a | n/a | 11163 | 8 | True | 10432 | 731 | 0.9345 |
| review | 5181.302 | n/a | n/a | 11167 | 6 | True | 10496 | 671 | 0.9399 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

