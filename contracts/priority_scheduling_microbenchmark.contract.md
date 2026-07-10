Priority Scheduling Microbenchmark Contract
==========================================

Purpose
-------

This contract defines the public microbenchmark for queue-priority behavior.

Workload
--------

Synthetic mixed-priority burst:

- low-priority requests arrive first
- high-priority requests arrive slightly later
- we check whether the later high-priority requests move ahead anyway

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
- `experiments/reports/latest_priority_scheduling_microbenchmark_summary.csv`
- `experiments/reports/latest_priority_scheduling_microbenchmark_summary.md`
- `experiments/reports/latest_priority_scheduling_microbenchmark_run_contract.json`
- `experiments/reports/latest_priority_scheduling_microbenchmark_attach_gain.svg`
- `experiments/reports/latest_priority_scheduling_microbenchmark_queue_wait.svg`
- `experiments/reports/latest_priority_scheduling_microbenchmark_chart_manifest.json`

Recommended matrix columns
--------------------------

- `part`
- `sweep_axis`
- `sweep_value`
- `request`
- `prio_class`
- `arrival`
- `attach`
- `complete`
- `attach_gain`
- `complete_gain`
- `beat_low_attach`
- `beat_low_complete`
- `queue_ms`
- `latency_ms`
- `worker_hint_prio`
- `sent_top_prio`
- `worker_top_prio`
- `sglang_prio`
- `runtime_match`
- `effect`

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

- `attach_gain > 0` for some high-priority requests
- `beat_low_attach > 0` for some high-priority requests
- lower mean `queue_ms` for high-priority requests
- worker-side hint proof is present

Known failure signatures
------------------------

- no worker attach/completed events:
  - runtime image is missing full precise instrumentation
- all high-priority requests behave like low-priority requests:
  - scheduling effect not observed in this run
