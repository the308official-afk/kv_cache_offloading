

```bash
run_id	model	request_source	gap_ms	low_requests	high_requests	max_jump_ahead	high_jump_ahead_count	high_jump_ahead_rate	high_completed_ahead_count	priority_hint_seen	priority_path_status	result
priority_scheduling_microbenchmark_20260713_170902__sweep_1	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	swebench_dataset	50	8	4	32	18	56.20%	14	yes	worker_received_hint	priority_reordered
priority_scheduling_microbenchmark_20260713_170902__sweep_2	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	swebench_dataset	100	8	4	32	16	50.00%	12	yes	worker_received_hint	priority_reordered
priority_scheduling_microbenchmark_20260713_170902__sweep_3	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	swebench_dataset	200	8	4	32	6	18.80%	6	yes	worker_received_hint	priority_reordered
priority_scheduling_microbenchmark_20260713_170902__sweep_4	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	swebench_dataset	400	8	4	32	0	0.00%	0	yes	worker_received_hint	no_visible_reorder


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
