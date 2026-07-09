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
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
PRIORITY_SCHEDULING_MODE=all \
EXPERIMENT_RESET_MODE=flush \
PRIORITY_SCHEDULING_SWEEP_AXIS=PRIORITY_ARRIVAL_GAP_MS \
PRIORITY_SCHEDULING_SWEEP_VALUES="50 100 200 400" \
LOW_PRIORITY_COUNT=8 \
HIGH_PRIORITY_COUNT=4 \
PRIORITY_INPUT_LEN=4000 \
PRIORITY_OUTPUT_LEN=128 \
PRIORITY_INTER_REQUEST_GAP_MS=20 \
./agentbench/run_priority_scheduling_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
========================================
EXPERIMENT DIRS READY (raw/report/chart/runtime directories exist and are writable)
========================================
  /home/central/ojaiyeob/kv_cache_offloading/experiments/raw/sglang_transfer_logs
  /home/central/ojaiyeob/kv_cache_offloading/experiments/raw/lpx_decode_split/profiles
  /home/central/ojaiyeob/kv_cache_offloading/experiments/raw/agentbench/results
  /home/central/ojaiyeob/kv_cache_offloading/experiments/raw/agentbench/diagnostics
  /home/central/ojaiyeob/kv_cache_offloading/experiments/reports
  /home/central/ojaiyeob/kv_cache_offloading/experiments/charts
  /home/central/ojaiyeob/kv_cache_offloading/experiments/runtime_state
========================================
PRIORITY SCHEDULING MICROBENCH CONTRACT
========================================
Contract file: contracts/priority_scheduling_microbenchmark.contract.sh
Contract doc: contracts/priority_scheduling_microbenchmark.contract.md
Mode: all
Model: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Machine profile: gh200

Public wrapper:
  /home/central/ojaiyeob/kv_cache_offloading/agentbench/run_priority_scheduling_microbenchmark_single_host.sh

Internal helper:
  probe=/home/central/ojaiyeob/kv_cache_offloading/agentbench/run_priority_scheduling_probe_single_host.sh

Runtime stack:
  dynamo_source_dir=/home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo
  sglang_source_image=lmsysorg/sglang:v0.5.11-cu129-runtime
  sglang_source_dir=/home/central/ojaiyeob/kv_cache_offloading/upstream/sglang
  frontend_image=local/dynamo-frontend:runtime-json-logs-gh200
  worker_image=local/dynamo-sglang:runtime-json-logs-gh200

Workload defaults:
  low_priority_count=8
  high_priority_count=4
  low_priority_value=1
  high_priority_value=10
  input_len_words=4000
  output_len_tokens=128
  arrival_gap_ms=200
  inter_request_gap_ms=20
  sweep_axis=PRIORITY_ARRIVAL_GAP_MS
  sweep_values=50 100 200 400

Runtime defaults:
  attribution_mode=precise
  request_context_mode=auto
  top_level_priority_mode=auto
  experiment_reset_mode=flush
  transfer_log_profile=full
  worker_base_args=--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority
  probe_seed=42
  sweep_seed_mode=fixed
========================================
PRECISE CLEAN START ACTIVE (clearing any old runtime before Priority scheduling microbenchmark)
========================================
========================================
PRECISE CLEAN START READY (old runtime cleared before Priority scheduling microbenchmark)
========================================
========================================
PRIORITY SCHEDULING MICROBENCH SWEEP
========================================
Sweep axis: PRIORITY_ARRIVAL_GAP_MS
Sweep values: 50 100 200 400
[1/4] PRIORITY_ARRIVAL_GAP_MS=50 priority_probe_seed=42
Ensuring machine-specific precise runtime images...
Using machine profile: gh200
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs-gh200
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs-gh200
frontend image ok
worker image ok
========================================
(1/6) PRECISE RUNTIME IMAGE READY (the machine-specific Dynamo images are there)
========================================
Reusing extracted SGLang source root: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang
Refreshing SGLang transfer logging patch for precise priority attribution...
========================================
(2/6) PRECISE LOCAL READY (the local extracted/patched SGLang source is good)
========================================
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
SGLang root: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang
Local transfer markers: ok
Local priority markers: ok
Ready to start Dynamo: yes
Priority scheduling run ID: priority_scheduling_microbenchmark_20260709_052438__sweep_1
Model: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
Attribution mode: precise
Low-priority count: 8
High-priority count: 4
Input length words: 4000
Output length tokens: 128
Arrival gap ms: 50
Inter-request gap ms: 20
Top-level priority mode: auto
Request-context mode: auto
Driver log: experiments/reports/priority_scheduling/priority_scheduling_microbenchmark_20260709_052438__sweep_1/priority_scheduling_driver.log
Smoke log: experiments/reports/priority_scheduling/priority_scheduling_microbenchmark_20260709_052438__sweep_1/priority_scheduling_smoke_test.log
Worker runtime log: experiments/reports/priority_scheduling/priority_scheduling_microbenchmark_20260709_052438__sweep_1/priority_scheduling_worker_runtime.log

Stopping Dynamo...
========================================
(3/6) MODEL READINESS ACTIVE (extended model wait and smoke timing are active)
========================================
MODEL_READY_RETRIES=900
MODEL_READY_DELAY_SECS=3
MODEL_READY_STABLE_HITS=2
MODEL_SMOKE_RETRIES=180
MODEL_SMOKE_DELAY_SECS=15
MODEL_COOLDOWN_SECS=60
Starting Dynamo for Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8...
Smoke test 1/180 for Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Smoke test passed for Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Running precise priority-attribution preflight...
Local SGLang transfer markers: ok (/home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang)
Local SGLang priority markers: ok (/home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang)
Worker container running: dynamo-sglang-worker
Worker overlay mount: ok
Worker env markers:
  SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=
  DYN_RUNTIME_JSON_LOGS=1
  SGLANG_TRANSFER_LOG=1
  SGLANG_TRANSFER_LOG_PROFILE=full
/usr/local/lib/python3.12/dist-packages/torchao/quantization/quant_api.py:1731: SyntaxWarning: invalid escape sequence '\.'
  """Configuration class for applying different quantization configs to modules or parameters based on their fully qualified names (FQNs).
2026-07-09T05:39:28.975550Z  WARN __init__: dynamo.nixl_connect: Failed to load CuPy for GPU acceleration, utilizing numpy to provide CPU based operations.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.cudart module is deprecated and will be removed in a future release, please switch to use the cuda.bindings.run         time module instead.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.nvrtc module is deprecated and will be removed in a future release, please switch to use the cuda.bindings.nvrt         c module instead.
2026-07-09T05:39:32.643071Z  WARN encode_worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
2026-07-09T05:39:32.643638Z  WARN worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
Dynamo decode handler markers: {"attach_logged = False": true, "path": "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/request_handlers/llm/decode_handler.py", "request: Dic         t[str, Any]": true, "worker.decode.request_attached": true}
========================================
(4/6) PRECISE ATTRIBUTION CHECK FAILED (the live running worker is missing required instrumentation)
========================================
FAIL: worker SGLang priority markers are missing
ojaiyeob@gracehopper:~/kv_cache_offloading$

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



```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
SGLANG_TRANSFER_LOG=1 \
SGLANG_TRANSFER_LOG_PROFILE=full \
DYNAMO_MODEL_PATH="Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8" \
DYNAMO_SERVED_MODEL_NAME="Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8" \
./run_dynamo_single_host.sh start
```



```bash
cd ~/kv_cache_offloading

docker exec -i dynamo-sglang-worker python3 - <<'PY'
from pathlib import Path
import inspect
import json

out = {}

def read_text(path_str):
    p = Path(path_str)
    out[path_str] = {"exists": p.exists()}
    if not p.exists():
        return None
    try:
        text = p.read_text()
        out[path_str]["readable"] = True
        return text
    except Exception as e:
        out[path_str]["readable"] = False
        out[path_str]["error"] = repr(e)
        return None

handler_path = "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/request_handlers/handler_base.py"
publisher_path = "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/publisher.py"
kv_rust_path = "/usr/local/lib/python3.12/dist-packages/dynamo/lib/bindings/python/rust/llm/kv.rs"

handler_text = read_text(handler_path)
publisher_text = read_text(publisher_path)
kv_rust_text = read_text(kv_rust_path)

if handler_text is not None:
    out[handler_path]["markers"] = {
        "self.kv_publishers": "self.kv_publishers" in handler_text,
        "self.kv_publisher": "self.kv_publisher" in handler_text,
        "publish_cleared()": "publish_cleared()" in handler_text,
        "kv_clear_event_status": "kv_clear_event_status" in handler_text,
        'register_engine_route("clear_kv_blocks"': 'register_engine_route("clear_kv_blocks"' in handler_text,
        'call_tokenizer_manager({"method": "flush_cache"})': 'call_tokenizer_manager({"method": "flush_cache"})' in handler_text,
    }

if publisher_text is not None:
    out[publisher_path]["markers"] = {
        "self.kv_publishers": "self.kv_publishers" in publisher_text,
        "self.kv_publisher": "self.kv_publisher" in publisher_text,
        "return self.kv_publishers": "return self.kv_publishers" in publisher_text,
    }

if kv_rust_text is not None:
    out[kv_rust_path]["markers"] = {
        "fn publish_cleared": "fn publish_cleared" in kv_rust_text,
        "KvCacheEventData::Cleared": "KvCacheEventData::Cleared" in kv_rust_text,
    }

so_files = sorted(str(p) for p in Path("/usr/local/lib/python3.12/dist-packages/dynamo").glob("_core*.so"))
out["compiled_core"] = {
    "count": len(so_files),
    "files": so_files,
}

try:
    from dynamo.sglang.request_handlers import handler_base
    src = inspect.getsource(handler_base.WorkerHandlerBase.clear_kv_blocks)
    out["live_python_method"] = {
        "loaded": True,
        "publish_cleared()": "publish_cleared()" in src,
        "kv_clear_event_status": "kv_clear_event_status" in src,
        "flush_cache": "flush_cache" in src,
    }
except Exception as e:
    out["live_python_method"] = {
        "loaded": False,
        "error": repr(e),
    }

print(json.dumps(out, indent=2, sort_keys=True))
PY
```


```bash
/usr/local/lib/python3.12/dist-packages/torchao/quantization/quant_api.py:1731: SyntaxWarning: invalid escape sequence '\.'
  """Configuration class for applying different quantization configs to modules or parameters based on their fully qualified names (FQNs).
2026-07-08T22:55:41.164291Z  WARN __init__: dynamo.nixl_connect: Failed to load CuPy for GPU acceleration, utilizing numpy to provide CPU based operations.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.cudart module is deprecated and will be removed in a future release, please switch to use the cuda.bindings.runtime module instead.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.nvrtc module is deprecated and will be removed in a future release, please switch to use the cuda.bindings.nvrtc module instead.
2026-07-08T22:55:44.734711Z  WARN encode_worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
2026-07-08T22:55:44.735262Z  WARN worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
{
  "/usr/local/lib/python3.12/dist-packages/dynamo/lib/bindings/python/rust/llm/kv.rs": {
    "exists": false
  },
  "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/publisher.py": {
    "exists": true,
    "markers": {
      "return self.kv_publishers": true,
      "self.kv_publisher": true,
      "self.kv_publishers": true
    },
    "readable": true
  },
  "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/request_handlers/handler_base.py": {
    "exists": true,
    "markers": {
      "call_tokenizer_manager({\"method\": \"flush_cache\"})": true,
      "kv_clear_event_status": true,
      "publish_cleared()": true,
      "register_engine_route(\"clear_kv_blocks\"": true,
      "self.kv_publisher": true,
      "self.kv_publishers": true
    },
    "readable": true
  },
  "compiled_core": {
    "count": 1,
    "files": [
      "/usr/local/lib/python3.12/dist-packages/dynamo/_core.abi3.so"
    ]
  },
  "live_python_method": {
    "error": "AttributeError(\"module 'dynamo.sglang.request_handlers.handler_base' has no attribute 'WorkerHandlerBase'\")",
    "loaded": false
  }
}
ojaiyeob@gracehopper:~/kv_cache_offloading$
```


```bash
cd ~/kv_cache_offloading

docker exec -i dynamo-sglang-worker python3 - <<'PY'
from pathlib import Path
import json

paths = [
    "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/init_llm.py",
    "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/publisher.py",
    "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/request_handlers/handler_base.py",
]

checks = {
    "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/init_llm.py": [
        "clear_kv_blocks_endpoint = runtime.endpoint(",
        "clear_kv_blocks_endpoint.serve_endpoint(",
        "publisher =",
        "handler =",
    ],
    "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/publisher.py": [
        "self.kv_publishers = []",
        "self.kv_publisher = self.kv_publishers[0] if self.kv_publishers else None",
        "return self.kv_publishers",
        "KvEventPublisher(",
    ],
    "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/request_handlers/handler_base.py": [
        "self.kv_publishers = list(getattr(publisher, \"kv_publishers\", []) or [])",
        "self.kv_publisher = publisher.kv_publisher",
        "publish_cleared()",
    ],
}

out = {}
for path in paths:
    p = Path(path)
    text = p.read_text() if p.exists() else ""
    out[path] = {
        "exists": p.exists(),
        "markers": {marker: (marker in text) for marker in checks[path]},
    }

print(json.dumps(out, indent=2, sort_keys=True))
PY
```

```bash
docker logs dynamo-sglang-worker 2>&1 | grep -niE 'kv_publisher|kv_publishers|cache report|publisher'
```

```bash
cd ~/kv_cache_offloading

docker exec -i dynamo-sglang-worker python3 - <<'PY'
import json
from dynamo.sglang.args import Config
from dynamo.sglang.main import build_parser

parser = build_parser()
args = parser.parse_args([])

out = {
    "parsed_default_enable_cache_report": getattr(args, "enable_cache_report", None),
    "parsed_default_kv_events_config": getattr(args, "kv_events_config", None),
}
print(json.dumps(out, indent=2, sort_keys=True))
PY
```

```bash
docker logs dynamo-sglang-worker 2>&1 | grep -niE 'kv_events_config|enable-cache-report|cache-report|zmq kv event|Setting up ZMQ kv event subscriber'
```

```bash
docker exec -i dynamo-sglang-worker sh -lc 'ps -ef | grep "python3 -m dynamo.sglang" | grep -v grep'
```


```bash
cd ~/kv_cache_offloading

RUN_PREFIX="kv_retention_microbenchmark_20260708_231032__sweep"

python3 - <<'PY'
from pathlib import Path
import csv

run_prefix = "kv_retention_microbenchmark_20260708_231032__sweep"
root = Path("experiments/reports/retention_probe")

print("cell\thint_profile\tprompt_hash\tlatency_ms\tcached_prompt_tokens\tcache_reuse_ratio\tstatus")
for path in sorted(root.glob(f"{run_prefix}*/retention_probe_requests.csv")):
    with path.open() as f:
        for row in csv.DictReader(f):
            if row["request_role"] == "a_first":
                print(
                    f"{path.parent.name}\t{row['hint_profile']}\t{row['prompt_hash']}\t"
                    f"{row['latency_ms']}\t{row['cached_prompt_tokens']}\t"
                    f"{row['cache_reuse_ratio']}\t{row['status']}"
                )
PY
```

```bash
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

RUN_PREFIX="kv_retention_microbenchmark_20260708_231032__sweep"

python3 - <<'PY'
from pathlib import Path
import csv

run_prefix = "kv_retention_microbenchmark_20260708_231032__sweep"
root = Path("experiments/reports/retention_probe")

print("cell\thint_profile\tprompt_hash\tlatency_ms\tcached_prompt_tokens\tcache_reuse_ratio\tstatus")
for path in sorted(root.glob(f"{run_prefix}*/retention_probe_requests.csv")):
    with path.open() as f:
        for row in csv.DictReader(f):
            if row["request_role"] == "a_first":
                print(
                    f"{path.parent.name}\t{row['hint_profile']}\t{row['prompt_hash']}\t"
                    f"{row['latency_ms']}\t{row['cached_prompt_tokens']}\t"
                    f"{row['cache_reuse_ratio']}\t{row['status']}"
                )
PY
cell    hint_profile    prompt_hash     latency_ms      cached_prompt_tokens    cache_reuse_ratio       status
kv_retention_microbenchmark_20260708_231032__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d100_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__high-priority__off_   high-priority       aa0e63e437e0803e        71                      200
kv_retention_microbenchmark_20260708_231032__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d100_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__none__off__control    noneaa0e63e437e0803e        296                     200
kv_retention_microbenchmark_20260708_231032__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d200_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__high-priority__off_   high-priority       0d8590e6919608d0        74                      200
kv_retention_microbenchmark_20260708_231032__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d200_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__none__off__control    none0d8590e6919608d0        71                      200
ojaiyeob@gracehopper:~/kv_cache_offloading$

```


```bash
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

RUN_PREFIX="kv_retention_microbenchmark_20260708_231032__sweep"

python3 - <<'PY'
from pathlib import Path
import csv

run_prefix = "kv_retention_microbenchmark_20260708_231032__sweep"
root = Path("experiments/reports/retention_probe")

print("cell\thint_profile\tprompt_hash\tlatency_ms\tcached_prompt_tokens\tcache_reuse_ratio\tstatus")
for path in sorted(root.glob(f"{run_prefix}*/retention_probe_requests.csv")):
    with path.open() as f:
        for row in csv.DictReader(f):
            if row["request_role"] == "a_first":
                print(
                    f"{path.parent.name}\t{row['hint_profile']}\t{row['prompt_hash']}\t"
                    f"{row['latency_ms']}\t{row['cached_prompt_tokens']}\t"
                    f"{row['cache_reuse_ratio']}\t{row['status']}"
                )
PY
cell    hint_profile    prompt_hash     latency_ms      cached_prompt_tokens    cache_reuse_ratio       status
kv_retention_microbenchmark_20260708_231032__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d100_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__high-priority__off_   high-priority       aa0e63e437e0803e        71                      200
kv_retention_microbenchmark_20260708_231032__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d100_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__none__off__control    noneaa0e63e437e0803e        296                     200
kv_retention_microbenchmark_20260708_231032__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d200_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__high-priority__off_   high-priority       0d8590e6919608d0        74                      200
kv_retention_microbenchmark_20260708_231032__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d200_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__none__off__control    none0d8590e6919608d0        71                      200
ojaiyeob@gracehopper:~/kv_cache_offloading$

```
