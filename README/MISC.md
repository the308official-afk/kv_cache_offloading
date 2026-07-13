

```bash
benchmark_id	part	sweep_axis	sweep_value	run_id	model	request_source	source_instance_id	source_task_index	request	prio_class	arrival	attach	complete	attach_gain	complete_gain	beat_low_attach	beat_low_complete	queue_ms	latency_ms	low_wait_ms	high_wait_ms	low_latency_ms	high_latency_ms	high_attach_leapfrogs	high_complete_leapfrogs	top_prio_compat	worker_hint_status	worker_top_prio_status	sglang_prio_status	worker_hint_prio	sent_top_prio	worker_top_prio	sglang_prio	runtime_match	effect
priority_scheduling_microbenchmark_20260713_153205	sweep	PRIORITY_ARRIVAL_GAP_MS	50	priority_scheduling_microbenchmark_20260713_153205__sweep_1	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	swebench_dataset														424	561	1762	1795	18	14	unsupported	full	none	worker_received_hint						yes
priority_scheduling_microbenchmark_20260713_153205	sweep	PRIORITY_ARRIVAL_GAP_MS	100	priority_scheduling_microbenchmark_20260713_153205__sweep_2	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	swebench_dataset														354	523	1962	1946	12	12	unsupported	full	none	worker_received_hint						yes
priority_scheduling_microbenchmark_20260713_153205	sweep	PRIORITY_ARRIVAL_GAP_MS	200	priority_scheduling_microbenchmark_20260713_153205__sweep_3	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	swebench_dataset														326	525	1862	1745	4	3	unsupported	full	none	worker_received_hint						yes
priority_scheduling_microbenchmark_20260713_153205	sweep	PRIORITY_ARRIVAL_GAP_MS	400	priority_scheduling_microbenchmark_20260713_153205__sweep_4	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	swebench_dataset														318	399	1799	1538	0	0	unsupported	full	none	worker_received_hint						no


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
