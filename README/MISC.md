

```bash
cd ~/kv_cache_offloading

BATCH_DIR="$(ls -td experiments/reports/batches/prompt_evolution_batch_* | head -1)"

grep -n "Tool-call parser" "$BATCH_DIR/prompt_evolution_batch_driver.log"
grep -n "DYN_TOOL_CALL_PARSER" "$BATCH_DIR/prompt_evolution_batch_driver.log" || true
```


```bash

```


```bash

```
