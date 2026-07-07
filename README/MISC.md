```bash
docker logs -f dynamo-sglang-worker | egrep -i "prefill|cache|evict|hicache|warn|error"
```


```bash
while true; do
  date
  nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total --format=csv,noheader
  sleep 2
done
```


```bash
while true; do
  date
  docker stats --no-stream dynamo-sglang-worker
  echo
  vmstat 1 2 | tail -1
  echo "----------------------------------------"
  sleep 2
done
```


```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
RETENTION_PROBE_ID="cachepin_debug_control_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
KV_TIER_MODES=gpu_cpu \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES=none \
CONTROL_CACHE_CONTROL_PROFILE=off \
PROTECTED_CACHE_CONTROL_PROFILES=off \
DISTRACTOR_COUNT=800 \
PROTECTED_INPUT_LEN=4000 \
DISTRACTOR_INPUT_LEN=400 \
EXPERIMENT_RESET_MODE=restart \
STOP_ON_PROBE_FAILURE=1 \
./agentbench/run_kv_retention_probe_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```


```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
RETENTION_PROBE_ID="cachepin_debug_ephemeral_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
KV_TIER_MODES=gpu_cpu \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES=none \
CONTROL_CACHE_CONTROL_PROFILE=ephemeral:1h \
PROTECTED_CACHE_CONTROL_PROFILES=ephemeral:1h \
DISTRACTOR_COUNT=800 \
PROTECTED_INPUT_LEN=4000 \
DISTRACTOR_INPUT_LEN=400 \
EXPERIMENT_RESET_MODE=restart \
STOP_ON_PROBE_FAILURE=1 \
./agentbench/run_kv_retention_probe_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```


```bash

```




benchmark_id	part	row_kind	run_id	model	kv_tier	arm	turn	distractors	cache_control	ttl	http_status	latency_ms	prompt_tokens	cached_tokens	cache_hit	reuse_ratio	warm	first_ms	replay_ms	delta_ms	speedup_x	router_pin	worker_pin	worker_refreshes	req_cache_status	worker_cache_status	replay_evicts	replay_evict_status	result	reuse_signal
cache_pinning_microbenchmark_20260707_021550	validate	validate_turn	cache_pinning_microbenchmark_20260707_021550__validate	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8		protected	turn1		ephemeral:1h	1h	200	762	30		miss							spawned	applied	0					pin_path_applied_and_cache_reused	
cache_pinning_microbenchmark_20260707_021550	validate	validate_turn	cache_pinning_microbenchmark_20260707_021550__validate	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8		protected	turn2		ephemeral:1h	1h	200	1245	175	128	hit							spawned	applied	0					pin_path_applied_and_cache_reused	
cache_pinning_microbenchmark_20260707_021550	validate	validate_summary	cache_pinning_microbenchmark_20260707_021550__validate	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8		protected	turn2		ephemeral:1h	1h	200	1245		128	hit			762	1245			spawned	applied	0					pin_path_applied_and_cache_reused	doc_validation
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	replay	60	off		200	75		1984	hit	0.97	TRUE	201	75	-126	2.68				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	replay	60	ephemeral:1h		200	74		1984	hit	0.97	TRUE	201	74	-127	2.716				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	replay	120	off		200	74		1984	hit	0.97	TRUE	198	74	-124	2.676				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	replay	120	ephemeral:1h		200	78		1984	hit	0.97	TRUE	198	78	-120	2.538				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	replay	200	off		200	76		1984	hit	0.97	TRUE	201	76	-125	2.645				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	replay	200	ephemeral:1h		200	74		1984	hit	0.97	TRUE	201	74	-127	2.716				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	replay	240	off		200	74		1984	hit	0.97	TRUE	200	74	-126	2.703				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	replay	240	ephemeral:1h		200	78		1984	hit	0.97	TRUE	204	78	-126	2.615				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_compare	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	compare			ephemeral:1h		complete												missing_runtime_json			missing_runtime_json			not_sent	inconclusive


