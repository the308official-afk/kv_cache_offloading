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
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

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
/usr/local/lib/python3.12/dist-packages/torchao/quantization/quant_api.py:1731: SyntaxWarning: invalid escape sequence '\.'
  """Configuration class for applying different quantization configs to modules or parameters based on their fully qualified names (FQNs).
2026-07-08T23:02:21.409620Z  WARN __init__: dynamo.nixl_connect: Failed to load CuPy for GPU acceleration, utilizing numpy to provide CPU based operations.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.cudart module is deprecated and will be removed in a future release, please switch to use the cuda.bindings.runtime module instead.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.nvrtc module is deprecated and will be removed in a future release, please switch to use the cuda.bindings.nvrtc module instead.
2026-07-08T23:02:24.923511Z  WARN encode_worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
2026-07-08T23:02:24.924077Z  WARN worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
Traceback (most recent call last):
  File "<stdin>", line 3, in <module>
ImportError: cannot import name 'build_parser' from 'dynamo.sglang.main' (/usr/local/lib/python3.12/dist-packages/dynamo/sglang/main.py)
ojaiyeob@gracehopper:~/kv_cache_offloading$ docker logs dynamo-sglang-worker 2>&1 | grep -niE 'kv_events_config|enable-cache-report|cache-report|zmq kv event|Setting up ZMQ kv event subscriber'
32:2026-07-08T22:50:27.932926Z  INFO args.parse_args: Derived use_kv_events=False from kv_events_config=None
37:2026-07-08T22:50:28.153361Z  INFO engine.__init__: server_args=ServerArgs(model_path='Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8', tokenizer_path='Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8', tokenizer_mode='auto', tokenizer_backend='huggingface', tokenizer_worker_num=1, skip_tokenizer_init=False, load_format='auto', model_loader_extra_config='{}', trust_remote_code=False, context_length=None, is_embedding=False, enable_multimodal=None, revision=None, model_impl='auto', host='127.0.0.1', port=30000, fastapi_root_path='', grpc_mode=False, skip_server_warmup=False, warmups=None, nccl_port=None, checkpoint_engine_wait_weights_before_ready=False, ssl_keyfile=None, ssl_certfile=None, ssl_ca_certs=None, ssl_keyfile_password=None, enable_ssl_refresh=False, enable_http2=False, dtype='auto', quantization=None, quantization_param_path=None, kv_cache_dtype='auto', enable_fp32_lm_head=False, modelopt_quant=None, modelopt_checkpoint_restore_path=None, modelopt_checkpoint_save_path=None, modelopt_export_path=None, quantize_and_serve=False, rl_quant_profile=None, mem_fraction_static=0.858, max_running_requests=None, max_queued_requests=None, max_total_tokens=None, chunked_prefill_size=8192, enable_dynamic_chunking=False, max_prefill_tokens=16384, prefill_max_requests=None, schedule_policy='fcfs', enable_priority_scheduling=True, disable_priority_preemption=False, default_priority_value=None, abort_on_priority_when_disabled=False, schedule_low_priority_values_first=False, priority_scheduling_preemption_threshold=10, schedule_conservativeness=1.0, page_size=64, swa_full_tokens_ratio=0.8, disable_hybrid_swa_memory=False, radix_eviction_policy='priority', enable_prefill_delayer=False, prefill_delayer_max_delay_passes=30, prefill_delayer_token_usage_low_watermark=None, prefill_delayer_forward_passes_buckets=None, prefill_delayer_wait_seconds_buckets=None, device='cuda', tp_size=1, pp_size=1, pp_max_micro_batch_size=None, pp_async_batch_depth=0, stream_interval=1, batch_notify_size=16, stream_response_default_include_usage=False, incremental_streaming_output=True, enable_streaming_session=False, random_seed=831733109, constrained_json_whitespace_pattern=None, constrained_json_disable_any_whitespace=False, watchdog_timeout=300, soft_watchdog_timeout=None, dist_timeout=None, download_dir=None, model_checksum=None, base_gpu_id=0, gpu_id_step=1, sleep_on_idle=False, use_ray=False, custom_sigquit_handler=None, log_level='info', log_level_http=None, log_requests=False, log_requests_level=2, log_requests_format='text', log_requests_target=None, uvicorn_access_log_exclude_prefixes=[], crash_dump_folder=None, show_time_cost=False, enable_metrics=False, grpc_http_sidecar_port=None, enable_mfu_metrics=False, enable_metrics_for_all_schedulers=False, tokenizer_metrics_custom_labels_header='x-custom-labels', tokenizer_metrics_allowed_custom_labels=None, extra_metric_labels=None, bucket_time_to_first_token=None, bucket_inter_token_latency=None, bucket_e2e_request_latency=None, prompt_tokens_buckets=None, generation_tokens_buckets=None, gc_warning_threshold_secs=0.0, decode_log_interval=40, enable_request_time_stats_logging=False, kv_events_config=None, enable_trace=False, otlp_traces_endpoint='localhost:4317', export_metrics_to_file=False, export_metrics_to_file_dir=None, api_key=None, admin_api_key=None, served_model_name='Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8', weight_version='default', chat_template=None, hf_chat_template_name=None, completion_template=None, file_storage_path='sglang_storage', enable_cache_report=True, reasoning_parser=None, strip_thinking_cache=False, tool_call_parser=None, tool_server=None, sampling_defaults='model', dp_size=1, load_balance_method='round_robin', attn_cp_size=1, moe_dp_size=1, dist_init_addr=None, nnodes=1, node_rank=0, json_model_override_args='{}', preferred_sampling_params=None, enable_lora=None, enable_lora_overlap_loading=None, max_lora_rank=None, lora_target_modules=None, lora_paths=None, max_loaded_loras=None, max_loras_per_batch=8, lora_eviction_policy='lru', lora_backend='csgmv', max_lora_chunk_size=16, experts_shared_outer_loras=None, lora_use_virtual_experts=False, lora_strict_loading=False, attention_backend='fa3', decode_attention_backend=None, prefill_attention_backend=None, sampling_backend='flashinfer', grammar_backend='xgrammar', mm_attention_backend=None, fp8_gemm_runner_backend='auto', fp4_gemm_runner_backend='auto', nsa_prefill_backend=None, nsa_decode_backend=None, disable_flashinfer_autotune=False, mamba_backend='triton', speculative_algorithm=None, speculative_draft_model_path=None, speculative_draft_model_revision=None, speculative_draft_load_format=None, speculative_num_steps=None, speculative_eagle_topk=None, speculative_num_draft_tokens=None, speculative_dflash_block_size=None, speculative_dflash_draft_window_size=None, speculative_accept_threshold_single=1.0, speculative_accept_threshold_acc=1.0, speculative_token_map=None, speculative_attention_mode='prefill', speculative_draft_attention_backend=None, speculative_moe_runner_backend='auto', speculative_moe_a2a_backend=None, speculative_draft_model_quantization=None, speculative_adaptive=False, speculative_adaptive_config=None, speculative_skip_dp_mlp_sync=False, speculative_ngram_min_bfs_breadth=1, speculative_ngram_max_bfs_breadth=10, speculative_ngram_match_type='BFS', speculative_ngram_max_trie_depth=18, speculative_ngram_capacity=10000000, speculative_ngram_external_corpus_path=None, speculative_ngram_external_sam_budget=0, speculative_ngram_external_corpus_max_tokens=10000000, enable_multi_layer_eagle=False, ep_size=1, moe_a2a_backend='none', moe_runner_backend='auto', record_nolora_graph=True, flashinfer_mxfp4_moe_precision='default', enable_flashinfer_allreduce_fusion=False, enforce_disable_flashinfer_allreduce_fusion=False, enable_aiter_allreduce_fusion=False, deepep_mode='auto', ep_num_redundant_experts=0, ep_dispatch_algorithm=None, init_expert_location='trivial', enable_eplb=False, eplb_algorithm='auto', eplb_rebalance_num_iterations=1000, eplb_rebalance_layers_per_chunk=None, eplb_min_rebalancing_utilization_threshold=1.0, expert_distribution_recorder_mode=None, expert_distribution_recorder_buffer_size=1000, enable_expert_distribution_metrics=False, deepep_config=None, moe_dense_tp_size=None, elastic_ep_backend=None, enable_elastic_expert_backup=False, mooncake_ib_device=None, elastic_ep_rejoin=False, max_mamba_cache_size=None, mamba_ssm_dtype=None, mamba_full_memory_ratio=0.9, mamba_scheduler_strategy='no_buffer', mamba_track_interval=256, linear_attn_backend='triton', linear_attn_decode_backend=None, linear_attn_prefill_backend=None, enable_hierarchical_cache=False, hicache_ratio=2.0, hicache_size=0, hicache_write_policy='write_through', hicache_io_backend='kernel', hicache_mem_layout='layer_first', hicache_storage_backend=None, hicache_storage_prefetch_policy='best_effort', hicache_storage_backend_extra_config=None, enable_hisparse=False, hisparse_config=None, enable_lmcache=False, kt_weight_path=None, kt_method='AMXINT4', kt_cpuinfer=None, kt_threadpool_count=2, kt_num_gpu_experts=None, kt_max_deferred_experts_per_token=None, dllm_algorithm=None, dllm_algorithm_config=None, cpu_offload_gb=0, offload_group_size=-1, offload_num_in_group=1, offload_prefetch_step=1, offload_mode='cpu', enable_mis=False, disable_radix_cache=False, cuda_graph_max_bs=256, cuda_graph_bs=[1, 2, 4, 8, 12, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256], disable_cuda_graph=False, disable_cuda_graph_padding=False, enable_breakable_cuda_graph=False, enable_profile_cuda_graph=False, enable_cudagraph_gc=False, debug_cuda_graph=False, enable_layerwise_nvtx_marker=False, enable_nccl_nvls=False, enable_symm_mem=False, disable_flashinfer_cutlass_moe_fp4_allgather=False, enable_tokenizer_batch_encode=False, disable_tokenizer_batch_decode=False, disable_outlines_disk_cache=False, disable_custom_all_reduce=False, enable_mscclpp=False, enable_torch_symm_mem=False, pre_warm_nccl=False, disable_overlap_schedule=False, enable_mixed_chunk=False, enable_dp_attention=False, enable_dp_attention_local_control_broadcast=False, enable_dp_lm_head=False, enable_two_batch_overlap=False, enable_single_batch_overlap=False, tbo_token_distribution_threshold=0.48, enable_torch_compile=False, disable_piecewise_cuda_graph=False, enforce_piecewise_cuda_graph=False, enable_torch_compile_debug_mode=False, torch_compile_max_bs=32, piecewise_cuda_graph_max_tokens=8192, piecewise_cuda_graph_tokens=[4, 8, 12, 16, 20, 24, 28, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240, 256, 288, 320, 352, 384, 416, 448, 480, 512, 576, 640, 704, 768, 832, 896, 960, 1024, 1280, 1536, 1792, 2048, 2304, 2560, 2816, 3072, 3328, 3584, 3840, 4096, 4608, 5120, 5632, 6144, 6656, 7168, 7680, 8192], piecewise_cuda_graph_compiler='eager', torchao_config='', enable_nan_detection=False, enable_p2p_check=False, triton_attention_reduce_in_fp32=False, triton_attention_num_kv_splits=8, triton_attention_split_tile_size=None, num_continuous_decode_steps=1, delete_ckpt_after_loading=False, enable_memory_saver=False, enable_weights_cpu_backup=False, enable_draft_weights_cpu_backup=False, allow_auto_truncate=False, enable_custom_logit_processor=False, flashinfer_mla_disable_ragged=False, disable_shared_experts_fusion=False, enforce_shared_experts_fusion=False, disable_chunked_prefix_cache=False, disable_fast_image_processor=False, keep_mm_feature_on_device=False, enable_return_hidden_states=False, enable_return_routed_experts=False, scheduler_recv_interval=1, numa_node=None, enable_deterministic_inference=False, rl_on_policy_target=None, enable_attn_tp_input_scattered=False, gc_threshold=None, enable_nsa_prefill_context_parallel=False, nsa_prefill_cp_mode='round-robin-split', enable_fused_qk_norm_rope=False, enable_precise_embedding_interpolation=False, enable_fused_moe_sum_all_reduce=False, enable_prefill_context_parallel=False, prefill_cp_mode='in-seq-split', enable_dynamic_batch_tokenizer=False, dynamic_batch_tokenizer_batch_size=32, dynamic_batch_tokenizer_batch_timeout=0.002, debug_tensor_dump_output_folder=None, debug_tensor_dump_layers=None, debug_tensor_dump_input_file=None, debug_tensor_dump_inject=False, disaggregation_mode='null', disaggregation_transfer_backend='mooncake', disaggregation_bootstrap_port=41573, disaggregation_ib_device=None, disaggregation_decode_enable_radix_cache=False, disaggregation_decode_enable_offload_kvcache=False, num_reserved_decode_tokens=512, disaggregation_decode_polling_interval=1, encoder_only=False, language_only=False, encoder_transfer_backend='zmq_to_scheduler', encoder_urls=[], enable_adaptive_dispatch_to_encoder=False, custom_weight_loader=[], weight_loader_disable_mmap=False, weight_loader_prefetch_checkpoints=False, weight_loader_prefetch_num_threads=4, remote_instance_weight_loader_seed_instance_ip=None, remote_instance_weight_loader_seed_instance_service_port=None, remote_instance_weight_loader_send_weights_group_ports=None, remote_instance_weight_loader_backend='nccl', remote_instance_weight_loader_start_seed_via_transfer_engine=False, engine_info_bootstrap_port=6789, modelexpress_config=None, enable_pdmux=False, pdmux_config_path=None, sm_group_num=8, enable_broadcast_mm_inputs_process=False, enable_prefix_mm_cache=False, mm_enable_dp_encoder=False, mm_process_config={}, limit_mm_data_per_request=None, enable_mm_global_cache=False, decrypted_config_file=None, decrypted_draft_config_file=None, forward_hooks=None, enable_quant_communications=False, msprobe_dump_config=None)
39:2026-07-08T22:50:28.167268Z  INFO engine._launch_subprocesses: server_args=ServerArgs(model_path='Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8', tokenizer_path='Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8', tokenizer_mode='auto', tokenizer_backend='huggingface', tokenizer_worker_num=1, skip_tokenizer_init=False, load_format='auto', model_loader_extra_config='{}', trust_remote_code=False, context_length=None, is_embedding=False, enable_multimodal=None, revision=None, model_impl='auto', host='127.0.0.1', port=30000, fastapi_root_path='', grpc_mode=False, skip_server_warmup=False, warmups=None, nccl_port=None, checkpoint_engine_wait_weights_before_ready=False, ssl_keyfile=None, ssl_certfile=None, ssl_ca_certs=None, ssl_keyfile_password=None, enable_ssl_refresh=False, enable_http2=False, dtype='auto', quantization=None, quantization_param_path=None, kv_cache_dtype='auto', enable_fp32_lm_head=False, modelopt_quant=None, modelopt_checkpoint_restore_path=None, modelopt_checkpoint_save_path=None, modelopt_export_path=None, quantize_and_serve=False, rl_quant_profile=None, mem_fraction_static=0.858, max_running_requests=None, max_queued_requests=None, max_total_tokens=None, chunked_prefill_size=8192, enable_dynamic_chunking=False, max_prefill_tokens=16384, prefill_max_requests=None, schedule_policy='fcfs', enable_priority_scheduling=True, disable_priority_preemption=False, default_priority_value=None, abort_on_priority_when_disabled=False, schedule_low_priority_values_first=False, priority_scheduling_preemption_threshold=10, schedule_conservativeness=1.0, page_size=64, swa_full_tokens_ratio=0.8, disable_hybrid_swa_memory=False, radix_eviction_policy='priority', enable_prefill_delayer=False, prefill_delayer_max_delay_passes=30, prefill_delayer_token_usage_low_watermark=None, prefill_delayer_forward_passes_buckets=None, prefill_delayer_wait_seconds_buckets=None, device='cuda', tp_size=1, pp_size=1, pp_max_micro_batch_size=None, pp_async_batch_depth=0, stream_interval=1, batch_notify_size=16, stream_response_default_include_usage=False, incremental_streaming_output=True, enable_streaming_session=False, random_seed=831733109, constrained_json_whitespace_pattern=None, constrained_json_disable_any_whitespace=False, watchdog_timeout=300, soft_watchdog_timeout=None, dist_timeout=None, download_dir=None, model_checksum=None, base_gpu_id=0, gpu_id_step=1, sleep_on_idle=False, use_ray=False, custom_sigquit_handler=None, log_level='info', log_level_http=None, log_requests=False, log_requests_level=2, log_requests_format='text', log_requests_target=None, uvicorn_access_log_exclude_prefixes=[], crash_dump_folder=None, show_time_cost=False, enable_metrics=False, grpc_http_sidecar_port=None, enable_mfu_metrics=False, enable_metrics_for_all_schedulers=False, tokenizer_metrics_custom_labels_header='x-custom-labels', tokenizer_metrics_allowed_custom_labels=None, extra_metric_labels=None, bucket_time_to_first_token=None, bucket_inter_token_latency=None, bucket_e2e_request_latency=None, prompt_tokens_buckets=None, generation_tokens_buckets=None, gc_warning_threshold_secs=0.0, decode_log_interval=40, enable_request_time_stats_logging=False, kv_events_config=None, enable_trace=False, otlp_traces_endpoint='localhost:4317', export_metrics_to_file=False, export_metrics_to_file_dir=None, api_key=None, admin_api_key=None, served_model_name='Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8', weight_version='default', chat_template=None, hf_chat_template_name=None, completion_template=None, file_storage_path='sglang_storage', enable_cache_report=True, reasoning_parser=None, strip_thinking_cache=False, tool_call_parser=None, tool_server=None, sampling_defaults='model', dp_size=1, load_balance_method='round_robin', attn_cp_size=1, moe_dp_size=1, dist_init_addr=None, nnodes=1, node_rank=0, json_model_override_args='{}', preferred_sampling_params=None, enable_lora=None, enable_lora_overlap_loading=None, max_lora_rank=None, lora_target_modules=None, lora_paths=None, max_loaded_loras=None, max_loras_per_batch=8, lora_eviction_policy='lru', lora_backend='csgmv', max_lora_chunk_size=16, experts_shared_outer_loras=None, lora_use_virtual_experts=False, lora_strict_loading=False, attention_backend='fa3', decode_attention_backend=None, prefill_attention_backend=None, sampling_backend='flashinfer', grammar_backend='xgrammar', mm_attention_backend=None, fp8_gemm_runner_backend='auto', fp4_gemm_runner_backend='auto', nsa_prefill_backend=None, nsa_decode_backend=None, disable_flashinfer_autotune=False, mamba_backend='triton', speculative_algorithm=None, speculative_draft_model_path=None, speculative_draft_model_revision=None, speculative_draft_load_format=None, speculative_num_steps=None, speculative_eagle_topk=None, speculative_num_draft_tokens=None, speculative_dflash_block_size=None, speculative_dflash_draft_window_size=None, speculative_accept_threshold_single=1.0, speculative_accept_threshold_acc=1.0, speculative_token_map=None, speculative_attention_mode='prefill', speculative_draft_attention_backend=None, speculative_moe_runner_backend='auto', speculative_moe_a2a_backend=None, speculative_draft_model_quantization=None, speculative_adaptive=False, speculative_adaptive_config=None, speculative_skip_dp_mlp_sync=False, speculative_ngram_min_bfs_breadth=1, speculative_ngram_max_bfs_breadth=10, speculative_ngram_match_type='BFS', speculative_ngram_max_trie_depth=18, speculative_ngram_capacity=10000000, speculative_ngram_external_corpus_path=None, speculative_ngram_external_sam_budget=0, speculative_ngram_external_corpus_max_tokens=10000000, enable_multi_layer_eagle=False, ep_size=1, moe_a2a_backend='none', moe_runner_backend='auto', record_nolora_graph=True, flashinfer_mxfp4_moe_precision='default', enable_flashinfer_allreduce_fusion=False, enforce_disable_flashinfer_allreduce_fusion=False, enable_aiter_allreduce_fusion=False, deepep_mode='auto', ep_num_redundant_experts=0, ep_dispatch_algorithm=None, init_expert_location='trivial', enable_eplb=False, eplb_algorithm='auto', eplb_rebalance_num_iterations=1000, eplb_rebalance_layers_per_chunk=None, eplb_min_rebalancing_utilization_threshold=1.0, expert_distribution_recorder_mode=None, expert_distribution_recorder_buffer_size=1000, enable_expert_distribution_metrics=False, deepep_config=None, moe_dense_tp_size=None, elastic_ep_backend=None, enable_elastic_expert_backup=False, mooncake_ib_device=None, elastic_ep_rejoin=False, max_mamba_cache_size=None, mamba_ssm_dtype=None, mamba_full_memory_ratio=0.9, mamba_scheduler_strategy='no_buffer', mamba_track_interval=256, linear_attn_backend='triton', linear_attn_decode_backend=None, linear_attn_prefill_backend=None, enable_hierarchical_cache=False, hicache_ratio=2.0, hicache_size=0, hicache_write_policy='write_through', hicache_io_backend='kernel', hicache_mem_layout='layer_first', hicache_storage_backend=None, hicache_storage_prefetch_policy='best_effort', hicache_storage_backend_extra_config=None, enable_hisparse=False, hisparse_config=None, enable_lmcache=False, kt_weight_path=None, kt_method='AMXINT4', kt_cpuinfer=None, kt_threadpool_count=2, kt_num_gpu_experts=None, kt_max_deferred_experts_per_token=None, dllm_algorithm=None, dllm_algorithm_config=None, cpu_offload_gb=0, offload_group_size=-1, offload_num_in_group=1, offload_prefetch_step=1, offload_mode='cpu', enable_mis=False, disable_radix_cache=False, cuda_graph_max_bs=256, cuda_graph_bs=[1, 2, 4, 8, 12, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160, 168, 176, 184, 192, 200, 208, 216, 224, 232, 240, 248, 256], disable_cuda_graph=False, disable_cuda_graph_padding=False, enable_breakable_cuda_graph=False, enable_profile_cuda_graph=False, enable_cudagraph_gc=False, debug_cuda_graph=False, enable_layerwise_nvtx_marker=False, enable_nccl_nvls=False, enable_symm_mem=False, disable_flashinfer_cutlass_moe_fp4_allgather=False, enable_tokenizer_batch_encode=False, disable_tokenizer_batch_decode=False, disable_outlines_disk_cache=False, disable_custom_all_reduce=False, enable_mscclpp=False, enable_torch_symm_mem=False, pre_warm_nccl=False, disable_overlap_schedule=False, enable_mixed_chunk=False, enable_dp_attention=False, enable_dp_attention_local_control_broadcast=False, enable_dp_lm_head=False, enable_two_batch_overlap=False, enable_single_batch_overlap=False, tbo_token_distribution_threshold=0.48, enable_torch_compile=False, disable_piecewise_cuda_graph=False, enforce_piecewise_cuda_graph=False, enable_torch_compile_debug_mode=False, torch_compile_max_bs=32, piecewise_cuda_graph_max_tokens=8192, piecewise_cuda_graph_tokens=[4, 8, 12, 16, 20, 24, 28, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240, 256, 288, 320, 352, 384, 416, 448, 480, 512, 576, 640, 704, 768, 832, 896, 960, 1024, 1280, 1536, 1792, 2048, 2304, 2560, 2816, 3072, 3328, 3584, 3840, 4096, 4608, 5120, 5632, 6144, 6656, 7168, 7680, 8192], piecewise_cuda_graph_compiler='eager', torchao_config='', enable_nan_detection=False, enable_p2p_check=False, triton_attention_reduce_in_fp32=False, triton_attention_num_kv_splits=8, triton_attention_split_tile_size=None, num_continuous_decode_steps=1, delete_ckpt_after_loading=False, enable_memory_saver=False, enable_weights_cpu_backup=False, enable_draft_weights_cpu_backup=False, allow_auto_truncate=False, enable_custom_logit_processor=False, flashinfer_mla_disable_ragged=False, disable_shared_experts_fusion=False, enforce_shared_experts_fusion=False, disable_chunked_prefix_cache=False, disable_fast_image_processor=False, keep_mm_feature_on_device=False, enable_return_hidden_states=False, enable_return_routed_experts=False, scheduler_recv_interval=1, numa_node=None, enable_deterministic_inference=False, rl_on_policy_target=None, enable_attn_tp_input_scattered=False, gc_threshold=None, enable_nsa_prefill_context_parallel=False, nsa_prefill_cp_mode='round-robin-split', enable_fused_qk_norm_rope=False, enable_precise_embedding_interpolation=False, enable_fused_moe_sum_all_reduce=False, enable_prefill_context_parallel=False, prefill_cp_mode='in-seq-split', enable_dynamic_batch_tokenizer=False, dynamic_batch_tokenizer_batch_size=32, dynamic_batch_tokenizer_batch_timeout=0.002, debug_tensor_dump_output_folder=None, debug_tensor_dump_layers=None, debug_tensor_dump_input_file=None, debug_tensor_dump_inject=False, disaggregation_mode='null', disaggregation_transfer_backend='mooncake', disaggregation_bootstrap_port=41573, disaggregation_ib_device=None, disaggregation_decode_enable_radix_cache=False, disaggregation_decode_enable_offload_kvcache=False, num_reserved_decode_tokens=512, disaggregation_decode_polling_interval=1, encoder_only=False, language_only=False, encoder_transfer_backend='zmq_to_scheduler', encoder_urls=[], enable_adaptive_dispatch_to_encoder=False, custom_weight_loader=[], weight_loader_disable_mmap=False, weight_loader_prefetch_checkpoints=False, weight_loader_prefetch_num_threads=4, remote_instance_weight_loader_seed_instance_ip=None, remote_instance_weight_loader_seed_instance_service_port=None, remote_instance_weight_loader_send_weights_group_ports=None, remote_instance_weight_loader_backend='nccl', remote_instance_weight_loader_start_seed_via_transfer_engine=False, engine_info_bootstrap_port=6789, modelexpress_config=None, enable_pdmux=False, pdmux_config_path=None, sm_group_num=8, enable_broadcast_mm_inputs_process=False, enable_prefix_mm_cache=False, mm_enable_dp_encoder=False, mm_process_config={}, limit_mm_data_per_request=None, enable_mm_global_cache=False, decrypted_config_file=None, decrypted_draft_config_file=None, forward_hooks=None, enable_quant_communications=False, msprobe_dump_config=None)
ojaiyeob@gracehopper:~/kv_cache_offloading$ docker exec -i dynamo-sglang-worker sh -lc 'ps -ef | grep "python3 -m dynamo.sglang" | grep -v grep'
dynamo         1       0  7 22:44 ?        00:01:22 python3 -m dynamo.sglang --model-path Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 --discovery-backend etcd --page-size 64 --enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority
ojaiyeob@gracehopper:~/kv_cache_offloading$

```
