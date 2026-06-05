# SGLang Transfer Logging

This workflow makes host/device KV movement instrumentation repeatable. It
extracts the exact `sglang` Python package from the worker image, patches it in
the repo, and bind-mounts the patched package into the Dynamo SGLang worker.

## What It Instruments

The patch targets four layers:

- `memory_pool_host.py` for actual transfer timing, direction, tensor shapes,
  and observed bytes.
- `hiradix_cache.py` for semantic token context around `write_backup()` and
  `load_back()`.
- `radix_cache.py`, `schedule_batch.py`, and `schedule_policy.py` for request
  context around cache insertion, prefix matching, and host load-back.
- `cache_controller.py` for carrying that request/token context through async
  cache operations into the low-level memory-pool copy.

The low-level transfer functions are logged as:

- `backup_from_device_all_layer()` as `device_to_host`
- `load_to_device_per_layer()` as `host_to_device`

The patch writes structured log lines with this prefix:

```text
[SGLANG_TRANSFER_JSON]
```

Each event includes elapsed time, observed tensor bytes, tensor shapes/dtypes,
direction, function name, cache-index previews when enabled, and semantic token
previews when the transfer happens under HiRadix `write_backup()` or
`load_back()`. When request context is visible in SGLang, the event can also
include fields like `sglang_request_id`, `runtime_context_id`, `phase`,
`hint_profile`, and `request_context_function`.

## 1. Extract SGLang From the Worker Image

Use the same image you plan to run:

```bash
cd ~/kv_cache_offloading

WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh
```

Extract from the same worker image that will run the overlay. The SGLang Python
source and compiled `sgl_kernel` package must match. If they do not, startup can
fail with imports such as `cannot import name ... from sgl_kernel`.

If you want to use the stock NGC image instead:

```bash
SGLANG_IMAGE=nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.2 \
./runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh
```

If the worker container is already present and you want to avoid another image
pull, extract from the container:

```bash
SGLANG_CONTAINER=dynamo-sglang-worker \
./runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh
```

If extraction fails, first check whether the EC2 copy has the latest extractor:

```bash
grep -n "importlib.util.find_spec" \
  runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh
```

The extractor streams files with `tar` instead of raw `docker cp` because some
SGLang packages contain out-of-tree symlinks, such as
`srt/mem_cache/cpp_radix_tree/.clang-format`, that are irrelevant to runtime
instrumentation but can make `docker cp` fail.

Then inspect where the image keeps Python packages:

```bash
docker run --rm --entrypoint python3 \
  nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.2 \
  -c 'import sys; print("\n".join(sys.path))'
```

The extracted package is written to:

```text
upstream/sglang/python/sglang
```

## 2. Patch Transfer Logging

```bash
cd ~/kv_cache_offloading

python3 runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py \
  --sglang-root upstream/sglang/python/sglang
```

Success should mention:

```text
patched transfer functions:
  - backup_from_device_all_layer (... occurrences)
  - load_to_device_per_layer (... occurrences)
patched semantic context functions:
  - write_backup (... occurrences)
  - load_back (... occurrences)
patched async transfer context propagation:
  - CacheOperation context capture
  - write-back transfer context (... calls)
  - load-back transfer context (... calls)
patched request context around cache insertion:
  - cache_finished_req request context (... occurrences)
  - cache_unfinished_req request context (... occurrences)
patched request context around prefix matching:
  - Req.init_next_round_input match_prefix context (... calls)
patched request context around host load-back:
  - SchedulePolicy init_load_back context (... calls)
```

If no functions are patched, inspect:

```bash
find upstream/sglang/python/sglang -name memory_pool_host.py -print
rg -n "backup_from_device_all_layer|load_to_device_per_layer" \
  upstream/sglang/python/sglang
```

`memory_pool_host.py` can contain several classes with the same method names.
The patcher should instrument every occurrence. Confirm with:

```bash
grep -n "_sgl_log_transfer_event" \
  upstream/sglang/python/sglang/srt/mem_cache/memory_pool_host.py

grep -n "_sgl_transfer_token_context" \
  upstream/sglang/python/sglang/srt/mem_cache/hiradix_cache.py

grep -n "_sgl_transfer_request_context" \
  upstream/sglang/python/sglang/srt/mem_cache/radix_cache.py \
  upstream/sglang/python/sglang/srt/managers/schedule_batch.py \
  upstream/sglang/python/sglang/srt/managers/schedule_policy.py
```

## 3. Run With the Patched SGLang Overlay

Single-host:

```bash
cd ~/kv_cache_offloading

WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$PWD/upstream/sglang/python/sglang" \
SGLANG_TRANSFER_LOG=1 \
SGLANG_TRANSFER_LOG_PROFILE=light \
DYN_RUNTIME_JSON_LOGS=1 \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

`DYN_RUNTIME_JSON_LOGS=1` plus the local instrumented Dynamo images are needed
when you want request IDs, phase labels, and hints to show up directly in
worker-side reports. The SGLang overlay still provides the transfer rows.

Worker-only:

```bash
cd ~/kv_cache_offloading

WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$PWD/upstream/sglang/python/sglang" \
SGLANG_TRANSFER_LOG=1 \
SGLANG_TRANSFER_LOG_PROFILE=light \
./run_dynamo_worker.sh start
```

By default, events are written to:

```text
experiments/raw/sglang_transfer_logs/sglang_transfer_events_<YYYYmmdd_HHMMSS>_<pid>.jsonl
experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl -> latest timestamped file
```

They also appear in worker stderr/stdout, so this should work too:

```bash
docker logs dynamo-sglang-worker 2>&1 | grep '\[SGLANG_TRANSFER_JSON\]'
```

If the directory exists but no event file appears, verify the overlay and env
first:

```bash
docker inspect dynamo-sglang-worker \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | \
  grep -E 'SGLANG_TRANSFER_LOG|SGLANG_TRANSFER_LOG_PATH'

docker inspect dynamo-sglang-worker \
  --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}' | \
  grep sglang_transfer_overlay

docker exec dynamo-sglang-worker python3 - <<'PY'
import inspect
import sglang.srt.mem_cache.memory_pool_host as mph
print(mph.__file__)
print("transfer marker:", "_sgl_log_transfer_event" in inspect.getsource(mph))
PY
```

If the marker is present, the run has not hit the instrumented host-tier
movement functions yet. Enable HiCache and use enough cache pressure to trigger
`backup_from_device_all_layer()` / `load_to_device_per_layer()`:

```bash
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --enable-hierarchical-cache --mem-fraction-static 0.7 --hicache-ratio 1' \
WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$PWD/upstream/sglang/python/sglang" \
SGLANG_TRANSFER_LOG=1 \
SGLANG_TRANSFER_LOG_SYNC_TIMING=1 \
./run_dynamo_single_host.sh start
```

This runtime expects the host pool to be larger than the device KV pool. Keep
`--hicache-ratio 1`; if host RAM is too tight, lower `--mem-fraction-static` or
free host memory before starting the worker.

## 4. Summarize Transfer Events

From the direct JSONL file:

```bash
LATEST_TRANSFER_LOG="$(ls -t experiments/raw/sglang_transfer_logs/sglang_transfer_events_*.jsonl | head -1)"

python3 runtime_instrumentation/sglang_transfer_logging/parse_transfer_events.py \
  "$LATEST_TRANSFER_LOG" \
  --out-dir experiments/parsed/sglang_transfer_logs
```

Or from captured worker logs:

```bash
docker logs dynamo-sglang-worker > experiments/raw/sglang_transfer_logs/worker.log 2>&1

python3 runtime_instrumentation/sglang_transfer_logging/parse_transfer_events.py \
  experiments/raw/sglang_transfer_logs/worker.log \
  --out-dir experiments/parsed/sglang_transfer_logs
```

Main outputs:

```text
transfer_events.jsonl
transfer_events.csv
transfer_summary.csv
```

`transfer_events.csv` is the easiest file for per-line inspection. It includes
the source log line number, `timestamp`, `timestamp_ns`, `direction`, a readable
`direction_label` (`host->device` or `device->host`), function name, token
preview, estimated KV MB, and timing fields. When request metadata is visible
inside the patched worker, it also includes attribution fields such as
`request_id`, `external_request_id`, `runtime_context_id`, `sglang_request_id`,
`phase`, `hint_profile`, and `agent_hints_source`.

## Useful Knobs

Use profiles first:

```bash
SGLANG_TRANSFER_LOG=1
SGLANG_TRANSFER_LOG_PROFILE=light
```

Profiles:

```text
off     disables patched transfer logging
light   fast default; request attribution, direction, byte counts, wall timing
timing  light plus synchronized CUDA transfer timing
full    timing plus semantic token previews, token counts, and token hashes
```

`light` is the effective default when `SGLANG_TRANSFER_LOG=1` and no profile is
set. Use `full` only for small runs where token-prefix inspection matters.

Low-level overrides remain available:

```bash
SGLANG_TRANSFER_LOG_DIR="$PWD/experiments/raw/sglang_transfer_logs"
SGLANG_TRANSFER_LOG_BASENAME=sglang_transfer_events_$(date +%Y%m%d_%H%M%S)_$$
SGLANG_TRANSFER_LOG_PATH=/transfer-logs/${SGLANG_TRANSFER_LOG_BASENAME}.jsonl
SGLANG_TRANSFER_LOG_TOKEN_PREVIEW=8
SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS=4
SGLANG_TRANSFER_LOG_FULL_TOKENS=0
SGLANG_TRANSFER_LOG_INDEX_PREVIEW=0
SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT=32
SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC=0
SGLANG_TRANSFER_LOG_SYNC_TIMING=0
SGLANG_TRANSFER_LOG_SEMANTIC_TOKENS=0
SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=0
SGLANG_TRANSFER_LOG_VERBOSE=0
```

`SGLANG_TRANSFER_LOG_PROFILE=timing` or `SGLANG_TRANSFER_LOG_SYNC_TIMING=1` is
preferred for precise transfer timing because it synchronizes CUDA devices
before the event is written. It is heavier than `light`. The transfer logger
also emits a UTC `timestamp`; the run report can use that as a weaker
time-window fallback when direct request-id attribution is not visible.

Use full semantic-token logging only for small requests:

```bash
SGLANG_TRANSFER_LOG_PROFILE=full
```

`SGLANG_TRANSFER_LOG_FULL_TOKENS=1` additionally writes the full token list
instead of only previews and hashes.

Use index preview only when you are comfortable with a small extra GPU-to-CPU
sync for index tensors:

```bash
SGLANG_TRANSFER_LOG_INDEX_PREVIEW=1
```

Use synchronized CUDA timing only for measurement runs. It inserts a device
sync while logging, so it is more honest but heavier:

```bash
SGLANG_TRANSFER_LOG_SYNC_TIMING=1
```

Use overhead timing only for short calibration runs. It records how much time
the logger spends collecting metadata, semantic tokens, CUDA sync timing, and
JSON serialization:

```bash
SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=1
```

Use verbose mode when you want tensor details, empty fallback fields, and other
diagnostics in every event:

```bash
SGLANG_TRANSFER_LOG_VERBOSE=1
```

## Expected Event Shape

```json
{
  "event": "sglang.transfer",
  "transfer_log_profile": "light",
  "function": "backup_from_device_all_layer",
  "direction": "device_to_host",
  "elapsed_ms": 0.42,
  "elapsed_ms_wall": 0.42,
  "num_bytes_observed": 1024,
  "num_mb_observed": 0.0009765625,
  "host_indices_count": 64,
  "device_indices_count": 64,
  "kv_item_granularity_assumption": "token",
  "kv_num_bytes_estimated": 3670016,
  "kv_num_mb_estimated": 3.5,
  "kv_num_bytes_estimated_page_granular": 234881024,
  "kv_num_mb_estimated_page_granular": 224.0,
  "kv_estimate_formula": "2*head_num*head_dim*dtype.itemsize",
  "sglang_request_id": "abc123",
  "request_context_function": "cache_finished_req",
  "overhead_total_logger_ms": 0.12
}
```

With `SGLANG_TRANSFER_LOG_PROFILE=full`, events can also include
`semantic_context_function`, `semantic_token_source`, `semantic_token_count`,
`semantic_token_ids_preview`, `semantic_token_ids_sha256`, `token_ids_preview`,
and `token_preview_source`.

## Notes

`token_ids_preview` is now semantic when a transfer occurs under
`hiradix_cache.py`'s `write_backup()` or `load_back()`. In that case,
`token_preview_source` is `semantic_context`, and the same values are available
under `semantic_token_ids_preview`. The extractor follows nested HiRadix fields
such as `node.key.token_ids`, which is where the semantic token IDs are still
available before the lower memory-pool copy.

`num_bytes_observed` is a conservative scan of tensors visible in the Python
frame, often just `host_indices` and `device_indices`. For KV payload size, use
`kv_num_bytes_estimated` / `kv_num_mb_estimated`; those are token-granular and
computed from the memory-pool shape metadata, dtype item size, and layer count.
The page-granular estimate is still emitted separately as
`kv_num_bytes_estimated_page_granular` for comparison.

`elapsed_ms` is kept as a compatibility alias for `elapsed_ms_wall`. When
`SGLANG_TRANSFER_LOG_SYNC_TIMING=1`, events also include
`elapsed_ms_cuda_sync` and `cuda_sync_wait_ms`.

If no semantic context is active, the event falls back to a low-level local
heuristic and marks `token_preview_source` as `local_heuristic`. Treat that
fallback as debugging metadata, not tokenizer IDs.

Default events are compact. Tensor details, empty local-token fallback fields,
and null errors are emitted only when `SGLANG_TRANSFER_LOG_VERBOSE=1`.
Overhead timing fields are emitted only when
`SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=1`.

`request_context_function` tells you where the request metadata was captured.
The most useful values are `cache_finished_req` / `cache_unfinished_req` for
device-to-host write-back, `Req.init_next_round_input.match_prefix` for prefix
lookup, and `SchedulePolicy.add_one_req.init_load_back` for host-to-device
reload.

The next file to instrument is `hicache_storage.py` if you need storage-tier
read/write details below the host-memory tier.
