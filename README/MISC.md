

```bash
ojaiyeob@gracehopper:~/kv_cache_offloading$ ./run_dynamo_single_host.sh stop || true
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
KV_RETENTION_MODE=sweep \
RETENTION_REQUEST_SOURCE=swebench_dataset \
RETENTION_SWEBENCH_DATASET=ScaleAI/SWE-bench_Pro \
RETENTION_SWEBENCH_SPLIT=test \
RETENTION_SWEBENCH_INDEX=0 \
KV_RETENTION_RESET_MODE=restart \
DISTRACTOR_COUNTS="800" \
PROTECTED_HINT_PROFILES="high-priority" \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
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
KV RETENTION MICROBENCH CONTRACT
========================================
Contract file: contracts/kv_retention_microbenchmark.contract.sh
Contract doc: contracts/kv_retention_microbenchmark.contract.md
Mode: sweep
Model: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Machine profile: gh200
Schema version: 1

Public wrapper:
  /home/central/ojaiyeob/kv_cache_offloading/agentbench/run_kv_retention_microbenchmark_single_host.sh

Internal helpers:
  probe=/home/central/ojaiyeob/kv_cache_offloading/agentbench/run_kv_retention_probe_single_host.sh
  sweep=/home/central/ojaiyeob/kv_cache_offloading/agentbench/run_kv_retention_threshold_sweep_single_host.sh

Runtime stack:
  dynamo_source_dir=/home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo
  sglang_source_image=lmsysorg/sglang:v0.5.11-cu129-runtime
  sglang_source_dir=/home/central/ojaiyeob/kv_cache_offloading/upstream/sglang
  frontend_image=local/dynamo-frontend:runtime-json-logs-gh200
  worker_image=local/dynamo-sglang:runtime-json-logs-gh200

Control defaults:
  control_hint=none
  protected_hints=high-priority
  control_cache_control=off
  protected_cache_control=off

Workload defaults:
  request_source=swebench_dataset
  swebench_dataset=ScaleAI/SWE-bench_Pro
  swebench_split=test
  swebench_index=0
  swebench_instance_id=
  swebench_distractor_start_index=-1
  swebench_allow_distractor_reuse=0
  kv_tier_modes=gpu_only
  distractor_count=100
  distractor_counts=800
  protected_input_len=14000
  distractor_input_len=14000
  random_output_len=1
  prompt_isolation_mode=disjoint
  max_context_tokens=17146

Runtime defaults:
  attribution_mode=precise
  request_context_mode=auto
  top_level_priority_mode=auto
  experiment_reset_mode=restart
  transfer_log_profile=full
  worker_base_args=--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority

Readiness defaults:
  MODEL_READY_RETRIES=900
  MODEL_READY_DELAY_SECS=3
  MODEL_READY_STABLE_HITS=2
  MODEL_SMOKE_RETRIES=180
  MODEL_SMOKE_DELAY_SECS=15
  MODEL_COOLDOWN_SECS=60
========================================
PRECISE CLEAN START ACTIVE (clearing any old runtime before KV retention microbenchmark)
========================================
========================================
PRECISE CLEAN START READY (old runtime cleared before KV retention microbenchmark)
========================================
========================================
KV RETENTION MICROBENCH SWEEP
========================================
Retention threshold sweep ID: kv_retention_microbenchmark_20260713_065643__sweep
Attribution mode: precise
Models: 1
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
KV tier modes: gpu_only
Control hint profile: none
Protected hint profiles: high-priority
Control cache-control profile: off
Protected cache-control profiles: off
Request source: swebench_dataset
SWE-bench dataset: ScaleAI/SWE-bench_Pro
SWE-bench split: test
SWE-bench protected index: 0
SWE-bench protected instance_id: auto
SWE-bench distractor start index: -1
SWE-bench distractor reuse allowed: 0
Distractor counts: 800
Retention probe seed: 42
Retention sweep seed mode: per_cell
Retention prompt isolation mode: disjoint
Protected input len: 14000
Distractor input len: 14000
Random output len: 1
Max context tokens: 17146
Context reserve tokens: 2048
GPU-only mem fraction static: 0.7
Default cache-control TTL: 1h
SGLang transfer log profile: full
Output dir: experiments/reports/retention_threshold_sweeps/kv_retention_microbenchmark_20260713_065643__sweep

===== Sweep cell =====
model=Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
kv_tier_mode=gpu_only
distractor_count=800
retention_probe_seed=1842
retention_probe_id=kv_retention_microbenchmark_20260713_065643__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d800
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
Refreshing SGLang transfer logging patch for precise KV attribution...
memory_pool_host: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
transfer_logging: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/mem_cache/transfer_logging.py
no transfer functions patched; they may already be instrumented or absent
hiradix_cache: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
no HiRadix semantic/cache functions patched; they may already be instrumented or absent
cache_controller: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/managers/cache_controller.py
no cache-controller propagation patched; it may already be instrumented or unsupported
radix_cache: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/mem_cache/radix_cache.py
no radix-cache request context patched; it may already be instrumented or unsupported
schedule_batch: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/managers/schedule_batch.py
no schedule-batch request context patched; it may already be instrumented or unsupported
schedule_policy: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/managers/schedule_policy.py
no schedule-policy request context patched; it may already be instrumented or unsupported
========================================
(2/6) PRECISE LOCAL READY (the local extracted/patched SGLang source is good)
========================================
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
SGLang root: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang
Local transfer markers: ok
Ready to start Dynamo: yes
Retention probe ID: kv_retention_microbenchmark_20260713_065643__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d800
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
Attribution mode: precise
Models: 1
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
KV tier modes: gpu_only
Control hint profile: none
Protected hint profiles: high-priority
Control cache-control profile: off
Protected cache-control profiles: off
Distractor cache-control profile: off
Request source: swebench_dataset
SWE-bench dataset: ScaleAI/SWE-bench_Pro
SWE-bench split: test
SWE-bench protected index: 0
SWE-bench protected instance_id: auto
SWE-bench distractor start index: -1
SWE-bench distractor reuse allowed: 0
Distractor count: 800
Protected input len: 14000
Distractor input len: 14000
Retention prompt isolation mode: disjoint
Random output len: 1
Max context tokens: 17146
Context reserve tokens: 2048
Top-level priority mode: auto
Default cache-control TTL: 1h
Cache-control doc mode: 1
Cache-control frontend flag status: disabled
Cache-control source pin-path status: not_requested
Cache-control pinned ratio: off
HiCache write policy: off
Mem fraction static: 0.7
GPU-only mem fraction static: 0.7
SGLang transfer log profile: full
SGLang root: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang
Output dir: experiments/reports/retention_probe_batches/kv_retention_microbenchmark_20260713_065643__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d800

===== Model: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 | KV tier: gpu_only =====
Worker args: --enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority --mem-fraction-static 0.7
Each hint profile below gets an isolated runtime reset so cache state stays isolated.
--- Arm role: control | Hint profile: none | Cache-control profile: off (reset mode: restart) ---
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
Starting Dynamo for Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 with KV tier gpu_only...
Smoke test 1/180 for Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Smoke test passed for Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Running precise KV-attribution preflight...
Local SGLang transfer markers: ok (/home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang)
Worker container running: dynamo-sglang-worker
Worker overlay mount: ok
Worker env markers:
  SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=0
  SGLANG_TRANSFER_LOG_PROFILE=full
  DYN_RUNTIME_JSON_LOGS=1
  SGLANG_TRANSFER_LOG=1
/usr/local/lib/python3.12/dist-packages/torchao/quantization/quant_api.py:1731: SyntaxWarning: invalid escape sequence '\.'
  """Configuration class for applying different quantization configs to modules or parameters based on their fully qualified names (FQNs).
2026-07-13T07:02:02.760877Z  WARN __init__: dynamo.nixl_connect: Failed to load CuPy for GPU acceleration, utilizing numpy to provide CPU based operations.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.cudart module is deprecated and will be removed in a future release, please switch to use the cuda.bindings.runtimemodule instead.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.nvrtc module is deprecated and will be removed in a future release, please switch to use the cuda.bindings.nvrtc moule instead.
2026-07-13T07:02:06.506146Z  WARN encode_worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
2026-07-13T07:02:06.506743Z  WARN worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
Dynamo decode handler markers: {"attach_logged = False": true, "path": "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/request_handlers/llm/decode_handler.py", "request: Dict[st, Any]": true, "worker.decode.request_attached": true}
/usr/local/lib/python3.12/dist-packages/torchao/quantization/quant_api.py:1731: SyntaxWarning: invalid escape sequence '\.'
  """Configuration class for applying different quantization configs to modules or parameters based on their fully qualified names (FQNs).
SGLang transfer markers: {"_sgl_log_transfer_event": true, "path": "/workspace/sglang_transfer_overlay/sglang/srt/mem_cache/memory_pool_host.py"}
========================================
(4/6) PRECISE ATTRIBUTION READY (the live running worker really has the instrumentation)
========================================
PASS: precise transfer attribution is ready
========================================
(5/6) MODEL READINESS GO (model registration and smoke test both passed)
========================================
========================================
(6/6) PRECISE EXPERIMENT GO (smoke test passed and requests are about to start)
========================================
Machine profile: gh200
Attribution mode: transfer
Smoke test: ok
Live attribution check: ok
Requests may now start.
Cooldown: 60s
Running retention probe: model=Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 kv_tier=gpu_only hint_profile=none cache_control_profile=off arm_role=control run_id=kv_retention_microbenchmark_2060713_065643__sweep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d800_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__none__off__control
Not enough SWE-bench dataset rows for this distractor_count without reuse. need=800 available=730. Use a smaller DISTRACTOR_COUNT or set RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE=1.
Postprocessing retention probe with worker runtime log: experiments/reports/retention_probe_batches/kv_retention_microbenchmark_20260713_065643__sweep_Qwen_Qwen3-Coder-30B-A3B-InstructFP8__gpu_only__d800/Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__none__off__worker_runtime.log
No existing request rows found for postprocess-only mode: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/retention_probe/kv_retention_microbenchmark_20260713_065643__swep_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__d800_Qwen_Qwen3-Coder-30B-A3B-Instruct-FP8__gpu_only__none__off__control/retention_probe_requests.csv

Retention threshold sweep complete.
Progress CSV:    experiments/reports/retention_threshold_sweeps/kv_retention_microbenchmark_20260713_065643__sweep/retention_threshold_sweep_progress.csv
Sweep matrix:    experiments/reports/retention_threshold_sweeps/kv_retention_microbenchmark_20260713_065643__sweep/retention_threshold_matrix.csv
Comparison CSV:  experiments/reports/retention_threshold_sweeps/kv_retention_microbenchmark_20260713_065643__sweep/retention_threshold_comparison.csv
Summary Markdown:experiments/reports/retention_threshold_sweeps/kv_retention_microbenchmark_20260713_065643__sweep/retention_threshold_summary.md
Latest progress: experiments/reports/retention_threshold_sweep_progress.csv
Latest matrix:   experiments/reports/retention_threshold_matrix.csv
Latest compare:  experiments/reports/retention_threshold_comparison.csv
Latest summary:  experiments/reports/retention_threshold_summary.md
matrix: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643/microbenchmark_matrix.csv
summary csv: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643/microbenchmark_summary.csv
summary md: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643/microbenchmark_summary.md
run contract: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643/run_contract.json
Final cleanup: stopping Dynamo once after KV retention microbenchmark.
========================================
KV RETENTION MICROBENCH PHASE 4 READY
========================================
Run directory: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643
Run contract: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643/run_contract.json
Microbenchmark matrix: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643/microbenchmark_matrix.csv
Microbenchmark summary: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643/microbenchmark_summary.csv
Microbenchmark summary md: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643/microbenchmark_summary.md
Replay latency chart: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643/charts/replay_latency.svg
Replay cached chart: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643/charts/replay_cached_tokens.svg
Survival chart: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260713_065643/charts/survival_curve.svg
Last probe run id: <none>
Last sweep run id: kv_retention_microbenchmark_20260713_065643__sweep

Current status:
  - public wrapper: ready
  - contract-driven defaults: ready
  - helper orchestration: ready
  - consolidated microbenchmark report: ready
  - plotting: ready
ojaiyeob@gracehopper:~/kv_cache_offloading$

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
