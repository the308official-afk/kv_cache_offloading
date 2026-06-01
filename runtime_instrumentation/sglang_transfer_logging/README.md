# SGLang Transfer Logging

This workflow makes host/device KV movement instrumentation repeatable. It
extracts the exact `sglang` Python package from the worker image, patches it in
the repo, and bind-mounts the patched package into the Dynamo SGLang worker.

## What It Instruments

The patch targets two layers:

- `memory_pool_host.py` for actual transfer timing, direction, tensor shapes,
  and observed bytes.
- `hiradix_cache.py` for semantic token context around `write_backup()` and
  `load_back()`.

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
`load_back()`.

## 1. Extract SGLang From the Worker Image

Use the same image you plan to run:

```bash
cd ~/kv_cache_offloading

SGLANG_IMAGE=nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.2 \
./runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh
```

If you use a local instrumented worker image:

```bash
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
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
```

## 3. Run With the Patched SGLang Overlay

Single-host:

```bash
cd ~/kv_cache_offloading

WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$PWD/upstream/sglang/python/sglang" \
SGLANG_TRANSFER_LOG=1 \
./run_dynamo_single_host.sh start
```

Worker-only:

```bash
cd ~/kv_cache_offloading

WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$PWD/upstream/sglang/python/sglang" \
SGLANG_TRANSFER_LOG=1 \
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
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --enable-hierarchical-cache --hicache-ratio 0.1' \
WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$PWD/upstream/sglang/python/sglang" \
SGLANG_TRANSFER_LOG=1 \
./run_dynamo_single_host.sh start
```

If startup fails with `Not enough host memory available`, lower
`--hicache-ratio` to `0.05` or free host memory before starting the worker.

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
transfer_summary.csv
```

## Useful Knobs

```bash
SGLANG_TRANSFER_LOG=1
SGLANG_TRANSFER_LOG_DIR="$PWD/experiments/raw/sglang_transfer_logs"
SGLANG_TRANSFER_LOG_BASENAME=sglang_transfer_events_$(date +%Y%m%d_%H%M%S)_$$
SGLANG_TRANSFER_LOG_PATH=/transfer-logs/${SGLANG_TRANSFER_LOG_BASENAME}.jsonl
SGLANG_TRANSFER_LOG_TOKEN_PREVIEW=32
SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS=16
SGLANG_TRANSFER_LOG_FULL_TOKENS=0
SGLANG_TRANSFER_LOG_INDEX_PREVIEW=0
SGLANG_TRANSFER_LOG_INDEX_PREVIEW_COUNT=32
SGLANG_TRANSFER_LOG_TOKEN_TENSOR_SYNC=0
```

Use full semantic-token logging only for small requests:

```bash
SGLANG_TRANSFER_LOG_FULL_TOKENS=1
```

Use index preview only when you are comfortable with a small extra GPU-to-CPU
sync for index tensors:

```bash
SGLANG_TRANSFER_LOG_INDEX_PREVIEW=1
```

## Expected Event Shape

```json
{
  "event": "sglang.transfer",
  "function": "backup_from_device_all_layer",
  "direction": "device_to_host",
  "elapsed_ms": 0.42,
  "num_bytes_observed": 1048576,
  "num_mb_observed": 1.0,
  "tensor_details": [
    {
      "name": "cache_loc",
      "shape": [64],
      "dtype": "torch.int64",
      "device": "cuda:0",
      "num_bytes": 512
    }
  ],
  "semantic_context_function": "write_backup",
  "semantic_token_source": "write_backup.node.key",
  "semantic_token_count": 64,
  "semantic_token_ids_preview": [151644, 872, 198],
  "semantic_token_ids_sha256": "...",
  "token_ids_preview": [151644, 872, 198],
  "token_preview_source": "semantic_context",
  "device_indices_count": 2048,
  "device_indices_preview": [],
  "device_indices_preview_skipped": "cuda_tensor_set_SGLANG_TRANSFER_LOG_INDEX_PREVIEW=1"
}
```

## Notes

`token_ids_preview` is now semantic when a transfer occurs under
`hiradix_cache.py`'s `write_backup()` or `load_back()`. In that case,
`token_preview_source` is `semantic_context`, and the same values are available
under `semantic_token_ids_preview`.

If no semantic context is active, the event falls back to a low-level local
heuristic and marks `token_preview_source` as `local_heuristic`. Treat that
fallback as debugging metadata, not tokenizer IDs.

The next files to instrument are:

- `cache_controller.py` for transfer reasons
- `hicache_storage.py` for storage-tier reads/writes
