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
export AGENTBENCH_DEEPAGENTS_SOURCE=upstream
export AGENTBENCH_TASK_OVERRIDES_FILE=agentbench/prompt_overrides/task_overrides.txt
export AGENTBENCH_EXECUTION_LOOP=0
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=1
export AGENTBENCH_PRINT_CHECKPOINTS=0
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning"
export MODEL_READY_RETRIES=120
export MODEL_READY_DELAY_SECS=2
export MODEL_READY_STABLE_HITS=2
export MODEL_SMOKE_RETRIES=60
export MODEL_SMOKE_DELAY_SECS=10
export MODEL_COOLDOWN_SECS=30

echo "Using model: $MODEL_NAME"
echo "Using machine profile: $DYNAMO_MACHINE_PROFILE"
echo "Frontend image: $FRONTEND_IMAGE"
echo "Worker image: $WORKER_IMAGE"
```

Machine profile quick switch:

```bash
# known-good EC2 / x86 path
export DYNAMO_MACHINE_PROFILE=ec2
source runtime_instrumentation/dynamo_machine_profile.sh

# GH200 / ARM64 path
export DYNAMO_MACHINE_PROFILE=gh200
source runtime_instrumentation/dynamo_machine_profile.sh
```

All experiments below inherit this execution policy unless you explicitly
override it in the shell.

For larger models such as `Qwen/Qwen3-Coder-30B-A3B-Instruct`, raise the
readiness window before starting long experiments:

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
layout.

Then build the local runtime-logging images once:

```bash
cd ~/kv_cache_offloading

LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh

docker image inspect "$FRONTEND_IMAGE" >/dev/null
docker image inspect "$WORKER_IMAGE" >/dev/null
echo "instrumented images ok"
```

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

For larger models, increase the Dynamo startup-registration wait first:

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

### Step 1: Build Images And Patch SGLang

```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-ec2}"   # or gh200
source runtime_instrumentation/dynamo_machine_profile.sh

if ! docker image inspect "$FRONTEND_IMAGE" >/dev/null 2>&1 || \
   ! docker image inspect "$WORKER_IMAGE" >/dev/null 2>&1; then
  LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh
fi

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

For larger models such as `Qwen/Qwen3-Coder-30B-A3B-Instruct`, set a longer
readiness and smoke-test window first.

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
MODEL_READY_RETRIES=120          Dynamo start wait for model registration.
MODEL_READY_DELAY_SECS=2         Seconds between registration checks.
MODEL_READY_STABLE_HITS=2        Required consecutive successful registration checks.
MODEL_SMOKE_RETRIES=60           Smoke-test retry count.
MODEL_SMOKE_DELAY_SECS=10        Seconds between smoke-test retries.
MODEL_COOLDOWN_SECS=30           Extra wait after smoke-test success.
STOP_DYNAMO_WHEN_DONE=1          Stop Dynamo after the final model.
```

For larger models, especially 30B/31B-class models, use a wider readiness
window:

```bash
MODEL_READY_RETRIES=900
MODEL_READY_DELAY_SECS=3
MODEL_READY_STABLE_HITS=2
MODEL_SMOKE_RETRIES=180
MODEL_SMOKE_DELAY_SECS=15
MODEL_COOLDOWN_SECS=60
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

### Pilot Sweep

Use this first. It is small enough to catch setup issues before a long run.

```bash
cd ~/kv_cache_offloading

export SGLANG_ROOT="$PWD/upstream/sglang/python/sglang"
source runtime_instrumentation/dynamo_machine_profile.sh

export AGENTBENCH_EXECUTION_LOOP=0
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=1

DESIGN_SPACE_ID="pilot_design_space_$(date +%Y%m%d_%H%M%S)" \
START_INDEX=0 \
END_INDEX=1 \
HINT_PROFILES="baseline high-reuse" \
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
  Qwen/Qwen2.5-7B-Instruct
```

To watch the SGLang worker while each model starts:

```bash
docker logs -f dynamo-sglang-worker
```

### Larger Sweep

```bash
cd ~/kv_cache_offloading

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

Important matrix columns:

```text
model
hint_profile
hint_provider
llm_stage
llm_operation
kv_tier_mode
sglang_transfer_log_profile
gpu_hbm_gb
host_ram_gb
cpu_gpu_interconnect
mem_fraction_static
hicache_ratio
storage_backend
storage_prefetch_policy
file_storage_path
host_file_storage_path
storage_media
storage_capacity_gb
avg_ttft_ms
avg_latency_ms
avg_cache_reuse_ratio
host_to_device_transfer_count
host_to_device_mb
device_to_host_transfer_count
device_to_host_mb
direct_attribution_rate
patch_rate
```

Notes:

```text
llm_stage and llm_operation are design-space labels in this script.
kv_tier_mode changes actual SGLang worker startup args.
Precise KV attribution still comes from SGLang transfer logs and Dynamo runtime JSON logs.
gpu_cpu_storage enables SGLang's storage backend flags, but storage-specific
read/write timing needs direct `hicache_storage.py` instrumentation.
For kernel-level attention/MLP measurements, run a separate profiler experiment and join by run/model/profile.
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
MODEL_SMOKE_RETRIES             Default 60.
MODEL_SMOKE_DELAY_SECS          Default 10.
MODEL_COOLDOWN_SECS             Default 30.
STOP_DYNAMO_WHEN_DONE=1         Stop Dynamo after the final model.
```

For larger models, increase those to something like:

```text
MODEL_READY_RETRIES=900
MODEL_READY_DELAY_SECS=3
MODEL_READY_STABLE_HITS=2
MODEL_SMOKE_RETRIES=180
MODEL_SMOKE_DELAY_SECS=15
MODEL_COOLDOWN_SECS=60
```

KV tier mode mapping:

```text
gpu_only          HBM-only KV cache. No --enable-hierarchical-cache.
gpu_cpu           HBM + CPU RAM. Adds --enable-hierarchical-cache and --hicache-ratio.
gpu_cpu_storage   HBM + CPU RAM + file storage. Adds --hicache-storage-backend,
                  --hicache-storage-prefetch-policy, and --file-storage-path.
```

## Experiment 9: KV Retention Probe

Use this to test whether a protected prompt stays useful in cache after many
unrelated prompts.

The synthetic sequence is:

```text
A first request -> many unique distractor requests -> same A request again
```

Run this first with `KV_TIER_MODE=gpu_only`. That answers the simplest
retention question: did prompt A appear to stay in GPU KV cache after pressure
from distractor prompts?

### Step 0: Prepare Instrumented SGLang

Only do this for **precise** retention runs. You can skip it for **light**
retention runs.

Run this before the automated retention run. It makes sure the Dynamo images
exist, extracts the SGLang source into the repo, and patches it so SGLang emits
direct cache events such as `event: "sglang.cache"` with your external retention
probe request IDs attached when the patch is active.

```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-ec2}"   # or gh200
source runtime_instrumentation/dynamo_machine_profile.sh

if ! docker image inspect "$FRONTEND_IMAGE" >/dev/null 2>&1 || \
   ! docker image inspect "$WORKER_IMAGE" >/dev/null 2>&1; then
  LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh
fi

SGLANG_IMAGE="$WORKER_IMAGE" \
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

Quick patch check:

```bash
for file in \
  "$SGLANG_ROOT/srt/mem_cache/memory_pool_host.py" \
  "$SGLANG_ROOT/srt/mem_cache/radix_cache.py" \
  "$SGLANG_ROOT/srt/mem_cache/hiradix_cache.py"; do
  [ -f "$file" ] && grep -n "_sgl_log_cache_event\|_sgl_log_transfer_event" "$file"
done
```

If you skip this step, the retention probe still runs, but the
`sglang_cache_*` columns will stay empty/zero.

Use the same image for `SGLANG_IMAGE` and `WORKER_IMAGE`. If you extract
SGLang from a different image, the source overlay can mismatch the worker's
installed `sgl_kernel` package and the worker can fail during import.

### Automated Run

There are now two automated modes:

- `RETENTION_ATTRIBUTION_MODE=light`
  - fastest path
  - no instrumented Dynamo requirement
  - no patched SGLang requirement
  - decides retention mainly from replay latency / speedup
- `RETENTION_ATTRIBUTION_MODE=precise`
  - slower path
  - requires Step 0
  - adds direct cache / transfer attribution when available

Use `light` when you only want to know:

- did replay A stay faster?
- at what distractor count did that speedup disappear?
- did `high-priority` survive longer than `none`?

Use `precise` when you also want:

- direct cache-event evidence
- request-level attribution
- transfer logging / richer proof

For cross-machine attribution safety, use:

- `RETENTION_REQUEST_CONTEXT_MODE=auto`
  - the probe first tries `nvext.request_context`
  - if the frontend rejects that field, it retries without it
  - request identity is still carried through `nvext.agent_context` and
    `nvext.annotations`

This keeps attribution precise without falling back to time-window guessing.

This is the default path. It gives every hint profile its own fresh Dynamo
restart and cold cache start, then writes the reports. That prevents the
`high-priority` or `high-reuse` runs from inheriting warm KV cache from the
earlier `none` control run.

The automated wrapper already stops and restarts Dynamo for each arm, so you do
not need to manually run `./run_dynamo_single_host.sh start` first.

Positive-control pilot:

Use this first to prove replay speedup exists at all under gentle pressure.
With `500/500`, replay `A` should usually be faster than the first `A`
because everything still fits comfortably in GPU KV cache.

```bash
cd ~/kv_cache_offloading

RETENTION_PROBE_ID="retention_probe_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
RETENTION_REQUEST_CONTEXT_MODE=auto \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
DISTRACTOR_COUNT=2 \
PROTECTED_INPUT_LEN=500 \
DISTRACTOR_INPUT_LEN=500 \
GPU_ONLY_MEM_FRACTION_STATIC=0.70 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
./agentbench/run_kv_retention_probe_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

Precise version of the same run:

```bash
cd ~/kv_cache_offloading

export SGLANG_ROOT="$PWD/upstream/sglang/python/sglang"
export DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-ec2}"   # or gh200
source runtime_instrumentation/dynamo_machine_profile.sh

RETENTION_PROBE_ID="retention_probe_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=precise \
RETENTION_REQUEST_CONTEXT_MODE=auto \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
DISTRACTOR_COUNT=2 \
PROTECTED_INPUT_LEN=500 \
DISTRACTOR_INPUT_LEN=500 \
GPU_ONLY_MEM_FRACTION_STATIC=0.70 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
SGLANG_TRANSFER_LOG_PROFILE=full \
./agentbench/run_kv_retention_probe_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

Hint-sensitive pressure run:

Use this next when you want the runtime to have a real eviction choice, but
not such extreme pressure that one distractor immediately wipes out prompt A.

```bash
cd ~/kv_cache_offloading

RETENTION_PROBE_ID="retention_probe_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
RETENTION_REQUEST_CONTEXT_MODE=auto \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
DISTRACTOR_COUNT=10 \
PROTECTED_INPUT_LEN=8000 \
DISTRACTOR_INPUT_LEN=2000 \
GPU_ONLY_MEM_FRACTION_STATIC=0.70 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
./agentbench/run_kv_retention_probe_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

Stronger pressure run:

```bash
cd ~/kv_cache_offloading

RETENTION_PROBE_ID="retention_probe_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
RETENTION_REQUEST_CONTEXT_MODE=auto \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
DISTRACTOR_COUNT=25 \
PROTECTED_INPUT_LEN=8000 \
DISTRACTOR_INPUT_LEN=2000 \
GPU_ONLY_MEM_FRACTION_STATIC=0.70 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
./agentbench/run_kv_retention_probe_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

If you still do not see separation, then increase pressure gradually:

```bash
DISTRACTOR_COUNT=50
```

or:

```bash
GPU_ONLY_MEM_FRACTION_STATIC=0.60
```

Multiple models:

```bash
RETENTION_PROBE_ID="retention_probe_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
RETENTION_REQUEST_CONTEXT_MODE=auto \
KV_TIER_MODES="gpu_only" \
PROTECTED_HINT_PROFILES="high-priority" \
DISTRACTOR_COUNT=10 \
PROTECTED_INPUT_LEN=8000 \
DISTRACTOR_INPUT_LEN=2000 \
GPU_ONLY_MEM_FRACTION_STATIC=0.70 \
MAX_CONTEXT_TOKENS=17146 \
./agentbench/run_kv_retention_probe_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct \
  Qwen/Qwen2.5-7B-Instruct
```

To watch the worker after the wrapper starts Dynamo:

```bash
docker logs -f dynamo-sglang-worker
```

Automated-run behavior:

```text
1. stop Dynamo
2. start Dynamo for one model + one KV tier + one hint profile
3. wait for readiness and pass a smoke test
4. run that one retention probe
5. repeat from a fresh start for the next hint profile
```

Automated-run outputs:

```bash
LATEST_RETENTION_BATCH="$(ls -td experiments/reports/retention_probe_batches/* | head -1)"
echo "$LATEST_RETENTION_BATCH"

cat "$LATEST_RETENTION_BATCH/retention_probe_batch_summary.md"
cat "$LATEST_RETENTION_BATCH/retention_probe_progress.csv"
cat "$LATEST_RETENTION_BATCH/design_space_retention_matrix.csv"
cat experiments/reports/design_space_retention_matrix.csv
```

Each hint-profile run also saves a worker runtime log in the batch directory.
In `precise` mode, the retention report uses that worker log to map SGLang
internal request ids back to your external retention probe request ids, then
re-attaches `sglang.cache` events during postprocessing.

`experiments/reports/design_space_retention_matrix.csv` is a latest-batch view.
Each automated retention run refreshes it from that batch only, so it should not
mix old retention runs with the current run. The durable per-batch copy is:

```text
experiments/reports/retention_probe_batches/<RETENTION_PROBE_ID>/design_space_retention_matrix.csv
```

Useful knobs:

```text
RETENTION_ATTRIBUTION_MODE       light or precise.
KV_TIER_MODES                  gpu_only, gpu_cpu, gpu_cpu_storage.
CONTROL_HINT_PROFILE           Usually none.
PROTECTED_HINT_PROFILES        high-priority high-reuse baseline, etc.
DISTRACTOR_COUNT               Number of distractor prompts sent between first A and replay A.
PROTECTED_INPUT_LEN            Prompt A approximate input length.
DISTRACTOR_INPUT_LEN           Each distractor prompt approximate input length.
RANDOM_OUTPUT_LEN              Keep at 1 for retention latency probes.
MAX_CONTEXT_TOKENS             Effective worker context limit. Use the worker log value if SGLang reports one.
CONTEXT_RESERVE_TOKENS         Safety reserve for chat template and output tokens.
RETENTION_PROBE_SEED           Reproducible prompt generation seed.
SGLANG_TRANSFER_LOG_PROFILE    off, light, timing, or full. Precise mode only.
MEM_FRACTION_STATIC            SGLang static memory fraction.
GPU_ONLY_MEM_FRACTION_STATIC   Override GPU-only cache pressure directly.
HICACHE_RATIO                  Host KV pool ratio for gpu_cpu/gpu_cpu_storage.
STOP_DYNAMO_WHEN_DONE=1        Stop Dynamo after the final probe.
```

Do not set `PROTECTED_INPUT_LEN` or `DISTRACTOR_INPUT_LEN` above the effective
worker limit. If the worker logs `Input length (...) exceeds the maximum allowed
length (...)`, set `MAX_CONTEXT_TOKENS` to that allowed length and reduce both
input lengths. Also do not make them so large that one distractor immediately
consumes all leftover GPU KV room after prompt A. Start with `500/500` to prove
warm replay speedup exists, then move to something like `8000/2000` when you
want a hint-sensitive retention test.

### Manual Debugging Path

Use this only when you want to start Dynamo and run each probe by hand.

#### Step 1: Start Dynamo For GPU-Only Retention

This uses precise runtime logging, but disables hierarchical cache so the first
probe focuses on GPU-only retention.

```bash
cd ~/kv_cache_offloading

export SGLANG_ROOT="$PWD/upstream/sglang/python/sglang"
source runtime_instrumentation/dynamo_machine_profile.sh

./run_dynamo_single_host.sh stop

WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority --mem-fraction-static 0.7' \
WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$SGLANG_ROOT" \
SGLANG_TRANSFER_LOG=1 \
SGLANG_TRANSFER_LOG_PROFILE=full \
SGLANG_TRANSFER_LOG_SYNC_TIMING=1 \
DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
FRONTEND_IMAGE="$FRONTEND_IMAGE" \
WORKER_IMAGE="$WORKER_IMAGE" \
./run_dynamo_single_host.sh start
```

Watch the worker:

```bash
docker logs -f dynamo-sglang-worker
```

#### Step 2: Run No-Hint Control

Use a small positive-control setup first.

```bash
cd ~/kv_cache_offloading

python3.11 experiments/scripts/retention_probe/run_kv_retention_probe.py \
  --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
  --model "$MODEL_NAME" \
  --request-context-mode auto \
  --kv-tier-mode gpu_only \
  --protected-hint-profile none \
  --distractor-hint-profile none \
  --protected-input-len 500 \
  --distractor-input-len 500 \
  --distractor-count 2 \
  --random-output-len 1 \
  --ignore-eos
```

#### Step 3: Run Protected-Hint Probe

This marks prompt A as high priority. Distractors still carry no hints.

```bash
cd ~/kv_cache_offloading

python3.11 experiments/scripts/retention_probe/run_kv_retention_probe.py \
  --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
  --model "$MODEL_NAME" \
  --request-context-mode auto \
  --kv-tier-mode gpu_only \
  --protected-hint-profile high-priority \
  --distractor-hint-profile none \
  --protected-input-len 500 \
  --distractor-input-len 500 \
  --distractor-count 2 \
  --random-output-len 1 \
  --ignore-eos
```

If the positive control works, increase pressure gradually:

```bash
--protected-input-len 8000
--distractor-input-len 2000
--distractor-count 10
```

#### Step 4: Read The Retention Reports

```bash
LATEST_RETENTION="$(ls -td experiments/reports/retention_probe/* | head -1)"
echo "$LATEST_RETENTION"

cat "$LATEST_RETENTION/retention_probe_summary.md"
cat "$LATEST_RETENTION/retention_probe_summary.csv"
cat "$LATEST_RETENTION/retention_probe_requests.csv"
cat experiments/reports/design_space_retention_matrix.csv
```

### Retention Threshold Sweep

Use this when you want to answer:

- at what distractor count does prompt A stop surviving for `none`?
- at what distractor count does prompt A stop surviving for `high-priority`?
- do those thresholds differ enough to suggest the hint is actually respected?
- later, does explicit `cache_control` keep A alive longer than no
  `cache_control` under the same pressure?

This sweep is also automated in two modes:

- `RETENTION_ATTRIBUTION_MODE=light`
  - fastest way to find where `none` and `high-priority` diverge
  - no Step 0 required
- `RETENTION_ATTRIBUTION_MODE=precise`
  - requires Step 0
  - adds direct cache / transfer attribution where available
  - cache events can now carry external request metadata such as `request_id`,
    `hint_profile`, `priority`, and `reuse_likelihood` when the instrumented
    worker runtime JSON and patched SGLang logger are both active

For portability, the synthetic retention probe now keeps `nvext.agent_hints`
minimal and Dynamo-safe:

- runtime control sent in `agent_hints`: `priority`
- experiment metadata sent separately in:
  - `nvext.request_context`
  - `nvext.agent_context`
  - `nvext.annotations`

This avoids bad-request errors from unsupported hint keys such as
`reuse_likelihood` while preserving direct attribution.

By default, the retention probe and threshold sweep now launch the worker with
both `--enable-priority-scheduling` and `--radix-eviction-policy priority`.
Only override `WORKER_BASE_ARGS` if you intentionally want a different policy.

Top-level priority compatibility:

- `RETENTION_TOP_LEVEL_PRIORITY_MODE=auto` is now the safest default.
- In `auto` mode, the probe tries top-level `priority` once.
- If the frontend rejects it with `Unsupported parameter(s): priority`, the
  probe retries without top-level `priority`, keeps `nvext.agent_hints`, and
  records that fallback in the report.
- This is useful on machines where the frontend/runtime accepts agent hints but
  does not accept top-level `priority`.
- If your top-level priority smoke test fails but the canonical
  `nvext.agent_hints.priority` smoke test succeeds, use:

```bash
export RETENTION_TOP_LEVEL_PRIORITY_MODE=disable
```

That keeps the experiment on the canonical hint path only and avoids the
top-level `priority` bad-request error entirely.

Cache-control variant:

- `CONTROL_CACHE_CONTROL_PROFILE=off` means ordinary behavior.
- `PROTECTED_CACHE_CONTROL_PROFILES="ephemeral:1h"` means the protected A
  requests are sent with `nvext.cache_control = {"type":"ephemeral","ttl":"1h"}`.
- This lets you test explicit cache retention separately from priority hints.

Recommended first run:

Start with a moderate setup that can still show hint differences without
immediately overflowing the leftover GPU KV room after prompt A.

If you are using a larger model such as `Qwen/Qwen3-Coder-30B-A3B-Instruct`,
set a larger readiness window first:

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

RETENTION_SWEEP_ID="retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
RETENTION_REQUEST_CONTEXT_MODE=auto \
DISTRACTOR_COUNTS="2 10 20" \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
PROTECTED_INPUT_LEN=8000 \
DISTRACTOR_INPUT_LEN=2000 \
GPU_ONLY_MEM_FRACTION_STATIC=0.7 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
RETENTION_TOP_LEVEL_PRIORITY_MODE=auto \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_kv_retention_threshold_sweep_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

Cache-control sweep of the same idea:

```bash
cd ~/kv_cache_offloading

RETENTION_SWEEP_ID="retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
RETENTION_REQUEST_CONTEXT_MODE=auto \
DISTRACTOR_COUNTS="2 10 20" \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES=none \
CONTROL_CACHE_CONTROL_PROFILE=off \
PROTECTED_CACHE_CONTROL_PROFILES="ephemeral:1h" \
PROTECTED_INPUT_LEN=8000 \
DISTRACTOR_INPUT_LEN=2000 \
GPU_ONLY_MEM_FRACTION_STATIC=0.7 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_kv_retention_threshold_sweep_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

That second sweep answers a different question:

- priority sweep: does the protected request survive longer because of a
  stronger priority hint?
- cache-control sweep: does the protected request survive longer because the
  frontend asked for explicit cache retention?

Canonical-hint-only variant for machines that reject top-level `priority`:

```bash
cd ~/kv_cache_offloading

export RETENTION_TOP_LEVEL_PRIORITY_MODE=disable

RETENTION_SWEEP_ID="retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
RETENTION_REQUEST_CONTEXT_MODE=auto \
DISTRACTOR_COUNTS="2 10 20" \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
PROTECTED_INPUT_LEN=8000 \
DISTRACTOR_INPUT_LEN=2000 \
GPU_ONLY_MEM_FRACTION_STATIC=0.7 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_kv_retention_threshold_sweep_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

Precise version of the same sweep:

```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-ec2}"   # or gh200
source runtime_instrumentation/dynamo_machine_profile.sh

SGLANG_IMAGE="$WORKER_IMAGE" \
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

RETENTION_SWEEP_ID="retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=precise \
RETENTION_REQUEST_CONTEXT_MODE=auto \
DISTRACTOR_COUNTS="10" \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
PROTECTED_INPUT_LEN=8000 \
DISTRACTOR_INPUT_LEN=2000 \
GPU_ONLY_MEM_FRACTION_STATIC=0.7 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
SGLANG_TRANSFER_LOG_PROFILE=full \
RETENTION_TOP_LEVEL_PRIORITY_MODE=auto \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_kv_retention_threshold_sweep_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

Run the same sweep in the background with `nohup`:

```bash
cd ~/kv_cache_offloading

RETENTION_SWEEP_ID="retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=precise \
RETENTION_REQUEST_CONTEXT_MODE=auto \
DISTRACTOR_COUNTS="2 10 20" \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
PROTECTED_INPUT_LEN=8000 \
DISTRACTOR_INPUT_LEN=2000 \
GPU_ONLY_MEM_FRACTION_STATIC=0.7 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
SGLANG_TRANSFER_LOG_PROFILE=full \
RETENTION_TOP_LEVEL_PRIORITY_MODE=auto \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_kv_retention_threshold_sweep_nohup.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

Run this when using a smaller machine like g5.2xlarge with limited GPU capacity (this has proved to work)

```bash
cd ~/kv_cache_offloading

RETENTION_SWEEP_ID="retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=precise \
RETENTION_REQUEST_CONTEXT_MODE=auto \
DISTRACTOR_COUNTS="2 10 20 40 60 80 100 200" \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
PROTECTED_INPUT_LEN=200 \
DISTRACTOR_INPUT_LEN=200 \
GPU_ONLY_MEM_FRACTION_STATIC=0.7 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
SGLANG_TRANSFER_LOG_PROFILE=full \
RETENTION_TOP_LEVEL_PRIORITY_MODE=auto \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_kv_retention_threshold_sweep_nohup.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

This has proved to work in GH200, showing KV cache retention from provided priority hints

```bash
cd ~/kv_cache_offloading-v5

export RETENTION_TOP_LEVEL_PRIORITY_MODE=disable

RETENTION_SWEEP_ID="retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=precise \
RETENTION_REQUEST_CONTEXT_MODE=auto \
DISTRACTOR_COUNTS="200" \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
PROTECTED_INPUT_LEN=2000 \
DISTRACTOR_INPUT_LEN=2000 \
GPU_ONLY_MEM_FRACTION_STATIC=0.7 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
SGLANG_TRANSFER_LOG_PROFILE=full \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_kv_retention_threshold_sweep_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

That prints:

- the sweep id
- the background PID
- the `nohup` log path
- the stable latest-log shortcut
- the partial report paths you can inspect while the run is still going

Useful commands while it runs:

```bash
LATEST_THRESHOLD_SWEEP="$(ls -td experiments/reports/retention_threshold_sweeps/* | head -1)"
echo "$LATEST_THRESHOLD_SWEEP"

tail -f "$LATEST_THRESHOLD_SWEEP/nohup.log"
tail -f experiments/reports/latest_retention_threshold_nohup.log
cat "$LATEST_THRESHOLD_SWEEP/retention_threshold_sweep_progress.csv"
cat "$LATEST_THRESHOLD_SWEEP/retention_threshold_matrix.csv"
cat "$LATEST_THRESHOLD_SWEEP/retention_threshold_comparison.csv"
cat "$LATEST_THRESHOLD_SWEEP/retention_threshold_summary.md"
```

To watch the worker:

```bash
docker logs -f dynamo-sglang-worker
```

Outputs:

```bash
LATEST_THRESHOLD_SWEEP="$(ls -td experiments/reports/retention_threshold_sweeps/* | head -1)"
echo "$LATEST_THRESHOLD_SWEEP"

cat "$LATEST_THRESHOLD_SWEEP/retention_threshold_sweep_progress.csv"
cat "$LATEST_THRESHOLD_SWEEP/retention_threshold_matrix.csv"
cat "$LATEST_THRESHOLD_SWEEP/retention_threshold_comparison.csv"
cat "$LATEST_THRESHOLD_SWEEP/retention_threshold_summary.md"
```

What the new files mean:

```text
retention_threshold_sweep_progress.csv
  One row per distractor-count run.

retention_threshold_matrix.csv
  One row per hint profile per distractor count, with replay latency and cache evidence.

retention_threshold_comparison.csv
  Direct control vs protected threshold comparison.

retention_threshold_summary.md
  Short interpretation of whether the protected run survived longer.
```

Each new call to `./agentbench/run_kv_retention_threshold_sweep_single_host.sh`
automatically clears the top-level live `retention_threshold_*` files in
`experiments/reports/` before writing fresh progress. Older archived sweep
folders under `experiments/reports/retention_threshold_sweeps/` are kept.

The reports now also carry `retention_attribution_mode`, so you can tell
whether a row came from the fast latency-only path or the precise attribution
path.

They also now carry frontend-priority compatibility signals, so you can tell
whether:

- top-level `priority` was attempted
- the frontend accepted it
- the probe had to fall back without it
- the worker still saw `agent_hints.priority`

How to read the result:

- if `high-priority` first evicts later than `none`, that is evidence the hint helped retention
- if both first evict at the same distractor count, question whether the hint is actually respected by the runtime
- if neither evicts in the sweep range, increase `DISTRACTOR_COUNTS` or reduce `GPU_ONLY_MEM_FRACTION_STATIC`

The threshold report uses an intentionally strict survival rule:

- replay A must succeed
- if replay exposes `a_replay_cached_tokens`, that is the primary reuse signal
- otherwise replay A must have direct cache attribution
- and at least one cache match event
- replay A must also show meaningful benefit:
  - speedup ratio >= `1.05`, or
  - latency gain >= `100` ms

Key columns:

```text
protected_hint_profile       none, high-priority, high-reuse, etc.
kv_tier_mode                 gpu_only, gpu_cpu, or gpu_cpu_storage label.
a_first_latency_ms           First A request wall-clock latency.
a_replay_latency_ms          Second A request wall-clock latency.
a_first_status               HTTP status for the first A request.
a_replay_status              HTTP status for the replay A request.
a_replay_latency_delta_ms    replay - first. Negative means replay was faster.
a_replay_speedup_ratio       first / replay. Above 1.000 means replay was faster.
worker_kv_capacity_tokens    Effective GPU KV capacity seen by the worker.
worker_context_len           Model context length reported by the worker.
a_first_prompt_tokens        Prompt-token size of the first A request.
first_distractor_prompt_tokens
                             Prompt-token size of the first distractor request.
kv_tokens_left_after_a       Remaining GPU KV room after A is stored.
kv_tokens_left_after_a_after_first_distractor
                             Remaining GPU KV room after A and one distractor.
a_replay_cached_tokens       Cached prompt tokens reported for replay, if exposed.
a_replay_prompt_tokens       Replay prompt-token count, if exposed.
a_replay_cache_reuse_ratio   cached / prompt tokens for replay, if exposed.
a_replay_sglang_cache_events Direct SGLang cache events matched to replay request.
a_replay_sglang_cache_match_events
                             Direct SGLang match-prefix/cache-lookup events for replay.
a_replay_sglang_cache_direct True means SGLang evidence matched this request ID.
survived_by_usage            True means replay reported real cached prompt tokens.
survived_by_events           True means replay had direct SGLang cache-match evidence.
survived_by_latency          True means replay showed meaningful speedup.
survived_effective           True means replay both reused cache and got faster.
effective_survival_source    Which signal was used for the final survival decision.
reuse_signal                 Quick label: true_reuse_hit, usage_hit_without_speedup,
                             semantic_match_only, event_match_with_speedup, or no_reuse_evidence.
```

Interpretation:

```text
If high-priority A replays faster than no-hint A, the hint may be improving retention.
If `survived_by_usage=true`, replay reported real cached prompt-token reuse.
If `reuse_signal=semantic_match_only`, SGLang noticed related cache state but replay did not show strong practical reuse.
If `kv_tokens_left_after_a` is small and `first_distractor_prompt_tokens` is larger than that leftover room, A is likely to be displaced quickly on `gpu_only`.
If cached-token evidence is higher for high-priority A, the hint may be preserving more prefix KV.
If the cache columns are empty, the endpoint did not expose cached-token usage for this request.
If SGLang cache direct attribution is true, the cache evidence came from instrumented SGLang events, not timestamp guessing.
For CPU or storage reload behavior, rerun this idea with gpu_cpu or gpu_cpu_storage.
```

This probe is synthetic on purpose. After it shows a clear effect, use
Experiment 8 to test the same idea across real SWE-bench tasks, hint profiles,
and KV tier modes.

## Experiment 10: Priority Scheduling Probe

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

### Step 0: Prepare Instrumented Dynamo And Patched SGLang

Do this once before the `precise` version if you want the strongest proof:

- worker runtime JSON from Dynamo
- patched SGLang priority-path events

```bash
cd ~/kv_cache_offloading

source runtime_instrumentation/dynamo_machine_profile.sh

docker image inspect "$FRONTEND_IMAGE" >/dev/null 2>&1 || \
docker image inspect "$WORKER_IMAGE" >/dev/null 2>&1 || \
  LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh

SGLANG_IMAGE="$WORKER_IMAGE" \
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

If you only want the lightweight scheduling check, you can skip Step 0 and run
the `light` version below.

If the driver log later warns that the worker log contains no `[RUNTIME_JSON]`
lines, stop there and rebuild the local runtime-json images from the prepared
Dynamo source before trusting the result.

### Step 1: Run The Precise Scheduling Probe

```bash
cd ~/kv_cache_offloading

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

This `precise` path gives you:

- worker runtime ordering evidence
- worker-side hint-received evidence
- and, if `SGLANG_ROOT` is exported from Step 0, patched SGLang priority-path evidence
- automatic retry without top-level `priority` if the frontend rejects that field
- automatic retry without `nvext.request_context` if that field is unsupported

For portability, the synthetic scheduling probe also keeps
`nvext.agent_hints` minimal and Dynamo-safe:

- runtime control sent in `agent_hints`: `priority`
- request identity and experiment metadata sent separately in:
  - `nvext.request_context`
  - `nvext.agent_context`
  - `nvext.annotations`

Canonical-hint-only variant for machines that reject top-level `priority`:

```bash
cd ~/kv_cache_offloading

PRIORITY_SCHEDULING_ID="priority_scheduling_$(date +%Y%m%d_%H%M%S)" \
PRIORITY_SCHEDULING_ATTRIBUTION_MODE=precise \
PRIORITY_REQUEST_CONTEXT_MODE=auto \
LOW_PRIORITY_COUNT=8 \
HIGH_PRIORITY_COUNT=4 \
PRIORITY_INPUT_LEN=4000 \
PRIORITY_OUTPUT_LEN=128 \
PRIORITY_ARRIVAL_GAP_MS=200 \
PRIORITY_INTER_REQUEST_GAP_MS=20 \
PRIORITY_TOP_LEVEL_PRIORITY_MODE=disable \
SGLANG_TRANSFER_LOG_PROFILE=full \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_priority_scheduling_probe_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

How the two priority modes differ:

- `PRIORITY_TOP_LEVEL_PRIORITY_MODE=auto`
  - tries top-level `priority` first
  - if the frontend returns `Unsupported parameter(s): priority`, the probe retries without it
  - this is the safest default when moving between machines
- `PRIORITY_TOP_LEVEL_PRIORITY_MODE=disable`
  - never sends top-level `priority`
  - only uses the canonical `nvext.agent_hints.priority` path
  - use this when you already know the frontend rejects top-level `priority`

### Step 2: Run The Fast/Light Version

Fast/light version:

```bash
cd ~/kv_cache_offloading

PRIORITY_SCHEDULING_ID="priority_scheduling_$(date +%Y%m%d_%H%M%S)" \
PRIORITY_SCHEDULING_ATTRIBUTION_MODE=light \
PRIORITY_REQUEST_CONTEXT_MODE=auto \
LOW_PRIORITY_COUNT=8 \
HIGH_PRIORITY_COUNT=4 \
PRIORITY_INPUT_LEN=4000 \
PRIORITY_OUTPUT_LEN=128 \
PRIORITY_ARRIVAL_GAP_MS=200 \
PRIORITY_INTER_REQUEST_GAP_MS=20 \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_priority_scheduling_probe_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

This `light` path is simpler:

- no patched-SGLang requirement
- no transfer-log dependency
- still useful for checking whether high-priority requests jumped ahead

### Step 3: Watch The Worker

To watch the worker:

```bash
docker logs -f dynamo-sglang-worker
```

### Step 4: Inspect Outputs

Outputs:

```bash
LATEST_PRIORITY="$(ls -td experiments/reports/priority_scheduling/* | head -1)"
echo "$LATEST_PRIORITY"

cat "$LATEST_PRIORITY/priority_scheduling_requests.csv"
cat "$LATEST_PRIORITY/priority_scheduling_summary.csv"
cat "$LATEST_PRIORITY/priority_scheduling_summary.md"
```

Top-level latest copies:

```bash
cat experiments/reports/priority_scheduling_requests.csv
cat experiments/reports/priority_scheduling_summary.csv
cat experiments/reports/priority_scheduling_summary.md
```

What the files mean:

```text
priority_scheduling_requests.csv
  One row per synthetic request.

priority_scheduling_summary.csv
  One compact row with the main queue-order metrics.

priority_scheduling_summary.md
  Short interpretation of whether high-priority actually jumped ahead.
```

Important failure signal:

```text
If priority_scheduling_summary.csv shows:

  frontend_top_level_priority_compatibility=unsupported
  worker_runtime_event_coverage=0 / N
  worker_priority_path_status=not_seen

then the probe did not really reach the worker scheduling path.
That run should be treated as a frontend-validation failure, not as evidence
that priority scheduling had no effect.
```

How to read the result:

```text
If high_priority_attached_leapfrogs > 0, later high-priority requests were
attached before earlier low-priority requests.

If high_priority_completed_leapfrogs > 0, later high-priority requests also
finished ahead of earlier low-priority requests.

If mean_high_queue_wait_ms is clearly lower than mean_low_queue_wait_ms, that
is extra evidence that priority affected scheduling.

If leapfrogs stay at 0 and queue waits look similar, the runtime likely did
not reorder based on the supplied priority path.
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

## Utilities

### Latest Result And Report

```bash
LATEST_RESULT="$(ls -td experiments/raw/agentbench/results/* | head -1)"
LATEST_REPORT="$(ls -td experiments/reports/runs/* | head -1)"

echo "$LATEST_RESULT"
echo "$LATEST_REPORT"
```

### Patch And Tool Activity

```bash
wc -c "$LATEST_RESULT/workspace.patch"
cat "$LATEST_RESULT/others/git_status.txt"
cat "$LATEST_RESULT/others/git_diff_stat.txt"
cat "$LATEST_REPORT/tool_call_details.md"
cat "$LATEST_REPORT/tool_call_details.csv"
```

### Phase Metrics

```bash
cat "$LATEST_REPORT/phase_summary.md"
cat "$LATEST_REPORT/phase_summary.csv"
cat "$LATEST_REPORT/phase_runtime_metrics.csv"
cat "$LATEST_REPORT/model_request_metrics.csv"
```

### All-Runs Runtime Metrics

These top-level reports refresh whenever a normal run report is built:

```bash
cat experiments/reports/all_runs_task_phase_request_metrics.csv
cat experiments/reports/all_runs_hint_profile_impact.csv
cat experiments/reports/all_runs_phase_metrics.csv
cat experiments/reports/all_runs_phase_request_metrics.csv
cat experiments/reports/all_runs_kv_transfer_metrics.csv
cat experiments/reports/all_runs_instrumentation_overhead.csv

cat experiments/reports/latest_runs_task_phase_request_metrics.md
cat experiments/reports/latest_runs_hint_profile_impact.md
cat experiments/reports/latest_runs_phase_metrics.md
cat experiments/reports/latest_runs_phase_request_metrics.md
cat experiments/reports/latest_runs_kv_transfer_metrics.md
cat experiments/reports/latest_runs_instrumentation_overhead.md
```

Use `all_runs_task_phase_request_metrics.csv` first when you want the broad
drilldown view: every run, every phase, and every model request inside each
phase. Use `all_runs_hint_profile_impact.csv` when comparing hint profiles
across phases.

`all_runs_phase_metrics.csv` has one row per AgentBench phase.
`all_runs_phase_request_metrics.csv` has one row per model/API request inside a
phase.
`all_runs_instrumentation_overhead.csv` is for calibration runs with
`SGLANG_TRANSFER_LOG_OVERHEAD_TIMING=1`; it shows compact timing buckets for
logger overhead, token extraction, CUDA sync timing, and JSON serialization.

These all-runs files keep compact identity columns only: `run_id`,
`task_label`, `instance_id_short`, `hint_profile`, `phase`, and request indexes.
They also include `hint_provider` so AgentBench-derived, Deep Agents-derived,
and no-hint control runs can be compared separately.
Use the per-run report folders when you need full raw IDs or debug provenance.

### Prompt Evolution

```bash
cat "$LATEST_RESULT/prompt_evolution_report.md"
cat "$LATEST_RESULT/prompt_evolution_values/index.json"
ls "$LATEST_RESULT/prompt_evolution_values"
```

### Runtime Hint Evidence

```bash
grep -R "hint_probe_id\|agent_hints\|worker.decode" -n "$LATEST_RESULT" | head -50
cat "$LATEST_RESULT/runtime_hint_alignment_analysis.md"
cat "$LATEST_RESULT/others/runtime_hint_alignment_summary_table.csv"
```

Worker-side hint proof requires the instrumented runtime. A non-instrumented run
can still produce prompt-evolution files, but it cannot prove that hints reached
SGLang worker logs.

### Rebuild Latest Run Report

```bash
LATEST_RESULT="$(ls -td experiments/raw/agentbench/results/* | head -1)"

python3 experiments/scripts/agentbench_report/build_run_report.py \
  --agentbench-result-dir "$LATEST_RESULT" \
  --transfer-log experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl
```

### Clean Fresh Start

Dry run:

```bash
./experiments/scripts/clean_experiment_data.sh
```

Delete generated experiment data and reports:

```bash
./run_dynamo_single_host.sh stop
./experiments/scripts/clean_experiment_data.sh --yes
```

This clears `experiments/raw`, `experiments/parsed`, run reports, batch reports,
design-space reports, top-level generated summary CSV/Markdown files under
`experiments/reports`, and legacy `agentbench/results` data if present. It
preserves experiment scripts, READMEs, upstream repos, and instrumentation code.

### Stop Dynamo

```bash
./run_dynamo_single_host.sh stop
```

## Report Field Notes

- `worker_runtime_json_matched=True` means worker runtime logs were matched by
  request/context ID.
- `transfer_request_id_matched=True` means transfer events were matched by
  request/context ID. This is the precise attribution signal.
- `transfer_time_window_matched=True` is weaker; it means events fell inside the
  request timestamp window.
- `cache_hit`, `cached_token_count`, `recomputed_prefix_tokens`, and
  `cache_reuse_ratio` are effective values derived from the best available
  evidence.
- `ttft_ms` uses the best available source. Prefer
  `ttft_source=worker_runtime_json.request_received_to_attached`.
- `model_request_metrics.csv` is the best file when one phase sends multiple
  SGLang requests.


  error status=400 {"message":"Validation: Unsupported parameter(s): `priority`","type":"Bad Request","code":400}
