

```bash
cd ~/kv_cache_offloading

RUN_ID="speculative_prefill_microbenchmark_20260710_163720__probe"

python3.11 experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py \
  --frontend-url "http://127.0.0.1:8000/v1/chat/completions" \
  --model "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8" \
  --run-id "$RUN_ID" \
  --output-root "experiments/reports/speculative_prefill" \
  --worker-runtime-log "experiments/reports/speculative_prefill/$RUN_ID/speculative_prefill_worker_runtime.log" \
  --postprocess-only
```


```bash
cat "experiments/reports/speculative_prefill/$RUN_ID/speculative_prefill_summary.csv"
cat "experiments/reports/speculative_prefill/$RUN_ID/speculative_prefill_matrix.csv"
cat "experiments/reports/speculative_prefill/$RUN_ID/speculative_prefill_summary.md"
```
