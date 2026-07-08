=== RESTART ===
first_ms	replay_ms
293	38
296	38
298	187
298	39

=== FLUSH ===
first_ms	replay_ms
296	38
71	37
70	184
74	37


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









```bash
python3 - <<'PY'
import csv
from pathlib import Path

path = Path("experiments/reports/latest_retention_probe_requests.csv")
rows = list(csv.DictReader(path.open()))

distractors = [r for r in rows if str(r.get("request_role","")).startswith("distractor_")]
reused = [r for r in distractors if str(r.get("cached_prompt_tokens","")).strip() not in {"", "0"}]

print("total_distractors:", len(distractors))
print("reused_distractors:", len(reused))

for r in reused[:20]:
    print(
        r["request_role"],
        "cached_prompt_tokens=", r.get("cached_prompt_tokens",""),
        "cache_reuse_ratio=", r.get("cache_reuse_ratio",""),
        "prompt_hash=", r.get("prompt_hash",""),
    )
PY
```





```bash
python3 - <<'PY'
import csv
from pathlib import Path
from collections import Counter

path = Path("experiments/reports/latest_retention_probe_requests.csv")
rows = list(csv.DictReader(path.open()))

distractors = [r for r in rows if str(r.get("request_role","")).startswith("distractor_")]
hashes = [r.get("prompt_hash","") for r in distractors]

print("total_distractors:", len(distractors))
print("unique_prompt_hashes:", len(set(hashes)))

dups = [item for item, count in Counter(hashes).items() if count > 1]
print("repeated_hashes:", len(dups))
if dups:
    print("example_repeated_hashes:", dups[:10])
PY
```




benchmark_id	part	row_kind	run_id	model	kv_tier	arm	turn	distractors	cache_control	ttl	http_status	latency_ms	prompt_tokens	cached_tokens	cache_hit	reuse_ratio	warm	first_ms	replay_ms	delta_ms	speedup_x	router_pin	worker_pin	worker_refreshes	req_cache_status	worker_cache_status	replay_evicts	replay_evict_status	result	reuse_signal
cache_pinning_microbenchmark_20260707_165021	validate	validate_turn	cache_pinning_microbenchmark_20260707_165021__validate	Qwen/Qwen2.5-Coder-7B-Instruct		protected	turn1		ephemeral:1h	1h	200	729	30		miss							spawned	applied	0					pin_path_applied_and_cache_reused	
cache_pinning_microbenchmark_20260707_165021	validate	validate_turn	cache_pinning_microbenchmark_20260707_165021__validate	Qwen/Qwen2.5-Coder-7B-Instruct		protected	turn2		ephemeral:1h	1h	200	694	175	128	hit							spawned	applied	0					pin_path_applied_and_cache_reused	
cache_pinning_microbenchmark_20260707_165021	validate	validate_summary	cache_pinning_microbenchmark_20260707_165021__validate	Qwen/Qwen2.5-Coder-7B-Instruct		protected	turn2		ephemeral:1h	1h	200	694		128	hit			729	694			spawned	applied	0					pin_path_applied_and_cache_reused	doc_validation
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	control	replay	600	off		200	43		832	hit	0.96	TRUE	128	43	-85	2.977				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	protected	replay	600	ephemeral:1h		200	42		832	hit	0.96	TRUE	128	42	-86	3.048				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	control	replay	800	off		200	44		832	hit	0.96	TRUE	128	44	-84	2.909				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	protected	replay	800	ephemeral:1h		200	32		832	hit	0.96	TRUE	291	32	-259	9.094				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	control	replay	1000	off		200	31		832	hit	0.96	TRUE	289	31	-258	9.323				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	protected	replay	1000	ephemeral:1h		200	31		832	hit	0.96	TRUE	290	31	-259	9.355				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_compare	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	compare			ephemeral:1h		complete												missing_runtime_json			missing_runtime_json			not_sent	inconclusive


