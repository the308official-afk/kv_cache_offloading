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
