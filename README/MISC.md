

```bash
benchmark_id	part	run_id	model	kv_tier	arm	hint_profile	cache_control	distractors	first_status	replay_status	first_ms	replay_ms	delta_ms	speedup_x	replay_cached	replay_reuse	warm	warm_source	req_prio_status	worker_prio_status	replay_evicts	replay_evict_cache	replay_evict_status	result
kv_retention_microbenchmark_20260713_050903	sweep	kv_retention_microbenchmark_20260713_050903__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	control	none	off	100	200	200	291	33	-258	8.818	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	control_row
kv_retention_microbenchmark_20260713_050903	sweep	kv_retention_microbenchmark_20260713_050903__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	protected	high-priority	off	100	200	200	63	32	-31	1.969	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	mechanism_enabled_no_effect
kv_retention_microbenchmark_20260713_050903	sweep	kv_retention_microbenchmark_20260713_050903__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	control	none	off	150	200	200	62	31	-31	2	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	control_row
kv_retention_microbenchmark_20260713_050903	sweep	kv_retention_microbenchmark_20260713_050903__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	protected	high-priority	off	150	200	200	62	33	-29	1.879	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	mechanism_enabled_no_effect
kv_retention_microbenchmark_20260713_050903	sweep	kv_retention_microbenchmark_20260713_050903__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	control	none	off	200	200	200	64	32	-32	2	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	control_row
kv_retention_microbenchmark_20260713_050903	sweep	kv_retention_microbenchmark_20260713_050903__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	protected	high-priority	off	200	200	200	63	32	-31	1.969	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	mechanism_enabled_no_effect
kv_retention_microbenchmark_20260713_050903	sweep	kv_retention_microbenchmark_20260713_050903__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	control	none	off	250	200	200	65	32	-33	2.031	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	control_row
kv_retention_microbenchmark_20260713_050903	sweep	kv_retention_microbenchmark_20260713_050903__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	protected	high-priority	off	250	200	200	64	31	-33	2.065	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	mechanism_enabled_no_effect
kv_retention_microbenchmark_20260713_050903	sweep	kv_retention_microbenchmark_20260713_050903__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	control	none	off	300	200	200	64	33	-31	1.939	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	control_row
kv_retention_microbenchmark_20260713_050903	sweep	kv_retention_microbenchmark_20260713_050903__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	protected	high-priority	off	300	200	200	62	32	-30	1.938	1600	0.978	TRUE	response_usage_cached_tokens			0		no_evict_seen	mechanism_enabled_no_effect


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
