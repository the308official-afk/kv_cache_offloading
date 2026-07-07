status	run_id	model	kv_tier	arm	cache_control	distractors	first_http_status	replay_http_status	first_ms	replay_ms	delta_ms	speedup_x	replay_cached	replay_reuse	warm	warm_source	reuse_signal	req_cache_status	req_cache_values	worker_cache_status	worker_cache_values	replay_evicts	replay_evict_cache	replay_evict_cache_match	replay_evict_status	result
complete	cache_pinning_microbenchmark_20260707_004059__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	off	60	200	200	189	127	-62	1.488	1216	0.976	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:off|a_replay:off	missing_runtime_json		0		FALSE	no_evict_seen	control_row
complete	cache_pinning_microbenchmark_20260707_004059__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	ephemeral:1h	60	200	200	189	128	-61	1.477	1216	0.976	TRUE	response_usage_cached_tokens	true_reuse_hit	full	a_first:ephemeral:1h|a_replay:ephemeral:1h	missing_runtime_json		0		FALSE	no_evict_seen	not_sent

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
CACHE_PINNING_MODE=validate \
./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```


run_id	model	ttl	frontend_flag	turn1_status	turn2_status	turn1_ms	turn2_ms	turn1_cached	turn2_cached	turn2_cache	router_pin	router_ttls	router_skip	worker_pin	worker_ttls	worker_pin_refreshes	result
cache_pinning_microbenchmark_20260707_010545__validate	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	1h	#NAME?	200	200	770	1250		128	hit	spawned	3600	cache_control_ttl_missing	applied	3600	0	pin_path_applied_and_cache_reused

# Cache-Pinning Doc Validation

- run_id: `cache_pinning_microbenchmark_20260707_010545__validate`
- model: `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8`
- ttl: `1h`
- frontend_flag: `--enable-cache-control`
- turn1_status: `200`
- turn2_status: `200`
- turn1_ms: `770`
- turn2_ms: `1250`
- turn1_cached: ``
- turn2_cached: `128`
- turn2_cache: `hit`
- router_pin: `spawned`
- router_ttls: `3600`
- router_skip: `cache_control_ttl_missing`
- worker_pin: `applied`
- worker_ttls: `3600`
- worker_pin_refreshes: `0`
- result: `pin_path_applied_and_cache_reused`


```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
CACHE_PINNING_MODE=sweep \
EXPERIMENT_RESET_MODE=restart \
DISTRACTOR_COUNTS="120 160 200 240" \
PROTECTED_INPUT_LEN=2000 \
DISTRACTOR_INPUT_LEN=2000 \
./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```
