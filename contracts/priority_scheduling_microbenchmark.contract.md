Priority Scheduling Microbenchmark Contract
==========================================

Purpose
-------

This contract defines the public microbenchmark for queue-priority behavior.

Workload
--------

Synthetic or direct SWE-bench task-level mixed-priority burst:

- low-priority requests arrive first
- high-priority requests arrive slightly later
- we check whether the later high-priority requests move ahead anyway
- in `PRIORITY_REQUEST_SOURCE=swebench_dataset`, each request prompt is one
  SWE-bench Pro task row
- in `PRIORITY_REQUEST_SOURCE=swebench_trajectory`, each request prompt is one
  captured Experiment 6 trajectory prompt row

Public entrypoint
-----------------

- shell contract:
  - `contracts/priority_scheduling_microbenchmark.contract.sh`
- public wrapper:
  - `agentbench/run_priority_scheduling_microbenchmark_single_host.sh`
- lower-level helper:
  - `agentbench/run_priority_scheduling_probe_single_host.sh`

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
- `PRIORITY_SCHEDULING_MODE`
- `PRIORITY_SCHEDULING_ATTRIBUTION_MODE`
- `PRIORITY_REQUEST_CONTEXT_MODE`
- `PRIORITY_TOP_LEVEL_PRIORITY_MODE`
- `LOW_PRIORITY_COUNT`
- `HIGH_PRIORITY_COUNT`
- `LOW_PRIORITY_VALUE`
- `HIGH_PRIORITY_VALUE`
- `PRIORITY_INPUT_LEN`
- `PRIORITY_OUTPUT_LEN`
- `PRIORITY_ARRIVAL_GAP_MS`
- `PRIORITY_INTER_REQUEST_GAP_MS`
- `PRIORITY_SCHEDULING_SWEEP_AXIS`
- `PRIORITY_SCHEDULING_SWEEP_VALUES`
- `PRIORITY_SCHEDULING_SWEEP_SEED_MODE`
- `PRIORITY_REQUEST_SOURCE`
- `PRIORITY_SWEBENCH_DATASET`
- `PRIORITY_SWEBENCH_SPLIT`
- `PRIORITY_SWEBENCH_START_INDEX`
- `PRIORITY_SWEBENCH_ALLOW_REUSE`
- `PRIORITY_TRAJECTORY_PROMPT_CATALOG`
- `PRIORITY_TRAJECTORY_STAGES`
- `PRIORITY_TRAJECTORY_START_TASK_INDEX`
- `PRIORITY_TRAJECTORY_PROMPT_PREFIX_MODE`
- `PRIORITY_TRAJECTORY_ALLOW_REUSE`
- `RETENTION_PROMPT_ISOLATION_MODE`
- `SGLANG_TRANSFER_LOG_PROFILE`
- `WORKER_BASE_ARGS`

Default proof settings
----------------------

- attribution mode:
  - `precise`
- request context mode:
  - `auto`
- top-level priority mode:
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

- `experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv`
- `experiments/reports/latest_priority_scheduling_microbenchmark_summary.md`
- `experiments/reports/latest_priority_scheduling_microbenchmark_run_contract.json`
- `experiments/reports/latest_priority_scheduling_microbenchmark_jump_ahead.svg`
  - line chart of jump-ahead rate versus arrival gap
- `experiments/charts/exp11_prioritysched_jump_ahead_vs_arrival_gap.svg`
  - same chart copied into the shared chart folder

Recommended matrix columns
--------------------------

- `run_id`
- `model`
- `request_source`
- `hint_kind`
- `gap_ms`
- `low_requests`
- `high_requests`
- `max_jump_ahead`
- `high_jump_ahead_count`
- `high_jump_ahead_rate`
- `high_completed_ahead_count`
- `hint_seen`
- `hint_path_status`
- `result`

Decision-proof code paths
-------------------------

- `experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py`
  - builds the synthetic request burst and hint payloads
- `upstream/dynamo/lib/llm/src/preprocessor.rs`
  - carries priority into routed request metadata
- `upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py`
  - reads routed priority and forwards it into live generation
- `runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py`
  - injects SGLang-side priority-path logging

Success criteria
----------------

Strong scheduling evidence means:

- `hint_kind=priority`
- `hint_seen=yes`
- `high_jump_ahead_count > 0`
- `high_jump_ahead_rate > 0%`
- `result=priority_reordered`

Known failure signatures
------------------------

- no worker attach/completed events:
  - runtime image is missing full precise instrumentation
- all high-priority requests behave like low-priority requests:
  - `high_jump_ahead_count=0`
  - `result=no_visible_reorder`
