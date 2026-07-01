Speculative Prefill Microbenchmark Contract
==========================================

Purpose
-------

This contract defines the public speculative-prefill microbenchmark.

Workload
--------

Two-turn synthetic flow:

- turn A runs first
- protected arm sends `speculative_prefill=true`
- Dynamo may warm the likely next turn in the background
- turn B is compared between control and protected arms

Public entrypoint
-----------------

- shell contract:
  - `contracts/speculative_prefill_microbenchmark.contract.sh`
- public wrapper:
  - `agentbench/run_speculative_prefill_microbenchmark_single_host.sh`
- lower-level helper:
  - `agentbench/run_speculative_prefill_probe_single_host.sh`

Supported modes
---------------

- `probe`
- `sweep`
- `all`
- `plot`

Standard precise runtime stack
------------------------------

- Dynamo source:
  - `upstream/dynamo`
- extracted SGLang source:
  - `upstream/sglang`
- extracted SGLang image:
  - `lmsysorg/sglang:v0.5.11-cu129-runtime`
- machine-specific runtime images:
  - `local/dynamo-frontend:runtime-json-logs-<machine-profile>`
  - `local/dynamo-sglang:runtime-json-logs-<machine-profile>`

Public control surface
----------------------

- `DYNAMO_MACHINE_PROFILE`
- `SPEC_PREFILL_MODE`
- `SPEC_PREFILL_ATTRIBUTION_MODE`
- `SPEC_PREFILL_REQUEST_CONTEXT_MODE`
- `SPEC_PREFILL_TURN_A_WORDS`
- `SPEC_PREFILL_TURN_B_WORDS`
- `SPEC_PREFILL_OUTPUT_TOKENS`
- `SPEC_PREFILL_WARMUP_WAIT_MS`
- `SPEC_PREFILL_SWEEP_AXIS`
- `SPEC_PREFILL_SWEEP_VALUES`
- `SGLANG_TRANSFER_LOG_PROFILE`
- `WORKER_BASE_ARGS`

Default proof settings
----------------------

- attribution mode:
  - `precise`
- request context mode:
  - `auto`
- worker args:
  - `--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority`

Readiness defaults
------------------

- `MODEL_READY_RETRIES=900`
- `MODEL_READY_DELAY_SECS=3`
- `MODEL_READY_STABLE_HITS=2`
- `MODEL_SMOKE_RETRIES=180`
- `MODEL_SMOKE_DELAY_SECS=15`
- `MODEL_COOLDOWN_SECS=60`

Consolidated public outputs
---------------------------

- `experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv`
- `experiments/reports/latest_speculative_prefill_microbenchmark_summary.csv`
- `experiments/reports/latest_speculative_prefill_microbenchmark_summary.md`
- `experiments/reports/latest_speculative_prefill_microbenchmark_run_contract.json`
- `experiments/reports/latest_speculative_prefill_microbenchmark_turnb_latency.svg`
- `experiments/reports/latest_speculative_prefill_microbenchmark_turnb_cached.svg`
- `experiments/reports/latest_speculative_prefill_microbenchmark_chart_manifest.json`

Recommended matrix columns
--------------------------

- `part`
- `sweep_axis`
- `sweep_value`
- `arm`
- `spec_prefill`
- `turn_a_ms`
- `turn_b_ms`
- `turn_b_gain_ms`
- `turn_b_cached`
- `turn_b_reuse`
- `hint_status`
- `prefill_wrap`
- `prefill_spawned`
- `prefill_sent`
- `prefill_done`
- `prefill_target_seen`
- `prefill_tokens`
- `effect`

Decision-proof code paths
-------------------------

- `experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py`
  - builds turn A / turn B requests and attaches the hint
- `upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs`
  - reads the hint and makes the real speculative-prefill decision
- `upstream/dynamo/lib/llm/src/preprocessor.rs`
  - calls into the speculative-prefill decision path

Success criteria
----------------

Strong direct evidence means:

- `prefill_sent=true`
- `prefill_done=true`
- and protected turn B is warmer or faster than control

Known failure signatures
------------------------

- `hint_status=on` but `prefill_sent=false`:
  - hint arrived but decision path did not launch background prefill
- no protected gain:
  - speculative prefill was not beneficial in that setup
