KV RETENTION MICROBENCHMARK CONTRACT
====================================

Purpose
-------

This contract defines the exact prerequisites for the KV retention
microbenchmark stack used in this repository.

This benchmark is intended to answer two questions:

1. Does the retention-control path work end to end?
2. Under distractor pressure, does the protected arm retain replay reuse longer
   than control?


Files
-----

Machine-readable contract:

- `contracts/kv_retention_microbenchmark.contract.sh`

Human-readable contract:

- `contracts/kv_retention_microbenchmark.contract.md`

Planned public entrypoint:

- `agentbench/run_kv_retention_microbenchmark_single_host.sh`

Current lower-level helpers:

- `agentbench/run_kv_retention_probe_single_host.sh`
- `agentbench/run_kv_retention_threshold_sweep_single_host.sh`

Planned primary outputs:

- `experiments/reports/latest_kv_retention_microbenchmark_matrix.csv`
- `experiments/reports/latest_kv_retention_microbenchmark_summary.md`
- `experiments/reports/latest_kv_retention_microbenchmark_run_contract.json`
- `experiments/reports/latest_kv_retention_microbenchmark_replay_latency.svg`
- `experiments/reports/latest_kv_retention_microbenchmark_replay_cached_tokens.svg`


Supported modes
---------------

- `probe`
  - one retention-probe run
- `sweep`
  - threshold sweep across distractor counts
- `all`
  - sweep, then plot
- `plot`
  - rebuild charts from one existing microbenchmark matrix CSV


Standard precise runtime stack
------------------------------

This experiment does not currently use an isolated PR-pinned stack like the
cache-pinning benchmark.

Instead, it uses the repository's standard precise runtime path:

- Dynamo source dir:
  - `upstream/dynamo`
- SGLang extraction source image:
  - `lmsysorg/sglang:v0.5.11-cu129-runtime`
- extracted SGLang source dir:
  - `upstream/sglang`
- machine-specific precise images:
  - `local/dynamo-frontend:runtime-json-logs-${DYNAMO_MACHINE_PROFILE}`
  - `local/dynamo-sglang:runtime-json-logs-${DYNAMO_MACHINE_PROFILE}`

Machine profile should be explicitly set:

- `DYNAMO_MACHINE_PROFILE=ec2`
- or `DYNAMO_MACHINE_PROFILE=gh200`


Public control surface
----------------------

The shell contract currently exposes:

- experiment mode:
  - `KV_RETENTION_MODE`
- request source:
  - `RETENTION_REQUEST_SOURCE`
  - `RETENTION_SWEBENCH_DATASET`
  - `RETENTION_SWEBENCH_SPLIT`
  - `RETENTION_SWEBENCH_INDEX`
  - `RETENTION_SWEBENCH_INSTANCE_ID`
  - `RETENTION_SWEBENCH_DISTRACTOR_START_INDEX`
  - `RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE`
- attribution path:
  - `RETENTION_ATTRIBUTION_MODE`
  - `RETENTION_REQUEST_CONTEXT_MODE`
  - `RETENTION_TOP_LEVEL_PRIORITY_MODE`
- reset policy:
  - `KV_RETENTION_RESET_MODE`
- controls under test:
  - `CONTROL_HINT_PROFILE`
  - `PROTECTED_HINT_PROFILES`
  - `CONTROL_CACHE_CONTROL_PROFILE`
  - `PROTECTED_CACHE_CONTROL_PROFILES`
- workload shape:
  - `DISTRACTOR_COUNT`
  - `DISTRACTOR_COUNTS`
  - `PROTECTED_INPUT_LEN`
  - `DISTRACTOR_INPUT_LEN`
  - `RANDOM_OUTPUT_LEN`
  - `RETENTION_SWEEP_SEED_MODE`
  - `RETENTION_PROMPT_ISOLATION_MODE`
  - `MAX_CONTEXT_TOKENS`
- runtime shape:
  - `KV_TIER_MODES`
  - `GPU_ONLY_MEM_FRACTION_STATIC`
  - `GPU_CPU_MEM_FRACTION_STATIC`
  - `GPU_CPU_STORAGE_MEM_FRACTION_STATIC`
  - `HICACHE_RATIO`
  - `HICACHE_STORAGE_BACKEND`
  - `HICACHE_STORAGE_PREFETCH_POLICY`
  - `WORKER_BASE_ARGS`
- proof thresholds:
  - `RETENTION_MATCH_EVENT_MIN`
  - `RETENTION_MIN_SPEEDUP_RATIO`
  - `RETENTION_MIN_LATENCY_GAIN_MS`

Default proof settings
----------------------

- sweep seed mode:
  - `per_cell`
- prompt isolation mode:
  - `disjoint`

So if someone edits the shell contract, the future public microbenchmark wrapper
will change behavior directly from those values.

Request-source defaults:

- `RETENTION_REQUEST_SOURCE=synthetic`
- `RETENTION_SWEBENCH_DATASET=ScaleAI/SWE-bench_Pro`
- `RETENTION_SWEBENCH_SPLIT=test`
- `RETENTION_SWEBENCH_INDEX=0`
- `RETENTION_SWEBENCH_INSTANCE_ID=`
- `RETENTION_SWEBENCH_DISTRACTOR_START_INDEX=-1`
- `RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE=0`
- `RETENTION_TRAJECTORY_PROMPT_CATALOG=experiments/reports/latest_swebench_trajectory_prompt_catalog.csv`
- `RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX=0`
- `RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID=`
- `RETENTION_TRAJECTORY_PROTECTED_STAGE=patch_generation`
- `RETENTION_TRAJECTORY_STAGES=planning execution patch_generation review`
- `RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX=-1`
- `RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE=0`

For direct SWE-bench Pro runs, use:

- `RETENTION_REQUEST_SOURCE=swebench_dataset`

That path reads the Hugging Face dataset directly and builds:

- protected A from one SWE-bench task
- distractors from other SWE-bench tasks
- protected A replay from the same protected task

For multi-stage SWE-bench trajectory runs, use:

- `RETENTION_REQUEST_SOURCE=swebench_trajectory`

That path reads a prepared prompt catalog and builds:

- protected A from one captured task stage
- distractors from multiple captured stages from other tasks
- protected A replay from the same captured task stage

Prepare that catalog with:

- `./agentbench/prepare_swebench_trajectory_prompts.sh`


Machine/runtime prerequisites
-----------------------------

- Docker must be installed and usable.
- Git must be installed.
- Enough disk space must be available for precise-image builds.
- Python must be available.
- The standard precise runtime image pair should exist or be buildable for the
  selected machine profile.

Recommended readiness variables:

- `MODEL_READY_RETRIES=900`
- `MODEL_READY_DELAY_SECS=3`
- `MODEL_READY_STABLE_HITS=2`
- `MODEL_SMOKE_RETRIES=180`
- `MODEL_SMOKE_DELAY_SECS=15`
- `MODEL_COOLDOWN_SECS=60`


Supported control types
-----------------------

This contract currently treats two control families as valid:

- `priority`
- `cache_control`

Default control for the retention benchmark:

- `priority`

Typical priority retention pattern:

- `CONTROL_HINT_PROFILE=none`
- `PROTECTED_HINT_PROFILES=high-priority`

Typical cache-control retention pattern:

- `CONTROL_CACHE_CONTROL_PROFILE=off`
- `PROTECTED_CACHE_CONTROL_PROFILES=ephemeral:1h`


Required request payload behavior
---------------------------------

Priority-protected requests must be able to carry:

- `nvext.agent_hints.priority`
- and, when supported by the frontend:
  - top-level `priority`

Cache-control-protected requests must be able to carry:

```json
{
  "nvext": {
    "cache_control": {
      "type": "ephemeral",
      "ttl": "1h"
    }
  }
}
```


Current default workload contract
---------------------------------

Probe defaults:

- `KV_TIER_MODES=gpu_only`
- `DISTRACTOR_COUNT=100`
- `PROTECTED_INPUT_LEN=14000`
- `DISTRACTOR_INPUT_LEN=14000`
- `RANDOM_OUTPUT_LEN=1`
- `MAX_CONTEXT_TOKENS=17146`

Sweep defaults:

- `DISTRACTOR_COUNTS=25 50 75 100 125 150`

Default worker/runtime settings:

- `SGLANG_TRANSFER_LOG_PROFILE=full`
- `WORKER_BASE_ARGS=--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority`
- `MEM_FRACTION_STATIC=0.7`
- `HICACHE_RATIO=1`
- `KV_RETENTION_RESET_MODE=restart`

Why the reset default matters:

- the control arm and protected arm should both start cold
- `KV_RETENTION_RESET_MODE=restart` prevents the protected `a_first` request
  from accidentally inheriting warm cache from the control arm
- `KV_RETENTION_RESET_MODE=flush` is faster, but only valid when the live
  Dynamo runtime serves `POST /clear_kv_blocks`
- the instrumented Dynamo source-prep path now repairs and verifies the
  frontend route registration plus the worker-side `clear_kv_blocks` plumbing
  before image build, so future precise rebuilds should fail early if flush
  support is missing


Validation and proof signals
----------------------------

Probe success should be judged from a combination of:

- replay cached tokens
- replay reuse ratio
- warm / survived interpretation
- worker-side proof that the protected control reached the worker
- SGLang-side proof, when available

Direct proof signals for priority retention include:

Worker/runtime side:

- worker saw routed/top-level priority
- worker forwarded priority into generation

SGLang side:

- `priority_hint_seen`
- `scheduler_priority_applied`

Retention behavior side:

- replay cached tokens are present
- replay latency is reduced versus cold replay
- protected arm stays warm deeper than control in the sweep


Sweep success criteria
----------------------

The sweep is considered behaviorally successful when:

- the control arm loses replay warmth earlier
- the protected arm keeps replay reuse longer
- and this difference is visible in the threshold comparison

The current proof thresholds in the shell contract are:

- `RETENTION_MATCH_EVENT_MIN=1`
- `RETENTION_MIN_SPEEDUP_RATIO=1.05`
- `RETENTION_MIN_LATENCY_GAIN_MS=100`


Planned consolidated reports
----------------------------

Per-run:

- `experiments/reports/kv_retention_microbenchmark/<run_id>/microbenchmark_matrix.csv`
- `experiments/reports/kv_retention_microbenchmark/<run_id>/microbenchmark_summary.csv`
- `experiments/reports/kv_retention_microbenchmark/<run_id>/microbenchmark_summary.md`
- `experiments/reports/kv_retention_microbenchmark/<run_id>/run_contract.json`

Top-level latest:

- `experiments/reports/latest_kv_retention_microbenchmark_matrix.csv`
- `experiments/reports/latest_kv_retention_microbenchmark_summary.md`
- `experiments/reports/latest_kv_retention_microbenchmark_run_contract.json`

Public charts:

- `experiments/reports/latest_kv_retention_microbenchmark_replay_latency.svg`
- `experiments/reports/latest_kv_retention_microbenchmark_replay_cached_tokens.svg`


Recommended public matrix schema
--------------------------------

The intended compact public matrix should center on:

- `run_id`
- `mode`
- `model`
- `kv_tier`
- `arm`
- `hint_profile`
- `cache_control`
- `distractors`
- `first_ms`
- `replay_ms`
- `delta_ms`
- `speedup_x`
- `replay_cached`
- `replay_reuse`
- `warm`
- `warm_source`
- `req_prio_status`
- `worker_prio_status`
- `replay_evicts`
- `replay_evict_cache`
- `replay_evict_status`
- `result`

The public matrix should avoid:

- raw request payload dumps
- verbose fallback/debug strings
- long cache-value blobs
- duplicated internal-only status columns


Decision-proof code paths
-------------------------

Source/profile selection:

- `runtime_instrumentation/dynamo_machine_profile.sh`
- `runtime_instrumentation/sglang_source_profile.sh`

Source preparation and local proof checks:

- `runtime_instrumentation/prepare_instrumented_dynamo_source.sh`
- `runtime_instrumentation/precise_sglang_helper.sh`

Dynamo proof path:

- `upstream/dynamo/lib/llm/src/preprocessor.rs`
  - preserves request metadata and hint observability
- `upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py`
  - reads routed priority
  - forwards priority into generation

SGLang proof path:

- `runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py`
  - injects transfer and priority-path logging hooks

Report proof path:

- `experiments/scripts/retention_probe/run_kv_retention_probe.py`
  - interprets replay warmth
  - interprets worker priority status
  - interprets eviction evidence


Known failure signatures
------------------------

- frontend rejected top-level priority
- live worker missing precise attribution markers
- SGLang priority-path markers unavailable on the extracted source version
- replay did not warm even in the protected arm
- stale latest reports caused mixed conclusions
- cache-control forced `gpu_only` promotion did not happen when expected
