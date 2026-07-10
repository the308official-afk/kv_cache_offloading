

```bash
benchmark_id	part	sweep_axis	sweep_value	run_id	model	arm	spec_prefill	turn_a_ms	turn_b_ms	turn_b_gain_ms	turn_b_cached	turn_b_reuse	hint_status	prefill_wrap	prefill_spawned	prefill_sent	prefill_done	prefill_target_seen	prefill_tokens	effect
speculative_prefill_microbenchmark_20260710_171732	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	0	speculative_prefill_microbenchmark_20260710_171732__sweep_1	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	control	FALSE	563	498	0	8128	0.564	off	missing	FALSE	FALSE	FALSE	FALSE		baseline_off
speculative_prefill_microbenchmark_20260710_171732	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	0	speculative_prefill_microbenchmark_20260710_171732__sweep_1	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	protected	TRUE	450	562	-64	8128	0.564	on	inferred_on	TRUE	TRUE	TRUE	TRUE	8155	direct_no_visible_gain
speculative_prefill_microbenchmark_20260710_171732	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	500	speculative_prefill_microbenchmark_20260710_171732__sweep_2	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	control	FALSE	431	497	0	8128	0.564	off	missing	FALSE	FALSE	FALSE	FALSE		baseline_off
speculative_prefill_microbenchmark_20260710_171732	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	500	speculative_prefill_microbenchmark_20260710_171732__sweep_2	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	protected	TRUE	449	561	-64	8128	0.564	on	inferred_on	TRUE	TRUE	TRUE	TRUE	8155	direct_no_visible_gain
speculative_prefill_microbenchmark_20260710_171732	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	1000	speculative_prefill_microbenchmark_20260710_171732__sweep_3	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	control	FALSE	433	497	0	8128	0.564	off	missing	FALSE	FALSE	FALSE	FALSE		baseline_off
speculative_prefill_microbenchmark_20260710_171732	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	1000	speculative_prefill_microbenchmark_20260710_171732__sweep_3	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	protected	TRUE	451	559	-62	8128	0.564	on	inferred_on	TRUE	TRUE	TRUE	TRUE	8155	direct_no_visible_gain
speculative_prefill_microbenchmark_20260710_171732	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	2000	speculative_prefill_microbenchmark_20260710_171732__sweep_4	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	control	FALSE	435	503	0	8128	0.564	off	missing	FALSE	FALSE	FALSE	FALSE		baseline_off
speculative_prefill_microbenchmark_20260710_171732	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	2000	speculative_prefill_microbenchmark_20260710_171732__sweep_4	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	protected	TRUE	449	562	-59	8128	0.564	on	inferred_on	TRUE	TRUE	TRUE	TRUE	8155	direct_no_visible_gain


```


```bash
# Speculative Prefill Probe: speculative_prefill_microbenchmark_20260710_163720__probe

- Model: `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8`
- Attribution mode: `precise`
- Turn A words: `4000`
- Turn B words: `512`
- Output tokens: `64`
- Warmup wait ms: `500`

## Result

- Control turn B latency ms: `291`
- Protected turn B latency ms: `337`
- Turn B latency delta ms (control - protected): `-46`
- Control turn B cached tokens: `8128`
- Protected turn B cached tokens: `8128`
- Turn B cached-token delta (protected - control): `0`
- Protected prefill evidence status: `direct_prefill_seen`
- Protected prefill completed: `True`
- Protected target seen in prefill events: `True`
- Protected anonymous warmup seen: `True`
- Overall effect verdict: `direct_no_visible_gain`

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
