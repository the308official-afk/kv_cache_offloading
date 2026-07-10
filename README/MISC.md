

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
