

```bash
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

grep -n 'DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER:-hermes}"' \
  agentbench/run_prompt_evolution_batch_single_host.sh

grep -n "Tool-call parser" \
  agentbench/run_prompt_evolution_batch_single_host.sh
17:DYN_TOOL_CALL_PARSER="${DYN_TOOL_CALL_PARSER:-hermes}"
134:  echo "Tool-call parser: ${DYN_TOOL_CALL_PARSER}"
ojaiyeob@gracehopper:~/kv_cache_offloading$

```


```bash
BATCH_DIR="$(ls -td experiments/reports/batches/prompt_evolution_batch_* | head -1)"

grep -n "Tool-call parser" "$BATCH_DIR/prompt_evolution_batch_driver.log"
```


```bash
cat experiments/reports/all_runs_execution_prompts.csv
cat experiments/reports/all_runs_overview.csv
```
