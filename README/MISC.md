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
