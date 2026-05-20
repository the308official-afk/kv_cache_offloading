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

## Hint alignment evidence

AgentBench now writes a `runtime_hint_alignment` report for each run. That report checks three different things:

- whether AgentBench attached hints to the request
- whether frontend or worker structured logs directly showed those hints
- whether runtime behavior was consistent with a hint

This matters because these are not the same claim. A hint can be present in the request wrapper while the SGLang worker log still shows `agent_hints=null`. In that case, the report records propagation but does not claim worker-side compliance.

For future runs, direct worker-side proof requires `[RUNTIME_JSON]` worker events to contain non-null `agent_hints` or explicit worker/runtime fields derived from those hints.

New runs also include a `hint_probe_id` in the AgentBench hint payload. Think of it as a bright tracking label. The structured runtime logs should preserve these fields when the hint payload is visible:

- `agent_hints`
- `agent_hints_source`
- `agent_hints_keys`
- `hint_probe_id`

If `hint_probe_id` appears in AgentBench but not in worker logs, the report can say exactly that the probe reached the request wrapper but did not show direct worker-side evidence.

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

### 2. Prepare the instrumented Dynamo source

For a fresh machine, use the all-in-one preparation script. It fetches Dynamo
source if needed, applies the tracked patches, repairs known source drift, and
verifies the markers required for hint-alignment experiments.

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
./runtime_instrumentation/prepare_instrumented_dynamo_source.sh
```

After this succeeds, build the images in step 3.

### 2a. Apply the tracked logging patch manually

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
./runtime_instrumentation/apply_runtime_json_logging_patch.sh
```

### 2b. Apply the agent-hint preservation patch manually

This patch makes Dynamo preserve AgentBench hint metadata after the HTTP
boundary. It keeps custom `nvext.agent_hints` fields, copies them into
`extra_args.runtime_observability`, and allows worker-side logs to prove whether
the SGLang worker received the same hint probe.

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
./runtime_instrumentation/apply_dynamo_hint_preservation_patch.sh
```

### 3. Build custom images

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

Default output tags:

- `local/dynamo-frontend:runtime-json-logs`
- `local/dynamo-sglang:runtime-json-logs`

If the frontend build runs out of disk while installing benchmark extras, use
the lean frontend mode. AgentBench runs outside the Dynamo frontend container,
so the frontend image does not need Dynamo's internal benchmark package for this
experiment:

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

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
- full frontend request-forwarding changes
- changes that require a rebuilt wheel or native extension

### 3c. Worker hot-patch without rebuilding

If the worker container is already running and you only need to add Python-side hint visibility fields, use the hot-patch script:

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
./runtime_instrumentation/hotpatch_worker_hint_logging.sh
```

This script:

- finds the installed worker Python files inside `dynamo-sglang-worker`
- creates `dynamo.common.runtime_logging` inside the container if it is missing
- copies them out to a temporary directory
- patches worker `[RUNTIME_JSON]` events to include `agent_hints_source`, `agent_hints_keys`, and `hint_probe_id`
- copies the files back into the running container
- compile-checks the patched files
- restarts only the worker container

This is temporary by design. If the container is recreated from the image, rerun the hot-patch script.

### 3d. Frontend hot-patch without rebuilding

If the frontend container is already running and you only need to prove whether
AgentBench hints reach the Dynamo frontend, use the frontend hot-patch script:

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
./runtime_instrumentation/hotpatch_frontend_hint_logging.sh
```

This script:

- finds the installed frontend processor Python file inside `dynamo-frontend`
- creates `dynamo.common.runtime_logging` inside the container if it is missing
- copies the frontend file out to a temporary directory
- patches the processor `generator` method to emit `frontend.request.received`
- includes `agent_hints`, `agent_hints_source`, `agent_hints_keys`, and `hint_probe_id`
- copies the patched files back into the running container
- compile-checks the patched files
- restarts only the frontend container

This checkpoint intentionally answers one narrow question: did Dynamo frontend
receive the hint payload from the client request? If the frontend sees the probe
but the worker still logs `agent_hints=null`, the gap is between frontend
preprocessing/dispatch and the SGLang worker request.

After the next run, check:

```bash
docker logs dynamo-frontend 2>&1 | grep -E 'frontend.request.received|agent_hints_source|hint_probe_id|agent_hints_keys'
```

This is temporary by design. If the container is recreated from the image, rerun
the hot-patch script.

### 3e. Frontend-boundary proxy without rebuilding

When `DYN_CHAT_PROCESSOR` is unset or set to `dynamo`, chat requests use Dynamo's
native frontend path. In that mode, Python hot-patching `vllm_processor.py` or
`sglang_processor.py` will not prove what the HTTP frontend received.

Use the hint logging proxy to add a no-rebuild checkpoint immediately before
Dynamo's HTTP endpoint:

```text
AgentBench -> hint logging proxy -> Dynamo frontend -> SGLang worker
```

Start the proxy in one terminal:

```bash
cd /Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading
python3.11 runtime_instrumentation/hint_logging_proxy.py \
  --listen-port 8001 \
  --target-base-url http://127.0.0.1:8000 \
  --log-file /tmp/dynamo_hint_proxy_runtime.log
```

Then run AgentBench against the proxy URL and tell the report where the proxy log
is:

```bash
AGENTBENCH_FRONTEND_BOUNDARY_LOG=/tmp/dynamo_hint_proxy_runtime.log \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:8001/v1/chat/completions \
  --model Qwen/Qwen2.5-7B-Instruct \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0
```

The proxy emits `[RUNTIME_JSON]` events with:

- `frontend.boundary.request_received`
- `frontend.boundary.request_completed`
- `agent_hints`
- `agent_hints_source`
- `agent_hints_keys`
- `hint_probe_id`

AgentBench copies the proxy log into `others/frontend_boundary_proxy.log` and
also folds it into the frontend hint-alignment evidence.

AgentBench normally sends the hint payload through:

- `nvext.agent_hints`

There is also an opt-in `extra_args.runtime_observability.agent_hints` experiment
controlled by `AGENTBENCH_SEND_TOP_LEVEL_EXTRA_ARGS=1`. Dynamo's native OpenAI
validation may reject that top-level field with HTTP 400, so it is disabled by
default.

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
