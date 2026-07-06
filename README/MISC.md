FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs-gh200
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs-gh200
frontend image ok
worker image ok
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
Retention probe ID: kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d25
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
Attribution mode: precise
Models: 1
  Qwen/Qwen2.5-Coder-7B-Instruct
KV tier modes: gpu_only
Control hint profile: none
Protected hint profiles: high-priority
Control cache-control profile: off
Protected cache-control profiles: off
Distractor cache-control profile: off
Distractor count: 25
Protected input len: 400
Distractor input len: 400
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
Output dir: experiments/reports/retention_probe_batches/kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d25

===== Model: Qwen/Qwen2.5-Coder-7B-Instruct | KV tier: gpu_only =====
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
Starting Dynamo for Qwen/Qwen2.5-Coder-7B-Instruct with KV tier gpu_only...
Dynamo head node is ready.

etcd endpoint: http://127.0.0.1:2379
nats endpoint: nats://127.0.0.1:4222
frontend:      http://127.0.0.1:8000
model name:    Qwen/Qwen2.5-Coder-7B-Instruct
kv block size: 64
machine profile: gh200
frontend image: local/dynamo-frontend:runtime-json-logs-gh200

Next steps:
  ./run_dynamo_head.sh status
  ./run_dynamo_head.sh logs
  ./run_dynamo_head.sh test
mkdir: cannot create directory ‘/home/central/ojaiyeob/kv_cache_offloading/experiments/raw’: Permission denied
ojaiyeob@gracehopper:~/kv_cache_offloading$





























ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

cd ~/kv_cache_offloading

cat experiments/reports/retention_probe_batches/kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d25/retention_probe_progress.log

DYNAMO_MACHINE_PROFILE=gh200 \
KV_RETENTION_MODE=sweep \
KV_RETENTION_RESET_MODE=restart \
DISTRACTOR_COUNTS="25 50 75 100 125 150" \
PROTECTED_INPUT_LEN=400 \
DISTRACTOR_INPUT_LEN=400 \
PROTECTED_HINT_PROFILES="high-priority" \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
========================================
KV RETENTION MICROBENCH CONTRACT
========================================
Contract file: contracts/kv_retention_microbenchmark.contract.sh
Contract doc: contracts/kv_retention_microbenchmark.contract.md
Mode: sweep
Model: Qwen/Qwen2.5-Coder-7B-Instruct
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
  kv_tier_modes=gpu_only
  distractor_count=100
  distractor_counts=25 50 75 100 125 150
  protected_input_len=400
  distractor_input_len=400
  random_output_len=1
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
KV RETENTION MICROBENCH SWEEP
========================================
Retention threshold sweep ID: kv_retention_microbenchmark_20260706_161337__sweep
Attribution mode: precise
Models: 1
  Qwen/Qwen2.5-Coder-7B-Instruct
KV tier modes: gpu_only
Control hint profile: none
Protected hint profiles: high-priority
Control cache-control profile: off
Protected cache-control profiles: off
Distractor counts: 25 50 75 100 125 150
Retention probe seed: 42
Retention sweep seed mode: fixed
Protected input len: 400
Distractor input len: 400
Random output len: 1
Max context tokens: 17146
Context reserve tokens: 2048
GPU-only mem fraction static: 0.7
Default cache-control TTL: 1h
SGLang transfer log profile: full
Output dir: experiments/reports/retention_threshold_sweeps/kv_retention_microbenchmark_20260706_161337__sweep

===== Sweep cell =====
model=Qwen/Qwen2.5-Coder-7B-Instruct
kv_tier_mode=gpu_only
distractor_count=25
retention_probe_seed=42
retention_probe_id=kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d25
Ensuring machine-specific precise runtime images...
Using machine profile: gh200
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs-gh200
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs-gh200
frontend image ok
worker image ok
========================================
(1/6) PRECISE RUNTIME IMAGE READY (the machine-specific Dynamo images are there)
========================================
Extracting SGLang source for precise KV attribution...
Using pinned/selected SGLang source image: local/dynamo-sglang:runtime-json-logs-gh200
Resolving installed sglang package path in image: local/dynamo-sglang:runtime-json-logs-gh200
Package path: /sgl-workspace/sglang/python/sglang
Destination: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang
Extracted sglang source to /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang
Potential instrumentation targets:
  /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
  /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/managers/cache_controller.py
  /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/mem_cache/hicache_storage.py
  /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
  /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/multimodal_gen/benchmarks/bench_serving.py
  /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/bench_serving.py
Refreshing SGLang transfer logging patch for precise KV attribution...
memory_pool_host: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
transfer_logging: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/mem_cache/transfer_logging.py
patched transfer functions:
  - backup_from_device_all_layer (6 occurrences)
  - load_to_device_per_layer (6 occurrences)
hiradix_cache: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
patched HiRadix semantic context/cache event functions:
  - write_backup (1 occurrence)
  - load_back (1 occurrence)
  - match_prefix cache event (1 occurrence)
  - insert cache event (1 occurrence)
  - evict cache event (1 occurrence)
cache_controller: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/managers/cache_controller.py
patched async transfer context propagation:
  - CacheOperation context capture
  - CacheOperation merge context
  - write-back transfer context (1 call)
  - load-back transfer context (1 call)
radix_cache: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang/srt/mem_cache/radix_cache.py
patched request context around cache insertion:
  - cache_finished_req request context (1 occurrence)
  - cache_unfinished_req request context (1 occurrence)
  - match_prefix cache event (1 occurrence)
  - insert cache event (1 occurrence)
  - cache_finished_req cache event (1 occurrence)
  - cache_unfinished_req cache event (1 occurrence)
  - evict cache event (1 occurrence)
  - evict priority event (1 occurrence)
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
Retention probe ID: kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d25
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
Attribution mode: precise
Models: 1
  Qwen/Qwen2.5-Coder-7B-Instruct
KV tier modes: gpu_only
Control hint profile: none
Protected hint profiles: high-priority
Control cache-control profile: off
Protected cache-control profiles: off
Distractor cache-control profile: off
Distractor count: 25
Protected input len: 400
Distractor input len: 400
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
Output dir: experiments/reports/retention_probe_batches/kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d25

===== Model: Qwen/Qwen2.5-Coder-7B-Instruct | KV tier: gpu_only =====
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
Starting Dynamo for Qwen/Qwen2.5-Coder-7B-Instruct with KV tier gpu_only...
===== Sweep cell =====
model=Qwen/Qwen2.5-Coder-7B-Instruct
kv_tier_mode=gpu_only
distractor_count=50
retention_probe_seed=42
retention_probe_id=kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d50
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
Retention probe ID: kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d50
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
Attribution mode: precise
Models: 1
  Qwen/Qwen2.5-Coder-7B-Instruct
KV tier modes: gpu_only
Control hint profile: none
Protected hint profiles: high-priority
Control cache-control profile: off
Protected cache-control profiles: off
Distractor cache-control profile: off
Distractor count: 50
Protected input len: 400
Distractor input len: 400
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
Output dir: experiments/reports/retention_probe_batches/kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d50

===== Model: Qwen/Qwen2.5-Coder-7B-Instruct | KV tier: gpu_only =====
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
Starting Dynamo for Qwen/Qwen2.5-Coder-7B-Instruct with KV tier gpu_only...
===== Sweep cell =====
model=Qwen/Qwen2.5-Coder-7B-Instruct
kv_tier_mode=gpu_only
distractor_count=75
retention_probe_seed=42
retention_probe_id=kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d75
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
Retention probe ID: kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d75
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
Attribution mode: precise
Models: 1
  Qwen/Qwen2.5-Coder-7B-Instruct
KV tier modes: gpu_only
Control hint profile: none
Protected hint profiles: high-priority
Control cache-control profile: off
Protected cache-control profiles: off
Distractor cache-control profile: off
Distractor count: 75
Protected input len: 400
Distractor input len: 400
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
Output dir: experiments/reports/retention_probe_batches/kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d75

===== Model: Qwen/Qwen2.5-Coder-7B-Instruct | KV tier: gpu_only =====
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
Starting Dynamo for Qwen/Qwen2.5-Coder-7B-Instruct with KV tier gpu_only...
===== Sweep cell =====
model=Qwen/Qwen2.5-Coder-7B-Instruct
kv_tier_mode=gpu_only
distractor_count=100
retention_probe_seed=42
retention_probe_id=kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d100
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
Retention probe ID: kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d100
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
Attribution mode: precise
Models: 1
  Qwen/Qwen2.5-Coder-7B-Instruct
KV tier modes: gpu_only
Control hint profile: none
Protected hint profiles: high-priority
Control cache-control profile: off
Protected cache-control profiles: off
Distractor cache-control profile: off
Distractor count: 100
Protected input len: 400
Distractor input len: 400
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
Output dir: experiments/reports/retention_probe_batches/kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d100

===== Model: Qwen/Qwen2.5-Coder-7B-Instruct | KV tier: gpu_only =====
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
Starting Dynamo for Qwen/Qwen2.5-Coder-7B-Instruct with KV tier gpu_only...
===== Sweep cell =====
model=Qwen/Qwen2.5-Coder-7B-Instruct
kv_tier_mode=gpu_only
distractor_count=125
retention_probe_seed=42
retention_probe_id=kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d125
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
Retention probe ID: kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d125
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
Attribution mode: precise
Models: 1
  Qwen/Qwen2.5-Coder-7B-Instruct
KV tier modes: gpu_only
Control hint profile: none
Protected hint profiles: high-priority
Control cache-control profile: off
Protected cache-control profiles: off
Distractor cache-control profile: off
Distractor count: 125
Protected input len: 400
Distractor input len: 400
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
Output dir: experiments/reports/retention_probe_batches/kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d125

===== Model: Qwen/Qwen2.5-Coder-7B-Instruct | KV tier: gpu_only =====
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
Starting Dynamo for Qwen/Qwen2.5-Coder-7B-Instruct with KV tier gpu_only...
===== Sweep cell =====
model=Qwen/Qwen2.5-Coder-7B-Instruct
kv_tier_mode=gpu_only
distractor_count=150
retention_probe_seed=42
retention_probe_id=kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d150
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
Retention probe ID: kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d150
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
Attribution mode: precise
Models: 1
  Qwen/Qwen2.5-Coder-7B-Instruct
KV tier modes: gpu_only
Control hint profile: none
Protected hint profiles: high-priority
Control cache-control profile: off
Protected cache-control profiles: off
Distractor cache-control profile: off
Distractor count: 150
Protected input len: 400
Distractor input len: 400
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
Output dir: experiments/reports/retention_probe_batches/kv_retention_microbenchmark_20260706_161337__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d150

===== Model: Qwen/Qwen2.5-Coder-7B-Instruct | KV tier: gpu_only =====
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
Starting Dynamo for Qwen/Qwen2.5-Coder-7B-Instruct with KV tier gpu_only...

Retention threshold sweep complete.
Progress CSV:    experiments/reports/retention_threshold_sweeps/kv_retention_microbenchmark_20260706_161337__sweep/retention_threshold_sweep_progress.csv
Sweep matrix:    experiments/reports/retention_threshold_sweeps/kv_retention_microbenchmark_20260706_161337__sweep/retention_threshold_matrix.csv
Comparison CSV:  experiments/reports/retention_threshold_sweeps/kv_retention_microbenchmark_20260706_161337__sweep/retention_threshold_comparison.csv
Summary Markdown:experiments/reports/retention_threshold_sweeps/kv_retention_microbenchmark_20260706_161337__sweep/retention_threshold_summary.md
Latest progress: experiments/reports/retention_threshold_sweep_progress.csv
Latest matrix:   experiments/reports/retention_threshold_matrix.csv
Latest compare:  experiments/reports/retention_threshold_comparison.csv
Latest summary:  experiments/reports/retention_threshold_summary.md
matrix: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337/microbenchmark_matrix.csv
summary csv: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337/microbenchmark_summary.csv
summary md: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337/microbenchmark_summary.md
run contract: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337/run_contract.json
Final cleanup: stopping Dynamo once after KV retention microbenchmark.
========================================
KV RETENTION MICROBENCH PHASE 4 READY
========================================
Run directory: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337
Run contract: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337/run_contract.json
Microbenchmark matrix: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337/microbenchmark_matrix.csv
Microbenchmark summary: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337/microbenchmark_summary.csv
Microbenchmark summary md: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337/microbenchmark_summary.md
Replay latency chart: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337/charts/replay_latency.svg
Replay cached chart: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337/charts/replay_cached_tokens.svg
Survival chart: experiments/reports/kv_retention_microbenchmark/kv_retention_microbenchmark_20260706_161337/charts/survival_curve.svg
Last probe run id: <none>
Last sweep run id: kv_retention_microbenchmark_20260706_161337__sweep

Current status:
  - public wrapper: ready
  - contract-driven defaults: ready
  - helper orchestration: ready
  - consolidated microbenchmark report: ready
  - plotting: ready
