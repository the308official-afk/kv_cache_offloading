

```bash
Request source: swebench_dataset
SWE-bench dataset: ScaleAI/SWE-bench_Pro
SWE-bench split: test
SWE-bench protected index: 0
SWE-bench protected instance_id: auto
SWE-bench distractor start index: -1
SWE-bench distractor reuse allowed: 0
Real request units CSV: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/latest_swebench_real_request_units.csv
Real protected request_unit_id: auto
Real protected phase groups: plan act patch review
Real distractor phase groups: plan act patch review
Real distractor reuse allowed: 0
Distractor count: 10

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
