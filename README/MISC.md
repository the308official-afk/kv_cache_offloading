status	run_id	model	kv_tier	arm	cache_control	distractors	first_http_status	replay_http_status	first_ms	replay_ms	delta_ms	speedup_x	replay_cached	replay_reuse	warm	warm_source	reuse_signal	req_cache_status	req_cache_values	worker_cache_status	worker_cache_values	replay_evicts	replay_evict_cache	replay_evict_cache_match	replay_evict_status	result
complete	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	off	60	200	200	201	75	-126	2.68	1984	0.97	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:off|a_replay:off	missing_runtime_json		0		FALSE	no_evict_seen	control_row
complete	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	ephemeral:1h	60	200	200	201	74	-127	2.716	1984	0.97	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:ephemeral:1h|a_replay:ephemeral:1h	missing_runtime_json		0		FALSE	no_evict_seen	not_sent
complete	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	off	120	200	200	198	74	-124	2.676	1984	0.97	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:off|a_replay:off	missing_runtime_json		0		FALSE	no_evict_seen	control_row
complete	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	ephemeral:1h	120	200	200	198	78	-120	2.538	1984	0.97	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:ephemeral:1h|a_replay:ephemeral:1h	missing_runtime_json		0		FALSE	no_evict_seen	not_sent
complete	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	off	200	200	200	201	76	-125	2.645	1984	0.97	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:off|a_replay:off	missing_runtime_json		0		FALSE	no_evict_seen	control_row
complete	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	ephemeral:1h	200	200	200	201	74	-127	2.716	1984	0.97	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:ephemeral:1h|a_replay:ephemeral:1h	missing_runtime_json		0		FALSE	no_evict_seen	not_sent
complete	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	off	240	200	200	200	74	-126	2.703	1984	0.97	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:off|a_replay:off	missing_runtime_json		0		FALSE	no_evict_seen	control_row
complete	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	ephemeral:1h	240	200	200	204	78	-126	2.615	1984	0.97	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:ephemeral:1h|a_replay:ephemeral:1h	missing_runtime_json		0		FALSE	no_evict_seen	not_sent



```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
CACHE_PINNING_MODE=sweep \
EXPERIMENT_RESET_MODE=restart \
DISTRACTOR_COUNTS="400 800 1200 1600" \
PROTECTED_INPUT_LEN=4000 \
DISTRACTOR_INPUT_LEN=400 \
./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```
