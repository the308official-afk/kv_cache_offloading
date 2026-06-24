# AgentBench Experiments

Use this guide as a live EC2 runbook for AgentBench + Deep Agents + Dynamo +
SGLang experiments.

The runtime path is:

```text
SWE-bench Pro -> AgentBench -> Deep Agents -> Dynamo frontend -> SGLang worker -> reports
```

## Quick Decision Guide

- **Basic AgentBench run**: use Experiment 1.
- **Model/tool-call debugging**: use Experiment 2.
- **Precise KV-transfer attribution**: use Experiment 3.
- **SGLang logging speed comparison**: use Experiment 4.
- **Hint-profile comparisons**: use Experiment 5.
- **Many SWE-bench tasks**: use Experiment 6.
- **Many models**: use Experiment 7.
- **Full design-space sweep**: use Experiment 8.
- **KV retention/eviction probe**: use Experiment 9.
- **Cache-control retention**: use Experiment 10.
- **Priority scheduling**: use Experiment 11.

For transfer-logging internals, see
[runtime_instrumentation/sglang_transfer_logging/README.md](../runtime_instrumentation/sglang_transfer_logging/README.md).
For tool-call diagnostics, see
[README_TOOL_CALL_DIAGNOSTICS.md](README_TOOL_CALL_DIAGNOSTICS.md).

## Common Setup

Run this once per shell before an experiment.

```bash
cd ~/kv_cache_offloading

MODEL_KIND="coder"  # coder, coder30b, or instruct
case "$MODEL_KIND" in
  coder)
    MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct'
    ;;
  coder30b)
    MODEL_NAME='Qwen/Qwen3-Coder-30B-A3B-Instruct'
    ;;
  instruct)
    MODEL_NAME='Qwen/Qwen2.5-7B-Instruct'
    ;;
  *)
    echo "MODEL_KIND must be coder, coder30b, or instruct" >&2
    exit 1
    ;;
esac

export MODEL_NAME
export DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-ec2}"  # ec2 or gh200
source runtime_instrumentation/dynamo_machine_profile.sh
source runtime_instrumentation/sglang_source_profile.sh
export AGENTBENCH_DEEPAGENTS_SOURCE=upstream
export AGENTBENCH_TASK_OVERRIDES_FILE=agentbench/prompt_overrides/task_overrides.txt
export AGENTBENCH_EXECUTION_LOOP=0
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=1
export AGENTBENCH_PRINT_CHECKPOINTS=0
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning"

echo "Using model: $MODEL_NAME"
echo "Using machine profile: $DYNAMO_MACHINE_PROFILE"
echo "Frontend image: $FRONTEND_IMAGE"
echo "Worker image: $WORKER_IMAGE"
echo "Pinned SGLang source image: $SGLANG_SOURCE_IMAGE"
```

Shared default readiness timing is now automatic for all experiment wrappers
and `run_dynamo_single_host.sh`:

- `MODEL_READY_RETRIES=900`
- `MODEL_READY_DELAY_SECS=3`
- `MODEL_READY_STABLE_HITS=2`
- `MODEL_SMOKE_RETRIES=180`
- `MODEL_SMOKE_DELAY_SECS=15`
- `MODEL_COOLDOWN_SECS=60`

Only export those manually when you want to override the shared defaults.

For wrapper-driven runs, you should now also see these terminal signals:

- `(3/6) MODEL READINESS ACTIVE (extended model wait and smoke timing are active)`
- `(5/6) MODEL READINESS GO (model registration and smoke test both passed)`

Precise-attribution note:

- the precise wrappers now share one reusable helper:
  [runtime_instrumentation/precise_sglang_helper.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/precise_sglang_helper.sh)
- the precise wrappers also now share one machine-aware runtime image helper:
  [runtime_instrumentation/ensure_precise_runtime_ready.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/ensure_precise_runtime_ready.sh)
- the helper uses a known-good pinned SGLang source image by default:
  [runtime_instrumentation/sglang_source_profile.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/sglang_source_profile.sh)
- this helper auto-extracts and re-patches the SGLang overlay before precise runs
- and the runtime-image helper now resolves the machine profile (`ec2` or `gh200`),
  prints the exact `FRONTEND_IMAGE` / `WORKER_IMAGE`, checks they exist, and
  auto-builds them on fresh machines by default inside the precise wrappers
- if you want check-only behavior instead, set:
  `AUTO_BUILD_PRECISE_IMAGES=0`
- so you should not need to manually re-run the SGLang extract/patch steps for
  every precise experiment anymore
- you may still want to run the helper manually when debugging a fresh machine:
  `./runtime_instrumentation/ensure_precise_runtime_ready.sh --machine-profile ec2 --build-if-missing`
- if you intentionally want a different SGLang source, override it explicitly:
  `export SGLANG_IMAGE=...` before the run

Machine profile quick switch:

```bash
# known-good EC2 / x86 path
export DYNAMO_MACHINE_PROFILE=ec2
source runtime_instrumentation/dynamo_machine_profile.sh

# GH200 / ARM64 path
export DYNAMO_MACHINE_PROFILE=gh200
source runtime_instrumentation/dynamo_machine_profile.sh
```

For precise experiments, treat this machine profile as required. The new
runtime helper will now stop early if `DYNAMO_MACHINE_PROFILE` is unset.

All experiments below inherit this execution policy unless you explicitly
override it in the shell.

These are now the default safe readiness settings across the automation
wrappers, and they are the recommended values for larger models such as
`Qwen/Qwen3-Coder-30B-A3B-Instruct`:

```bash
export MODEL_READY_RETRIES=900
export MODEL_READY_DELAY_SECS=3
export MODEL_READY_STABLE_HITS=2
export MODEL_SMOKE_RETRIES=180
export MODEL_SMOKE_DELAY_SECS=15
export MODEL_COOLDOWN_SECS=60
```

What these two groups mean:

```text
MODEL_READY_*   controls how long ./run_dynamo_single_host.sh start waits for model registration
MODEL_SMOKE_*   controls how long experiment wrappers wait after Dynamo has started
```

If this is a fresh machine, install Python 3.11 first, then install the
upstream Deep Agents dependency:

```bash
cd ~/kv_cache_offloading

sudo dnf install -y python3.11 python3.11-pip || true
python3.11 -m ensurepip --upgrade || true
python3.11 --version

mkdir -p upstream

if [ ! -f upstream/deepagents/libs/deepagents/pyproject.toml ]; then
  git clone https://github.com/langchain-ai/deepagents.git upstream/deepagents
  git -C upstream/deepagents checkout 2cf7e25dbb40e783d9d4d545c29e595800bf314f
fi

python3.11 -m pip install --upgrade pip
python3.11 -m pip install ./upstream/deepagents/libs/deepagents
python3.11 -m pip install -r agentbench/requirements.txt
```

If this is a fresh machine and you plan to run instrumented Dynamo/SGLang
experiments, prepare the local Dynamo source clone first:

```bash
cd ~/kv_cache_offloading

./runtime_instrumentation/prepare_instrumented_dynamo_source.sh

ls -ld ~/kv_cache_offloading/upstream/dynamo
```

The source fetch step now checks out a pinned Dynamo revision that is known to
work with this repo's instrumentation. That avoids breakage from upstream
layout drift on fresh machines.

If the prepare step prints `Patch could not be applied cleanly`, do not stop
there. On a fresh upstream clone that can be expected. The script now repairs
known Dynamo source drift automatically. The real success signal is the final:

```text
Instrumented Dynamo source is ready.
```

You will also now see a short preparation summary like:

```text
Preparation summary:
  runtime_json_patch: drift_repaired
  hint_preservation_patch: applied_or_already_present
Safe to continue:
  - yes
```

`drift_repaired` means the tracked patch no longer matched the newest upstream
source exactly, but the automatic repair step restored the required
instrumentation anyway.

That repair path also recreates `runtime_logging.py` automatically if the
runtime patch did not lay it down on a fresh Dynamo clone, and patches the old
SGLang worker handler files directly when they still use the pre-instrumentation
layout. That now includes older prefill-handler layouts where the helper
function signature and completion logging block still differ from the newer
instrumented form.

The prepare step now verifies the full worker-runtime event path too, not just
the first marker. In other words, it checks for:

- `worker.decode.request_received`
- `worker.decode.request_attached`
- `worker.decode.request_completed`
- `worker.prefill.request_received`
- `worker.prefill.request_attached`
- `worker.prefill.request_completed`

So if `prepare_instrumented_dynamo_source.sh` ends successfully, it should now
be genuinely safe to continue into the image build.

Then build the local runtime-logging images once:

```bash
cd ~/kv_cache_offloading

LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh

docker image inspect "$FRONTEND_IMAGE" >/dev/null
docker image inspect "$WORKER_IMAGE" >/dev/null
echo "instrumented images ok"
```

If you suspect Docker reused a stale worker-image layer after a source repair,
force a no-cache rebuild:

```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-ec2}"   # or gh200
source runtime_instrumentation/dynamo_machine_profile.sh

./run_dynamo_single_host.sh stop || true
docker rm -f dynamo-sglang-worker dynamo-frontend dynamo-etcd dynamo-nats 2>/dev/null || true
docker rmi "$WORKER_IMAGE" || true

SKIP_FRONTEND=1 DOCKER_BUILD_NO_CACHE=1 LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

This is slower, but it prevents Docker from quietly reusing an older broken
worker layer after the Dynamo source patch changed.

If a running worker shows a half-patched decode path, for example:

- `worker.decode.request_attached` exists
- but `attach_logged = False` is still missing inside
  `DecodeWorkerHandler._process_token_stream(...)`

then use the same no-cache rebuild path above. That specific symptom means the
older decode-handler layout was only partially rewritten, and the fresh worker
image must be rebuilt from the updated repair script.

The build script now refuses to produce `runtime-json-logs` images from an
unprepared Dynamo source tree. If it fails, rerun:

```bash
cd ~/kv_cache_offloading
./runtime_instrumentation/prepare_instrumented_dynamo_source.sh
LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

If the image build fails with `no space left on device`, it means Docker ran
out of disk while unpacking or copying layers. Before retrying:

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh stop || true

df -h /
docker system df

docker container prune -f
docker image prune -f
docker builder prune -f
```

If the machine still does not have enough free space and you do not need old
Docker state:

```bash
docker system prune -af
docker builder prune -af

df -h /
docker system df
```

For instrumented Dynamo rebuilds, keep at least 80-120 GB free.

Those local image tags are not pulled from a registry. They must be built on
each new machine before experiments that use:

- `$FRONTEND_IMAGE`
- `$WORKER_IMAGE`

If you see an error like `Dynamo source directory not found`, it usually means
`~/kv_cache_offloading/upstream/dynamo` has not been created yet. Run the
prepare step above, then rerun the image build.

If you are on a Grace Hopper / ARM64 machine, set the machine profile before
the image build:

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

Profile behavior:

```text
ec2   -> x86/host-default build platform, image tags ending in -ec2
gh200 -> linux/arm64 build platform, image tags ending in -gh200
```

Using profile-specific image tags prevents a GH200 rebuild from overwriting the
known-good EC2 image names.

Before NodeBB SWE-bench tasks, complete
[README_AGENTBENCH_ENVIRONMENT.md](README_AGENTBENCH_ENVIRONMENT.md). Do not run
AgentBench while that preflight still fails with missing `node`, missing npm
modules, or missing `config.json`.

## Experiment 1: Basic AgentBench Run

Use this to test whether Dynamo, the model, Deep Agents, and AgentBench can run
without SGLang transfer instrumentation.

This collects prompt evolution, AgentBench measurements, tool behavior, patch
output, and curated reports. It does **not** collect host/device KV-transfer
events.

### Step 1: Start Non-Instrumented Dynamo

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh stop

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
./run_dynamo_single_host.sh start
```

These startup-registration waits are the default safe values. Re-export them
explicitly if you want to sanity-check your shell before a restart:

```bash
export MODEL_READY_RETRIES=900
export MODEL_READY_DELAY_SECS=3
export MODEL_READY_STABLE_HITS=2
```

Watch the SGLang worker logs after restart:

```bash
docker logs -f dynamo-sglang-worker
```

Verify:

```bash
curl -fsS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/models
```

### Step 2: Run One Task

```bash
cd ~/kv_cache_offloading

AGENTBENCH_WORKFLOW_MODE=baseline \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --prompt-evolution-value-char-limit 1000 \
  --quiet-checkpoints
```

### Step 3: Check Result

```bash
LATEST_RESULT="$(ls -td experiments/raw/agentbench/results/* | head -1)"
LATEST_REPORT="$(ls -td experiments/reports/runs/* | head -1)"

echo "$LATEST_RESULT"
echo "$LATEST_REPORT"

wc -c "$LATEST_RESULT/workspace.patch"
cat "$LATEST_RESULT/others/git_status.txt"
cat "$LATEST_RESULT/others/git_diff_stat.txt"
cat "$LATEST_REPORT/phase_summary.md"
cat "$LATEST_REPORT/tool_call_details.md"
```

Success signal:

```text
workspace.patch size > 0
tool_call_details shows edit/write/execute activity
```

## Experiment 2: Tool-Call Diagnostics

Use this when the model is not reliably editing files or calling tools. This is
the fastest way to separate model/parser issues from AgentBench issues.

### Step 1: Start Dynamo

Use the same non-instrumented Dynamo command from Experiment 1.

### Step 2: Probe Raw Dynamo Tool Calls

```bash
cd ~/kv_cache_offloading

python3.11 agentbench/diagnose_dynamo_tool_calls.py \
  --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
  --model "$MODEL_NAME"
```

Success signal:

```text
required tool_choice returns finish_reason='tool_calls'
named tool_choice returns finish_reason='tool_calls'
```

### Step 3: Probe Deep Agents Tool Loop

```bash
python3.11 agentbench/diagnose_deepagents_tool_loop.py \
  --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
  --model "$MODEL_NAME" \
  --case ls-read-execute

python3.11 agentbench/diagnose_deepagents_tool_loop.py \
  --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
  --model "$MODEL_NAME" \
  --case edit-validate
```

Success signal:

```text
case_success=True
required_tools_observed=True
multi_tool_loop_observed=True
```

Diagnostics are written under:

```text
experiments/raw/agentbench/diagnostics/
```

## Experiment 3: Precise KV Transfer Attribution

Use this to answer, per phase/request:

- Did this request reuse more cached KV?
- Did it move less data?
- Did it trigger host-to-device reloads?
- Did TTFT improve?
- Which AgentBench phase caused the transfer?

This is the main experiment for hint-impact analysis. It uses instrumented
Dynamo images, a patched SGLang overlay, HiCache, runtime JSON logs, and
request-id transfer attribution.

### Step 1: First-Time Runtime Prep For Manual Precise Attribution

```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-ec2}"   # or gh200
source runtime_instrumentation/dynamo_machine_profile.sh

if ! docker image inspect "$FRONTEND_IMAGE" >/dev/null 2>&1 || \
   ! docker image inspect "$WORKER_IMAGE" >/dev/null 2>&1; then
  LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh
fi

source runtime_instrumentation/sglang_source_profile.sh
./runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh

if [ -d upstream/sglang/python/sglang ]; then
  export SGLANG_ROOT="$PWD/upstream/sglang/python/sglang"
elif [ -d runtime_upstream/sglang/python/sglang ]; then
  export SGLANG_ROOT="$PWD/runtime_upstream/sglang/python/sglang"
else
  echo "Could not find extracted SGLang source" >&2
  exit 1
fi

python3 runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py \
  --sglang-root "$SGLANG_ROOT"

cat upstream/sglang/SOURCE_IMAGE.txt
```

Use this manual prep block when you are:

- preparing a fresh machine
- rebuilding instrumented Dynamo images
- or manually launching instrumented Dynamo/SGLang outside the higher-level
  experiment wrappers

For the precise wrappers in later experiments, the SGLang extract/patch refresh
is now handled automatically by the shared helper. The part that is still
manual on a fresh machine is building the instrumented Dynamo images when they
do not already exist.

Manual machine-aware runtime image check/build:

```bash
./runtime_instrumentation/ensure_precise_runtime_ready.sh \
  --machine-profile "${DYNAMO_MACHINE_PROFILE:-ec2}" \
  --build-if-missing
```

Verify the patch:

```bash
grep -n "_sgl_log_transfer_event" \
  "$SGLANG_ROOT/srt/mem_cache/memory_pool_host.py"

grep -n "_sgl_transfer_token_context" \
  "$SGLANG_ROOT/srt/mem_cache/hiradix_cache.py"

grep -n "_sgl_transfer_request_context" \
  "$SGLANG_ROOT/srt/mem_cache/radix_cache.py" \
  "$SGLANG_ROOT/srt/managers/schedule_batch.py" \
  "$SGLANG_ROOT/srt/managers/schedule_policy.py"
```

### Step 2: Start Instrumented Dynamo/SGLang

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh stop

WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority --enable-hierarchical-cache --mem-fraction-static 0.7 --hicache-ratio 1' \
WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$SGLANG_ROOT" \
SGLANG_TRANSFER_LOG=1 \
SGLANG_TRANSFER_LOG_PROFILE=full \
SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=1 \
DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
FRONTEND_IMAGE="$FRONTEND_IMAGE" \
WORKER_IMAGE="$WORKER_IMAGE" \
./run_dynamo_single_host.sh start
```

Watch the SGLang worker logs after restart:

```bash
docker logs -f dynamo-sglang-worker
```

Default rule for this README: use both `--enable-priority-scheduling` and
`--radix-eviction-policy priority` unless a section explicitly says otherwise.

If startup fails with host-memory pressure, stop Dynamo and clear page cache:

```bash
./run_dynamo_single_host.sh stop
free -h
sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
free -h
```

This HiCache runtime expects the host pool to be larger than the device KV pool,
so keep `--hicache-ratio 1` or higher.

### Step 3: Verify Instrumentation Is Active

```bash
./runtime_instrumentation/check_precise_attribution_ready.sh transfer

docker inspect dynamo-sglang-worker \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | \
  grep -E 'SGLANG_TRANSFER_LOG|SGLANG_TRANSFER_LOG_SYNC_TIMING|DYN_RUNTIME_JSON_LOGS'

docker inspect dynamo-sglang-worker \
  --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}' | \
  grep sglang_transfer_overlay

docker exec -i dynamo-sglang-worker python3 - <<'PY'
import inspect
import sglang.srt.mem_cache.memory_pool_host as mph
print(mph.__file__)
print("_sgl_log_transfer_event:", "_sgl_log_transfer_event" in inspect.getsource(mph))
PY
```

Expected:

```text
SGLANG_TRANSFER_LOG=1
SGLANG_TRANSFER_LOG_PROFILE=full
_sgl_log_transfer_event: True
```

If the automatic preflight fails, use these manual debug signals:

```bash
docker exec -i dynamo-sglang-worker python3 - <<'PY'
import inspect
from dynamo.sglang.request_handlers.llm import decode_handler
src = inspect.getsource(decode_handler.DecodeWorkerHandler._process_token_stream)
print("attach_logged = False" in src)
print("worker.decode.request_attached" in src)
print("request: Dict[str, Any]" in src)
PY

docker exec -i dynamo-sglang-worker python3 - <<'PY'
import inspect
import sglang.srt.mem_cache.memory_pool_host as mph
src = inspect.getsource(mph)
print("_sgl_log_transfer_event" in src)
PY
```

Use `SGLANG_TRANSFER_LOG_PROFILE=off` to disable transfer logging.
Use `SGLANG_TRANSFER_LOG_PROFILE=light` for fast/light transfer logging.
Use `SGLANG_TRANSFER_LOG_PROFILE=timing` for synchronized CUDA transfer timing.
Use `SGLANG_TRANSFER_LOG_PROFILE=full` as the default when you need semantic
token IDs, previews, and token hashes.
Add `SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=1` only for short calibration runs
where you want to measure how expensive the logging itself is.

Overhead calibration examples:

```bash
SGLANG_TRANSFER_LOG_PROFILE=light SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=1
SGLANG_TRANSFER_LOG_PROFILE=timing SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=1
SGLANG_TRANSFER_LOG_PROFILE=full SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=1
```

### Step 4: Run One Phased Task

```bash
cd ~/kv_cache_offloading

AGENTBENCH_WORKFLOW_MODE=phased \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --hint-provider agentbench \
  --hint-profile high-reuse \
  --prompt-evolution-value-char-limit 1000 \
  --quiet-checkpoints
```

### Step 5: Check Direct Attribution

```bash
export LATEST_REPORT="$(ls -td experiments/reports/runs/* | head -1)"
echo "$LATEST_REPORT"

python3 - <<'PY'
import csv
from pathlib import Path

report = Path(__import__("os").environ["LATEST_REPORT"])
rows = list(csv.DictReader((report / "phase_runtime_metrics.csv").open()))

for row in rows:
    print(
        row.get("phase"),
        "request_id=", row.get("request_id"),
        "worker_json=", row.get("worker_runtime_json_matched"),
        "transfer_id=", row.get("transfer_request_id_matched"),
        "ttft_source=", row.get("ttft_source"),
        "cache_source=", row.get("cache_hit_source"),
        "h2d_mb=", row.get("transfer_host_to_device_kv_mb_for_request"),
        "d2h_mb=", row.get("transfer_device_to_host_kv_mb_for_request"),
    )
PY
```

Precision success criteria:

```text
worker_runtime_json_matched=True
transfer_request_id_matched=True
ttft_source=worker_runtime_json.request_received_to_attached
```

If `transfer_request_id_matched=True`, the transfer evidence is matched by
request/context ID, not just timestamp windows.

### Step 6: Inspect Transfer Logs

```bash
ls -lh experiments/raw/sglang_transfer_logs/
tail -5 experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl

cat "$LATEST_REPORT/phase_runtime_metrics.csv"
cat "$LATEST_REPORT/model_request_metrics.csv"
cat "$LATEST_REPORT/transfer_events_by_function.csv"
cat "$LATEST_REPORT/phase_summary.md"
```

Important fields:

```text
direction
function
request_id / external_request_id / sglang_request_id
phase
hint_profile
kv_num_mb_estimated
elapsed_ms_cuda_sync
```

`semantic_token_ids_preview` and `semantic_token_count` appear only with
`SGLANG_TRANSFER_LOG_PROFILE=full`.

## Experiment 4: SGLang Logging Profile Wall-Time Comparison

Use this to answer one simple question: which transfer-logging profile makes.
the whole AgentBench task run faster or slower?

This measures only the AgentBench command wall-clock time. Dynamo startup,
model load time, and one small warmup generation are not included.

```bash
cd ~/kv_cache_offloading

PROFILES="off light timing full" \
INDEX=0 \
HINT_PROVIDER=agentbench \
HINT_PROFILE=high-reuse \
experiments/scripts/compare_sglang_logging_profiles_walltime.sh
```

Output:

```bash
cat experiments/reports/sglang_logging_profile_walltime.csv
```

The script is finished when it prints:

```text
All 4 logging-profile timing runs completed.
Wall-clock comparison written to: experiments/reports/sglang_logging_profile_walltime.csv
```

The CSV is intentionally small:

```text
profile,run_seconds,run_id
```

For this experiment the script forces:

```text
SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=0
```

That keeps the comparison focused on end-to-end run speed for `off`, `light`,
`timing`, and `full`.

## Experiment 5: Hint Profile Comparison

Use this after Experiment 3 is running successfully. It compares hint profiles
on the same SWE-bench task.

### Step 1: Run The Matrix

```bash
cd ~/kv_cache_offloading

for HINT_PROFILE in baseline high-reuse low-reuse high-priority low-priority long-output short-output; do
  echo "===== $HINT_PROFILE ====="

  AGENTBENCH_WORKFLOW_MODE=phased \
  python3.11 agentbench/deepagents_swebench_single_host.py \
    --app-variant upstream_deploy_coding_agent \
    --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
    --model "$MODEL_NAME" \
    --dataset ScaleAI/SWE-bench_Pro \
    --split test \
    --index 0 \
    --hint-provider agentbench \
    --hint-profile "$HINT_PROFILE" \
    --prompt-evolution-value-char-limit 1000 \
    --quiet-checkpoints
done
```

Hint provider options:

```text
agentbench   Use the selected --hint-profile values. This is the default.
deepagents   Derive deterministic hints from Deep Agents runtime phase state.
none         Send request context only, without nvext.agent_hints.
```

For portability, the broader AgentBench / Deep Agents path now sends only the
Dynamo-safe runtime-control subset in `nvext.agent_hints`:

- `priority`
- `osl`
- `expected_output_tokens`
- `speculative_prefill`
- `latency_sensitivity`

Experiment metadata such as `hint_profile`, `hint_probe_id`, `agent_phase`,
and `program_id` is carried separately through `nvext.request_context`,
`nvext.agent_context`, and `nvext.annotations`.

To compare providers on the same task:

```bash
cd ~/kv_cache_offloading

for HINT_PROVIDER in agentbench deepagents none; do
  echo "===== provider=$HINT_PROVIDER ====="

  AGENTBENCH_WORKFLOW_MODE=phased \
  python3.11 agentbench/deepagents_swebench_single_host.py \
    --app-variant upstream_deploy_coding_agent \
    --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
    --model "$MODEL_NAME" \
    --dataset ScaleAI/SWE-bench_Pro \
    --split test \
    --index 0 \
    --hint-provider "$HINT_PROVIDER" \
    --hint-profile high-reuse \
    --prompt-evolution-value-char-limit 1000 \
    --quiet-checkpoints
done
```

`deepagents` is an adapter mode: Deep Agents supplies the phase/runtime state,
and `agentbench/deepagents_app/src/hint_providers.py` converts that state into
the Dynamo/SGLang hint fields.

### Step 2: Build Comparison Report

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

Use these fields to compare hint impact:

```text
hint_profile
hint_provider
phase
ttft_ms
cached_token_count
recomputed_prefix_tokens
cache_reuse_ratio
transfer_request_id_matched
transfer_host_to_device_kv_mb_for_request
transfer_device_to_host_kv_mb_for_request
transfer_cuda_sync_ms_for_request
```

Recommended statistics:

```text
TTFT p50/p95
cache reuse ratio
cached tokens
recomputed prefix tokens
host->device transfer count and MB
device->host transfer count and MB
transfer ms per MB
transfer ms per cached token
direct attribution rate
semantic token count
unique semantic token hashes
```

## Experiment 6: Multi-Task Batch

Use this to scan many SWE-bench tasks and find runs where the model actually
edits files and creates patches.

```bash
cd ~/kv_cache_offloading

export AGENTBENCH_EXECUTION_LOOP=0
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=1

START_INDEX=0 \
END_INDEX=5 \
HINT_PROFILE=high-reuse \
./agentbench/run_swebench_batch_single_host.sh
```

### Prompt Evolution Batch

Use this when your main goal is to generate prompt-evolution reports across a
range of SWE-bench Pro tasks.

Manual version:

```bash
cd ~/kv_cache_offloading

export MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct'
export AGENTBENCH_EXECUTION_LOOP=0
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=1
export AGENTBENCH_PRINT_CHECKPOINTS=0

START_INDEX=0 \
END_INDEX=5 \
HINT_PROFILE=high-reuse \
HINT_PROVIDER=agentbench \
FRONTEND_URL="http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
MODEL="$MODEL_NAME" \
./agentbench/run_swebench_batch_single_host.sh
```

Automated version: stop Dynamo, restart it with the chosen model, wait for
`/v1/models`, run a smoke test, then launch the batch.

These larger-model readiness and smoke-test values are already the default for
this batch wrapper, but you can re-export them explicitly before starting:

```bash
export MODEL_READY_RETRIES=900
export MODEL_READY_DELAY_SECS=3
export MODEL_READY_STABLE_HITS=2
export MODEL_SMOKE_RETRIES=180
export MODEL_SMOKE_DELAY_SECS=15
export MODEL_COOLDOWN_SECS=60
```

```bash
cd ~/kv_cache_offloading

export MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct'
export AGENTBENCH_EXECUTION_LOOP=0
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=1
export AGENTBENCH_PRINT_CHECKPOINTS=0

START_INDEX=0 \
END_INDEX=5 \
HINT_PROFILE=high-reuse \
HINT_PROVIDER=agentbench \
FRONTEND_URL="http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
./agentbench/run_prompt_evolution_batch_single_host.sh \
  "$MODEL_NAME"
```

To watch the worker after the restart:

```bash
docker logs -f dynamo-sglang-worker
```

Note:

- `run_dynamo_single_host.sh start` uses:
  - `MODEL_READY_RETRIES`
  - `MODEL_READY_DELAY_SECS`
  - `MODEL_READY_STABLE_HITS`
- this wrapper then uses:
  - `MODEL_SMOKE_RETRIES`
  - `MODEL_SMOKE_DELAY_SECS`
  - `MODEL_COOLDOWN_SECS`
- for larger models, set both groups

This produces prompt-evolution summaries such as:

```bash
cat experiments/reports/prompt_evolution_task_summary.csv
cat experiments/reports/prompt_evolution_run_overview.csv
```

Batch outputs:

```text
experiments/reports/batches/<batch_id>/
  progress.log
  progress_overview.csv
```

Global summaries:

```bash
cat experiments/reports/latest_runs_overview.md
cat experiments/reports/latest_runs_task_summary.md
cat experiments/reports/latest_runs_execution_prompts.md
cat experiments/reports/all_runs_overview.csv
cat experiments/reports/all_runs_task_summary.csv
cat experiments/reports/all_runs_execution_prompts.csv
```

## Experiment 7: Multi-Model Multi-Task Batch

Use this to run Experiment 6 across multiple LLMs. Dynamo is restarted once per
model, waits for the model to register, then runs a real smoke-test request
before sending AgentBench requests.

Pass models directly to the script:

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh stop
./experiments/scripts/clean_experiment_data.sh --yes

export AGENTBENCH_EXECUTION_LOOP=0
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=1

START_INDEX=0 \
END_INDEX=5 \
HINT_PROFILE=high-reuse \
HINT_PROVIDER=agentbench \
./agentbench/run_swebench_multi_model_batch_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct \
  Qwen/Qwen2.5-7B-Instruct \
  Qwen/Qwen3-Coder-30B-A3B-Instruct \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
  Qwen/Qwen3.6-35B-A3B-FP8 \
  Qwen/Qwen3.6-27B-FP8 \
  Qwen/Qwen3.5-9B \
  Qwen/Qwen3-Coder-Next-FP8
```

Or edit the model list:

```bash
cat agentbench/model_lists/multi_model_batch.txt
```

Default file format:

```text
# One model per line. Lines starting with # are ignored.
Qwen/Qwen2.5-Coder-7B-Instruct
Qwen/Qwen2.5-7B-Instruct
```

To watch the worker while each model starts:

```bash
docker logs -f dynamo-sglang-worker
```

Readiness behavior:

```text
1. stop Dynamo
2. start Dynamo with the next model
3. wait for /v1/models registration
4. run a real /v1/chat/completions smoke test until HTTP success
5. run Experiment 6 for START_INDEX..END_INDEX
6. move to the next model
```

Outputs:

```text
experiments/reports/batches/<multi_model_batch_id>/
  multi_model_progress.log
  multi_model_overview.csv
  <model_safe_name>_smoke_test.log   # check this first if Dynamo returns 404

experiments/reports/batches/<multi_model_batch_id>_<model_safe_name>/
  progress.log
  progress_overview.csv

experiments/reports/multi_model_batch_overview.csv
```

Useful knobs:

```text
positional model args              Highest-priority model source.
MODELS='model-a,model-b'          Override the model-list file.
MODEL_LIST_FILE=...               Read one model per line.
MODEL_READY_RETRIES=900          Dynamo start wait for model registration.
MODEL_READY_DELAY_SECS=3         Seconds between registration checks.
MODEL_READY_STABLE_HITS=2        Required consecutive successful registration checks.
MODEL_SMOKE_RETRIES=180          Smoke-test retry count.
MODEL_SMOKE_DELAY_SECS=15        Seconds between smoke-test retries.
MODEL_COOLDOWN_SECS=60           Extra wait after smoke-test success.
STOP_DYNAMO_WHEN_DONE=1          Stop Dynamo after the final model.
```

## Experiment 8: Full Design-Space Sweep

Use this when you want one automated sweep across:

- multiple SWE-bench rows
- multiple LLM models
- multiple hint profiles
- prefill/decode labels
- attention/MLP operation labels
- precise KV-transfer attribution
- one selected SGLang transfer logging profile
- KV tier modes: GPU-only, GPU+CPU, and GPU+CPU+storage
- hardware/cache metadata

This experiment restarts Dynamo once per model and KV tier mode, waits for
model readiness, runs Experiment 6 for each hint profile, and writes a compact
design-space matrix. The normal run reports still get generated, including
`prompt_evolution_run_overview.csv`.

Before running this, complete Experiment 3 Step 1 once so the instrumented
images and patched SGLang source exist.

When this sweep runs in its precise KV-attribution mode, the wrapper now does a
live preflight after each Dynamo restart and model smoke test. If the running
worker is missing the patched precise-attribution markers, the sweep stops
before launching the expensive batch.

For each precise restart, you should now see this readiness chain before the
batch starts:

- `(1/6) PRECISE RUNTIME IMAGE READY (the machine-specific Dynamo images are there)`
- `(2/6) PRECISE LOCAL READY (the local extracted/patched SGLang source is good)`
- `(3/6) MODEL READINESS ACTIVE (extended model wait and smoke timing are active)`
- `(4/6) PRECISE ATTRIBUTION READY (the live running worker really has the instrumentation)`
- `(5/6) MODEL READINESS GO (model registration and smoke test both passed)`
- `(6/6) PRECISE EXPERIMENT GO (smoke test passed and requests are about to start)`

It also now resolves the machine profile (`ec2` or `gh200`), prints the exact
`FRONTEND_IMAGE` / `WORKER_IMAGE`, checks they exist, and auto-builds them on
fresh machines by default.

The precise SGLang patcher also now auto-cleans older fragile
`schedule_policy.py` wrappers before each run, so if you sync the latest repo
you should not hit the old `too many statically nested blocks` import failure.

Manual preflight command for the precise design-space path:

```bash
./runtime_instrumentation/ensure_precise_runtime_ready.sh \
  --machine-profile "${DYNAMO_MACHINE_PROFILE:-ec2}" \
  --build-if-missing

./runtime_instrumentation/check_precise_attribution_ready.sh transfer
```

### Larger Sweep

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
DESIGN_SPACE_ID="design_space_$(date +%Y%m%d_%H%M%S)" \
START_INDEX=0 \
END_INDEX=30 \
HINT_PROFILES="baseline high-reuse low-reuse high-priority low-priority" \
HINT_PROVIDER=agentbench \
LLM_STAGES="prefill decode" \
LLM_OPERATIONS="attention_kv ffn_mlp" \
KV_TIER_MODES="gpu_only gpu_cpu gpu_cpu_storage" \
SGLANG_TRANSFER_LOG_PROFILE=full \
MEM_FRACTION_STATIC=0.7 \
HICACHE_RATIO=1 \
HICACHE_STORAGE_BACKEND=file \
HICACHE_STORAGE_PREFETCH_POLICY=wait_complete \
FILE_STORAGE_PATH=/hicache-storage \
HOST_FILE_STORAGE_PATH=/mnt/docker-data/hicache_storage \
STORAGE_MEDIA=local_nvme_or_ebs \
CPU_GPU_INTERCONNECT="PCIe" \
./agentbench/run_swebench_design_space_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct \
  Qwen/Qwen2.5-7B-Instruct \
  Qwen/Qwen3-Coder-30B-A3B-Instruct
```

### Outputs

```bash
LATEST_DESIGN_SPACE="$(ls -td experiments/reports/design_space/* | head -1)"
echo "$LATEST_DESIGN_SPACE"

cat "$LATEST_DESIGN_SPACE/design_space_summary.md"
cat "$LATEST_DESIGN_SPACE/design_space_matrix.csv"
cat experiments/reports/design_space_matrix.csv
cat experiments/reports/design_space_retention_matrix.csv

cat experiments/reports/prompt_evolution_task_summary.csv
cat experiments/reports/prompt_evolution_run_overview.csv
```

Useful knobs:

```text
START_INDEX / END_INDEX          SWE-bench row range.
HINT_PROFILES                   Space-separated hint profiles.
HINT_PROVIDER                   agentbench, deepagents, or none.
LLM_STAGES                      Reporting labels, usually "prefill decode".
LLM_OPERATIONS                  Reporting labels, usually "attention_kv ffn_mlp".
KV_TIER_MODES                   gpu_only, gpu_cpu, gpu_cpu_storage.
SGLANG_TRANSFER_LOG_PROFILE     off, light, timing, or full.
GPU_HBM_GB                      Optional override; auto-detected when possible.
HOST_RAM_GB                     Optional override; auto-detected when possible.
CPU_GPU_INTERCONNECT            Example: PCIe, NVLink, SXM, unknown.
MEM_FRACTION_STATIC             SGLang static memory fraction.
HICACHE_RATIO                   Host KV pool ratio.
HICACHE_STORAGE_BACKEND         Storage backend for gpu_cpu_storage; default file.
HICACHE_STORAGE_PREFETCH_POLICY best_effort, wait_complete, or timeout.
FILE_STORAGE_PATH               Container path passed to --file-storage-path.
HOST_FILE_STORAGE_PATH          Host storage base directory mounted into the worker.
STORAGE_MEDIA                   Label such as local_nvme, ebs_gp3, or fsx_lustre.
HICACHE_WRITE_POLICY            Optional; adds --hicache-write-policy when set.
HICACHE_EXTRA_ARGS              Optional extra HiCache flags appended to worker args.
WORKER_EXTRA_ARGS_SUFFIX        Optional extra SGLang worker flags appended to all modes.
MODEL_SMOKE_RETRIES             Default 180.
MODEL_SMOKE_DELAY_SECS          Default 15.
MODEL_COOLDOWN_SECS             Default 60.
STOP_DYNAMO_WHEN_DONE=1         Stop Dynamo after the final model.
```

KV tier mode mapping:

```text
gpu_only          HBM-only KV cache. No --enable-hierarchical-cache.
gpu_cpu           HBM + CPU RAM. Adds --enable-hierarchical-cache and --hicache-ratio.
gpu_cpu_storage   HBM + CPU RAM + file storage. Adds --hicache-storage-backend,
                  --hicache-storage-prefetch-policy, and --file-storage-path.
```

## Experiment 9: KV Retention Probe

Use this for hint-based KV retention:

```text
A first -> distractors -> A replay
```

Best first run:

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
RETENTION_PROBE_ID="retention_probe_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=precise \
RETENTION_REQUEST_CONTEXT_MODE=auto \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
DISTRACTOR_COUNT=200 \
PROTECTED_INPUT_LEN=200 \
DISTRACTOR_INPUT_LEN=200 \
GPU_ONLY_MEM_FRACTION_STATIC=0.70 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
SGLANG_TRANSFER_LOG_PROFILE=full \
./agentbench/run_kv_retention_probe_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

Quick-look outputs:

```bash
cat experiments/reports/latest_retention_probe_progress.csv
cat experiments/reports/latest_retention_probe_matrix.csv
cat experiments/reports/latest_retention_probe_requests.csv
cat experiments/reports/latest_retention_probe_summary.md
```

Main knobs:

```text
DISTRACTOR_COUNT
PROTECTED_INPUT_LEN
DISTRACTOR_INPUT_LEN
GPU_ONLY_MEM_FRACTION_STATIC
PROTECTED_HINT_PROFILES
```

## Experiment 10: Cache-Control Retention

Use this to test `nvext.cache_control` directly.

Simple probe:

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
RETENTION_PROBE_ID="retention_probe_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=precise \
RETENTION_REQUEST_CONTEXT_MODE=auto \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES=none \
CONTROL_CACHE_CONTROL_PROFILE=off \
PROTECTED_CACHE_CONTROL_PROFILES="ephemeral:1h" \
DISTRACTOR_COUNT=200 \
PROTECTED_INPUT_LEN=500 \
DISTRACTOR_INPUT_LEN=500 \
GPU_ONLY_MEM_FRACTION_STATIC=0.70 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
SGLANG_TRANSFER_LOG_PROFILE=full \
./agentbench/run_kv_retention_probe_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

Main knobs:

```text
DISTRACTOR_COUNTS
PROTECTED_INPUT_LEN
DISTRACTOR_INPUT_LEN
GPU_ONLY_MEM_FRACTION_STATIC
PROTECTED_CACHE_CONTROL_PROFILES
```

Proof fields:

```text
request_cache_control_status
request_cache_control_values
worker_cache_control_status
worker_cache_control_values
```

Top-level outputs:

```bash
cat experiments/reports/latest_retention_probe_matrix.csv
cat experiments/reports/retention_threshold_matrix.csv
cat experiments/reports/retention_threshold_comparison.csv
cat experiments/reports/retention_threshold_summary.md
```

## Experiment 11: Priority Scheduling Probe

Use this when you want to test queue ordering directly:

- send a burst of low-priority requests first
- send a burst of high-priority requests slightly later
- check whether the later high-priority requests get attached first anyway

This is a synthetic scheduling experiment. It does **not** use SWE-bench.

What it measures:

- did high-priority requests leapfrog earlier low-priority requests?
- did high-priority requests wait less in the worker queue?
- did the worker actually receive the priority hints?
- if patched SGLang is active, did the SGLang priority path say it applied priority?

### Step 0: Optional First-Time Setup Or Recovery

Do this on a fresh machine, after rebuilding images, or when recovering a
broken instrumented runtime. It gives you the strongest proof:

- worker runtime JSON from Dynamo
- patched SGLang priority-path events

```bash
cd ~/kv_cache_offloading

source runtime_instrumentation/dynamo_machine_profile.sh
source runtime_instrumentation/sglang_source_profile.sh

docker image inspect "$FRONTEND_IMAGE" >/dev/null 2>&1 || \
docker image inspect "$WORKER_IMAGE" >/dev/null 2>&1 || \
  LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh

./runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh

if [ -d upstream/sglang/python/sglang ]; then
  export SGLANG_ROOT="$PWD/upstream/sglang/python/sglang"
elif [ -d runtime_upstream/sglang/python/sglang ]; then
  export SGLANG_ROOT="$PWD/runtime_upstream/sglang/python/sglang"
else
  echo "Could not find extracted SGLang source" >&2
  exit 1
fi

python3 runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py \
  --sglang-root "$SGLANG_ROOT"
```

For a healthy precise scheduling run, you should now see this readiness chain
before the synthetic requests are sent:

- `(1/6) PRECISE RUNTIME IMAGE READY (the machine-specific Dynamo images are there)`
- `(2/6) PRECISE LOCAL READY (the local extracted/patched SGLang source is good)`
- `(3/6) MODEL READINESS ACTIVE (extended model wait and smoke timing are active)`
- `(4/6) PRECISE ATTRIBUTION READY (the live running worker really has the instrumentation)`
- `(5/6) MODEL READINESS GO (model registration and smoke test both passed)`
- `(6/6) PRECISE EXPERIMENT GO (smoke test passed and requests are about to start)`

The precise SGLang patcher now removes older fragile `schedule_policy.py`
wrappers before the run, so syncing the latest repo should also prevent the
old `too many statically nested blocks` startup error.

### Step 1: Run The Precise Scheduling Probe

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
PRIORITY_SCHEDULING_ID="priority_scheduling_$(date +%Y%m%d_%H%M%S)" \
PRIORITY_SCHEDULING_ATTRIBUTION_MODE=precise \
PRIORITY_REQUEST_CONTEXT_MODE=auto \
LOW_PRIORITY_COUNT=8 \
HIGH_PRIORITY_COUNT=4 \
PRIORITY_INPUT_LEN=4000 \
PRIORITY_OUTPUT_LEN=128 \
PRIORITY_ARRIVAL_GAP_MS=200 \
PRIORITY_INTER_REQUEST_GAP_MS=20 \
PRIORITY_TOP_LEVEL_PRIORITY_MODE=auto \
SGLANG_TRANSFER_LOG_PROFILE=full \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_priority_scheduling_probe_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

### Step 3: Watch The Worker

To watch the worker:

```bash
docker logs -f dynamo-sglang-worker
```

### Step 4: Inspect Outputs

Outputs:

Top-level latest copies:

```bash
cat experiments/reports/priority_scheduling_readable.csv
cat experiments/reports/priority_scheduling_requests.csv
cat experiments/reports/priority_scheduling_proof.csv
cat experiments/reports/priority_scheduling_summary.csv
cat experiments/reports/priority_scheduling_summary.md

cat experiments/reports/latest_priority_scheduling_readable.csv
cat experiments/reports/latest_priority_scheduling_requests.csv
cat experiments/reports/latest_priority_scheduling_proof.csv
cat experiments/reports/latest_priority_scheduling_summary.csv
cat experiments/reports/latest_priority_scheduling_summary.md
cat experiments/reports/latest_priority_scheduling_run.txt
```

Most important request-level columns:

```text
priority_class                      low-priority or high-priority
arrival_index                       Planned client arrival order
client_latency_ms                   End-to-end client wall-clock latency
worker_request_received_timestamp   When the worker first saw the request
worker_request_attached_timestamp   When the worker attached/scheduled it
worker_queue_wait_ms                Worker-side wait before attach
attached_rank                       Order in which requests were attached
completed_rank                      Order in which requests finished
overtook_earlier_low_attached_count For each high-priority row, how many earlier
                                    low-priority rows it beat in attach order
worker_agent_hints_priority         Priority value seen in worker-side hint payload
worker_top_level_priority           Top-level priority value seen by worker path,
                                    when available
sglang_scheduler_priority_applied   Whether the SGLang priority-path log said
                                    scheduler priority was applied
```

Most important summary columns:

```text
frontend_top_level_priority_compatibility
  supported / unsupported / not_attempted

worker_high_hint_received_status
  Whether the worker actually received the expected high-priority hint values

worker_high_top_level_priority_status
  Whether the worker actually saw the top-level priority values

worker_priority_path_status
  applied / seen_not_applied / worker_received_hint / not_seen

high_priority_attached_leapfrogs
  Total number of earlier low-priority requests that were beaten by later
  high-priority requests in attach order

scheduling_effect_observed
  Simple yes/no summary of whether leapfrogging happened
```
