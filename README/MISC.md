

```bash
cd ~/kv_cache_offloading

RUN_DIR="experiments/reports/speculative_prefill/speculative_prefill_microbenchmark_20260710_161458__probe"

tail -n 200 "$RUN_DIR/speculative_prefill_driver.log"
echo
tail -n 200 "$RUN_DIR/speculative_prefill_smoke_test.log"
echo
grep -niE "error|failed|traceback|timed out|permission|no such|exception" \
  "$RUN_DIR/speculative_prefill_driver.log" \
  "$RUN_DIR/speculative_prefill_smoke_test.log" || true
```


```bash
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

RUN_DIR="experiments/reports/speculative_prefill/speculative_prefill_microbenchmark_20260710_161458__probe"

tail -n 200 "$RUN_DIR/speculative_prefill_driver.log"
echo
tail -n 200 "$RUN_DIR/speculative_prefill_smoke_test.log"
echo
grep -niE "error|failed|traceback|timed out|permission|no such|exception" \
  "$RUN_DIR/speculative_prefill_driver.log" \
  "$RUN_DIR/speculative_prefill_smoke_test.log" || true
Ensuring machine-specific precise runtime images...
Using machine profile: gh200
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs-gh200
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs-gh200
frontend image ok
worker image ok
Reusing extracted SGLang source root: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang
Refreshing SGLang transfer logging patch for precise speculative-prefill attribution...
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
Dynamo head node is ready.

etcd endpoint: http://127.0.0.1:2379
nats endpoint: nats://127.0.0.1:4222
frontend:      http://127.0.0.1:8000
model name:    Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
kv block size: 64
machine profile: gh200
frontend image: local/dynamo-frontend:runtime-json-logs-gh200

Next steps:
  ./run_dynamo_head.sh status
  ./run_dynamo_head.sh logs
  ./run_dynamo_head.sh test
Auto-configured SGLang KV events for cache report: {"publisher":"zmq","topic":"kv-events","endpoint":"tcp://*:5557","enable_kv_cache_events":true}
mkdir: cannot create directory ‘/home/central/ojaiyeob/dynamo_model_cache’: Permission denied

tail: cannot open 'experiments/reports/speculative_prefill/speculative_prefill_microbenchmark_20260710_161458__probe/speculative_prefill_smoke_test.log' for reading: No such file or directory

experiments/reports/speculative_prefill/speculative_prefill_microbenchmark_20260710_161458__probe/speculative_prefill_driver.log:75:mkdir: cannot create directory ‘/home/central/ojaiyeob/dynamo_model_cache’: Permission denied
grep: experiments/reports/speculative_prefill/speculative_prefill_microbenchmark_20260710_161458__probe/speculative_prefill_smoke_test.log: No such file or directory
ojaiyeob@gracehopper:~/kv_cache_offloading$

```
