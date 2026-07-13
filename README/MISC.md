

```bash
status	sweep_id	model	kv_tier	arm	hint_profile	protected_cache	distractors	first_status	replay_status	first_ms	replay_ms	replay_delta_ms	replay_speedup	replay_cached	replay_reuse	survived	survival_source	reuse_status	req_cache_status	req_cache_values	worker_cache_status	worker_cache_values	replay_evicts	replay_evict_cache	replay_evict_cache_match	replay_evict_status	effect_status
partial	kv_retention_microbenchmark_20260713_054358__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	control	none	off	100	200	200	290	32	-258	9.062	1600	0.978	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:off|a_replay:off	none		0		FALSE	no_evict_seen	control_row
partial	kv_retention_microbenchmark_20260713_054358__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	protected	high-priority	off	100	200	200	295	34	-261	8.676	1600	0.978	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:off|a_replay:off	none		0		FALSE	no_evict_seen	mechanism_enabled_no_effect
partial	kv_retention_microbenchmark_20260713_054358__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	control	none	off	150	200	200	293	33	-260	8.879	1600	0.978	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:off|a_replay:off	none		0		FALSE	no_evict_seen	control_row
partial	kv_retention_microbenchmark_20260713_054358__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	protected	high-priority	off	150	200	200	295	34	-261	8.676	1600	0.978	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:off|a_replay:off	none		0		FALSE	no_evict_seen	mechanism_enabled_no_effect
partial	kv_retention_microbenchmark_20260713_054358__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	control	none	off	200	200	200	290	33	-257	8.788	1600	0.978	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:off|a_replay:off	none		0		FALSE	no_evict_seen	control_row
partial	kv_retention_microbenchmark_20260713_054358__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_only	protected	high-priority	off	200	200	200	293	32	-261	9.156	1600	0.978	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:off|a_replay:off	none		0		FALSE	no_evict_seen	mechanism_enabled_no_effect


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
