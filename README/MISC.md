```bash
cd ~/kv_cache_offloading

RUN_ID="kv_retention_microbenchmark_20260706_163851__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d25"

cat "experiments/reports/retention_probe_batches/$RUN_ID/retention_probe_progress.log"
ls -l "experiments/reports/retention_probe_batches/$RUN_ID"
```

```bash
cd ~/kv_cache_offloading

RUN_ID="kv_retention_microbenchmark_20260706_163851__sweep_Qwen_Qwen2_5-Coder-7B-Instruct__gpu_only__d25"

cat "experiments/reports/retention_probe_batches/$RUN_ID"/*smoke_test.log 2>/dev/null || true
```
