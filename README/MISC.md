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
ojaiyeob@gracehopper:~/kv_cache_offloading$ DYNAMO_MACHINE_PROFILE=gh200 PRECISE_START_MODE=clean PRIORITY_SCHEDULING_MODE=all EXPERIMENT_RESET_MODE=flush PRIORITY_SCHEDULING_SWEEP_AXIS=PRIORITY_ARRIVAL_GAP_MS PRIORITY_SCHEDULING_SWEEP_VALUES="50 100 200 400" LOW_PRIORITY_COUNT=8 HIGH_PRIORITY_COUNT=4 PRIORITY_INPUT_LEN=4000 PRIORITY_OUTPUT_LEN=128 PRIORITY_INTER_REQUEST_GAP_MS=20 ./agentbench/run_priority_scheduling_microbenchmark_single_host.sh   Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
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
  retention_prompt_isolation_mode=strict
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
Priority scheduling run ID: priority_scheduling_microbenchmark_20260709_054713__sweep_1
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
Driver log: experiments/reports/priority_scheduling/priority_scheduling_microbenchmark_20260709_054713__sweep_1/priority_scheduling_driver.log
Smoke log: experiments/reports/priority_scheduling/priority_scheduling_microbenchmark_20260709_054713__sweep_1/priority_scheduling_smoke_test.log
Worker runtime log: experiments/reports/priority_scheduling/priority_scheduling_microbenchmark_20260709_054713__sweep_1/priority_scheduling_worker_runtime.log

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
  DYN_RUNTIME_JSON_LOGS=1
  SGLANG_TRANSFER_LOG_PROFILE=full
  SGLANG_TRANSFER_LOG=1
  SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=
/usr/local/lib/python3.12/dist-packages/torchao/quantization/quant_api.py:1731: SyntaxWarning: invalid escape sequence '\.'
  """Configuration class for applying different quantization configs to modules or parameters based on their fully qualified names (FQNs).
2026-07-09T05:58:28.692059Z  WARN __init__: dynamo.nixl_connect: Failed to load CuPy for GPU acceleration, utilizing numpy to provide CPU based operations.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.cudart module is deprecated and will be removed in a future release, please switch to use the cuda.bindings.runtime module instead.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.nvrtc module is deprecated and will be removed in a future release, please switch to use the cuda.bindings.nvrtc module instead.
2026-07-09T05:58:32.386294Z  WARN encode_worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
2026-07-09T05:58:32.386882Z  WARN worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
Dynamo decode handler markers: {"attach_logged = False": true, "path": "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/request_handlers/llm/decode_handler.py", "request: Dict[str, Any]": true, "worker.decode.request_attached": true}
========================================
(4/6) PRECISE ATTRIBUTION CHECK FAILED (the live running worker is missing required instrumentation)
========================================
FAIL: worker SGLang priority markers are missing
ojaiyeob@gracehopper:~/kv_cache_offloading$
```
