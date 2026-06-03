# Run Report: agentbench-20260602_193512

- Model: `Qwen/Qwen2.5-Coder-7B-Instruct`
- App variant: `upstream_deploy_coding_agent`
- Hint profile: `high-reuse`
- AgentBench result: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_193512`
- SGLang transfer log: `/home/ec2-user/kv_cache_offloading/experiments/raw/agentbench/results/agentbench-20260602_193512/others/sglang_transfer_log_not_found.jsonl`

## Outcome

- Patch nonempty: `False`
- Git diff nonempty: `False`
- Workspace patch bytes: `0`

## Runtime

| Phase | Latency ms | TTFT ms | TTFT source | Prompt tokens | Output tokens | Cache hit | Cached tokens | Recomputed tokens | Reuse ratio |
| --- | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| planning | 34130.285 | n/a | n/a | 10449 | 504 | False | 0 | 10449 | 0.0000 |
| execution | 5162.227 | n/a | n/a | 10970 | 128 | True | 8512 | 2458 | 0.7759 |
| execution | 5186.532 | n/a | n/a | 11122 | 128 | True | 8512 | 2610 | 0.7653 |
| execution | 5171.563 | n/a | n/a | 11262 | 128 | True | 8768 | 2494 | 0.7785 |
| patch_generation | 4886.044 | n/a | n/a | 10844 | 8 | True | 9600 | 1244 | 0.8853 |
| review | 4788.965 | n/a | n/a | 10847 | 6 | True | 9664 | 1183 | 0.8909 |

## Transfers

- Events: `0`
- Device to host present: `False`
- Host to device present: `False`
- Estimated KV MB: `0.000`
- CUDA sync timing ms: `0.000`
- Unique semantic token hashes: `0`

