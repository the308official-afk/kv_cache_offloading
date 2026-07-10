

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
