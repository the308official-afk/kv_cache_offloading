CACHE PINNING MICROBENCHMARK CONTRACT
=====================================

Purpose
-------

This contract defines the exact prerequisites for the cache-pinning
microbenchmark stack used in this repository.

This benchmark is intended to answer two questions:

1. Does the cache-pinning path work end to end?
2. Under distractor pressure, does `nvext.cache_control` improve replay
   retention versus control?


Files
-----

Machine-readable contract:

- `contracts/cache_pinning_microbenchmark.contract.sh`

Human-readable contract:

- `contracts/cache_pinning_microbenchmark.contract.md`

Public entrypoint:

- `agentbench/run_cache_pinning_microbenchmark_single_host.sh`

Primary outputs:

- `experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv`
- `experiments/reports/latest_cache_pinning_microbenchmark_summary.csv`
- `experiments/reports/latest_cache_pinning_microbenchmark_summary.md`
- `experiments/reports/latest_cache_pinning_microbenchmark_run_contract.json`
- `experiments/reports/latest_cache_pinning_microbenchmark_validation_latency.svg`
- `experiments/reports/latest_cache_pinning_microbenchmark_validation_cached_tokens.svg`
- `experiments/reports/latest_cache_pinning_microbenchmark_sweep_replay_latency.svg`
- `experiments/reports/latest_cache_pinning_microbenchmark_sweep_replay_cached_tokens.svg`


Supported modes
---------------

- `validate`
  - quick doc-style pin-path validation
- `sweep`
  - retention threshold sweep
- `all`
  - validation, then sweep
- `plot`
  - rebuild charts from one existing microbenchmark matrix CSV


Pinned upstream sources
-----------------------

The shell contract currently pins:

Dynamo:

- repo:
  - `https://github.com/ai-dynamo/dynamo.git`
- pull ref:
  - `6213`
- pinned commit:
  - `7d3d4ec8e4ae865af2f903b21b4afabca28e1940`

SGLang:

- repo:
  - `https://github.com/sgl-project/sglang.git`
- pull ref:
  - `18941`
- pinned commit:
  - `ff2f70b0fcb6b3ea130c46927ed98edf69d5c17c`


Pinned image names
------------------

- frontend image:
  - `local/dynamo-frontend:cache-pinning-${DYNAMO_MACHINE_PROFILE}`
- worker image:
  - `local/dynamo-sglang:cache-pinning-${DYNAMO_MACHINE_PROFILE}`
- EPP image:
  - `registry.k8s.io/gateway-api-inference-extension/epp:v0.5.1`


Explicit cache-pinning contract variables
-----------------------------------------

The shell contract now exposes the cache-pinning prerequisites directly.

Frontend flag control:

- `CACHE_PINNING_FRONTEND_FLAG_MODE`
  - `auto`
  - or `fixed`
- `CACHE_PINNING_FRONTEND_FLAG_VALUE`
  - default: `--enable-cache-control`
- `CACHE_PINNING_ENABLE_CACHE_CONTROL=1`
- `CACHE_PINNING_ROUTER_MODE=kv`

Worker/runtime prerequisites:

- `SGLANG_HICACHE_MAX_PINNED_RATIO`
- `CACHE_PINNING_ENABLE_HIERARCHICAL_CACHE=1`
- `CACHE_PINNING_REQUIRE_HIERARCHICAL_CACHE=1`
- `CACHE_PINNING_HICACHE_RATIO`
- `CACHE_PINNING_HICACHE_WRITE_POLICY=write_through`
- `CACHE_PINNING_PINNED_RATIO`
- `CACHE_PINNING_MEM_FRACTION_STATIC`
- `CACHE_PINNING_ENABLE_CACHE_REPORT=1`
- `CACHE_PINNING_REQUEST_TYPE=ephemeral`
- `CACHE_PINNING_TTL_MIN_SECONDS=300`
- `CACHE_PINNING_TTL_MAX_SECONDS=3600`
- `CACHE_PINNING_DEVELOPMENT_BRANCH_STACK=1`

So if someone edits the shell contract, the public microbenchmark wrapper now
changes behavior directly from those values.


Machine/runtime prerequisites
-----------------------------

- Docker must be installed and usable.
- Git must be installed.
- Enough disk space must be available for image builds.
- Python must be available.
- Supported machine profile should be explicitly set:
  - `DYNAMO_MACHINE_PROFILE=ec2`
  - or `DYNAMO_MACHINE_PROFILE=gh200`

Recommended readiness variables:

- `MODEL_READY_RETRIES=900`
- `MODEL_READY_DELAY_SECS=3`
- `MODEL_READY_STABLE_HITS=2`
- `MODEL_SMOKE_RETRIES=180`
- `MODEL_SMOKE_DELAY_SECS=15`
- `MODEL_COOLDOWN_SECS=60`


Required cache-pinning prerequisites
------------------------------------

Frontend/router side:

- the frontend cache-pinning flag must resolve to one of:
  - `--enable-cache-control`
  - or `--enable-agentic-cache-control`
- this is now controlled by the shell contract through:
  - `CACHE_PINNING_FRONTEND_FLAG_MODE`
  - `CACHE_PINNING_FRONTEND_FLAG_VALUE`
  - with `auto` meaning detect from the pinned Dynamo source
  - and `fixed` meaning use exactly the value in the contract
- router mode is now explicit in the shell contract:
  - `CACHE_PINNING_ROUTER_MODE=kv`

Worker side:

- hierarchical cache must be enabled
- a positive pinned ratio must be set
- HiCache write policy should be `write_through`

Current required values:

- `CACHE_PINNING_REQUEST_TYPE`
- `CACHE_PINNING_TTL`
- `CACHE_PINNING_TTL_MIN_SECONDS`
- `CACHE_PINNING_TTL_MAX_SECONDS`
- `CACHE_PINNING_PINNED_RATIO`
- `SGLANG_HICACHE_MAX_PINNED_RATIO`
- `CACHE_PINNING_HICACHE_RATIO`
- `CACHE_PINNING_HICACHE_WRITE_POLICY`
- `CACHE_PINNING_MEM_FRACTION_STATIC`
- `CACHE_PINNING_ENABLE_CACHE_REPORT`
- `CACHE_PINNING_ENABLE_HIERARCHICAL_CACHE`
- `CACHE_PINNING_REQUIRE_HIERARCHICAL_CACHE`
- `CACHE_PINNING_DEVELOPMENT_BRANCH_STACK`

Required env/flag signals that must effectively reach runtime:

- frontend flag:
  - `--enable-cache-control` or `--enable-agentic-cache-control`
- router mode:
  - `--router-mode kv`
- worker arguments should include:
  - `--enable-cache-report`
  - `--enable-hierarchical-cache`
  - `--hicache-ratio <value>`
  - `--hicache-write-policy write_through`
  - `--mem-fraction-static <value>`
- env:
  - `SGLANG_HICACHE_MAX_PINNED_RATIO=<value>`


Required request payload shape
------------------------------

Protected arm requests must carry:

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

The shell contract mirrors this request-format requirement with:

- `CACHE_PINNING_REQUEST_TYPE=ephemeral`
- `CACHE_PINNING_TTL`
- `CACHE_PINNING_TTL_MIN_SECONDS=300`
- `CACHE_PINNING_TTL_MAX_SECONDS=3600`


Validation proof signals
------------------------

The validation run is considered successful when all of the following are true:

- router sees cache control
- router creates pin state
- router spawns pin request
- worker applies pin path
- second turn reuses cached prefix tokens

Direct proof signals:

Frontend log:

- `router.cache_control_seen`
- `router.pin_state_created`
- `router.pin_prefix_spawned`

Worker log:

- `worker.pin_prefix_applied`
- optionally later:
  - `worker.pin_refreshed_cache_hit`
  - `worker.pin_refreshed_host_insert`


Sweep success criteria
----------------------

The sweep is considered behaviorally successful when:

- the control arm loses replay reuse earlier
- the protected arm keeps replay reuse longer
- and this separation is visible in the threshold matrix


Expected reports
----------------

Validation:

- `experiments/reports/latest_cache_pinning_doc_validation_summary.csv`
- `experiments/reports/latest_cache_pinning_doc_validation_requests.csv`
- `experiments/reports/latest_cache_pinning_doc_validation_summary.md`

Sweep:

- `experiments/reports/latest_cache_pinning_retention_threshold_progress.csv`
- `experiments/reports/latest_cache_pinning_retention_threshold_matrix.csv`
- `experiments/reports/latest_cache_pinning_retention_threshold_comparison.csv`
- `experiments/reports/latest_cache_pinning_retention_threshold_summary.md`


Decision-proof code paths
-------------------------

Source/profile selection:

- `runtime_instrumentation/cache_pinning_profile.sh`

Source fetch:

- `runtime_instrumentation/fetch_cache_pinning_dynamo_source.sh`
- `runtime_instrumentation/fetch_cache_pinning_sglang_source.sh`

Dynamo arbitration and proof:

- `runtime_instrumentation/repair_cache_pinning_dynamo_source.py`
  - reads cache-control TTL
  - creates router pin state
  - spawns pin request
  - patches live worker startup so the `cache_control` endpoint is served

SGLang arbitration and proof:

- `runtime_instrumentation/repair_cache_pinning_sglang_source.py`
  - emits worker-side pin-path events
  - proves `pin_prefix(...)` was applied
  - proves TTL refresh-on-hit when it happens

Runtime helper:

- `runtime_instrumentation/cache_pinning_runtime_helper.sh`
  - centralizes source preparation
  - image preparation
  - local proof-marker checks


Known failure signatures
------------------------

- frontend flag not found in isolated Dynamo source
- worker pin path not seen in worker logs
- `Failed to pin prefix: instance_id=... not found for endpoint dynamo/backend/cache_control`
- insufficient disk space during cache-pinning image build
- worker never reaches readiness smoke test


Current limitations
-------------------

- the current isolated retention sweep uses `light` attribution
- the microbenchmark report is intentionally compact, so deeper raw logs still
  live in the underlying validate and sweep run directories
- plotting is driven from the consolidated matrix CSV, so chart quality depends
  on the matrix having the fields you care about


Doc alignment summary
---------------------

Compared line-by-line with the NVIDIA cache-pinning doc, the shell contract now
explicitly exposes:

- development-branch requirement
- frontend cache-control flag behavior
- router mode = `kv`
- request type = `ephemeral`
- TTL
- TTL clamp range
- `SGLANG_HICACHE_MAX_PINNED_RATIO`
- hierarchical cache requirement
- HiCache ratio
- HiCache write policy
- cache-report requirement
