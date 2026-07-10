

```bash
ojaiyeob@gracehopper:~/kv_cache_offloading$ git pull origin main
From https://github.com/the308official-afk/kv_cache_offloading
 * branch            main       -> FETCH_HEAD
Already up to date.
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
SPEC_PREFILL_MODE=probe \
EXPERIMENT_RESET_MODE=restart \
SPEC_PREFILL_TURN_A_WORDS=4000 \
SPEC_PREFILL_TURN_B_WORDS=512 \
SPEC_PREFILL_OUTPUT_TOKENS=64 \
SPEC_PREFILL_WARMUP_WAIT_MS=500 \
./agentbench/run_speculative_prefill_microbenchmark_single_host.sh \
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
SPECULATIVE PREFILL MICROBENCH CONTRACT
========================================
Contract file: contracts/speculative_prefill_microbenchmark.contract.sh
Contract doc: contracts/speculative_prefill_microbenchmark.contract.md
Mode: probe
Model: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Machine profile: gh200

Public wrapper:
  /home/central/ojaiyeob/kv_cache_offloading/agentbench/run_speculative_prefill_microbenchmark_single_host.sh

Internal helper:
  probe=/home/central/ojaiyeob/kv_cache_offloading/agentbench/run_speculative_prefill_probe_single_host.sh

Runtime stack:
  dynamo_source_dir=/home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo
  sglang_source_image=lmsysorg/sglang:v0.5.11-cu129-runtime
  sglang_source_dir=/home/central/ojaiyeob/kv_cache_offloading/upstream/sglang
  frontend_image=local/dynamo-frontend:runtime-json-logs-gh200
  worker_image=local/dynamo-sglang:runtime-json-logs-gh200

Workload defaults:
  turn_a_words=4000
  turn_b_words=512
  output_tokens=64
  warmup_wait_ms=500
  sweep_axis=SPEC_PREFILL_WARMUP_WAIT_MS
  sweep_values=0 100 250 500 1000

Runtime defaults:
  attribution_mode=precise
  request_context_mode=auto
  experiment_reset_mode=restart
  transfer_log_profile=full
  worker_base_args=--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority
  probe_seed=42
  sweep_seed_mode=fixed
  retention_prompt_isolation_mode=strict
========================================
PRECISE CLEAN START ACTIVE (clearing any old runtime before Speculative prefill microbenchmark)
========================================
========================================
PRECISE CLEAN START READY (old runtime cleared before Speculative prefill microbenchmark)
========================================
========================================
SPECULATIVE PREFILL MICROBENCH PROBE
========================================
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
Refreshing SGLang transfer logging patch for precise speculative-prefill attribution...
========================================
(2/6) PRECISE LOCAL READY (the local extracted/patched SGLang source is good)
========================================
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
SGLang root: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang
Local transfer markers: ok
Dynamo root: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo
Local speculative-prefill markers: ok
Ready to start Dynamo: yes
Speculative prefill run ID: speculative_prefill_microbenchmark_20260710_161458__probe
Model: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Machine profile: gh200
Frontend image: local/dynamo-frontend:runtime-json-logs-gh200
Worker image: local/dynamo-sglang:runtime-json-logs-gh200
Auto-build precise images: 1
Attribution mode: precise
Turn A input words: 4000
Turn B input words: 512
Output length tokens: 64
Warmup wait ms: 500
Request-context mode: auto
Driver log: experiments/reports/speculative_prefill/speculative_prefill_microbenchmark_20260710_161458__probe/speculative_prefill_driver.log
Smoke log: experiments/reports/speculative_prefill/speculative_prefill_microbenchmark_20260710_161458__probe/speculative_prefill_smoke_test.log
Worker runtime log: experiments/reports/speculative_prefill/speculative_prefill_microbenchmark_20260710_161458__probe/speculative_prefill_worker_runtime.log
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
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

grep -Rni "worker.spec_prefill" experiments/reports/speculative_prefill | tail -100
ojaiyeob@gracehopper:~/kv_cache_offloading$
```
PY
```
