

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
cd ~/kv_cache_offloading

RUN_ID="$(cat experiments/reports/latest_speculative_prefill_microbenchmark_last_probe_run_id.txt 2>/dev/null || true)"
echo "RUN_ID=$RUN_ID"

RUN_DIR="experiments/reports/speculative_prefill/${RUN_ID}"

grep -n "worker.spec_prefill" "$RUN_DIR/speculative_prefill_worker_runtime.log" || true
echo
grep -n "speculative_prefill" "$RUN_DIR/speculative_prefill_worker_runtime.log" | head -50 || true
echo
tail -n 120 "$RUN_DIR/speculative_prefill_worker_runtime.log"
```
