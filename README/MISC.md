

```bash
benchmark_id	part	run_id	model	kv_tier	arm	hint_profile	cache_control	distractors	first_status	replay_status	first_ms	replay_ms	delta_ms	speedup_x	replay_cached	replay_reuse	warm	warm_source	req_prio_status	worker_prio_status	replay_evicts	replay_evict_cache	replay_evict_status	result
kv_retention_microbenchmark_20260713_041007	sweep	kv_retention_microbenchmark_20260713_041007__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	control	none	off	10	200	200	292	33	-259	8.848	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	control_row
kv_retention_microbenchmark_20260713_041007	sweep	kv_retention_microbenchmark_20260713_041007__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	protected	high-priority	off	10	200	200	292	33	-259	8.848	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	mechanism_enabled_no_effect
kv_retention_microbenchmark_20260713_041007	sweep	kv_retention_microbenchmark_20260713_041007__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	control	none	off	20	200	200	295	34	-261	8.676	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	control_row
kv_retention_microbenchmark_20260713_041007	sweep	kv_retention_microbenchmark_20260713_041007__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	protected	high-priority	off	20	200	200	293	34	-259	8.618	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	mechanism_enabled_no_effect
kv_retention_microbenchmark_20260713_041007	sweep	kv_retention_microbenchmark_20260713_041007__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	control	none	off	30	200	200	292	32	-260	9.125	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	control_row
kv_retention_microbenchmark_20260713_041007	sweep	kv_retention_microbenchmark_20260713_041007__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	protected	high-priority	off	30	200	200	289	32	-257	9.031	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	mechanism_enabled_no_effect


```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
SPEC_PREFILL_MODE=all \
EXPERIMENT_RESET_MODE=flush \
SPEC_PREFILL_SWEEP_AXIS=SPEC_PREFILL_WARMUP_WAIT_MS \
SPEC_PREFILL_SWEEP_VALUES="0 500 1000 2000" \
SPEC_PREFILL_TURN_A_WORDS=4000 \
SPEC_PREFILL_TURN_B_WORDS=2048 \
SPEC_PREFILL_OUTPUT_TOKENS=128 \
./agentbench/run_speculative_prefill_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```
