

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
SPEC_PREFILL_MODE=all \
EXPERIMENT_RESET_MODE=flush \
RETENTION_PROMPT_ISOLATION_MODE=disjoint \
SPEC_PREFILL_SWEEP_SEED_MODE=per_value \
SPEC_PREFILL_SWEEP_AXIS=SPEC_PREFILL_WARMUP_WAIT_MS \
SPEC_PREFILL_SWEEP_VALUES="0 500 1000 2000" \
SPEC_PREFILL_TURN_A_WORDS=4000 \
SPEC_PREFILL_TURN_B_WORDS=2048 \
SPEC_PREFILL_OUTPUT_TOKENS=128 \
./agentbench/run_speculative_prefill_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8

```


```bash
benchmark_id	part	sweep_axis	sweep_value	run_id	model	arm	spec_prefill	prompt_isolation_mode	turn_a_ms	turn_b_ms	turn_b_gain_ms	turn_b_cached	turn_b_reuse	turn_a_prompt_family	turn_b_prompt_family	turn_a_prompt_hash	turn_b_prompt_hash	hint_status	prefill_wrap	prefill_spawned	prefill_sent	prefill_done	prefill_target_seen	prefill_tokens	effect
speculative_prefill_microbenchmark_20260710_182813	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	0	speculative_prefill_microbenchmark_20260710_182813__sweep_1	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	control	FALSE	disjoint	8367	10305	0	92160	0.651	disjoint:e62170cc43913775	disjoint:2baf677f5f662382	4fe4e0b5390cacdd	ad800042b1d4d151	off	missing	FALSE	FALSE	FALSE	FALSE		baseline_off
speculative_prefill_microbenchmark_20260710_182813	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	0	speculative_prefill_microbenchmark_20260710_182813__sweep_1	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	protected	TRUE	disjoint	8934	10766	-461	96192	0.661	disjoint:2c4b487db4718e2a	disjoint:bc3d24f2710c3e1c	c5140fecc0256429	a4c817be7712bf28	on	inferred_on	TRUE	TRUE	TRUE	TRUE	96196	direct_no_visible_gain
speculative_prefill_microbenchmark_20260710_182813	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	500	speculative_prefill_microbenchmark_20260710_182813__sweep_2	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	control	FALSE	disjoint	8203	10390	0	92160	0.651	disjoint:5a8c9ed7bf0161d2	disjoint:7ebf987c9e4b5a61	d3e738924f2930cf	9a2d688abc738a79	off	missing	FALSE	FALSE	FALSE	FALSE		baseline_off
speculative_prefill_microbenchmark_20260710_182813	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	500	speculative_prefill_microbenchmark_20260710_182813__sweep_2	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	protected	TRUE	disjoint	9087	10256	134	96192	0.67	disjoint:b3b41845a89e449f	disjoint:a1f22bb2d1d36a4a	1ef7354cfed8c20f	68bb2782cc5c87e7	on	inferred_on	TRUE	TRUE	TRUE	TRUE	96222	faster_direct
speculative_prefill_microbenchmark_20260710_182813	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	1000	speculative_prefill_microbenchmark_20260710_182813__sweep_3	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	control	FALSE	disjoint	8330	10915	0	92160	0.642	disjoint:5820e13c6fa2eb56	disjoint:0d01b2f8f5f45406	9b2aa889fece2005	77c24c7abb3c135a	off	missing	FALSE	FALSE	FALSE	FALSE		baseline_off
speculative_prefill_microbenchmark_20260710_182813	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	1000	speculative_prefill_microbenchmark_20260710_182813__sweep_3	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	protected	TRUE	disjoint	7721	9715	1200	88128	0.651	disjoint:49aea2bd375585e3	disjoint:fb254d54f41351aa	93fcae2492066a38	e5e60a7bc2a9a7c9	on	inferred_on	TRUE	TRUE	TRUE	TRUE	88189	faster_direct
speculative_prefill_microbenchmark_20260710_182813	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	2000	speculative_prefill_microbenchmark_20260710_182813__sweep_4	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	control	FALSE	disjoint	8641	11119	0	92224	0.642	disjoint:83634902a0ac8ee7	disjoint:038d72c126033266	f1e2b38cf74ad008	167a103225015bea	off	missing	FALSE	FALSE	FALSE	FALSE		baseline_off
speculative_prefill_microbenchmark_20260710_182813	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	2000	speculative_prefill_microbenchmark_20260710_182813__sweep_4	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	protected	TRUE	disjoint	8887	10220	899	96192	0.671	disjoint:2a57f6968968fc7e	disjoint:59748ef8031df62f	f163264c0b6495a0	87956151db5be60c	on	inferred_on	TRUE	TRUE	TRUE	TRUE	96193	faster_direct


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
