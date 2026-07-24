Speculative Prefill Microbenchmark Contract
==========================================

Purpose
-------

This contract defines the public speculative-prefill microbenchmark.

Workload
--------

Two-turn synthetic, direct SWE-bench task-level, or Exp6 trajectory-prompt flow:

- turn A runs first
- protected arm sends `speculative_prefill=true`
- Dynamo may warm the likely next turn in the background
- turn B is compared between control and protected arms
- in `SPEC_PREFILL_REQUEST_SOURCE=swebench_dataset`, turn A and turn B are
  formatted from SWE-bench Pro task rows
- in `SPEC_PREFILL_REQUEST_SOURCE=swebench_trajectory`, turn A and turn B are
  read from the Exp6 trajectory prompt catalog, usually as two stages from the
  same task, such as `planning -> execution`
- for real request sources, `SPEC_PREFILL_REAL_TURN_B_MODE=long_followup`
  keeps turn A real but makes turn B a deterministic detailed next-turn follow-up; this is the
  clearest real-data test because speculative prefill warms the next-turn
  conversation prefix, not an arbitrary future user prompt
- `SPEC_PREFILL_TURN_A_OUTPUT_TOKENS` and
  `SPEC_PREFILL_TURN_B_OUTPUT_TOKENS` can be used to let turn A produce a
  longer answer while keeping turn B's measured decode cost bounded

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
- `SPEC_PREFILL_TURN_A_OUTPUT_TOKENS`
- `SPEC_PREFILL_TURN_B_OUTPUT_TOKENS`
- `SPEC_PREFILL_WARMUP_WAIT_MS`
- `SPEC_PREFILL_STREAM_RESPONSES`
- `SPEC_PREFILL_INTERTURN_DISTRACTOR_COUNT`
- `SPEC_PREFILL_INTERTURN_DISTRACTOR_START_INDEX`
- `SPEC_PREFILL_INTERTURN_DISTRACTOR_OUTPUT_TOKENS`
- `SPEC_PREFILL_SWEEP_AXIS`
- `SPEC_PREFILL_SWEEP_VALUES`
- `SPEC_PREFILL_SWEEP_SEED_MODE`
- `SPEC_PREFILL_REQUEST_SOURCE`
- `SPEC_PREFILL_REAL_TURN_B_MODE`
- `SPEC_PREFILL_SWEBENCH_DATASET`
- `SPEC_PREFILL_SWEBENCH_SPLIT`
- `SPEC_PREFILL_TURN_A_INDEX`
- `SPEC_PREFILL_TURN_B_INDEX`
- `SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET`
- `SPEC_PREFILL_COMPARISON_MODE`
- `SPEC_PREFILL_TRAJECTORY_PROMPT_CATALOG`
- `SPEC_PREFILL_TRAJECTORY_TURN_A_TASK_INDEX`
- `SPEC_PREFILL_TRAJECTORY_TURN_A_STAGE`
- `SPEC_PREFILL_TRAJECTORY_TURN_B_TASK_INDEX`
- `SPEC_PREFILL_TRAJECTORY_TURN_B_STAGE`
- `SPEC_PREFILL_TRAJECTORY_PROTECTED_OFFSET`
- `SPEC_PREFILL_TRAJECTORY_PROMPT_PREFIX_MODE`
- `RETENTION_PROMPT_ISOLATION_MODE`
- `SGLANG_TRANSFER_LOG_PROFILE`
- `WORKER_BASE_ARGS`

Default proof settings
----------------------

- attribution mode:
  - `precise`
- request context mode:
  - `auto`
- sweep seed mode:
  - `per_value`
- prompt isolation mode:
  - `disjoint`
- request source:
  - `synthetic`
- SWE-bench dataset:
  - `ScaleAI/SWE-bench_Pro`
- SWE-bench split:
  - `test`
- comparison mode:
  - `offset`
  - use `same_task_isolated` for fair SWE-bench latency comparisons; this forces protected offset to `0`, while runtime reset still follows `EXPERIMENT_RESET_MODE`
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
- `experiments/reports/latest_speculative_prefill_microbenchmark_summary.md`
- `experiments/reports/latest_speculative_prefill_microbenchmark_run_contract.json`
- `experiments/reports/latest_speculative_prefill_microbenchmark_turnb_latency.svg`
- `experiments/reports/latest_speculative_prefill_microbenchmark_turnb_ttft.svg`
- `experiments/reports/latest_speculative_prefill_microbenchmark_turnb_ttft_gain.svg`

Recommended matrix columns
--------------------------

- `part`
- `sweep_axis`
- `sweep_value`
- `arm`
- `spec_prefill`
- `request_source`
- `comparison_mode`
- `turn_a_ms`
- `turn_a_ttft_ms`
- `turn_b_ms`
- `turn_b_ttft_ms`
- `turn_b_gain_ms`
- `turn_b_ttft_gain_ms`
- `turn_b_cached`
- `turn_b_reuse`
- `interturn_distractor_count`
- `interturn_distractor_success_count`
- `interturn_distractor_ms_total`
- `interturn_distractor_cached_total`
- `prompt_isolation_mode`
- `turn_a_prompt_family`
- `turn_b_prompt_family`
- `turn_a_prompt_hash`
- `turn_b_prompt_hash`
- `turn_a_source_instance_id`
- `turn_a_source_task_index`
- `turn_b_source_instance_id`
- `turn_b_source_task_index`
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
- and protected turn B has lower TTFT or lower total latency than control

For real SWE-bench task prompts, the cleanest chart is usually:

- `experiments/charts/exp12_specprefill_turn_b_ttft_vs_sweep.svg`

That chart focuses on time-to-first-token, which is the part speculative
prefill is most directly meant to reduce.

Known failure signatures
------------------------

- `hint_status=on` but `prefill_sent=false`:
  - hint arrived but decision path did not launch background prefill
- no protected gain:
  - speculative prefill was not beneficial in that setup
