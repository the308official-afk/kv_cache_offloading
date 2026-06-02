# AgentBench Experiment Runs

This guide runs one SWE-bench Pro task through the local AgentBench/Deep Agents
harness via Dynamo and SGLang. Use it to collect prompt-evolution artifacts,
runtime-hint evidence, cache/token stats, and task-completion evidence.

The core path is:

```text
SWE-bench Pro -> AgentBench runner -> prompt builder -> Deep Agents
-> Dynamo frontend -> SGLang worker -> result artifacts
```

## 1. Choose Model

Use `MODEL_KIND` to switch between the general Instruct model and the
code-specialized Coder model. Keep the same selected model for both Dynamo
startup and the AgentBench run command.

```bash
cd ~/kv_cache_offloading

MODEL_KIND="coder"  # coder or instruct
case "$MODEL_KIND" in
  coder)
    MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct'
    ;;
  instruct)
    MODEL_NAME='Qwen/Qwen2.5-7B-Instruct'
    ;;
  *)
    echo "MODEL_KIND must be coder or instruct" >&2
    exit 1
    ;;
esac

echo "Using model: $MODEL_NAME"
```

## 2. Start Dynamo/SGLang

Experiment artifacts can be collected with either non-instrumented or
instrumented Dynamo/SGLang.

- Use **non-instrumented** Dynamo/SGLang when the goal is only the prompt
  evolution story and AgentBench-side measurements.
- Use **instrumented** Dynamo/SGLang when the run also needs worker-side
  `agent_hints`, `hint_probe_id`, and `worker.decode.*` proof.

### 2.1 Non-Instrumented Run

Use this faster path when the only goal is to collect:

```text
prompt_evolution_report.*
prompt_evolution_values/*.json
others/measurements.*
others/cache_value_analysis.*
others/run_summary_table.csv
```

Start the published default Dynamo/SGLang runtime:

```bash
cd ~/kv_cache_offloading

export MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct'
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning"

./run_dynamo_single_host.sh stop

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
./run_dynamo_single_host.sh start
```

Do not set `FRONTEND_IMAGE` or `WORKER_IMAGE` for the non-instrumented path.
Leaving them unset uses the published default image instead of local
instrumented images.

Verify the model is available:

```bash
curl -fsS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/models
```

If this run hits the 32k context limit, restart with the larger SGLang context
override:

```bash
./run_dynamo_single_host.sh stop

SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length 65536' \
./run_dynamo_single_host.sh start
```

### 2.2 Instrumented Run

Use this path when the experiment should also include strong runtime-hint
evidence from worker logs.

If the SWE-bench prompt exceeds the default 32k context window, restart with the
larger SGLang context override:

```bash
./run_dynamo_single_host.sh stop

SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1 \
DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length 65536' \
./run_dynamo_single_host.sh start
```

See logs

```bash
docker logs -f dynamo-sglang-worker
```

Verify the model is available:

```bash
curl -fsS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/models
```

Verify the long-context override reached the worker container:

```bash
docker inspect dynamo-sglang-worker \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | \
  grep SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN
```

Expected:

```text
SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1
```

### 2.3 SGLang Host/Device Transfer Logging

Use this path when you want the SGLang worker to log host/device KV movement
directly. It bind-mounts a patched SGLang Python package into the worker and
emits structured transfer events from functions such as
`backup_from_device_all_layer()` and `load_to_device_per_layer()`.

Prepare the SGLang overlay once:

```bash
cd ~/kv_cache_offloading

export MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct'
export FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs
export WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs

docker image inspect "$FRONTEND_IMAGE" >/dev/null 2>&1 || \
  LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh

docker image inspect "$WORKER_IMAGE" >/dev/null

./runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh

cat upstream/sglang/SOURCE_IMAGE.txt

if [ -d upstream/sglang/python/sglang ]; then
  export SGLANG_ROOT="$PWD/upstream/sglang/python/sglang"
elif [ -d runtime_upstream/sglang/python/sglang ]; then
  export SGLANG_ROOT="$PWD/runtime_upstream/sglang/python/sglang"
else
  echo "Could not find extracted SGLang source" >&2
  exit 1
fi

echo "Using SGLang root: $SGLANG_ROOT"

grep -n "SEMANTIC_CONTEXT_FUNCTIONS\|patch_hiradix_cache\|transfer_token_context" \
  runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py

python3 runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py \
  --sglang-root "$SGLANG_ROOT"

grep -n "_sgl_log_transfer_event" \
  "$SGLANG_ROOT/srt/mem_cache/memory_pool_host.py"

grep -n "_sgl_transfer_token_context" \
  "$SGLANG_ROOT/srt/mem_cache/hiradix_cache.py"

# If a worker container already exists, this avoids pulling another image:
# SGLANG_CONTAINER=dynamo-sglang-worker \
# ./runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh

# If extraction fails, confirm this script is up to date:
# grep -n "importlib.util.find_spec" \
#   runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh
# grep -n "tar -C" \
#   runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh
```

If you encounter an out-of-host memory error, Try clearing page cache first

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh stop

free -h
sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
free -h
```

Preferred current extraction path is `upstream/sglang/python/sglang`. Older EC2
copies may still extract to `runtime_upstream/sglang/python/sglang`; the
`SGLANG_ROOT` detection above supports both. If the `grep` for
`SEMANTIC_CONTEXT_FUNCTIONS` prints nothing, sync the latest repo changes before
patching because that machine still has the older memory-pool-only patcher.

Start Dynamo/SGLang with the patched SGLang overlay and HiCache enabled:

```bash
./run_dynamo_single_host.sh stop

WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --enable-hierarchical-cache --mem-fraction-static 0.7 --hicache-ratio 1' \
WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$SGLANG_ROOT" \
SGLANG_TRANSFER_LOG=1 \
SGLANG_TRANSFER_LOG_SYNC_TIMING=1 \
DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
FRONTEND_IMAGE="$FRONTEND_IMAGE" \
WORKER_IMAGE="$WORKER_IMAGE" \
./run_dynamo_single_host.sh start
```

```bash
./run_dynamo_single_host.sh stop

WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --enable-hierarchical-cache --mem-fraction-static 0.7 --hicache-ratio 1' \
WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$SGLANG_ROOT" \
SGLANG_TRANSFER_LOG=1 \
SGLANG_TRANSFER_LOG_FULL_TOKENS=0 \
SGLANG_TRANSFER_LOG_TOKEN_PREVIEW=8 \
SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS=4 \
SGLANG_TRANSFER_LOG_INDEX_PREVIEW=0 \
SGLANG_TRANSFER_LOG_SYNC_TIMING=1 \
SGLANG_TRANSFER_LOG_VERBOSE=0 \
DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
FRONTEND_IMAGE="$FRONTEND_IMAGE" \
WORKER_IMAGE="$WORKER_IMAGE" \
./run_dynamo_single_host.sh start
```

Then start a test run (don't remove this)

```bash
cd ~/kv_cache_offloading

export AGENTBENCH_DEEPAGENTS_SOURCE=upstream
export AGENTBENCH_TASK_OVERRIDES_FILE=agentbench/prompt_overrides/task_overrides.txt
export AGENTBENCH_EXECUTION_LOOP=1
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=0
export AGENTBENCH_PRINT_CHECKPOINTS=0
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning"

AGENTBENCH_WORKFLOW_MODE=phased \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --prompt-evolution-value-char-limit 1000 \
  --quiet-checkpoints
```

Use `--hint-profile` for controlled hint experiments. Available profiles:

```text
baseline
high-reuse
low-reuse
high-priority
low-priority
long-output
short-output
```

Example single-profile run:

```bash
export AGENTBENCH_DEEPAGENTS_SOURCE=upstream
export AGENTBENCH_TASK_OVERRIDES_FILE=agentbench/prompt_overrides/task_overrides.txt
export AGENTBENCH_EXECUTION_LOOP=1
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=0
export AGENTBENCH_PRINT_CHECKPOINTS=0
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning"

AGENTBENCH_WORKFLOW_MODE=phased \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --hint-profile high-reuse \
  --prompt-evolution-value-char-limit 1000 \
  --quiet-checkpoints
```

Example matrix run:

```bash
export AGENTBENCH_DEEPAGENTS_SOURCE=upstream
export AGENTBENCH_TASK_OVERRIDES_FILE=agentbench/prompt_overrides/task_overrides.txt
export AGENTBENCH_EXECUTION_LOOP=1
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=0
export AGENTBENCH_PRINT_CHECKPOINTS=0
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning"

for HINT_PROFILE in baseline high-reuse low-reuse high-priority low-priority long-output short-output; do
  AGENTBENCH_WORKFLOW_MODE=phased \
  python3.11 agentbench/deepagents_swebench_single_host.py \
    --app-variant upstream_deploy_coding_agent \
    --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
    --model "$MODEL_NAME" \
    --dataset ScaleAI/SWE-bench_Pro \
    --split test \
    --index 0 \
    --hint-profile "$HINT_PROFILE" \
    --prompt-evolution-value-char-limit 1000 \
    --quiet-checkpoints
done
```

At the end of the run, AgentBench automatically builds the curated report under:

```text
experiments/reports/runs/<run_id>/
  run_manifest.json
  run_metrics.json
  run_metrics.csv
  transfer_summary.csv
  summary.md
```

It uses the exact AgentBench result directory and the current SGLang transfer
log. To disable this post-run report hook for a run, pass `--no-run-report` or
set `AGENTBENCH_AUTO_RUN_REPORT=0`.

This SGLang HiCache protocol expects the host pool to be larger than the device
KV pool, so do not lower `--hicache-ratio` below `1` on this runtime. If startup
fails with `Not enough host memory available`, either free host RAM and keep
`--hicache-ratio 1`, or reduce the GPU KV pool by lowering
`--mem-fraction-static` while keeping `--hicache-ratio 1`.

Transfer events are written to:

```text
experiments/raw/sglang_transfer_logs/sglang_transfer_events_<YYYYmmdd_HHMMSS>_<pid>.jsonl
experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl -> latest timestamped file
```

Inspect them:

```bash
ls -lh experiments/raw/sglang_transfer_logs/
tail -20 experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl
```

If the directory exists but no event file appears, first verify the patched
overlay reached the worker:

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

Summarize transfer counts, MB totals, and timing:

```bash
LATEST_TRANSFER_LOG="$(ls -t experiments/raw/sglang_transfer_logs/sglang_transfer_events_*.jsonl | head -1)"

python3 runtime_instrumentation/sglang_transfer_logging/parse_transfer_events.py \
  "$LATEST_TRANSFER_LOG" \
  --out-dir experiments/parsed/sglang_transfer_logs

head -20 experiments/parsed/sglang_transfer_logs/transfer_events.csv
cat experiments/parsed/sglang_transfer_logs/transfer_summary.csv
```

AgentBench builds the run-level report automatically. To inspect the latest
curated report:

```bash
LATEST_RUN_REPORT="$(ls -td experiments/reports/runs/* | head -1)"
cat "$LATEST_RUN_REPORT/summary.md"
cat "$LATEST_RUN_REPORT/run_metrics.csv"
cat "$LATEST_RUN_REPORT/subrequest_metrics.csv"
cat "$LATEST_RUN_REPORT/transfer_summary.csv"
```

For the first run after enabling direct attribution, check whether the new
request-matched evidence is active. `transfer_request_id_matched=True` means a
direct request id matched. `transfer_time_window_matched=True` is weaker: it
means a transfer event landed inside the subrequest timestamp window.
The direct path is enabled by the SGLang patcher wrapping cache insertion,
prefix matching, and host load-back with request context. Confirm those wrappers
after patching:

```bash
grep -n "_sgl_transfer_request_context" \
  "$SGLANG_ROOT/srt/mem_cache/radix_cache.py" \
  "$SGLANG_ROOT/srt/managers/schedule_batch.py" \
  "$SGLANG_ROOT/srt/managers/schedule_policy.py"
```

```bash
python3 - <<'PY'
import csv
from pathlib import Path

report = Path(__import__("os").environ["LATEST_RUN_REPORT"])
with (report / "run_metrics.csv").open() as handle:
    for row in csv.DictReader(handle):
        print(
            row["phase"],
            "worker_runtime_json_matched=", row.get("worker_runtime_json_matched"),
            "transfer_request_id_matched=", row.get("transfer_request_id_matched"),
        )
with (report / "subrequest_metrics.csv").open() as handle:
    for row in csv.DictReader(handle):
        print(
            row["phase"],
            "subrequest=", row.get("subrequest_index"),
            "sglang_request_id=", row.get("sglang_request_id"),
            "ttft_ms=", row.get("ttft_ms"),
            "cached_tokens=", row.get("cached_token_count"),
            "transfer_request_id_matched=", row.get("transfer_request_id_matched"),
            "transfer_time_window_matched=", row.get("transfer_time_window_matched"),
        )
PY
```

For old runs, or when you want to rebuild a report manually:

```bash
LATEST_RESULT="$(ls -td experiments/raw/agentbench/results/* | head -1)"

python3 experiments/scripts/agentbench_report/build_run_report.py \
  --agentbench-result-dir "$LATEST_RESULT" \
  --transfer-log experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl
```

`run_metrics.json` keeps the old runtime cache fields as
`runtime_*_reported`, but its main `cache_hit`, `cached_token_count`,
`recomputed_prefix_tokens`, and `cache_reuse_ratio` fields are effective values
derived from API usage, SGLang worker prefill logs, scheduler cached blocks, and
runtime events. For non-streaming runs, `ttft_ms` uses the best available
evidence in this order: `runtime_events.latency.ttft_ms`, worker
`[RUNTIME_JSON]` request-received to request-attached timing, then plain worker
logs from frontend request timestamp to first SGLang decode batch.

For source clarity, `run_metrics.json` includes `metric_sources`. Fields prefixed
with `sglang_*` are parsed directly from SGLang worker logs; transfer totals are
parsed from the SGLang transfer JSONL. When worker `[RUNTIME_JSON]` or transfer
events include request metadata, the report uses direct request-id matching.
Otherwise, AgentBench still supplies phase names, request IDs, hint metadata,
task metadata, patch outcome, and client/API usage accounting.
`subrequest_metrics.csv` is the best file when one phase sends multiple model
requests, because it splits rows by SGLang `runtime_context_id` /
`sglang_request_id`.

See the detailed workflow in
[runtime_instrumentation/sglang_transfer_logging/README.md](../runtime_instrumentation/sglang_transfer_logging/README.md).

Transfer JSON now separates the low-level copy facts from semantic token
context:

- `num_bytes_observed` and `elapsed_ms_wall` come from `memory_pool_host.py`.
  `elapsed_ms` is kept as a compatibility alias for wall time.
- `timestamp` is the UTC wall-clock time emitted by the transfer logger.
  `timestamp_ns` is kept for high-resolution ordering.
- `direction` is `device_to_host` for GPU/HBM to host write-back, or
  `host_to_device` for host to GPU/HBM reload. The parsed
  `transfer_events.csv` also includes `direction_label` as `device->host` or
  `host->device` for each source log line.
- `kv_num_bytes_estimated` and `kv_num_mb_estimated` estimate the actual KV
  payload size using token-granular memory-pool metadata. Prefer these for
  transfer volume.
- `kv_num_bytes_estimated_page_granular` is emitted separately for comparison
  when page-granular accounting is useful.
- `semantic_token_ids_preview`, `semantic_token_count`, and
  `semantic_token_source` come from HiRadix `write_backup()` / `load_back()`;
  the extractor follows nested fields such as `node.key.token_ids`.
- If the patched worker can see request context, transfer rows also include
  request attribution such as `request_id`, `external_request_id`,
  `runtime_context_id`, `sglang_request_id`, `phase`, `hint_profile`, and
  `agent_hints_source`. `request_context_function` shows where that context was
  captured, such as `cache_finished_req`,
  `Req.init_next_round_input.match_prefix`, or
  `SchedulePolicy.add_one_req.init_load_back`.
- `token_preview_source=semantic_context` means `token_ids_preview` is a real
  semantic token preview. `token_preview_source=local_heuristic` means the event
  did not have HiRadix token context and the preview should not be treated as
  tokenizer IDs.
- `SGLANG_TRANSFER_LOG_VERBOSE=1` restores tensor details and empty diagnostic
  fields. `SGLANG_TRANSFER_LOG_SYNC_TIMING=1` adds synchronized CUDA timing.

## 3. Prepare AgentBench Environment

Before running the task on a new machine, complete
[README_AGENTBENCH_ENVIRONMENT.md](README_AGENTBENCH_ENVIRONMENT.md).

That setup verifies:

- the harness writes `workspace.patch` at the report root
- Node is visible from the shell used to launch AgentBench
- NodeBB npm dependencies are installed
- Redis-backed NodeBB test dependencies are available
- `nodebb-test-redis` and `config.json` exist
- selected NodeBB tests get past environment setup errors

Do not rerun AgentBench while the manual preflight still fails with:

```text
node: command not found
Cannot find module '...'
ENOENT ... config.json
```

## 4. Run One AgentBench Task

Before running AgentBench, choose which DeepAgents Python library to import:

```bash
export AGENTBENCH_DEEPAGENTS_SOURCE=upstream
export AGENTBENCH_TASK_OVERRIDES_FILE=agentbench/prompt_overrides/task_overrides.txt
export AGENTBENCH_EXECUTION_LOOP=1
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=0
export AGENTBENCH_PRINT_CHECKPOINTS=0
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning"
```

Use `upstream` for the current tool-loop experiments. The known-good run shape
that emitted `read_file`, `write_file`, `edit_file`, and `execute` used the
cloned DeepAgents library under `upstream/deepagents/libs/deepagents`.
Use `python_environment` only when intentionally comparing against the installed
DeepAgents package.

`AGENTBENCH_TASK_OVERRIDES_FILE` points to an independent text file with prompt
nudges for smaller models. Unset it or empty the file for a vanilla prompt.
`AGENTBENCH_EXECUTION_LOOP=1` enables the harness-driven execution loop:
inspect, edit, test, then fix/test until a patch plus validation attempt exists
or the max step count is reached. `AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6`
limits the loop. `AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1` requires an
`execute` validation attempt before the loop can finish. Keep
`AGENTBENCH_EXECUTION_GUARD=0` when the loop is enabled so the old read-only
retry guard does not mix with the stronger loop controller. Set
`AGENTBENCH_PRINT_CHECKPOINTS=0` or pass `--quiet-checkpoints` to keep
`# [CHECK_POINT]` blocks out of the terminal while still saving
`others/checkpoints.json`. `PYTHONWARNINGS` hides dependency deprecation
warnings from the live terminal output. If Hugging Face warns about
unauthenticated requests, optionally set `HF_TOKEN` in your shell before
starting Dynamo or AgentBench.

Automatic SWE-bench runs use shared checkouts under `agentbench/repos/`.
The harness now resets tracked changes and removes untracked non-ignored files
before each shared-checkout run so stale files do not leak between experiments.
Use `--keep-shared-workspace-changes` only when deliberately debugging a dirty
checkout. Patch capture also includes newly-created untracked files, so
`workspace.patch` can contain files created with `write_file`.

### 4.1 Baseline Single-Loop Run

Use this first when you want a complete run that actually attempts the task.
This mode gives Deep Agents one continuous tool loop instead of splitting the
work into separate planning/execution/review calls.

```bash
cd ~/kv_cache_offloading

MODEL_KIND=coder  # coder or instruct

case "$MODEL_KIND" in
  coder)
    MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct'
    ;;
  instruct)
    MODEL_NAME='Qwen/Qwen2.5-7B-Instruct'
    ;;
esac

echo "Using model: $MODEL_NAME"
```

```bash
cd ~/kv_cache_offloading

export AGENTBENCH_DEEPAGENTS_SOURCE=upstream
export AGENTBENCH_TASK_OVERRIDES_FILE=agentbench/prompt_overrides/task_overrides.txt
export AGENTBENCH_PRINT_CHECKPOINTS=0
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning"

AGENTBENCH_WORKFLOW_MODE=baseline \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --prompt-evolution-value-char-limit 1000 \
  --quiet-checkpoints
```

Check if the run succeeded in executing the task assigned it

```bash
LATEST_RESULT="$(ls -td experiments/raw/agentbench/results/* | head -1)"
echo "$LATEST_RESULT"

wc -c "$LATEST_RESULT/workspace.patch"
cat "$LATEST_RESULT/others/git_status.txt"
cat "$LATEST_RESULT/others/git_diff_stat.txt"
cat "$LATEST_RESULT/others/git_untracked_files.txt"
```

### 4.2 Phased Run

Use this when the goal is phase-level stats: planning, execution,
patch-generation, and review. It is better for runtime analysis, but if the
planning response is empty or malformed, later phases may inherit bad context.

```bash
cd ~/kv_cache_offloading

export AGENTBENCH_DEEPAGENTS_SOURCE=upstream
export AGENTBENCH_TASK_OVERRIDES_FILE=agentbench/prompt_overrides/task_overrides.txt
export AGENTBENCH_EXECUTION_LOOP=1
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=0
export AGENTBENCH_PRINT_CHECKPOINTS=0
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning"

AGENTBENCH_WORKFLOW_MODE=phased \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --hint-profile high-reuse \
  --prompt-evolution-value-char-limit 1000 \
  --quiet-checkpoints
```

The `--prompt-evolution-value-char-limit 1000` option keeps each captured
before/after value readable by truncating long strings with an ellipsis.

### 4.3 Multi-Task Run

The harness runs one SWE-bench task per process via `--index`. To try multiple
tasks, loop over indexes:

```bash
cd ~/kv_cache_offloading

export MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct'
export AGENTBENCH_DEEPAGENTS_SOURCE=upstream
export AGENTBENCH_TASK_OVERRIDES_FILE=agentbench/prompt_overrides/task_overrides.txt
export AGENTBENCH_EXECUTION_LOOP=1
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=0
export AGENTBENCH_PRINT_CHECKPOINTS=0
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning"

START_INDEX=0
END_INDEX=3

for INDEX in $(seq "$START_INDEX" "$END_INDEX"); do
  echo "===== Running SWE-bench index $INDEX ====="

  AGENTBENCH_WORKFLOW_MODE=phased \
  python3.11 agentbench/deepagents_swebench_single_host.py \
    --app-variant upstream_deploy_coding_agent \
    --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
    --model "$MODEL_NAME" \
    --dataset ScaleAI/SWE-bench_Pro \
    --split test \
    --index "$INDEX" \
    --hint-profile high-reuse \
    --prompt-evolution-value-char-limit 1000 \
    --quiet-checkpoints \
  || echo "Index $INDEX failed; continuing"

  echo
done
```

Then check which tasks produced patches:

```bash
cd ~/kv_cache_offloading

for REPORT in experiments/reports/runs/*; do
  [ -f "$REPORT/summary.md" ] || continue
  echo "===== $(basename "$REPORT") ====="
  grep -E "Patch nonempty|Git diff nonempty|Model|App variant|Hint profile" "$REPORT/summary.md"
done
```

This is the fastest way to find SWE-bench tasks that produce a patch. For clean
per-task run-level transfer totals, restart Dynamo before each task so every run
gets a fresh `sglang_transfer_events_*.jsonl`. If you keep the same worker
running, `subrequest_metrics.csv` is still useful because it uses per-subrequest
time windows, but the run-level transfer total may include earlier tasks from
the same worker session.

## 5. Find The Latest Result

```bash
LATEST_RESULT="$(ls -td experiments/raw/agentbench/results/* | head -1)"
echo "$LATEST_RESULT"
```

## 6. Check Task Completion

Use this before reading the richer reports. A complete task attempt should
usually leave a non-empty patch or git diff.

```bash
cat "$LATEST_RESULT/others/git_status.txt"
cat "$LATEST_RESULT/others/git_diff_stat.txt"
cat "$LATEST_RESULT/others/git_untracked_files.txt"
wc -c "$LATEST_RESULT/workspace.patch"
```

If the execution loop was enabled, inspect the harness-directed steps:

```bash
cat "$LATEST_RESULT/others/execution_loop_table.csv"
cat "$LATEST_RESULT/others/execution_loop_trace.json"
```

Useful signal:

```text
workspace.patch size > 0
git_status.txt or git_diff_stat.txt is non-empty
model output includes edit/write/execute tool activity, not only ls/read_file
```

New files are expected to appear in `git_untracked_files.txt` and are included
in `workspace.patch`. If `git_status.txt` shows `??` files but
`workspace.patch` is still empty, that run used an older copy of the harness.

If baseline edits files but phased does not, debug the phased orchestration. If
both baseline and phased runs fail to edit files, try the other model by
rerunning from **1. Choose Model** with `MODEL_KIND=instruct` or
`MODEL_KIND=coder`.

If the latest run still writes `others/workspace.patch`, that run used an older
copy of the harness or was created before the report-layout update. New runs
should write:

```text
experiments/raw/agentbench/results/<run_id>/workspace.patch
```

## 7. Inspect Prompt Evolution Artifacts

```bash
cat "$LATEST_RESULT/prompt_evolution_values/index.json"
ls "$LATEST_RESULT/prompt_evolution_values"
cat "$LATEST_RESULT/prompt_evolution_report.md"
```

Main prompt-evolution artifacts:

```text
prompt_evolution_report.json
prompt_evolution_report.md
prompt_evolution_report.csv
prompt_evolution_values/index.json
prompt_evolution_values/*.json
```

The per-stage value files under `prompt_evolution_values/` contain:

```json
{
  "stage": "...",
  "diff_summary": {},
  "before": {},
  "after": {}
}
```

## 8. Inspect Measurement And Cache Stats

```bash
cat "$LATEST_RESULT/others/run_summary_table.csv"
cat "$LATEST_RESULT/others/measurement_summary_table.csv"
cat "$LATEST_RESULT/others/cache_value_summary_table.csv"
cat "$LATEST_RESULT/others/kv_hierarchy_summary_table.csv"
```

For comparisons across hint configurations, prefer the curated run report:

```bash
LATEST_RUN_REPORT="$(ls -td experiments/reports/runs/* | head -1)"
cat "$LATEST_RUN_REPORT/run_metrics.csv"
```

For the compact agent-behavior view, use:

```bash
cat "$LATEST_RUN_REPORT/agent_behavior_summary.md"
cat "$LATEST_RUN_REPORT/agent_behavior_summary.csv"
cat "$LATEST_RUN_REPORT/agent_tool_calls.md"
cat "$LATEST_RUN_REPORT/agent_tool_calls.csv"
cat experiments/reports/latest_agent_behavior_summary.csv
cat experiments/reports/latest_agent_tool_calls.csv
```

This is the quick table to check after each run. It reports the run/repo/runtime,
execution subrequest count, tool calls, tools used, patch size, and phase-level
runtime/cache/transfer fields.

`agent_tool_calls.md` shows the exact tool-call arguments when available. For
`execute`, check the `Command` column to confirm whether the model actually ran
the expected validation command.

Build a multi-run comparison after a profile matrix:

```bash
COMPARISON_ID="hint_matrix_$(date +%Y%m%d_%H%M%S)"

python3 experiments/scripts/agentbench_report/build_comparison_report.py \
  --latest 7 \
  --comparison-id "$COMPARISON_ID"

LATEST_COMPARISON="$(ls -td experiments/reports/comparisons/* | head -1)"
cat "$LATEST_COMPARISON/summary.md"
cat "$LATEST_COMPARISON/runs.csv"
cat "$LATEST_COMPARISON/phase_metrics.csv"
cat "$LATEST_COMPARISON/transfer_metrics.csv"
cat "$LATEST_COMPARISON/profile_phase_summary.csv"
```

The comparison report writes:

```text
experiments/reports/comparisons/<comparison_id>/
  comparison_manifest.json
  comparison_metrics.json
  runs.csv
  phase_metrics.csv
  transfer_metrics.csv
  profile_phase_summary.csv
  summary.md
```

`phase_metrics.csv` includes direct-attribution columns when available:
`worker_runtime_json_matched`, `worker_runtime_json_cached_tokens`,
`worker_runtime_json_request_received_to_attached_ms`,
`transfer_request_id_matched`,
`transfer_device_to_host_kv_mb_for_request`,
`transfer_host_to_device_kv_mb_for_request`, and
`transfer_cuda_sync_ms_for_request`.

For phase-level runs, inspect:

```bash
cat "$LATEST_RESULT/step_results.json"
cat "$LATEST_RESULT/stage_lifecycle_table.csv"
```

## 9. Verify Runtime-Hint Evidence

```bash
grep -R "hint_probe_id\|agent_hints\|worker.decode" -n "$LATEST_RESULT" | head -50
cat "$LATEST_RESULT/runtime_hint_alignment_analysis.md"
cat "$LATEST_RESULT/others/runtime_hint_alignment_summary_table.csv"
```

Success signal: `others/worker_runtime.log` contains
`worker.decode.request_received`, `worker.decode.request_attached`, or
`worker.decode.request_completed` events with AgentBench `agent_hints`, including
`hint_probe_id: "...::hint_probe"`.

This worker-side success signal requires the instrumented runtime. A
non-instrumented run can still produce the prompt-evolution files, but it will
not prove that hints reached the SGLang worker logs.

## 10. Expected Prompt Evolution Stages

Typical stages include:

- `task_input`
- `formatted_prompt`
- `final_model_request`
- `system_context`
- `tool_runtime_context`
- `runtime_preprocessing`
- `model_behavior`
