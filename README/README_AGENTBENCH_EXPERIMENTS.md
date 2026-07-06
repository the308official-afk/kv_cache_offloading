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

## Supported Hints At A Glance

These are the main Dynamo-facing knobs that are worth treating as real runtime
controls in this setup.

| Hint | Status | What it does |
|---|---|---|
| `priority` | supported | Main scheduling hint. Affects router ordering and backend priority behavior. |
| `osl` | supported | Expected output length. Used for routing/resource estimation. |
| `expected_output_tokens` | supported alias | Same role as `osl`; Dynamo maps either one into routing. |
| `speculative_prefill` | supported | Warms likely next-turn KV cache after the current response finishes. |
| `latency_sensitivity` | deprecated fallback | Older priority-like fallback that feeds routing `priority_jump`. |

Nearby supported control:

| Control | Status | What it does |
|---|---|---|
| `session_control` | supported | Sticky routing / subagent session affinity. Not a scheduling hint. |

Observed in logs, but not automatically treated as live runtime controls in the
pinned setup unless we wire them in ourselves:

- `reuse_likelihood`
- `hint_profile`
- `hint_probe_id`
- `agent_phase`
- `program_id`
- `context_type`
- `cache_control` as a true TTL pinning control

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
- the public wrappers for Experiments `9`-`12` now also share one experiment-directory preflight helper:
  [runtime_instrumentation/ensure_experiment_dirs_ready.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/ensure_experiment_dirs_ready.sh)
- the helper uses a known-good pinned SGLang source image by default:
  [runtime_instrumentation/sglang_source_profile.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/sglang_source_profile.sh)
- this helper auto-extracts and re-patches the SGLang overlay before precise runs
- and the runtime-image helper now resolves the machine profile (`ec2` or `gh200`),
  prints the exact `FRONTEND_IMAGE` / `WORKER_IMAGE`, checks they exist, and
  auto-builds them on fresh machines by default inside the precise wrappers
- the runtime-image helper also records a small source-signature stamp when
  images are built, so precise wrappers can now notice when the local
  instrumented Dynamo source changed and rebuild automatically instead of
  making you guess whether a rebuild is needed
- the experiment-directory helper auto-creates and write-checks the required
  `experiments/raw`, `experiments/reports`, `experiments/charts`, and
  `experiments/runtime_state` paths before runs; it breaks out immediately if a
  machine cannot create or write them
- the public microbenchmark wrappers for Experiments `9`-`12` now also do one
  automatic clean-start before the real run begins, so an older live worker
  does not get reused accidentally for a precise run
- that clean-start happens once per experiment, before the first probe/sweep
  request; after that, the experiment still uses its own normal reset mode
  inside the sweep
- the default is `PRECISE_START_MODE=clean`
- if you intentionally want the old reuse-first behavior, set:
  `PRECISE_START_MODE=reuse`
- if you want check-only behavior instead, set:
  `AUTO_BUILD_PRECISE_IMAGES=0`
- so you should not need to manually re-run the SGLang extract/patch steps for
  every precise experiment anymore
- and you should not need to manually decide whether Dynamo needs a rebuild for
  precise experiments anymore; the wrappers now make that decision for you
- you may still want to run the helper manually when debugging a fresh machine:
  `./runtime_instrumentation/ensure_precise_runtime_ready.sh --machine-profile ec2 --build-if-missing`
- on GH200, this is the manual preflight to run once before your first suite or
  precise experiment:

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
./runtime_instrumentation/ensure_precise_runtime_ready.sh \
  --machine-profile gh200 \
  --build-if-missing
```
- if you intentionally want a different SGLang source, override it explicitly:
  `export SGLANG_IMAGE=...` before the run

First-time machine bring-up:

- Experiments `9`, `11`, and `12` use the shared precise runtime stack.
- Experiment `10` uses a separate isolated cache-pinning stack.

So on a fresh machine:

1. shared precise runtime for Experiments `9`, `11`, `12`

```bash
cd ~/kv_cache_offloading

# EC2 / x86
DYNAMO_MACHINE_PROFILE=ec2 \
./runtime_instrumentation/ensure_precise_runtime_ready.sh \
  --machine-profile ec2 \
  --build-if-missing

# GH200 / ARM64
DYNAMO_MACHINE_PROFILE=gh200 \
./runtime_instrumentation/ensure_precise_runtime_ready.sh \
  --machine-profile gh200 \
  --build-if-missing
```

2. isolated cache-pinning runtime for Experiment `10`

```bash
cd ~/kv_cache_offloading

# EC2 / x86
DYNAMO_MACHINE_PROFILE=ec2 \
CACHE_PINNING_MODE=validate \
./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct

# GH200 / ARM64
DYNAMO_MACHINE_PROFILE=gh200 \
CACHE_PINNING_MODE=validate \
./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

The `validate` run above is the first-time bring-up for Experiment `10` because
it will prepare the isolated cache-pinning Dynamo/SGLang sources and build the
machine-specific cache-pinning images if they are missing.

Source-of-truth table:

| Stack | Experiments | Dynamo source | SGLang source | EC2 images | GH200 images |
| --- | --- | --- | --- | --- | --- |
| Shared precise runtime | `9`, `11`, `12` | `upstream/dynamo` pinned to `8cee1e50e10fefb0ac570144b48458a043361d94` | pinned source image `lmsysorg/sglang:v0.5.11-cu129-runtime` | `local/dynamo-frontend:runtime-json-logs-ec2`<br>`local/dynamo-sglang:runtime-json-logs-ec2` | `local/dynamo-frontend:runtime-json-logs-gh200`<br>`local/dynamo-sglang:runtime-json-logs-gh200` |
| Isolated cache-pinning stack | `10` | `upstream/dynamo_cache_pinning` pinned to PR `6213` / ref `7d3d4ec8e4ae865af2f903b21b4afabca28e1940` | `upstream/sglang_cache_pinning` pinned to PR `18941` / ref `ff2f70b0fcb6b3ea130c46927ed98edf69d5c17c` | `local/dynamo-frontend:cache-pinning-ec2`<br>`local/dynamo-sglang:cache-pinning-ec2` | `local/dynamo-frontend:cache-pinning-gh200`<br>`local/dynamo-sglang:cache-pinning-gh200` |

Interpretation:

- the source baseline is intended to stay the same across `ec2` and `gh200`
- what changes between the two machines is the built image architecture and tag
- so GH200 should rebuild the same intended stack for `linux/arm64`, instead of
  reusing the EC2/x86 image artifacts

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

The prepare step now also repairs and verifies the Dynamo KV-flush path used by
`EXPERIMENT_RESET_MODE=flush` and `KV_RETENTION_RESET_MODE=flush`. It checks
for:

- `pub mod clear_kv_blocks;` in
  [`upstream/dynamo/lib/llm/src/http/service.rs`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/http/service.rs)
- `super::clear_kv_blocks::clear_kv_blocks_router(state.clone(), None),` in
  [`upstream/dynamo/lib/llm/src/http/service/service_v2.rs`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/http/service/service_v2.rs)
- `clear_kv_blocks_endpoint = runtime.endpoint(...)` in
  [`upstream/dynamo/components/src/dynamo/sglang/init_llm.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/init_llm.py)
- `clear_kv_blocks_endpoint.serve_endpoint(...)` in
  [`upstream/dynamo/components/src/dynamo/sglang/init_llm.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/init_llm.py)
- `async def clear_kv_blocks(...)` in
  [`upstream/dynamo/components/src/dynamo/sglang/request_handlers/handler_base.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/handler_base.py)
- `runtime.register_engine_route("clear_kv_blocks", ...)` in
  [`upstream/dynamo/components/src/dynamo/sglang/request_handlers/handler_base.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/handler_base.py)
- `flush_cache` in
  [`upstream/dynamo/components/src/dynamo/sglang/request_handlers/handler_base.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/handler_base.py)

So if a future upstream clone is missing either:

- the frontend `/clear_kv_blocks` route registration, or
- the worker-side flush plumbing,

the prepare/build path should now fail early instead of letting you discover it
later through `POST /clear_kv_blocks -> 404`.

Then build the local runtime-logging images once:

```bash
cd ~/kv_cache_offloading

LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh

docker image inspect "$FRONTEND_IMAGE" >/dev/null
docker image inspect "$WORKER_IMAGE" >/dev/null
echo "instrumented images ok"
```

Manual rebuild is now mainly a first-time or recovery path. The precise
experiment wrappers will normally auto-check the machine profile, local
instrumented source, image freshness, live worker instrumentation, and rebuild
when needed.

For most rebuilds, you do not need to delete `upstream/dynamo`. The normal
clean rebuild path is:

```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-ec2}"   # or gh200
source runtime_instrumentation/dynamo_machine_profile.sh

./run_dynamo_single_host.sh stop || true
docker rm -f dynamo-sglang-worker dynamo-frontend dynamo-etcd dynamo-nats 2>/dev/null || true
docker rmi "$FRONTEND_IMAGE" "$WORKER_IMAGE" || true

./runtime_instrumentation/prepare_instrumented_dynamo_source.sh

DOCKER_BUILD_NO_CACHE=1 LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

This is the recommended default because:

- it clears the old running containers
- it clears the old precise frontend/worker images
- it keeps the local Dynamo source clone and repairs it in place
- it avoids the extra time of recloning Dynamo on every rebuild

Only delete `upstream/dynamo` when you suspect the source clone itself is
corrupted, inconsistent, or behaving strangely across repeated prepare runs.
That stronger reset path is:

```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-ec2}"   # or gh200
source runtime_instrumentation/dynamo_machine_profile.sh

./run_dynamo_single_host.sh stop || true
docker rm -f dynamo-sglang-worker dynamo-frontend dynamo-etcd dynamo-nats 2>/dev/null || true
docker rmi "$FRONTEND_IMAGE" "$WORKER_IMAGE" || true

rm -rf upstream/dynamo

./runtime_instrumentation/prepare_instrumented_dynamo_source.sh

DOCKER_BUILD_NO_CACHE=1 LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

So in simple terms:

- default: keep `upstream/dynamo`, remove containers/images, rebuild
- only if suspicious: also remove `upstream/dynamo` and let the repo fetch a
  fresh pinned clone

That is usually the best balance between cleanliness and rebuild time.

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
Dynamo-safe runtime-control subset in `nvext.agent_hints`. See
[Supported Hints At A Glance](#supported-hints-at-a-glance) above.

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

This is the public KV-retention microbenchmark entrypoint.

Contract files:

- [`contracts/kv_retention_microbenchmark.contract.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/kv_retention_microbenchmark.contract.sh)
- [`contracts/kv_retention_microbenchmark.contract.md`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/kv_retention_microbenchmark.contract.md)

Public wrapper:

- [`agentbench/run_kv_retention_microbenchmark_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_kv_retention_microbenchmark_single_host.sh)

Supported modes:

- `probe`: one `A first -> distractors -> A replay` run
- `sweep`: threshold sweep across distractor counts
- `all`: sweep, then plot
- `plot`: rebuild charts from one existing matrix CSV

### Run

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
KV_RETENTION_MODE=probe \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

This works on EC2
```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
PRECISE_START_MODE=clean \
KV_RETENTION_MODE=sweep \
RETENTION_ATTRIBUTION_MODE=precise \
KV_RETENTION_RESET_MODE=flush \
RETENTION_SWEEP_SEED_MODE=per_cell \
STOP_ON_PROBE_FAILURE=1 \
DISTRACTOR_COUNTS="25 50 75 100 125 150" \
PROTECTED_INPUT_LEN=400 \
DISTRACTOR_INPUT_LEN=400 \
PROTECTED_HINT_PROFILES="high-priority" \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

This works on GH200?
```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
KV_RETENTION_MODE=sweep \
RETENTION_ATTRIBUTION_MODE=precise \
RETENTION_REQUEST_CONTEXT_MODE=auto \
RETENTION_TOP_LEVEL_PRIORITY_MODE=disable \
KV_RETENTION_RESET_MODE=flush \
RETENTION_SWEEP_SEED_MODE=per_cell \
STOP_ON_PROBE_FAILURE=1 \
DISTRACTOR_COUNTS="200" \
PROTECTED_INPUT_LEN=2000 \
DISTRACTOR_INPUT_LEN=2000 \
PROTECTED_HINT_PROFILES="high-priority" \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

DISTRACTOR_COUNTS="2 10 50 100 200" \

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
KV_RETENTION_MODE=all \
RETENTION_ATTRIBUTION_MODE=flush \
KV_RETENTION_RESET_MODE=restart \
STOP_ON_PROBE_FAILURE=1 \
DISTRACTOR_COUNTS="25 50 75 100 125 150" \
PROTECTED_INPUT_LEN=400 \
DISTRACTOR_INPUT_LEN=400 \
PROTECTED_HINT_PROFILES="high-priority" \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
KV_RETENTION_MODE=plot \
KV_RETENTION_PLOT_MATRIX_CSV=experiments/reports/latest_kv_retention_microbenchmark_matrix.csv \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

### Core Contract Knobs

```text
CONTROL_HINT_PROFILE
PROTECTED_HINT_PROFILES
CONTROL_CACHE_CONTROL_PROFILE
PROTECTED_CACHE_CONTROL_PROFILES
KV_RETENTION_RESET_MODE
KV_TIER_MODES
DISTRACTOR_COUNT
DISTRACTOR_COUNTS
PROTECTED_INPUT_LEN
DISTRACTOR_INPUT_LEN
GPU_ONLY_MEM_FRACTION_STATIC
SGLANG_TRANSFER_LOG_PROFILE
```

The contract is the source of truth for:

- precise runtime defaults
- model-readiness timing
- priority-hint defaults
- optional cache-control comparison settings
- top-level latest report paths

If you want to use `KV_RETENTION_RESET_MODE=flush`, first make sure the current
runtime actually serves the live flush endpoint:

```bash
cd ~/kv_cache_offloading

python3 - <<'PY'
import urllib.request, urllib.error

url = "http://127.0.0.1:8000/clear_kv_blocks"
req = urllib.request.Request(url, data=b"{}", method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        print("STATUS:", resp.status)
        print(resp.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP_ERROR:", e.code)
    print(e.read().decode())
except Exception as e:
    print("FAILED:", e)
PY
```

Expected success signal:

- `STATUS: 200`

If you still get `404`, rebuild the precise runtime images from the repaired
instrumented Dynamo source before using `flush`.

If you want to prove the source is fixed before rebuilding, these two checks
should both print matches:

```bash
cd ~/kv_cache_offloading

grep -n 'pub mod clear_kv_blocks;' \
  upstream/dynamo/lib/llm/src/http/service.rs

grep -n 'clear_kv_blocks_router(state.clone(), None)' \
  upstream/dynamo/lib/llm/src/http/service/service_v2.rs
```

The public experiment wrappers now automate this for you when you choose
`flush`:

- Experiment 9 (`KV_RETENTION_RESET_MODE=flush`)
- Experiment 10 sweep path (`EXPERIMENT_RESET_MODE=flush`)
- Experiment 11 (`EXPERIMENT_RESET_MODE=flush`)
- Experiment 12 (`EXPERIMENT_RESET_MODE=flush`)

In other words, the wrapper now does a live `POST /clear_kv_blocks` check after
runtime startup and before the experiment requests begin. If that check fails,
the wrapper exits early instead of letting you discover the problem halfway
through a sweep.

### Top-Level Outputs

```bash
cat experiments/reports/latest_kv_retention_microbenchmark_matrix.csv
cat experiments/reports/latest_kv_retention_microbenchmark_summary.csv
cat experiments/reports/latest_kv_retention_microbenchmark_summary.md
cat experiments/reports/latest_kv_retention_microbenchmark_run_contract.json

ls experiments/reports/latest_kv_retention_microbenchmark_*.svg
cat experiments/reports/latest_kv_retention_microbenchmark_chart_manifest.json
```

Main outputs:

- `latest_kv_retention_microbenchmark_matrix.csv`: normalized probe + sweep table
- `latest_kv_retention_microbenchmark_summary.csv`: one-row summary
- `latest_kv_retention_microbenchmark_run_contract.json`: exact resolved settings
- `replay_latency.svg`
- `replay_cached_tokens.svg`
- `survival_curve.svg`

### Decision Proof

Use these as the exact places to inspect when you want to prove that priority
retention signals were attached, read, applied, and summarized.

- [`contracts/kv_retention_microbenchmark.contract.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/kv_retention_microbenchmark.contract.sh)  
  Contract. Owns the public defaults for probe vs sweep, hint arms,
  distractor pressure, precise-runtime settings, and top-level latest outputs.

- [`agentbench/run_kv_retention_microbenchmark_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_kv_retention_microbenchmark_single_host.sh)  
  Public wrapper. Reads the contract, runs `probe` / `sweep` / `all` / `plot`,
  clears stale latest outputs, and writes the consolidated report and chart
  artifacts.

- [`experiments/scripts/retention_probe/build_kv_retention_microbenchmark_report.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/retention_probe/build_kv_retention_microbenchmark_report.py)  
  Report builder. Merges probe and sweep evidence into one compact matrix, one
  summary row, one markdown summary, and one `run_contract.json`.

- [`experiments/scripts/retention_probe/plot_kv_retention_microbenchmark.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/retention_probe/plot_kv_retention_microbenchmark.py)  
  Plotter. Reads only the matrix CSV and generates slide-ready SVG charts.

- [`experiments/scripts/retention_probe/run_kv_retention_probe.py:523`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/retention_probe/run_kv_retention_probe.py:523) `send_probe_request(...)`  
  Script layer. Builds the probe request and attaches the hint payload for
  `a_first`, distractors, and `a_replay`.

- [`experiments/scripts/retention_probe/run_kv_retention_probe.py:667`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/retention_probe/run_kv_retention_probe.py:667) `payload["priority"] = priority if priority is not None else ""`  
  Script layer. Records whether top-level priority was actually sent on the
  request path.

- [`upstream/dynamo/lib/llm/src/preprocessor.rs:174`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor.rs:174) `runtime_observability_extra_args_from_nvext(...)`  
  Dynamo. Preserves `nvext.agent_hints` and request metadata into runtime
  observability so later logs can still identify the request.

- [`upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:493`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:493) `priority = (request.get("routing") or {}).get("priority")`  
  Dynamo. Reads the routed priority value inside the live worker handler.

- [`upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:528`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:528) `async_generate(..., **self._priority_kwargs(priority))`  
  Dynamo. Applies the priority by forwarding it into the live generation call.

- [`runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py:2253`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py:2253) `wrap_priority_event_function(...)`  
  SGLang instrumentation patcher. Inserts the logging hooks that watch the
  priority path inside patched SGLang code.

- [`runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py:2700`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py:2700) `wrap_priority_event_function(text, "evict", "radix_cache.evict")`  
  SGLang instrumentation patcher. Hooks the eviction path so we can see whether
  priority-related evidence shows up when cache entries are removed.

- [`experiments/scripts/retention_probe/run_kv_retention_probe.py:1085`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/retention_probe/run_kv_retention_probe.py:1085) `if action == "priority_hint_seen":`  
  Report builder. Interprets raw `sglang.priority` events as “SGLang saw the
  priority hint.”

- [`experiments/scripts/retention_probe/run_kv_retention_probe.py:1087`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/retention_probe/run_kv_retention_probe.py:1087) `if action == "scheduler_priority_applied":`  
  Report builder. Interprets raw `sglang.priority` events as “SGLang says it
  actually applied scheduling priority.”

- [`experiments/scripts/retention_probe/run_kv_retention_probe.py:1197`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/retention_probe/run_kv_retention_probe.py:1197) `worker_priority_status(...)`  
  Report builder. Collapses the raw worker/SGLang evidence into the compact
  `worker_prio_status` field in the matrix.

Strongest proof in this setup: `scheduler_priority_applied` in the raw
`sglang.priority` event stream.

### Lower-Level Wrappers

These are the lower-level wrappers behind this experiment. Normally use the
single public wrapper above.

- [`agentbench/run_kv_retention_probe_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_kv_retention_probe_single_host.sh)
  - probe component
- [`agentbench/run_kv_retention_threshold_sweep_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_kv_retention_threshold_sweep_single_host.sh)
  - sweep component

## Experiment 10: Cache-Pinning Microbenchmark

This is the public cache-pinning entrypoint.

Contract files:

- [`contracts/cache_pinning_microbenchmark.contract.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/cache_pinning_microbenchmark.contract.sh)
- [`contracts/cache_pinning_microbenchmark.contract.md`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/cache_pinning_microbenchmark.contract.md)

Public wrapper:

- [`agentbench/run_cache_pinning_microbenchmark_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_cache_pinning_microbenchmark_single_host.sh)

Supported modes:

- `validate`: two-turn doc-style cache-pinning check
- `sweep`: threshold sweep, `off` vs `ephemeral:1h`
- `all`: validation, then sweep, then plot
- `plot`: rebuild charts from one existing matrix CSV

Direct wrapper default:

- `EXPERIMENT_RESET_MODE=restart`

### Run

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
CACHE_PINNING_MODE=validate \
./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
CACHE_PINNING_MODE=sweep \
DISTRACTOR_COUNTS="40 80 120 160" \
PROTECTED_INPUT_LEN=500 \
DISTRACTOR_INPUT_LEN=200 \
./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
CACHE_PINNING_MODE=all \
DISTRACTOR_COUNTS="40 80 120 160" \
PROTECTED_INPUT_LEN=500 \
DISTRACTOR_INPUT_LEN=200 \
./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
CACHE_PINNING_MODE=plot \
CACHE_PINNING_PLOT_MATRIX_CSV=experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv \
./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

### Core Contract Knobs

```text
CACHE_PINNING_FRONTEND_FLAG_MODE
CACHE_PINNING_TTL
CACHE_PINNING_PINNED_RATIO
SGLANG_HICACHE_MAX_PINNED_RATIO
CACHE_PINNING_HICACHE_RATIO
CACHE_PINNING_MEM_FRACTION_STATIC
```

The contract is the source of truth for:

- pinned Dynamo/SGLang refs
- frontend cache-control flag behavior
- TTL and pinned-ratio settings
- HiCache and memory settings
- readiness defaults

Pinned stack:

- Dynamo PR `#6213`
  - commit `7d3d4ec8e4ae865af2f903b21b4afabca28e1940`
- SGLang PR `#18941`
  - commit `ff2f70b0fcb6b3ea130c46927ed98edf69d5c17c`

### Top-Level Outputs

```bash
cat experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv
cat experiments/reports/latest_cache_pinning_microbenchmark_summary.csv
cat experiments/reports/latest_cache_pinning_microbenchmark_summary.md
cat experiments/reports/latest_cache_pinning_microbenchmark_run_contract.json

ls experiments/reports/latest_cache_pinning_microbenchmark_*.svg
cat experiments/reports/latest_cache_pinning_microbenchmark_chart_manifest.json
```

Main outputs:

- `latest_cache_pinning_microbenchmark_matrix.csv`: validation + sweep table
- `latest_cache_pinning_microbenchmark_summary.csv`: one-row summary
- `latest_cache_pinning_microbenchmark_run_contract.json`: exact resolved settings
- `validation_latency.svg` / `validation_cached_tokens.svg`
- `sweep_replay_latency.svg` / `sweep_replay_cached_tokens.svg`

### Decision Proof

These are the exact places to inspect when you want to prove the signal path.

- [`contracts/cache_pinning_microbenchmark.contract.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/cache_pinning_microbenchmark.contract.sh)  
  Contract. Owns the pinned repos, commits, frontend flag behavior, router mode,
  request type, TTL, pinned ratio, HiCache knobs, and readiness defaults.

- [`agentbench/run_cache_pinning_microbenchmark_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_cache_pinning_microbenchmark_single_host.sh)  
  Public wrapper. Reads the contract, runs validate/sweep/all/plot, clears stale
  latest outputs, and writes the consolidated report and chart artifacts.

- [`experiments/scripts/cache_pinning/build_cache_pinning_microbenchmark_report.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/cache_pinning/build_cache_pinning_microbenchmark_report.py)  
  Report builder. Merges validation and sweep evidence into one compact matrix,
  one summary row, one markdown summary, and one `run_contract.json`.

- [`experiments/scripts/cache_pinning/plot_cache_pinning_microbenchmark.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/cache_pinning/plot_cache_pinning_microbenchmark.py)  
  Plotter. Reads only the matrix CSV and generates slide-ready SVG charts.

- [`runtime_instrumentation/repair_cache_pinning_dynamo_source.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/repair_cache_pinning_dynamo_source.py)  
  Local patcher for Dynamo. Adds router-side logs:
  - `router.cache_control_seen`
  - `router.pin_state_created`
  - `router.pin_state_skipped`
  - `router.pin_prefix_spawned`
  - and patches `init_llm.py` so the worker serves the live `cache_control` endpoint

- [`runtime_instrumentation/repair_cache_pinning_sglang_source.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/repair_cache_pinning_sglang_source.py)  
  Local patcher for SGLang. Adds worker-side logs:
  - `worker.pin_prefix_applied`
  - `worker.pin_refreshed_host_insert`
  - `worker.pin_refreshed_cache_hit`

### Feature Codepaths Under Test

- `upstream/dynamo_cache_pinning/lib/llm/src/preprocessor.rs` (Dynamo)  
  Reads `nvext.cache_control` and carries TTL into routing metadata.

- `upstream/dynamo_cache_pinning/lib/llm/src/kv_router/push_router.rs` (Dynamo)  
  Builds pin state and spawns the pin-prefix request after generation.

- `upstream/dynamo_cache_pinning/lib/llm/src/kv_router/cache_control.rs` (Dynamo)  
  Sends the TTL pin RPC toward the worker.

- `upstream/dynamo_cache_pinning/components/src/dynamo/sglang/init_llm.py` (Dynamo)  
  Serves the live `cache_control` endpoint on the worker.

- `upstream/dynamo_cache_pinning/components/src/dynamo/frontend/frontend_args.py` (Dynamo)  
  Exposes the cache-control frontend flag.

- `upstream/sglang_cache_pinning/python/sglang/srt/mem_cache/hiradix_cache.py` (SGLang)  
  Implements `pin_prefix(...)` and refresh-on-hit TTL behavior.

- `upstream/sglang_cache_pinning/python/sglang/srt/managers/scheduler.py` (SGLang)  
  Enforces pin-budget gating.

### Success Reading

- Validation success:
  - `turn2_cached > 0`
  - `router_pin=spawned`
  - `worker_pin=applied`

- Sweep success:
  - protected arm stays warm deeper than control

- If both arms turn cold at the same point:
  - cache pinning did not improve retention in that setup

### Lower-Level Wrappers

These are the lower-level wrappers behind this experiment. Normally use the
single public wrapper above.

- [`agentbench/run_cache_pinning_doc_validation_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_cache_pinning_doc_validation_single_host.sh)
  - validate component
- [`agentbench/run_cache_pinning_retention_threshold_sweep_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_cache_pinning_retention_threshold_sweep_single_host.sh)
  - sweep component

Component report names now use compact fields such as:

- `output_tokens`
- `router_pin`
- `worker_pin`
- `cache_control`
- `replay_http_status`
- `delta_ms`
- `speedup_x`
- `warm`
- `reuse_signal`
- `result`

## Experiment 11: Priority Scheduling Probe

This is the public priority-scheduling microbenchmark entrypoint.

Contract files:

- [`contracts/priority_scheduling_microbenchmark.contract.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/priority_scheduling_microbenchmark.contract.sh)
- [`contracts/priority_scheduling_microbenchmark.contract.md`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/priority_scheduling_microbenchmark.contract.md)

Public wrapper:

- [`agentbench/run_priority_scheduling_microbenchmark_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_priority_scheduling_microbenchmark_single_host.sh)

Supported modes:

- `probe`: one live mixed-priority burst
- `sweep`: multiple live bursts over one public knob
- `all`: sweep, then plot
- `plot`: rebuild charts from one existing matrix CSV

This is a synthetic scheduling experiment. It does **not** use SWE-bench.

### Run

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
PRIORITY_SCHEDULING_MODE=probe \
./agentbench/run_priority_scheduling_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
PRIORITY_SCHEDULING_MODE=sweep \
PRIORITY_SCHEDULING_SWEEP_AXIS=PRIORITY_ARRIVAL_GAP_MS \
PRIORITY_SCHEDULING_SWEEP_VALUES="50 100 200 400" \
./agentbench/run_priority_scheduling_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
PRIORITY_SCHEDULING_MODE=all \
LOW_PRIORITY_COUNT=8 \
HIGH_PRIORITY_COUNT=4 \
PRIORITY_INPUT_LEN=4000 \
PRIORITY_OUTPUT_LEN=128 \
PRIORITY_ARRIVAL_GAP_MS=200 \
PRIORITY_INTER_REQUEST_GAP_MS=20 \
./agentbench/run_priority_scheduling_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
PRIORITY_SCHEDULING_MODE=plot \
PRIORITY_SCHEDULING_PLOT_MATRIX_CSV=experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv \
./agentbench/run_priority_scheduling_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

### Core Contract Knobs

```text
LOW_PRIORITY_COUNT
HIGH_PRIORITY_COUNT
LOW_PRIORITY_VALUE
HIGH_PRIORITY_VALUE
PRIORITY_INPUT_LEN
PRIORITY_OUTPUT_LEN
PRIORITY_ARRIVAL_GAP_MS
PRIORITY_INTER_REQUEST_GAP_MS
PRIORITY_SCHEDULING_SWEEP_AXIS
PRIORITY_SCHEDULING_SWEEP_VALUES
PRIORITY_TOP_LEVEL_PRIORITY_MODE
PRIORITY_REQUEST_CONTEXT_MODE
SGLANG_TRANSFER_LOG_PROFILE
WORKER_BASE_ARGS
```

The contract is the source of truth for:

- precise runtime defaults
- model-readiness timing
- queue-burst shape
- priority values
- top-level latest report paths

### Top-Level Outputs

```bash
cat experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv
cat experiments/reports/latest_priority_scheduling_microbenchmark_summary.csv
cat experiments/reports/latest_priority_scheduling_microbenchmark_summary.md
cat experiments/reports/latest_priority_scheduling_microbenchmark_run_contract.json

ls experiments/reports/latest_priority_scheduling_microbenchmark_*.svg
cat experiments/reports/latest_priority_scheduling_microbenchmark_chart_manifest.json
```

Main outputs:

- `latest_priority_scheduling_microbenchmark_matrix.csv`: one row per request or per sweep point
- `latest_priority_scheduling_microbenchmark_summary.csv`: one-row summary
- `latest_priority_scheduling_microbenchmark_run_contract.json`: exact resolved settings
- `attach_gain.svg`
- `queue_wait.svg`

### Debug

```bash
docker logs -f dynamo-sglang-worker
```

### Decision Proof

Use these as the exact places to inspect when you want to prove that queue
priority was attached, read, applied, and observed.

- [`contracts/priority_scheduling_microbenchmark.contract.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/priority_scheduling_microbenchmark.contract.sh)  
  Contract. Owns the public defaults for burst shape, priority values,
  precise-runtime settings, and top-level latest outputs.

- [`agentbench/run_priority_scheduling_microbenchmark_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_priority_scheduling_microbenchmark_single_host.sh)  
  Public wrapper. Reads the contract, runs `probe` / `sweep` / `all` / `plot`, clears
  stale latest outputs, and writes the consolidated report and chart artifacts.

- [`experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py)  
  Report builder. Normalizes the probe’s readable request table into one compact
  matrix, one summary row, one markdown summary, and one `run_contract.json`.

- [`experiments/scripts/priority_scheduling/plot_priority_scheduling_microbenchmark.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/plot_priority_scheduling_microbenchmark.py)  
  Plotter. Reads only the matrix CSV and generates slide-ready SVG charts.

- [`experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:350`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:350) `build_hint_payload(...)`  
  Script layer. Builds `agent_hints.priority`.

- [`experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:356`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:356) `payload["priority"] = priority_value`  
  Script layer. Adds top-level request priority when the frontend supports it.

- [`experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:608`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:608) `priority = top_level_priority_from_hints(hints)`  
  Script layer. Decides what priority value should be attempted for the live
  request.

- [`upstream/dynamo/lib/llm/src/preprocessor.rs:408`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor.rs:408) `RoutingHints { ... priority_jump, priority ... }`  
  Dynamo. Carries priority through the routed request structure.

- [`upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:493`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:493) `priority = (request.get("routing") or {}).get("priority")`  
  Dynamo. Reads the routed priority inside the live worker handler.

- [`upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:542`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:542) `_priority_kwargs(...)`  
  Dynamo. Applies the priority by forwarding it to generation.

- [`runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py:2253`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py:2253) `wrap_priority_event_function(...)`  
  SGLang instrumentation patcher. Injects priority-path logging into patched
  SGLang code.

- [`runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py:2700`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py:2700) `wrap_priority_event_function(text, "evict", "radix_cache.evict")`  
  SGLang instrumentation patcher. Hooks eviction-time priority evidence too.

- [`experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1052`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1052) parses `sglang.priority` events  
  Report builder. Turns raw SGLang priority logs into structured report fields.

- [`experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1166`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1166) `worker_priority_path_status(...)`  
  Report builder. Decides whether the worker-side priority proof is strong,
  partial, or missing.

- [`experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1212`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1212) computes leapfrogs and wait-time comparison  
  Report builder. Converts raw timing/order into the user-facing scheduling
  proof columns.

Strongest proof in this setup: `sglang_scheduler_priority_applied=true` plus a
positive `attach_gain` / `beat_low_attach`.

### Lower-Level Wrapper

Normally use the single public wrapper above.

- [`agentbench/run_priority_scheduling_probe_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_priority_scheduling_probe_single_host.sh)
  - probe component

Component report names now use compact fields such as:

- `request`
- `prio_class`
- `arrival`
- `attach`
- `complete`
- `attach_gain`
- `complete_gain`
- `beat_low_attach`
- `beat_low_complete`
- `queue_ms`
- `latency_ms`
- `worker_hint_prio`
- `sent_top_prio`
- `worker_top_prio`
- `sglang_prio`
- `runtime_match`
- `effect`

### Main Knobs

```text
LOW_PRIORITY_COUNT
HIGH_PRIORITY_COUNT
PRIORITY_INPUT_LEN
PRIORITY_OUTPUT_LEN
PRIORITY_ARRIVAL_GAP_MS
PRIORITY_INTER_REQUEST_GAP_MS
PRIORITY_SCHEDULING_SWEEP_AXIS
PRIORITY_SCHEDULING_SWEEP_VALUES
PRIORITY_TOP_LEVEL_PRIORITY_MODE
```

## Experiment 12: Speculative Prefill Probe

This is the public speculative-prefill microbenchmark entrypoint.

Contract files:

- [`contracts/speculative_prefill_microbenchmark.contract.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/speculative_prefill_microbenchmark.contract.sh)
- [`contracts/speculative_prefill_microbenchmark.contract.md`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/speculative_prefill_microbenchmark.contract.md)

Public wrapper:

- [`agentbench/run_speculative_prefill_microbenchmark_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_speculative_prefill_microbenchmark_single_host.sh)

Supported modes:

- `probe`: one live two-turn speculative-prefill run
- `sweep`: multiple live runs over one public knob
- `all`: sweep, then plot
- `plot`: rebuild charts from one existing matrix CSV

This is a synthetic two-turn experiment. It does **not** use SWE-bench.

### Run

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
SPEC_PREFILL_MODE=probe \
./agentbench/run_speculative_prefill_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
SPEC_PREFILL_MODE=sweep \
SPEC_PREFILL_SWEEP_AXIS=SPEC_PREFILL_WARMUP_WAIT_MS \
SPEC_PREFILL_SWEEP_VALUES="0 100 250 500 1000" \
./agentbench/run_speculative_prefill_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
SPEC_PREFILL_MODE=all \
SPEC_PREFILL_TURN_A_WORDS=4000 \
SPEC_PREFILL_TURN_B_WORDS=512 \
SPEC_PREFILL_OUTPUT_TOKENS=64 \
SPEC_PREFILL_WARMUP_WAIT_MS=500 \
./agentbench/run_speculative_prefill_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
SPEC_PREFILL_MODE=plot \
SPEC_PREFILL_PLOT_MATRIX_CSV=experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv \
./agentbench/run_speculative_prefill_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

### Core Contract Knobs

```text
SPEC_PREFILL_TURN_A_WORDS
SPEC_PREFILL_TURN_B_WORDS
SPEC_PREFILL_OUTPUT_TOKENS
SPEC_PREFILL_WARMUP_WAIT_MS
SPEC_PREFILL_SWEEP_AXIS
SPEC_PREFILL_SWEEP_VALUES
SPEC_PREFILL_REQUEST_CONTEXT_MODE
SGLANG_TRANSFER_LOG_PROFILE
WORKER_BASE_ARGS
```

The contract is the source of truth for:

- precise runtime defaults
- model-readiness timing
- two-turn workload shape
- warmup timing
- top-level latest report paths

### Top-Level Outputs

```bash
cat experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv
cat experiments/reports/latest_speculative_prefill_microbenchmark_summary.csv
cat experiments/reports/latest_speculative_prefill_microbenchmark_summary.md
cat experiments/reports/latest_speculative_prefill_microbenchmark_run_contract.json

ls experiments/reports/latest_speculative_prefill_microbenchmark_*.svg
cat experiments/reports/latest_speculative_prefill_microbenchmark_chart_manifest.json
```

Main outputs:

- `latest_speculative_prefill_microbenchmark_matrix.csv`: one row per arm or per sweep-arm point
- `latest_speculative_prefill_microbenchmark_summary.csv`: one-row summary
- `latest_speculative_prefill_microbenchmark_run_contract.json`: exact resolved settings
- `turnb_latency.svg`
- `turnb_cached.svg`

### Debug

```bash
docker logs -f dynamo-sglang-worker
```

### Decision Proof

Use these as the exact places to inspect when you want to prove that Dynamo
made a speculative-prefill decision.

- [`contracts/speculative_prefill_microbenchmark.contract.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/speculative_prefill_microbenchmark.contract.sh)  
  Contract. Owns the public defaults for the two-turn workload,
  precise-runtime settings, and top-level latest outputs.

- [`agentbench/run_speculative_prefill_microbenchmark_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_speculative_prefill_microbenchmark_single_host.sh)  
  Public wrapper. Reads the contract, runs `probe` / `sweep` / `all` / `plot`, clears
  stale latest outputs, and writes the consolidated report and chart artifacts.

- [`experiments/scripts/speculative_prefill/build_speculative_prefill_microbenchmark_report.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/build_speculative_prefill_microbenchmark_report.py)  
  Report builder. Normalizes the probe matrix into one compact matrix, one
  summary row, one markdown summary, and one `run_contract.json`.

- [`experiments/scripts/speculative_prefill/plot_speculative_prefill_microbenchmark.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/plot_speculative_prefill_microbenchmark.py)  
  Plotter. Reads only the matrix CSV and generates slide-ready SVG charts.

- [`experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:413`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:413) `"speculative_prefill": spec_prefill`  
  Script layer. Attaches the `speculative_prefill` hint to the protected arm.

- [`experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:415`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:415) `"spec_prefill_target_request_id": target_request_id`  
  Script layer. Attaches the exact turn-B request identity that the warmup is
  supposed to target.

- [`upstream/dynamo/lib/llm/src/protocols/openai/nvext.rs:426`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/protocols/openai/nvext.rs:426) `pub speculative_prefill: Option<bool>`  
  Dynamo. Declares the typed hint field on `AgentHints`.

- [`upstream/dynamo/lib/llm/src/preprocessor.rs:1810`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor.rs:1810) `speculative_prefill::maybe_wrap_stream(...)`  
  Dynamo. Calls into the real speculative-prefill decision path.

- [`upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:198`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:198) reads `hints.speculative_prefill`  
  Dynamo. This is the exact line that reads the hint.

- [`upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:202`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:202) emits `worker.spec_prefill.wrap_checked`  
  Dynamo. Proof that Dynamo reached the decision gate and recorded whether the
  hint was enabled.

- [`upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:219`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:219) emits `worker.spec_prefill.task_spawned`  
  Dynamo. Proof that it decided to launch the background speculative-prefill
  task.

- [`upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:355`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:355) emits `worker.spec_prefill.prefill_sent`  
  Dynamo. Strong proof that the synthetic warmup request was actually sent.

- [`upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:373`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:373) emits `worker.spec_prefill.prefill_completed`  
  Dynamo. Strong proof that the synthetic warmup request completed.

- [`experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:669`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:669) matches `worker.spec_prefill.wrap_checked`  
  Report builder. Pulls the decision-path runtime events back into the report.

- [`experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:677`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:677) `prefill_spawned`, `prefill_sent`, `prefill_done`  
  Report builder. Converts those raw runtime events into the compact proof
  columns in the matrix.

Strongest proof in this setup: `worker.spec_prefill.prefill_sent` followed by
`worker.spec_prefill.prefill_completed`.

### Lower-Level Wrapper

Normally use the single public wrapper above.

- [`agentbench/run_speculative_prefill_probe_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_speculative_prefill_probe_single_host.sh)
  - probe component

Component report names now use compact fields such as:

- `arm`
- `spec_prefill`
- `turn_a_ms`
- `turn_b_ms`
- `turn_b_gain_ms`
- `turn_b_cached`
- `turn_b_reuse`
- `hint_status`
- `prefill_wrap`
- `prefill_spawned`
- `prefill_sent`
- `prefill_done`
- `prefill_target_seen`
- `prefill_tokens`
- `effect`

### Main Knobs

```text
SPEC_PREFILL_TURN_A_WORDS
SPEC_PREFILL_TURN_B_WORDS
SPEC_PREFILL_OUTPUT_TOKENS
SPEC_PREFILL_WARMUP_WAIT_MS
SPEC_PREFILL_REQUEST_CONTEXT_MODE
```

## Experiment Suite: Agentic Hint Sweeps

Use this when you want one long run across the public microbenchmarks for:

- Experiment 9: KV retention
- Experiment 10: cache pinning
- Experiment 11: priority scheduling
- Experiment 12: speculative prefill

Public wrappers:

- [`agentbench/run_agentic_hint_sweeps_suite_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_agentic_hint_sweeps_suite_single_host.sh)
- [`agentbench/run_agentic_hint_sweeps_suite_nohup.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_agentic_hint_sweeps_suite_nohup.sh)

### Run

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
SUITE_ISOLATION_MODE=fast \
SUITE_EXPERIMENTS="9 11 12" \
DISTRACTOR_COUNTS="25 50 75 100" \
PROTECTED_INPUT_LEN=400 \
DISTRACTOR_INPUT_LEN=400 \
PROTECTED_HINT_PROFILES="high-priority" \
PRIORITY_SCHEDULING_SWEEP_AXIS=PRIORITY_ARRIVAL_GAP_MS \
PRIORITY_SCHEDULING_SWEEP_VALUES="50 100 200 400" \
LOW_PRIORITY_COUNT=8 \
HIGH_PRIORITY_COUNT=4 \
PRIORITY_INPUT_LEN=4000 \
PRIORITY_OUTPUT_LEN=128 \
SPEC_PREFILL_SWEEP_AXIS=SPEC_PREFILL_WARMUP_WAIT_MS \
SPEC_PREFILL_SWEEP_VALUES="0 100 250 500 1000" \
SPEC_PREFILL_TURN_A_WORDS=4000 \
SPEC_PREFILL_TURN_B_WORDS=512 \
SPEC_PREFILL_OUTPUT_TOKENS=64 \
./agentbench/run_agentic_hint_sweeps_suite_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

### Nohup

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
SUITE_ISOLATION_MODE=fast \
SUITE_EXPERIMENTS="9 11 12" \
DISTRACTOR_COUNTS="25 50 75 100" \
PROTECTED_INPUT_LEN=400 \
DISTRACTOR_INPUT_LEN=400 \
PROTECTED_HINT_PROFILES="high-priority" \
PRIORITY_SCHEDULING_SWEEP_AXIS=PRIORITY_ARRIVAL_GAP_MS \
PRIORITY_SCHEDULING_SWEEP_VALUES="50 100 200 400" \
LOW_PRIORITY_COUNT=8 \
HIGH_PRIORITY_COUNT=4 \
PRIORITY_INPUT_LEN=4000 \
PRIORITY_OUTPUT_LEN=128 \
SPEC_PREFILL_SWEEP_AXIS=SPEC_PREFILL_WARMUP_WAIT_MS \
SPEC_PREFILL_SWEEP_VALUES="0 100 250 500 1000" \
SPEC_PREFILL_TURN_A_WORDS=4000 \
SPEC_PREFILL_TURN_B_WORDS=512 \
SPEC_PREFILL_OUTPUT_TOKENS=64 \
./agentbench/run_agentic_hint_sweeps_suite_nohup.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
SUITE_INTERACTIVE_BUILD_PROGRESS=0 \
SUITE_ISOLATION_MODE=clean \
SUITE_EXPERIMENTS="10" \
CACHE_PINNING_MODE=all \
DISTRACTOR_COUNTS="40 80 120 160 200 240" \
PROTECTED_INPUT_LEN=500 \
DISTRACTOR_INPUT_LEN=200 \
./agentbench/run_agentic_hint_sweeps_suite_nohup.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

### Core Suite Knobs

```text
DYNAMO_MACHINE_PROFILE
SUITE_MODEL
SUITE_EXPERIMENTS
SUITE_CONTINUE_ON_ERROR
SUITE_ISOLATION_MODE
SUITE_DEFAULT_MODE
SUITE_INTERACTIVE_BUILD_PROGRESS
SUITE_ENSURE_PRECISE_RUNTIME
```

`SUITE_INTERACTIVE_BUILD_PROGRESS=1` keeps Docker's live progress UI for foreground runs when an image rebuild happens. On nohup runs, logs stay plain because there is no TTY.

Charts are published to [`experiments/charts/`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/charts) as soon as each experiment finishes, so you do not need to wait for the whole suite before the first chart files appear.

[`aws/download.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/aws/download.sh) now downloads both:

- [`experiments/reports/`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/reports)
- [`experiments/charts/`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/charts)

`SUITE_ENSURE_PRECISE_RUNTIME` controls a one-time suite preflight before the first experiment:

- `auto` (default): run `ensure_precise_runtime_ready.sh --build-if-missing` only when `DYNAMO_MACHINE_PROFILE=gh200`
- `1`: always run that suite-level preflight
- `0`: never run that suite-level preflight

Recommended behavior:

- `gh200`: leave `SUITE_ENSURE_PRECISE_RUNTIME=auto`
- `ec2`: leave `SUITE_ENSURE_PRECISE_RUNTIME=auto` and it will skip the extra suite-level prebuild

So on GH200, the suite now automatically does the equivalent of:

```bash
DYNAMO_MACHINE_PROFILE=gh200 \
./runtime_instrumentation/ensure_precise_runtime_ready.sh \
  --machine-profile gh200 \
  --build-if-missing
```

once at suite startup, before Experiment 9 begins.

`SUITE_ISOLATION_MODE` is the main runtime policy knob:

- `clean`:
  - restart between experiments
  - restart between sweep values
  - keep the same prompts across sweep values
- `fast`:
  - restart between experiments
  - no restart between sweep values
  - no flush between sweep values
  - change prompts across sweep values so runs do not reuse the exact same token sequence

Default behavior:

- `SUITE_DEFAULT_MODE=sweep`

So the suite now defaults to the main sweep for each experiment instead of quietly running probe/validate work first. If you want a different mode for one experiment, set that experiment's mode explicitly, for example `KV_RETENTION_MODE=plot`.

Use `clean` for the careful runs you want to trust for conclusions.

Use `fast` for quick debugging and iteration when you want to avoid the long wait inside an experiment.

For nohup runs, `suite_nohup.log` is created immediately, so you can tail it right away:

```bash
tail -n 20 -f experiments/reports/latest_agentic_hint_sweeps_suite_nohup.log
tail -n 200 -f experiments/reports/latest_agentic_hint_sweeps_suite_nohup.log
tail -n 200 -f experiments/reports/latest_agentic_hint_sweeps_suite_driver.log
```

Per-experiment sweep knobs still pass through unchanged. Examples:

```text
KV_RETENTION_SWEEP_VALUES
CACHE_PINNING_TTL
CACHE_PINNING_HICACHE_RATIO
PRIORITY_SCHEDULING_SWEEP_AXIS
PRIORITY_SCHEDULING_SWEEP_VALUES
SPEC_PREFILL_SWEEP_AXIS
SPEC_PREFILL_SWEEP_VALUES
```

### Top-Level Outputs

```bash
cat experiments/reports/latest_agentic_hint_sweeps_suite_summary.md
cat experiments/reports/latest_agentic_hint_sweeps_suite_manifest.json
cat experiments/reports/latest_agentic_hint_sweeps_suite_driver.log
```

Main outputs:

- `latest_agentic_hint_sweeps_suite_summary.md`: one landing-page summary for the full run
- `latest_agentic_hint_sweeps_suite_manifest.json`: exact experiment statuses, chart paths, and report paths
- `latest_agentic_hint_sweeps_suite_driver.log`: suite-level launch log
- `experiments/charts/`: shared folder containing only the latest chart SVGs and the matrix CSVs they were generated from

The suite banners now show the actual selected count, for example `1/3`, `2/3`, `3/3`.
When a wrapper uses `MODE=all`, the banner also shows the resolved behavior, for example:

- Experiment 9: `all (resolved to sweep + plot)`
- Experiment 10: `all (resolved to validate + sweep + plot)`
- Experiment 11: `all (resolved to sweep + plot)`
- Experiment 12: `all (resolved to sweep + plot)`

The suite terminal output and nohup log now print very clear start/end banners
for each experiment block, so you can easily see when 9, 10, 11, or 12 begins
and ends.

If a precise or cache-pinning image rebuild happens, you will also now see
clear build banners such as:

- `PRECISE IMAGE BUILD START`
- `PRECISE IMAGE BUILD DONE`
- `CACHE PINNING IMAGE BUILD START`
- `CACHE PINNING IMAGE BUILD DONE`

These appear in both the live terminal run and the nohup log.

### If Docker Space Is Tight

Use this before rerunning the suite if a Dynamo image build fails because of
disk space:

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh stop || true

df -h /
docker system df

docker container prune -f
docker image prune -f
docker builder prune -f

df -h /
docker system df
```

If you still need a more aggressive cleanup and do not need old Docker state:

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh stop || true

docker system prune -af
docker builder prune -af

df -h /
docker system df
```
