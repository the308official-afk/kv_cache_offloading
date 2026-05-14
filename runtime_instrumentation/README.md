# Runtime Instrumentation Workflow

This directory turns the Dynamo/SGLang runtime instrumentation into a repeatable workflow instead of a one-off local clone.

## What this instruments

The tracked patch in [patches/dynamo_runtime_json_logging.patch](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/patches/dynamo_runtime_json_logging.patch) adds opt-in structured JSON log events to upstream Dynamo runtime source.

Current event families:

- frontend:
  - `frontend.request.preprocessed`
  - `frontend.request.dispatched`
  - `frontend.request.completed`
  - `frontend.request.error`
- router:
  - `router.worker_selected`
- worker:
  - `worker.prefill.request_received`
  - `worker.prefill.request_attached`
  - `worker.prefill.request_completed`
  - `worker.decode.request_received`
  - `worker.decode.request_attached`
  - `worker.decode.request_completed`

These events are emitted only when:

```bash
export DYN_RUNTIME_JSON_LOGS=1
```

The log lines use a stable `[RUNTIME_JSON]` prefix so AgentBench or external tooling can parse them from normal container logs.

## Why this path is the long-term one

Instead of inferring runtime behavior from ad-hoc logs, this workflow lets you:

1. obtain upstream runtime source
2. apply a tracked instrumentation patch
3. build custom frontend and worker images
4. run your existing local Dynamo scripts against those images

That gives you a source-controlled bridge between:

- AgentBench policy recommendations
- actual runtime-side routing and worker events

## Workflow

### 1. Fetch upstream source

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
./runtime_instrumentation/fetch_dynamo_source.sh
```

This clones upstream into:

- `/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_upstream/dynamo`

The fetch script uses `GIT_LFS_SKIP_SMUDGE=1` so the source clone stays usable even if large LFS assets are not needed for instrumentation work.

### 2. Apply the tracked patch

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
./runtime_instrumentation/apply_runtime_json_logging_patch.sh
```

### 3. Build custom images

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

Default output tags:

- `local/dynamo-frontend:runtime-json-logs`
- `local/dynamo-sglang:runtime-json-logs`

### 3a. Worker-first activation

If you want to validate worker-side instrumentation before rebuilding the frontend, you can build and run only the worker image first.

Build only the worker image:

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
SKIP_FRONTEND=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

Then run the normal frontend image with the instrumented worker image:

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
DYN_RUNTIME_JSON_LOGS=1 \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

This lets you test:

- worker request lifecycle events
- worker prefill/decode observations
- worker log stability

without also rebuilding the frontend first.

To inspect the worker-side structured logs:

```bash
docker logs dynamo-sglang-worker 2>&1 | rg '\[RUNTIME_JSON\]'
```

Important limitation:

- worker-first activation is useful for validating worker instrumentation
- but full end-to-end external `request_id` propagation and frontend/router structured events still require the instrumented frontend image too

### 3b. Python-only worker dev mode

If you want to iterate on worker Python files without rebuilding the worker image every time, you can bind-mount the local worker source into the stock worker container.

This mode overrides only:

- `components/src/dynamo/common`
- `components/src/dynamo/sglang`
- `lib/bindings/python/src/dynamo/health_check.py`
- `lib/bindings/python/src/dynamo/runtime`

inside the worker container, while leaving compiled runtime pieces such as `dynamo._core` in the installed wheel untouched.

Example:

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
WORKER_DEV_MODE=1 \
WORKER_DEV_SOURCE_ROOT=/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_upstream/dynamo/components/src/dynamo \
WORKER_DEV_BINDINGS_ROOT=/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_upstream/dynamo/lib/bindings/python/src/dynamo \
DYN_RUNTIME_JSON_LOGS=1 \
./run_dynamo_worker.sh start
```

Single-host example:

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
WORKER_DEV_MODE=1 \
WORKER_DEV_SOURCE_ROOT=/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_upstream/dynamo/components/src/dynamo \
WORKER_DEV_BINDINGS_ROOT=/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_upstream/dynamo/lib/bindings/python/src/dynamo \
DYN_RUNTIME_JSON_LOGS=1 \
./run_dynamo_single_host.sh start
```

This is best for:

- Python-only worker logging changes
- faster iteration on `decode_handler.py`, `prefill_handler.py`, and `common/` helpers

This is not enough for:

- Rust changes like `kv.rs` or `selector.rs`
- frontend runtime instrumentation
- changes that require a rebuilt wheel or native extension

## Troubleshooting

### `apply_runtime_json_logging_patch.sh` fails after a fresh clone

If:

- `fetch_dynamo_source.sh` succeeded on a fresh upstream clone
- but `apply_runtime_json_logging_patch.sh` says the patch could not be applied cleanly

the most likely cause is that your local repo copy is stale and does not yet include the latest tracked patch file.

Fix:

1. update or re-upload this repo so EC2 has the latest:
   - [patches/dynamo_runtime_json_logging.patch](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/patches/dynamo_runtime_json_logging.patch)
2. remove the fresh clone and rerun:

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
rm -rf runtime_upstream/dynamo

./runtime_instrumentation/fetch_dynamo_source.sh
./runtime_instrumentation/apply_runtime_json_logging_patch.sh
```

### `runtime_upstream/dynamo` exists but is not a valid git clone

If the scripts complain that `runtime_upstream/dynamo` exists but is not a git repo or is incomplete, remove it and rerun:

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
rm -rf runtime_upstream/dynamo
./runtime_instrumentation/fetch_dynamo_source.sh
```

### 4. Run your existing local workflow against the custom images

Single-host:

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
DYN_RUNTIME_JSON_LOGS=1 \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

Multi-node head:

```bash
DYN_RUNTIME_JSON_LOGS=1 \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
./run_dynamo_head.sh start
```

Multi-node worker:

```bash
DYN_RUNTIME_JSON_LOGS=1 \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_worker.sh start
```

## Expected outcome

With these images running, your runtime-side logs should stop being only best-effort text parsing. They should start exposing:

- the same external `request_id` carried from AgentBench
- frontend dispatch events
- router worker-selection events
- worker-side request attach / completion events

That is the foundation for joining:

- `runtime_events.jsonl`
- `measurements.json`
- `cache_value_analysis.json`
- `kv_hierarchy_analysis.json`

against actual runtime-side facts instead of only inferred ones.
