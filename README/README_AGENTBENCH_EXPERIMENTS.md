# AgentBench Experiments

Use this guide as a live EC2 runbook for AgentBench + Deep Agents + Dynamo +
SGLang experiments.

The runtime path is:

```text
SWE-bench Pro -> AgentBench -> Deep Agents -> Dynamo frontend -> SGLang worker -> reports
```

## Experiment Snapshot

- **Experiment 9: KV retention** evaluates whether important prompts stay in KV
  cache after many competing prompts.
- **Experiment 10: Cache pinning** evaluates whether `cache_control` TTL hints
  keep protected prompts warm longer than unpinned prompts.
- **Experiment 11: Priority scheduling** evaluates whether high-priority
  requests jump ahead of lower-priority work in the queue.
- **Experiment 12: Speculative prefill** evaluates whether a current request can
  warm the KV cache for a likely next request.
- **Experiment 13: Latency sensitivity** evaluates whether latency-sensitive
  requests get priority-like queue movement.

## Quick Decision Guide

- **SWE-bench prompt / tool / behavior traces**: use [Experiment 6](#experiment-6-prompt-evolution-batch).
- **KV retention/eviction probe**: use [Experiment 9](#experiment-9-kv-retention-probe).
- **Cache-control retention**: use [Experiment 10](#experiment-10-cache-pinning-microbenchmark).
- **Priority scheduling**: use [Experiment 11](#experiment-11-priority-scheduling-probe).
- **Latency sensitivity**: use [Experiment 13](#experiment-13-latency-sensitivity-probe).
- **Speculative prefill**: use [Experiment 12](#experiment-12-speculative-prefill-probe).
- **Run the GH200 suite sequentially**: use [Experiment Suite: Agentic Hint Sweeps](#experiment-suite-agentic-hint-sweeps).

For transfer-logging internals, see
[runtime_instrumentation/sglang_transfer_logging/README.md](../runtime_instrumentation/sglang_transfer_logging/README.md).

## Supported Hints At A Glance

These are the main Dynamo-facing knobs that are worth treating as real runtime
controls in this setup.

| Hint | Status | What it does |
|---|---|---|
| `priority` | supported | Main scheduling hint. Affects router ordering and backend priority behavior. |
| `osl` | supported | Expected output length. Used for routing/resource estimation. |
| `expected_output_tokens` | supported alias | Same role as `osl`; Dynamo maps either one into routing. |
| `speculative_prefill` | supported | Warms likely next-turn KV cache after the current response finishes. |
| `latency_sensitivity` | experimental/deprecated fallback | Older priority-like fallback. Use [Experiment 13](#experiment-13-latency-sensitivity-probe) to test whether it is seen and causes visible queue movement. |

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

### Clear Generated Reports And Charts

Use this when you want to remove old generated outputs and start fresh:

```bash
cd ~/kv_cache_offloading

./clear_reports.sh
```

For non-interactive cleanup:

```bash
cd ~/kv_cache_offloading

./clear_reports.sh --yes
```

What it clears:

- `experiments/reports/*`
- `experiments/charts/*`

What it keeps:

- `experiments/raw`
- `experiments/runtime_state`
- upstream Dynamo/SGLang sources
- Docker images
- model caches

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

On `gh200`, the cache-pinning image helper now also repairs the `NATS` and
`etcd` download steps automatically so ARM builds use the real `arm64`
release asset names rather than broken `linux/arm64` paths.

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

## Experiment 6: Prompt Evolution Batch

Use this when your main goal is to generate prompt-evolution reports across a
range of SWE-bench Pro tasks, including:

- the exact model-facing request
- tool-capable runtime context
- tool calls made during the task
- per-phase planning / execution / review summaries
- final model behavior for each SWE-bench task

What made tool calling work reliably:

- use `DYN_TOOL_CALL_PARSER=qwen3_coder`
- use `DYN_REASONING_PARSER=qwen3`
- use pinned upstream Deep Agents
- require a tool-loop preflight before the batch
- let Deep Agents call tools naturally with a small execution loop
- soft-stop long recursion tasks instead of killing the batch
- refresh public CSVs after every task

Automated version: stop Dynamo, restart it with the chosen model, wait for
`/v1/models`, run a smoke test, then launch the batch.

```bash
cd ~/kv_cache_offloading

RUN_ID="exp6_prompt_evolution_gh200_1"
LOG_DIR="experiments/reports/exp6_prompt_evolution_nohup/${RUN_ID}"
mkdir -p "${LOG_DIR}"

nohup env \
  AGENTBENCH_EXECUTION_LOOP=1 \
  AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=3 \
  AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=0 \
  AGENTBENCH_EXECUTION_GUARD=0 \
  AGENTBENCH_PRINT_CHECKPOINTS=1 \
  DYN_TOOL_CALL_PARSER=qwen3_coder \
  DYN_REASONING_PARSER=qwen3 \
  AGENTBENCH_DEEPAGENTS_SOURCE=upstream \
  AGENTBENCH_FORCE_TOOL_CHOICE=auto \
  AGENTBENCH_DISABLE_GENERAL_PURPOSE_SUBAGENT=1 \
  AGENTBENCH_BATCH_CONTINUE_ON_ERROR=0 \
  AGENTBENCH_SOFT_STOP_RECURSION=1 \
  PROMPT_EVOLUTION_REFRESH_TRAJECTORY_CATALOG_EACH_TASK=1 \
  PROMPT_EVOLUTION_REFRESH_PUBLIC_REPORTS_EACH_TASK=1 \
  AGENTBENCH_AGENT_RECURSION_LIMIT=1000 \
  AGENTBENCH_MODEL_ONLY_PHASES="" \
  AGENTBENCH_TRACE_AGENT_STREAM=0 \
  PROMPT_EVOLUTION_REQUIRE_TOOL_LOOP=1 \
  PROMPT_EVOLUTION_TOOL_LOOP_CASE=edit-validate \
  PROMPT_EVOLUTION_BATCH_ID="${RUN_ID}" \
  DYNAMO_MACHINE_PROFILE=gh200 \
  PRECISE_START_MODE=clean \
  PROMPT_EVOLUTION_BATCH_START_INDEX=0 \
  PROMPT_EVOLUTION_BATCH_END_INDEX=730 \
  PROMPT_EVOLUTION_VALUE_CHAR_LIMIT=200000 \
  ./agentbench/run_prompt_evolution_batch_single_host.sh \
    Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
  >> "${LOG_DIR}/run.log" 2>&1 < /dev/null &

echo "RUN_ID=${RUN_ID}"
echo "LOG=${LOG_DIR}/run.log"
echo "PID=$!"
```

Watch it:

```bash
tail -f "${LOG_DIR}/run.log"
```

If your terminal reconnects later:

```bash
tail -f "$(ls -td experiments/reports/exp6_prompt_evolution_nohup/* | head -1)/run.log"
```

To pause the Exp6 nohup run and resume another day:

```bash
cd ~/kv_cache_offloading

# Stop the Exp6 batch wrapper and child SWE-bench batch loop.
pkill -f run_prompt_evolution_batch_single_host.sh || true
pkill -f run_swebench_batch_single_host.sh || true

# Stop the live Dynamo runtime.
./run_dynamo_single_host.sh stop || true
```

To resume, rerun the same nohup command with the same:

```bash
RUN_ID="exp6_prompt_evolution_gh200_1"
PROMPT_EVOLUTION_BATCH_ID="${RUN_ID}"
```

The batch will skip tasks already recorded in
`experiments/reports/batches/${RUN_ID}/task_trace_index.csv` and retry the first
missing task.

To watch the worker after the restart:

```bash
docker logs -f dynamo-sglang-worker
```

This produces prompt-evolution summaries such as:

```bash
cat experiments/reports/prompt_evolution_task_summary.csv
cat experiments/reports/prompt_evolution_run_overview.csv
```

It now also produces a per-task trace index that points straight to the
prompt-evolution, tool-call, and phase-summary artifacts for each SWE-bench
task in the batch:

```bash
cat experiments/reports/latest_prompt_evolution_trace_index.md
cat experiments/reports/latest_prompt_evolution_trace_index.csv
```

Use a new `RUN_ID` to start a fresh Experiment 6 run. Reuse the same `RUN_ID`
to continue a stopped run.

The wrapper uses `PROMPT_EVOLUTION_BATCH_ID="${RUN_ID}"` as the batch folder
name. If that batch folder already exists, the run continues from the first
missing task and keeps the rows already produced. If it does not exist, the run
starts fresh and clears old Experiment 6 public/report state.

If a task fails during SWE-bench repo checkout with `git checkout <commit>`
exit status `128`, rerun with the same `RUN_ID` after pulling the latest scripts.
The workspace prep now fetches the missing commit and retries the checkout once.
If it still fails, the error prints the stale shared repo cache under
`agentbench/repos/`; remove only that repo cache and rerun the same `RUN_ID`.

To confirm on GH200 before launching:

```bash
cd ~/kv_cache_offloading

RUN_ID="exp6_prompt_evolution_gh200_1"
BATCH_DIR="experiments/reports/batches/${RUN_ID}"

if [[ -d "$BATCH_DIR" ]]; then
  echo "Will resume: $BATCH_DIR"
else
  echo "Will start fresh: $BATCH_DIR"
fi
```

The latest readable Experiment 6 outputs are copied into the shared chart
folder:

```bash
ls experiments/charts/exp6_*
cat experiments/charts/exp6_prompt_evolution_run_overview.csv
cat experiments/charts/exp6_prompt_evolution_task_summary.csv
cat experiments/charts/exp6_swebench_trajectory_prompt_catalog.csv
cat experiments/charts/exp6_swebench_trajectory_task_prompt_counts.csv
```

`exp6_prompt_evolution_run_overview.csv` is the manager-facing table used for
the run-overview slides. It is the first report to inspect after Experiment 6.
`exp6_swebench_trajectory_prompt_catalog.csv` is the prompt catalog that
Experiment 9 uses when `RETENTION_REQUEST_SOURCE=swebench_trajectory`.
`exp6_swebench_trajectory_task_prompt_counts.csv` shows how many captured
model-facing prompts each SWE-bench task contributes by stage.

Global summaries:

```bash
cat experiments/reports/latest_runs_overview.md
cat experiments/reports/latest_runs_task_summary.md
cat experiments/reports/latest_runs_execution_prompts.md
cat experiments/reports/all_runs_overview.csv
cat experiments/reports/all_runs_task_summary.csv
cat experiments/reports/all_runs_execution_prompts.csv
```

## Slide Table Fragments

Generate simple paste-ready HTML snippets from the two CSV reports. The output
files are self-contained HTML snippets that you can open, copy, and paste into
`master-slide.html`.

```bash
python3 presentations/build_table_snippets.py \
  --task-summary-csv experiments/charts/exp6_prompt_evolution_task_summary.csv \
  --run-overview-csv experiments/charts/exp6_prompt_evolution_run_overview.csv \
  --output-dir /tmp/reference-output
```

This writes:

- `/tmp/reference-output/exp6_prompt_evolution_task_summary.snippet.html`
- `/tmp/reference-output/exp6_prompt_evolution_run_overview.snippet.html`

Each output file contains:

- one small `<style>` block
- one `<div>` wrapper
- one `<table>` rendered directly from the CSV contents

Workflow:

1. Run the script.
2. Open the `.snippet.html` file you want.
3. Copy its contents.
4. Paste the snippet into the desired slide in `master-slide.html`.

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

Default prompt-isolation policy:

- `RETENTION_PROMPT_ISOLATION_MODE=disjoint` for Experiments 9 and 11
- `SPEC_PREFILL_PROMPT_ISOLATION_MODE=disjoint` for Experiment 12

### What This Test Really Does

This experiment runs the same `A first -> distractors -> A replay` pattern for
two arms:

- control: no retention hint
- protected: retention hint enabled

The question is simple:

- under the same distractor pressure, does the protected arm keep request `A`
  warm longer than the control arm?

### What `sweep` Means Here

One sweep cell means:

- pick one distractor count
- run the control arm at that distractor count
- run the protected arm at that same distractor count
- compare the two rows

Across the sweep:

- the main knob that changes is `distractors`
- the workload shape stays the same unless you override it
- the important question is where control turns cold while protected still
  stays warm

### What Counts As Success

- the protected arm carries the hint you intended
- at the same distractor count, control goes cold but protected stays warm
- protected replay is faster than control replay

Columns to check first:

- hint identity: `hint_profile`
- pressure level: `distractors`
- survival: `warm`, `warm_source`
- replay benefit: `replay_ms`, `replay_cached`, `replay_reuse`
- summary verdict: `result`

If you want the signal-rich proof that the hint was really passed and seen, also
check:

- `req_prio_status`
- `worker_prio_status`

### Worked Success Example

Start here when the matrix feels confusing:

- [`contracts/examples/exp9_kv_retention_success.md`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/examples/exp9_kv_retention_success.md)

### Run

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
KV_RETENTION_MODE=probe \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

=== This works on EC2 ===
```bash
cd ~/kv_cache_offloading

SGLANG_TRANSFER_LOG=1 \
SGLANG_TRANSFER_LOG_PROFILE=full \
DYNAMO_MACHINE_PROFILE=ec2 \
PRECISE_START_MODE=clean \
KV_RETENTION_MODE=sweep \
RETENTION_ATTRIBUTION_MODE=precise \
KV_RETENTION_RESET_MODE=flush \
RETENTION_PROMPT_ISOLATION_MODE=disjoint \
RETENTION_SWEEP_SEED_MODE=per_cell \
STOP_ON_PROBE_FAILURE=1 \
DISTRACTOR_COUNTS="25 50 75 100 125 150" \
PROTECTED_INPUT_LEN=400 \
DISTRACTOR_INPUT_LEN=400 \
PROTECTED_HINT_PROFILES="high-priority" \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

=== This works on GH200 ===
```bash
cd ~/kv_cache_offloading

SGLANG_TRANSFER_LOG=1 \
SGLANG_TRANSFER_LOG_PROFILE=full \
DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
KV_RETENTION_MODE=sweep \
RETENTION_ATTRIBUTION_MODE=precise \
RETENTION_REQUEST_CONTEXT_MODE=auto \
RETENTION_TOP_LEVEL_PRIORITY_MODE=disable \
KV_RETENTION_RESET_MODE=flush \
RETENTION_SWEEP_SEED_MODE=per_cell \
RETENTION_PROMPT_ISOLATION_MODE=disjoint \
STOP_ON_PROBE_FAILURE=1 \
DISTRACTOR_COUNTS="100 110 120 130 140 150 160 170 180 190 200" \
PROTECTED_INPUT_LEN=2000 \
DISTRACTOR_INPUT_LEN=2000 \
PROTECTED_HINT_PROFILES="high-priority" \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

=== This works on GH200 with real SWE-bench Pro tasks ===

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
KV_RETENTION_MODE=sweep \
RETENTION_REQUEST_SOURCE=swebench_dataset \
RETENTION_SWEBENCH_DATASET=ScaleAI/SWE-bench_Pro \
RETENTION_SWEBENCH_SPLIT=test \
RETENTION_SWEBENCH_INDEX=0 \
KV_RETENTION_RESET_MODE=flush \
DISTRACTOR_COUNTS="200 400 730" \
PROTECTED_HINT_PROFILES="high-priority" \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

Mental model:

- one SWE-bench task becomes protected prompt A
- other SWE-bench tasks become distractors
- the same protected task is replayed as A again
- the report checks whether A stayed warm after the distractors

=== This uses multi-stage SWE-bench trajectory prompts ===

Use this after Experiment 6 has already produced
`experiments/reports/latest_swebench_trajectory_prompt_catalog.csv`.

Quickly check whether the current catalog has enough `planning` tasks for the
smoke test below:

```bash
cd ~/kv_cache_offloading

python3 - <<'PY'
import csv
from pathlib import Path

p = Path("experiments/reports/latest_swebench_trajectory_prompt_catalog.csv")
rows = list(csv.DictReader(p.open()))
planning_tasks = sorted({
    r.get("task_index")
    for r in rows
    if r.get("stage_name") == "planning" or r.get("phase") == "planning"
})
print("planning task count:", len(planning_tasks))
print("need at least:", 21, "for protected task + 20 distractor tasks")
print("first task indexes:", planning_tasks[:25])
PY
```

If the count is below 21, use smaller distractor counts or wait until the
catalog has more `planning` tasks.

To see how many prompts each task contributes by stage:

```bash
cat experiments/charts/exp6_swebench_trajectory_task_prompt_counts.csv
```

Step 2: run Experiment 9 against the prepared trajectory catalog.

For the quick smoke-test catalog above:

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
KV_RETENTION_MODE=sweep \
RETENTION_REQUEST_SOURCE=swebench_trajectory \
RETENTION_TRAJECTORY_PROMPT_CATALOG=experiments/reports/latest_swebench_trajectory_prompt_catalog.csv \
RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX=0 \
RETENTION_TRAJECTORY_PROTECTED_STAGE=planning \
RETENTION_TRAJECTORY_STAGES="planning" \
RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE=task_stage \
KV_RETENTION_RESET_MODE=restart \
DISTRACTOR_COUNTS="100 200 300 390" \
PROTECTED_HINT_PROFILES="high-priority" \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

For a larger planning-only run, change:

```text
DISTRACTOR_COUNTS="100 200 400 600"
```

For a fuller trajectory-pressure run, use more captured stages:

```text
RETENTION_TRAJECTORY_STAGES="planning execution patch_generation review"
```

In trajectory mode, `DISTRACTOR_COUNTS` means distractor tasks. If you include
four stages, each distractor task may send multiple prompt requests. This gives
Exp9 more realistic pressure from real agent planning, execution, patch, and
review prompts.

This mode replays prepared trajectory prompts only. It does not run
tools/tests/code edits again.

Compared with `RETENTION_REQUEST_SOURCE=swebench_dataset`, trajectory mode uses
the actual model-facing prompts captured during Experiment 6. If
`RETENTION_TRAJECTORY_STAGES="planning"`, each distractor task contributes only
its captured planning prompt. If you include more stages, each task can
contribute multiple prompt requests.

`RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE=task_stage` prepends a short
task/stage-specific prompt prefix before each trajectory prompt. This keeps
`A_first` and `A_replay` identical, but makes different distractor tasks diverge
early so trajectory prompts create cleaner KV-cache pressure.

To compare the exact prompts that dataset mode and trajectory mode would send:

```bash
cd ~/kv_cache_offloading

./agentbench/compare_exp9_prompt_sources.sh \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --dataset-protected-index 0 \
  --dataset-distractor-counts "200 400 730" \
  --trajectory-catalog experiments/reports/latest_swebench_trajectory_prompt_catalog.csv \
  --trajectory-protected-task-index 0 \
  --trajectory-protected-stage planning \
  --trajectory-stages "planning" \
  --trajectory-prompt-prefix-mode task_stage \
  --trajectory-distractor-counts "100 200 300 390"
```

This writes:

```bash
cat experiments/charts/exp9_prompt_source_summary.csv
cat experiments/charts/exp9_prompt_source_prompts.csv
cat experiments/charts/exp9_prompt_source_summary.md
```

Use the prefix columns to check whether trajectory prompts share the same early
wrapper:

```text
unique_prefix_256_count
unique_prefix_512_count
unique_prefix_1024_count
prompt_prefix_hash_256
prompt_prefix_hash_512
prompt_prefix_hash_1024
```

The full prompt text files are kept under
`experiments/reports/exp9_prompt_source_comparison/.../prompts/`.

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
RETENTION_REQUEST_SOURCE
RETENTION_SWEBENCH_DATASET
RETENTION_SWEBENCH_SPLIT
RETENTION_SWEBENCH_INDEX
RETENTION_SWEBENCH_INSTANCE_ID
RETENTION_SWEBENCH_DISTRACTOR_START_INDEX
RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE
RETENTION_TRAJECTORY_PROMPT_CATALOG
RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX
RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID
RETENTION_TRAJECTORY_PROTECTED_STAGE
RETENTION_TRAJECTORY_STAGES
RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE
RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX
RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE
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
cat experiments/reports/latest_kv_retention_microbenchmark_summary.md
cat experiments/reports/latest_kv_retention_microbenchmark_run_contract.json

ls experiments/charts/exp9_kvretention_*
```

Main outputs:

- `latest_kv_retention_microbenchmark_matrix.csv`: normalized probe + sweep table
- `latest_kv_retention_microbenchmark_summary.md`: readable summary
- `latest_kv_retention_microbenchmark_run_contract.json`: exact resolved settings
- `experiments/charts/exp9_kvretention_latency_vs_distractors.svg`
- `experiments/charts/exp9_kvretention_cache_vs_distractors.svg`

### Decision Proof

Exp9 now emits a generated decision-proof table after `sweep`, `all`, and
`plot` runs. The generated CSV/MD puts the quick-scan fields first, then keeps
the source-code evidence columns at the end.

Generated proof files:

- `experiments/reports/latest_exp9_decision_proof.csv`
- `experiments/reports/latest_exp9_decision_proof.md`
- `experiments/charts/exp9_decision_proof.csv`
- `experiments/charts/exp9_decision_proof.md`

Inspect the latest proof:

```bash
cat experiments/reports/latest_exp9_decision_proof.md
cat experiments/charts/exp9_decision_proof.md
```

Decision-proof columns:

- `step`: chronological proof step
- `checked_true`: whether the latest run produced the expected evidence
- `severity`: `critical`, `warning`, or `info`
- `component`: `harness`, `frontend`, `worker`, `sglang`, or `postprocess`
- `when`: when the logging/check happens
- `runtime_signal`: log/report signal expected from the run
- `evidence_value`: actual observed value from the latest run
- `meaning_short`: short plain-English verdict for the row
- `failure_meaning`: what to debug if the check is false
- `where`: exact source file and line
- `what_it_means`: full plain-English meaning
- `code_snippet`: source snippet being checked
- `evidence_source`: file/log/report used for the check
- `request_role`: `a_first`, `a_replay`, `protected`, or whole-run scope

The reference table below lists the code path and expected runtime signal.

| Step | When | Where | What It Means | Code Snippet | Runtime Signal |
|---:|---|---|---|---|---|
| 1 | Harness sends request | [`run_kv_retention_probe.py:1295`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/retention_probe/run_kv_retention_probe.py:1295) | AgentBench starts timing the HTTP request and sends the prompt plus `nvext` metadata. | `start = time.perf_counter()`<br>`status, response_json, error = post_json(...)` | `retention_probe_requests.csv` rows with request metadata |
| 2 | Frontend finishes preprocessing | [`sglang_processor.py:436`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py:436) | Dynamo frontend tokenized/preprocessed the request while preserving request context and hints. | `emit_runtime_event(...)`<br>`"frontend.request.preprocessed"` | `frontend.request.preprocessed` |
| 3 | Frontend dispatches request | [`sglang_processor.py:579`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py:579) | Dynamo frontend handed the preprocessed request to the router/worker path. | `emit_runtime_event(...)`<br>`"frontend.request.dispatched"` | `frontend.request.dispatched` |
| 4 | Worker receives request | [`decode_handler.py:482`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:482) | Dynamo worker received the request before generation starts. | `emit_runtime_event(...)`<br>`"worker.decode.request_received"` | `worker.decode.request_received` |
| 5 | Worker reads routed priority | [`decode_handler.py:493`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:493) | Worker extracts the routed top-level priority value when that path is enabled. | `priority = (request.get("routing") or {}).get("priority")` | request CSV priority / matrix `req_prio_status` |
| 6 | Worker forwards priority into SGLang | [`decode_handler.py:528`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:528) | Worker forwards the routed priority into the live SGLang generation call. | `decode = await self.engine.async_generate(...)`<br>`**self._priority_kwargs(priority)` | `worker_prio_status` / SGLang priority metadata |
| 7 | Worker attaches to SGLang request id | [`decode_handler.py:647`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:647) | SGLang produced a request id, allowing Dynamo request rows to join with SGLang runtime events. | `emit_runtime_event(...)`<br>`"worker.decode.request_attached"`<br>`sglang_request_id=sglang_request_id` | `worker.decode.request_attached` |
| 8 | SGLang priority/cache path executes | [`patch_sglang_transfer_logging.py:1542`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py:1542) | Instrumented SGLang emits priority/cache events when the patched runtime path executes. | `payload = {"event": "sglang.priority", ...}`<br>`print(line, file=sys.stderr, flush=True)` | `sglang.priority` or `sglang.cache` |
| 9 | Worker completes request | [`decode_handler.py:730`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:730) | Worker logs final usage, cached-token evidence, finish reason, and request context. | `emit_runtime_event(...)`<br>`"worker.decode.request_completed"`<br>`completion_usage=out["completion_usage"]` | `worker.decode.request_completed` |
| 10 | Frontend completes stream | [`sglang_processor.py:667`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py:667) | Frontend observed the final response chunk and logged completion. | `emit_runtime_event(...)`<br>`"frontend.request.completed"` | `frontend.request.completed` |
| 11 | Harness records CSV row | [`run_kv_retention_probe.py:1363`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/retention_probe/run_kv_retention_probe.py:1363) | AgentBench records latency, prompt hash, hint metadata, cached tokens, and status. | `return {`<br>`  "latency_ms": round_ms(latency_ms),`<br>`  "cached_prompt_tokens": cached_tokens,`<br>`}` | `retention_probe_requests.csv` status/latency/cached fields |
| 12 | Postprocess maps logs to report columns | [`run_kv_retention_probe.py:1772`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/retention_probe/run_kv_retention_probe.py:1772) | Postprocessing parses runtime logs and collapses them into public matrix fields. | `event = parse_sglang_event_line(line)`<br>`if event.get("event") == "sglang.priority":`<br>`  row["sglang_priority_events"] += 1` | `latest_kv_retention_microbenchmark_matrix.csv` |

Simple reading: the first rows prove the harness and frontend path, the middle
rows prove the worker-to-SGLang bridge, and the final rows prove the report
joined runtime evidence back into the public CSV.

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

Recommended flow:

- use the direct Experiment 10 wrapper
- start with `validate`
- only move to `sweep` after validation shows the pin path is really alive
- use `PRECISE_START_MODE=clean` so the run starts from a fresh isolated cache-pinning runtime
- for the sweep, keep the wrapper defaults unless you have a specific reason to override them

Direct wrapper default:

- `EXPERIMENT_RESET_MODE=restart`
- `RETENTION_PROMPT_ISOLATION_MODE=disjoint`

### What This Test Really Does

Experiment 10 has two stages:

- `validate`: prove the cache-pinning path is actually alive
- `sweep`: test whether `ephemeral:1h` survives deeper than plain `off`

So the first question is not "did latency improve?" The first question is:

- did the router spawn the pin path?
- did the worker apply it?

Only after that do we care about whether the protected arm stays warm longer.

### What `sweep` Means Here

One sweep cell means:

- pick one distractor count
- run the control arm with `cache_control=off`
- run the protected arm with `cache_control=ephemeral:1h`
- compare the two rows at that same distractor count

Across the sweep:

- the main knob that changes is `distractors`
- the TTL and cache-pinning setup stay fixed unless you override them
- the important question is where control turns cold while protected still
  stays warm

### What Counts As Success

Validation success:

- `router_pin=spawned`
- `worker_pin=applied`
- turn 2 reused cache

Sweep success:

- at the same distractor count, control turns cold first
- protected `ephemeral:1h` stays warm longer
- protected replay is faster than control replay

Columns to check first:

- setup proof: `cache_control`, `router_pin`, `worker_pin`, `result`
- retention effect: `warm`, `replay_ms`, `replay_cached`, `reuse_signal`

### Worked Success Example

Use this as the stable reference for both validation success and sweep success:

- [`contracts/examples/exp10_cache_pinning_success.md`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/examples/exp10_cache_pinning_success.md)

### Run

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=ec2 \
PRECISE_START_MODE=clean \
CACHE_PINNING_MODE=validate \
./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

=== This works on EC2 ===
```bash
cd ~/kv_cache_offloading

RUN_ID="cache_pinning_all_$(date +%Y%m%d_%H%M%S)"
LOG_DIR="experiments/reports/cache_pinning_microbenchmark_nohup/${RUN_ID}"
mkdir -p "${LOG_DIR}"

nohup env \
  DYNAMO_MACHINE_PROFILE=ec2 \
  PRECISE_START_MODE=clean \
  CACHE_PINNING_MODE=all \
  EXPERIMENT_RESET_MODE=restart \
  DISTRACTOR_COUNTS="60 120 200 240" \
  PROTECTED_INPUT_LEN=800 \
  DISTRACTOR_INPUT_LEN=200 \
  ./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
    Qwen/Qwen2.5-Coder-7B-Instruct \
  > "${LOG_DIR}/run.log" 2>&1 < /dev/null &

echo "RUN_ID=${RUN_ID}"
echo "LOG=${LOG_DIR}/run.log"
echo "PID=$!"
```

=== Cache pinning path works here GH200 (as seen from the csv report), but the sweep did not create enough pressure tp seperate control from protected ===
```bash
cd ~/kv_cache_offloading

RUN_ID="cache_pinning_all_$(date +%Y%m%d_%H%M%S)"
LOG_DIR="experiments/reports/cache_pinning_microbenchmark_nohup/${RUN_ID}"
mkdir -p "${LOG_DIR}"

nohup env \
  DYNAMO_MACHINE_PROFILE=gh200 \
  PRECISE_START_MODE=clean \
  CACHE_PINNING_MODE=all \
  EXPERIMENT_RESET_MODE=restart \
  DISTRACTOR_COUNTS="600 800 1000" \
  PROTECTED_INPUT_LEN=800 \
  DISTRACTOR_INPUT_LEN=200 \
  ./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
    Qwen/Qwen2.5-Coder-7B-Instruct \
  > "${LOG_DIR}/run.log" 2>&1 < /dev/null &

echo "RUN_ID=${RUN_ID}"
echo "LOG=${LOG_DIR}/run.log"
echo "PID=$!"
```

=== This works on GH200? ===
```bash
cd ~/kv_cache_offloading

RUN_ID="cache_pinning_all_$(date +%Y%m%d_%H%M%S)"
LOG_DIR="experiments/reports/cache_pinning_microbenchmark_nohup/${RUN_ID}"
mkdir -p "${LOG_DIR}"

nohup env \
  DYNAMO_MACHINE_PROFILE=gh200 \
  PRECISE_START_MODE=clean \
  CACHE_PINNING_MODE=sweep \
  EXPERIMENT_RESET_MODE=restart \
  DISTRACTOR_COUNTS="400 600 1200 1600" \
  PROTECTED_INPUT_LEN=4000 \
  DISTRACTOR_INPUT_LEN=400 \
  ./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
  > "${LOG_DIR}/run.log" 2>&1 < /dev/null &

echo "RUN_ID=${RUN_ID}"
echo "LOG=${LOG_DIR}/run.log"
echo "PID=$!"
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
cat experiments/reports/latest_exp10_decision_proof.md

ls experiments/reports/latest_cache_pinning_microbenchmark_*.svg
cat experiments/reports/latest_cache_pinning_microbenchmark_chart_manifest.json
ls experiments/charts/exp10_decision_proof.*
```

Main outputs:

- `latest_cache_pinning_microbenchmark_matrix.csv`: validation + sweep table
- `latest_cache_pinning_microbenchmark_summary.csv`: one-row summary
- `latest_cache_pinning_microbenchmark_run_contract.json`: exact resolved settings
- `latest_exp10_decision_proof.md`: generated code-path and runtime-evidence proof
- `experiments/charts/exp10_decision_proof.md`: same proof in the shared chart folder
- `validation_latency.svg` / `validation_cached_tokens.svg`
- `sweep_replay_latency.svg` / `sweep_replay_cached_tokens.svg`

### Decision Proof

Exp10 now emits a generated decision-proof table after `validate`, `sweep`,
`all`, and `plot` runs. The table is both documentation and run evidence: it
names the code location, shows the relevant snippet, names the runtime/report
signal, and then sets `checked_true` from the latest run artifacts.

Generated proof files:

- `experiments/reports/latest_exp10_decision_proof.csv`
- `experiments/reports/latest_exp10_decision_proof.md`
- `experiments/charts/exp10_decision_proof.csv`
- `experiments/charts/exp10_decision_proof.md`

Inspect the latest proof:

```bash
cat experiments/reports/latest_exp10_decision_proof.md
cat experiments/charts/exp10_decision_proof.md
```

Decision-proof columns:

- `step`: chronological proof step
- `when`: when the logging/check happens
- `where`: exact source file and line
- `what_it_means`: plain-English meaning
- `code_snippet`: source snippet being checked
- `runtime_signal`: log/report signal expected from the run
- `evidence_source`: file/log/report used for the check
- `evidence_value`: actual observed value from the latest run
- `experiment_part`: validate, sweep, report, or whole-run scope
- `cache_control_path`: contract, request, router, worker, or report layer
- `evidence_metric`: the proof metric being checked
- `checked_true`: whether the latest run produced the expected evidence
- `failure_meaning`: what to debug if the check is false

| Step | When | Where | What It Means | Code Snippet | Runtime Signal |
|---:|---|---|---|---|---|
| 1 | Contract pins isolated upstream stack | [`cache_pinning_microbenchmark.contract.sh:19`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/cache_pinning_microbenchmark.contract.sh:19) | Exp10 uses isolated Dynamo and SGLang cache-pinning PR refs instead of the generic precise stack. | `CACHE_PINNING_DYNAMO_SOURCE_REF`<br>`CACHE_PINNING_SGLANG_SOURCE_REF` | `run_contract.json` source refs |
| 2 | Contract enables cache-control frontend path | [`cache_pinning_microbenchmark.contract.sh:35`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/cache_pinning_microbenchmark.contract.sh:35) | The frontend is expected to expose the cache-control flag and use KV-router mode. | `CACHE_PINNING_FRONTEND_FLAG_VALUE:=--enable-cache-control`<br>`CACHE_PINNING_ROUTER_MODE:=kv` | frontend flag / router mode |
| 3 | Contract enables HiCache pin budget | [`cache_pinning_microbenchmark.contract.sh:44`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/cache_pinning_microbenchmark.contract.sh:44) | Cache pinning needs hierarchical cache plus a nonzero pinned ratio. | `CACHE_PINNING_PINNED_RATIO:=0.1`<br>`SGLANG_HICACHE_MAX_PINNED_RATIO` | pinned ratio / HiCache write policy |
| 4 | Wrapper launches doc validation | [`run_cache_pinning_microbenchmark_single_host.sh:280`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_cache_pinning_microbenchmark_single_host.sh:280) | The public wrapper runs the doc-style validation path with the contract TTL and pinning knobs. | `CACHE_PINNING_DOC_ID`<br>`CACHE_PINNING_TTL`<br>`CACHE_PINNING_PINNED_RATIO` | validation run id |
| 5 | Validation request sends cache-control | [`run_cache_pinning_doc_validation.py:317`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py:317) | Both validation turns send `nvext.cache_control` with the requested type and TTL. | `"nvext": {"cache_control": {"type": args.cache_control_type, "ttl": args.ttl}}` | matrix `cache_control=ephemeral:<ttl>` |
| 6 | Router logs cache-control receipt | [`repair_cache_pinning_dynamo_source.py:98`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/repair_cache_pinning_dynamo_source.py:98) | The Dynamo router logs when it sees cache-control TTL on the routed request. | `"event_type": "router.cache_control_seen"` | `router.cache_control_seen` |
| 7 | Router creates pin state | [`repair_cache_pinning_dynamo_source.py:128`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/repair_cache_pinning_dynamo_source.py:128) | The router builds pin state with TTL, token ids, and worker id. | `"event_type": "router.pin_state_created"` | `router.pin_state_created` / `router_pin` |
| 8 | Router spawns pin-prefix request | [`repair_cache_pinning_dynamo_source.py:175`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/repair_cache_pinning_dynamo_source.py:175) | After generation, the router sends the prefix-pin RPC to the worker. | `"event_type": "router.pin_prefix_spawned"` | `router.pin_prefix_spawned` / `router_pin=spawned` |
| 9 | Worker exposes cache-control endpoint | [`repair_cache_pinning_dynamo_source.py:54`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/repair_cache_pinning_dynamo_source.py:54) | The Dynamo worker serves the cache-control endpoint used by the router pin RPC. | `cache_control_endpoint.serve_endpoint(` | source readiness / live validation |
| 10 | SGLang worker logs pin-prefix applied | [`repair_cache_pinning_sglang_source.py:51`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/repair_cache_pinning_sglang_source.py:51) | The SGLang radix cache applies TTL pinning to the protected prefix. | `"worker.pin_prefix_applied"` | `worker.pin_prefix_applied` / `worker_pin=applied` |
| 11 | SGLang can refresh pinned-prefix TTL | [`repair_cache_pinning_sglang_source.py:90`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/repair_cache_pinning_sglang_source.py:90) | On a cache hit, pinned nodes can refresh their TTL. | `"worker.pin_refreshed_cache_hit"` | `worker.pin_refreshed_cache_hit` / `worker_refreshes` |
| 12 | Validation parser summarizes router pin | [`run_cache_pinning_doc_validation.py:163`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py:163) | The validation report converts router cache-pinning events into `router_pin` status. | `def summarize_router_pin(frontend_log: Path)` | `router_pin=spawned` |
| 13 | Validation parser summarizes worker pin | [`run_cache_pinning_doc_validation.py:199`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py:199) | The validation report converts worker pin events into `worker_pin` status. | `def summarize_worker_pin(worker_log: Path)` | `worker_pin=applied` |
| 14 | Validation confirms cache reuse | [`run_cache_pinning_doc_validation.py:235`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py:235) | The second validation turn should report cached prompt tokens. | `turn2_cached = row2.get("cached_tokens", "")` | `turn2_cached > 0` / `cache_hit=hit` |
| 15 | Validation final verdict is strong | [`run_cache_pinning_doc_validation.py:250`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/cache_pinning/run_cache_pinning_doc_validation.py:250) | The validation result is strongest when router pin, worker pin, and cache reuse all happen. | `pin_path_applied_and_cache_reused` | `result=pin_path_applied_and_cache_reused` |
| 16 | Wrapper launches retention sweep | [`run_cache_pinning_microbenchmark_single_host.sh:304`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_cache_pinning_microbenchmark_single_host.sh:304) | The public wrapper runs the pressure sweep after validation in `all` mode or directly in `sweep` mode. | `RETENTION_SWEEP_ID`<br>`PROTECTED_CACHE_CONTROL_PROFILES` | sweep run id / sweep rows |
| 17 | Sweep compares control and protected arms | [`compact_cache_pinning_retention_reports.py:96`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/cache_pinning/compact_cache_pinning_retention_reports.py:96) | The sweep has a control arm with cache-control off and a protected arm with `ephemeral:1h`. | `"arm": pick(row, "arm")`<br>`"cache_control": pick(row, "cache_control", "protected_cache", ...)` | matrix arm/cache-control rows |
| 18 | Sweep report records request cache-control | [`compact_cache_pinning_retention_reports.py:110`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/cache_pinning/compact_cache_pinning_retention_reports.py:110) | The component report records whether request metadata showed cache-control on the protected arm. | `"req_cache_status": pick(row, "req_cache_status", ...)` | `req_cache_status` / protected `cache_control` |
| 19 | Microbenchmark report normalizes sweep rows | [`build_cache_pinning_microbenchmark_report.py:269`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/cache_pinning/build_cache_pinning_microbenchmark_report.py:269) | The main matrix preserves replay latency, cached tokens, warm status, and reuse signal for each arm. | `def matrix_rows_from_sweep(` | `microbenchmark_matrix.csv` sweep rows |
| 20 | Sweep summary compares retention threshold | [`build_cache_pinning_microbenchmark_report.py:381`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/cache_pinning/build_cache_pinning_microbenchmark_report.py:381) | The summary compares the deepest warm distractor count for control and protected arms. | `"control_last_warm"`<br>`"protected_last_warm"` | `protected_last_warm > control_last_warm` |

Simple reading: validation proves the cache-control pin path exists
end-to-end, and the sweep proves whether protected `ephemeral:1h` requests stay
warm deeper than control requests.

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

This can use either synthetic prompts or direct SWE-bench Pro task prompts.
The direct SWE-bench mode is task-level only; it does not execute full
multi-step agents.

### What This Test Really Does

This experiment sends a mixed burst of low-priority and high-priority requests
into the same runtime.

The question is:

- when the queue is busy, do the high-priority requests get attached and
  completed sooner?

### What `sweep` Means Here

One sweep cell means:

- run one mixed burst of low-priority and high-priority requests
- keep the burst shape the same inside that run
- summarize how the two priority classes behaved

Across the sweep:

- one public scheduling knob changes between runs
- most commonly that knob is `PRIORITY_ARRIVAL_GAP_MS`
- the important question is whether later high-priority requests attach ahead
  of earlier low-priority requests

### What Counts As Success

- the worker really saw the priority hint
- high-priority requests attach ahead of earlier low-priority requests
- the jump-ahead rate is above zero for at least one sweep point

Columns to check first:

- hint proof: `hint_seen`
- path proof: `hint_path_status`
- ordering proof: `high_jump_ahead_count`, `high_jump_ahead_rate`
- summary verdict: `result`

### Worked Success Example

Use this when you want a one-row example of a clear scheduling win:

- [`contracts/examples/exp11_priority_scheduling_success.md`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/examples/exp11_priority_scheduling_success.md)

### Run

=== This works on GH200 ===
```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
PRIORITY_SCHEDULING_MODE=all \
EXPERIMENT_RESET_MODE=flush \
PRIORITY_SCHEDULING_SWEEP_AXIS=PRIORITY_ARRIVAL_GAP_MS \
PRIORITY_SCHEDULING_SWEEP_VALUES="50 100 200 400" \
LOW_PRIORITY_COUNT=8 \
HIGH_PRIORITY_COUNT=4 \
PRIORITY_INPUT_LEN=4000 \
PRIORITY_OUTPUT_LEN=128 \
PRIORITY_INTER_REQUEST_GAP_MS=20 \
./agentbench/run_priority_scheduling_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

=== This works on GH200 with real SWE-bench Pro tasks ===
```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
PRIORITY_SCHEDULING_MODE=all \
PRIORITY_REQUEST_SOURCE=swebench_dataset \
PRIORITY_SWEBENCH_DATASET=ScaleAI/SWE-bench_Pro \
PRIORITY_SWEBENCH_SPLIT=test \
PRIORITY_SWEBENCH_START_INDEX=0 \
EXPERIMENT_RESET_MODE=flush \
PRIORITY_SCHEDULING_SWEEP_AXIS=PRIORITY_ARRIVAL_GAP_MS \
PRIORITY_SCHEDULING_SWEEP_VALUES="50 100 200 400" \
LOW_PRIORITY_COUNT=8 \
HIGH_PRIORITY_COUNT=4 \
PRIORITY_OUTPUT_LEN=128 \
PRIORITY_INTER_REQUEST_GAP_MS=20 \
./agentbench/run_priority_scheduling_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

In this mode:

- each low/high request is one SWE-bench Pro task prompt
- `PRIORITY_SWEBENCH_START_INDEX=0` starts the burst at dataset row 0
- `LOW_PRIORITY_COUNT + HIGH_PRIORITY_COUNT` controls how many task prompts are used
- `PRIORITY_INPUT_LEN` is ignored because real task prompts come from the dataset

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
PRIORITY_REQUEST_SOURCE
PRIORITY_SWEBENCH_DATASET
PRIORITY_SWEBENCH_SPLIT
PRIORITY_SWEBENCH_START_INDEX
PRIORITY_SWEBENCH_ALLOW_REUSE
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
cat experiments/reports/latest_priority_scheduling_microbenchmark_summary.md
cat experiments/reports/latest_priority_scheduling_microbenchmark_run_contract.json

ls experiments/charts/exp11_prioritysched_*
```

Main outputs:

- `latest_priority_scheduling_microbenchmark_matrix.csv`: one compact row per sweep point
- `latest_priority_scheduling_microbenchmark_summary.md`: readable summary
- `latest_priority_scheduling_microbenchmark_run_contract.json`: exact resolved settings
- `latest_priority_scheduling_microbenchmark_jump_ahead.svg`: line chart of jump-ahead rate versus arrival gap
- `experiments/charts/exp11_prioritysched_jump_ahead_vs_arrival_gap.svg`: same chart in the shared chart folder

Main matrix columns:

- `gap_ms`: how late the high-priority burst arrived after the low-priority burst
- `low_requests`: number of low-priority requests in the burst
- `high_requests`: number of high-priority requests in the burst
- `max_jump_ahead`: maximum possible high-over-low reorder events
- `high_jump_ahead_count`: how many times high-priority requests attached before earlier low-priority requests
- `high_jump_ahead_rate`: `high_jump_ahead_count / max_jump_ahead`
- `hint_kind`: which hint field was sent
- `hint_seen`: whether the worker saw the hint
- `hint_path_status`: worker/SGLang hint-path evidence
- `result`: simple verdict, such as `priority_reordered` or `no_visible_reorder`

### Debug

```bash
docker logs -f dynamo-sglang-worker
```

### Decision Proof

Exp11 now emits a generated decision-proof table after `sweep`, `all`, and
`plot` runs. The table is both documentation and run evidence: it names the code
location, shows the relevant snippet, names the runtime/report signal, and then
sets `checked_true` from the latest run artifacts.

Generated proof files:

- `experiments/reports/latest_exp11_decision_proof.csv`
- `experiments/reports/latest_exp11_decision_proof.md`
- `experiments/charts/exp11_decision_proof.csv`
- `experiments/charts/exp11_decision_proof.md`

Inspect the latest proof:

```bash
cat experiments/reports/latest_exp11_decision_proof.md
cat experiments/charts/exp11_decision_proof.md
```

Decision-proof columns:

- `step`: chronological proof step
- `when`: when the logging/check happens
- `where`: exact source file and line
- `what_it_means`: plain-English meaning
- `code_snippet`: source snippet being checked
- `runtime_signal`: log/report signal expected from the run
- `evidence_source`: file/log/report used for the check
- `evidence_value`: actual observed value from the latest run
- `request_role`: low request, high request, or whole-run scope
- `priority_class`: which priority class the check applies to
- `order_metric`: arrival, attach, completion, or jump-ahead metric
- `checked_true`: whether the latest run produced the expected evidence
- `failure_meaning`: what to debug if the check is false

| Step | When | Where | What It Means | Code Snippet | Runtime Signal |
|---:|---|---|---|---|---|
| 1 | Harness builds low/high request specs | [`run_priority_scheduling_probe.py:797`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:797) | AgentBench creates a mixed burst with low-priority requests and high-priority requests. | `priority_class="low-priority"`<br>`priority_class="high-priority"` | request/proof CSV rows with both priority classes |
| 2 | Harness attaches priority hint | [`run_priority_scheduling_probe.py:496`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:496) | Each request gets an `nvext.agent_hints.priority` value. | `payload["priority"] = priority_value` | `worker_hint_prio` / `hint_seen` |
| 3 | Harness optionally sends top-level priority | [`run_priority_scheduling_probe.py:913`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:913) | When supported, the script also sends a top-level OpenAI-compatible `priority` field. | `payload["priority"] = priority` | `sent_top_prio` / top-level priority status |
| 4 | Frontend preprocesses request | [`sglang_processor.py:436`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py:436) | Dynamo frontend tokenizes/preprocesses the hinted request. | `emit_runtime_event(...)`<br>`"frontend.request.preprocessed"` | `frontend.request.preprocessed` |
| 5 | Frontend dispatches request | [`sglang_processor.py:579`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py:579) | Dynamo frontend hands the request to the router/worker path. | `emit_runtime_event(...)`<br>`"frontend.request.dispatched"` | `frontend.request.dispatched` |
| 6 | Worker receives request | [`decode_handler.py:482`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:482) | Dynamo worker receives the request before generation starts. | `emit_runtime_event(...)`<br>`"worker.decode.request_received"` | `worker.decode.request_received` |
| 7 | Worker reads routed priority | [`decode_handler.py:493`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:493) | Worker extracts routed priority from request routing metadata. | `priority = (request.get("routing") or {}).get("priority")` | worker priority fields / hint-path status |
| 8 | Worker forwards priority into SGLang | [`decode_handler.py:542`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:542) | Worker forwards priority into the live SGLang generation call. | `**self._priority_kwargs(priority)` | worker/SGLang priority metadata |
| 9 | Worker attaches request to SGLang id | [`decode_handler.py:647`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:647) | SGLang produced a request id, so worker runtime timestamps can be joined to the script request rows. | `emit_runtime_event(...)`<br>`"worker.decode.request_attached"`<br>`sglang_request_id=sglang_request_id` | `worker_request_attached_timestamp` / `attached_rank` |
| 10 | Worker completes request | [`decode_handler.py:730`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:730) | Worker logs completion, giving completion timestamps and request usage. | `emit_runtime_event(...)`<br>`"worker.decode.request_completed"` | `worker_request_completed_timestamp` / `completed_rank` |
| 11 | Report assigns attach order | [`run_priority_scheduling_probe.py:1410`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1410) | Postprocess sorts worker attach timestamps and assigns `attached_rank`. | `attached_rows.sort(...)`<br>`row["attached_rank"] = index` | `attached_rank` |
| 12 | Report computes high-priority jump-ahead count | [`run_priority_scheduling_probe.py:1445`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1445) | For each high-priority request, postprocess counts earlier low-priority requests it attached before. | `if low_attached is not None and low_attached > high_attached:`<br>`attached_leapfrogs += 1` | `beat_low_attach` / `high_jump_ahead_count` |
| 13 | Microbenchmark report computes jump-ahead rate | [`build_priority_scheduling_microbenchmark_report.py:243`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py:243) | The compact matrix converts raw leapfrogs into `high_jump_ahead_count` and `high_jump_ahead_rate`. | `max_jump_ahead = low_requests * high_requests`<br>`high_jump_ahead_rate = percent_text(...)` | `high_jump_ahead_count` / `high_jump_ahead_rate` |
| 14 | Matrix reports hint path | [`build_priority_scheduling_microbenchmark_report.py:262`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py:262) | The public matrix reports whether the worker saw priority hints. | `"hint_seen": priority_hint_seen_status(...)` | `hint_seen=yes` / `worker_hint_status=full` |
| 15 | Matrix reports final verdict | [`build_priority_scheduling_microbenchmark_report.py:247`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py:247) | The public matrix marks the run reordered when at least one high-priority request jumped ahead. | `result = f"{prefix}_reordered" if jump_count > 0 else "no_visible_reorder"` | `result=priority_reordered` |

Simple reading: the first rows prove the harness created low/high requests and
sent hints, the middle rows prove the worker saw and ordered the requests, and
the final rows prove the public matrix computed the jump-ahead result.

### Lower-Level Wrapper

Normally use the single public wrapper above.

- [`agentbench/run_priority_scheduling_probe_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_priority_scheduling_probe_single_host.sh)
  - probe component

The public microbenchmark matrix now uses compact fields such as:

- `gap_ms`
- `low_requests`
- `high_requests`
- `max_jump_ahead`
- `high_jump_ahead_count`
- `high_jump_ahead_rate`
- `high_completed_ahead_count`
- `hint_kind`
- `hint_seen`
- `hint_path_status`
- `result`

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

## Experiment 13: Latency Sensitivity Probe

This is the public latency-sensitivity microbenchmark entrypoint.

It reuses the Experiment 11 queue-burst harness, but sends
`nvext.agent_hints.latency_sensitivity` instead of `nvext.agent_hints.priority`.

Contract files:

- [`contracts/latency_sensitivity_microbenchmark.contract.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/latency_sensitivity_microbenchmark.contract.sh)
- [`contracts/latency_sensitivity_microbenchmark.contract.md`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/latency_sensitivity_microbenchmark.contract.md)

Public wrapper:

- [`agentbench/run_latency_sensitivity_microbenchmark_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_latency_sensitivity_microbenchmark_single_host.sh)

### What This Test Really Does

This experiment sends a mixed burst of low-latency-sensitivity and
high-latency-sensitivity requests into the same runtime.

The question is:

- does `latency_sensitivity` get received by the worker?
- do high-sensitivity requests attach ahead of earlier low-sensitivity requests?

### What `sweep` Means Here

One sweep cell means:

- run one mixed burst
- send low requests with `latency_sensitivity=0.2`
- send high requests with `latency_sensitivity=1.0`
- measure whether high-sensitivity requests jump ahead

Across the sweep:

- one scheduling knob changes between runs
- the default sweep knob is `PRIORITY_ARRIVAL_GAP_MS`

### Run

=== This works on GH200? ===
```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
LATENCY_SENSITIVITY_MODE=all \
EXPERIMENT_RESET_MODE=flush \
PRIORITY_SCHEDULING_SWEEP_AXIS=PRIORITY_ARRIVAL_GAP_MS \
PRIORITY_SCHEDULING_SWEEP_VALUES="50 100 200 400" \
LOW_PRIORITY_COUNT=8 \
HIGH_PRIORITY_COUNT=4 \
PRIORITY_INPUT_LEN=4000 \
PRIORITY_OUTPUT_LEN=128 \
PRIORITY_INTER_REQUEST_GAP_MS=20 \
./agentbench/run_latency_sensitivity_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

=== This works on GH200 with real SWE-bench Pro tasks ===
```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
LATENCY_SENSITIVITY_MODE=all \
PRIORITY_REQUEST_SOURCE=swebench_dataset \
PRIORITY_SWEBENCH_DATASET=ScaleAI/SWE-bench_Pro \
PRIORITY_SWEBENCH_SPLIT=test \
PRIORITY_SWEBENCH_START_INDEX=0 \
EXPERIMENT_RESET_MODE=flush \
PRIORITY_SCHEDULING_SWEEP_AXIS=PRIORITY_ARRIVAL_GAP_MS \
PRIORITY_SCHEDULING_SWEEP_VALUES="50 100 200 400" \
LOW_PRIORITY_COUNT=8 \
HIGH_PRIORITY_COUNT=4 \
PRIORITY_OUTPUT_LEN=128 \
PRIORITY_INTER_REQUEST_GAP_MS=20 \
./agentbench/run_latency_sensitivity_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

### Top-Level Outputs

```bash
cat experiments/reports/latest_latency_sensitivity_microbenchmark_matrix.csv
cat experiments/reports/latest_latency_sensitivity_microbenchmark_summary.md
cat experiments/reports/latest_latency_sensitivity_microbenchmark_run_contract.json
cat experiments/reports/latest_exp13_decision_proof.md

ls experiments/charts/exp13_latencysens_*
ls experiments/charts/exp13_decision_proof.*
```

Main outputs:

- `latest_latency_sensitivity_microbenchmark_matrix.csv`: one compact row per sweep point
- `latest_latency_sensitivity_microbenchmark_summary.md`: readable summary
- `latest_latency_sensitivity_microbenchmark_run_contract.json`: exact resolved settings
- `latest_latency_sensitivity_microbenchmark_jump_ahead.svg`: line chart of jump-ahead rate versus arrival gap
- `experiments/charts/exp13_latencysens_jump_ahead_vs_arrival_gap.svg`: same chart in the shared chart folder
- `latest_exp13_decision_proof.md`: generated code-path and runtime-evidence proof
- `experiments/charts/exp13_decision_proof.md`: same proof in the shared chart folder

Main matrix columns:

- `hint_kind`: should be `latency_sensitivity`
- `hint_seen`: whether the worker saw the latency-sensitivity hint
- `hint_path_status`: worker/SGLang hint-path evidence
- `high_jump_ahead_count`: how many times high-sensitivity requests attached before earlier low-sensitivity requests
- `high_jump_ahead_rate`: `high_jump_ahead_count / max_jump_ahead`
- `result`: simple verdict, such as `latency_sensitivity_reordered` or `no_visible_reorder`

Strongest proof in this setup:

- `hint_kind=latency_sensitivity`
- `hint_seen=yes`
- `high_jump_ahead_count > 0`
- `high_jump_ahead_rate > 0%`
- `result=latency_sensitivity_reordered`

### Decision Proof

Exp13 now emits a generated decision-proof table after `sweep`, `all`, and
`plot` runs. The table is both documentation and run evidence: it names the code
location, shows the relevant snippet, names the runtime/report signal, and then
sets `checked_true` from the latest run artifacts.

Generated proof files:

- `experiments/reports/latest_exp13_decision_proof.csv`
- `experiments/reports/latest_exp13_decision_proof.md`
- `experiments/charts/exp13_decision_proof.csv`
- `experiments/charts/exp13_decision_proof.md`

Inspect the latest proof:

```bash
cat experiments/reports/latest_exp13_decision_proof.md
cat experiments/charts/exp13_decision_proof.md
```

Decision-proof columns:

- `step`: chronological proof step
- `when`: when the logging/check happens
- `where`: exact source file and line
- `what_it_means`: plain-English meaning
- `code_snippet`: source snippet being checked
- `runtime_signal`: log/report signal expected from the run
- `evidence_source`: file/log/report used for the check
- `evidence_value`: actual observed value from the latest run
- `request_role`: low request, high request, or whole-run scope
- `sensitivity_class`: low-sensitivity, high-sensitivity, or whole-run scope
- `order_metric`: arrival, attach, completion, or jump-ahead metric
- `checked_true`: whether the latest run produced the expected evidence
- `failure_meaning`: what to debug if the check is false

| Step | When | Where | What It Means | Code Snippet | Runtime Signal |
|---:|---|---|---|---|---|
| 1 | Contract selects latency-sensitivity mode | [`latency_sensitivity_microbenchmark.contract.sh:18`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/latency_sensitivity_microbenchmark.contract.sh:18) | The public Exp13 wrapper forces the shared harness to send `latency_sensitivity` hints. | `: "${PRIORITY_HINT_KIND:=latency_sensitivity}"` | `run_contract.json` `PRIORITY_HINT_KIND` / matrix `hint_kind` |
| 2 | Harness builds low/high request specs | [`run_priority_scheduling_probe.py:724`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:724) | The shared harness creates a mixed burst of low-sensitivity and high-sensitivity requests. | `priority_class="low-priority"`<br>`priority_class="high-priority"` | request/proof CSV rows with both classes |
| 3 | Harness attaches latency-sensitivity hint | [`run_priority_scheduling_probe.py:489`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:489) | Each request gets `nvext.agent_hints.latency_sensitivity`; high requests get the high value and low requests get the low value. | `if args.hint_kind == "latency_sensitivity":`<br>`payload["latency_sensitivity"] = ...` | `agent_hints_latency_sensitivity` / `worker_latency_sensitivity` |
| 4 | Contract disables top-level priority | [`latency_sensitivity_microbenchmark.contract.sh:21`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/latency_sensitivity_microbenchmark.contract.sh:21) | Exp13 isolates the latency-sensitivity hint by not sending OpenAI top-level `priority`. | `: "${PRIORITY_TOP_LEVEL_PRIORITY_MODE:=disable}"` | `sent_top_prio=false` / `top_prio_compat=not_attempted` |
| 5 | Frontend preprocesses request | [`sglang_processor.py:436`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py:436) | Dynamo frontend tokenizes/preprocesses the hinted request and logs the `agent_hints` payload. | `emit_runtime_event(...)`<br>`"frontend.request.preprocessed"` | `frontend.request.preprocessed` |
| 6 | Frontend dispatches request | [`sglang_processor.py:579`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/frontend/sglang_processor.py:579) | Dynamo frontend hands the preprocessed request to the router/worker path. | `emit_runtime_event(...)`<br>`"frontend.request.dispatched"` | `frontend.request.dispatched` |
| 7 | Worker receives request | [`decode_handler.py:482`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:482) | Dynamo worker receives the request before generation starts. | `emit_runtime_event(...)`<br>`"worker.decode.request_received"` | `worker.decode.request_received` |
| 8 | Worker runtime payload includes agent hints | [`decode_handler.py:56`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:56) | The worker-side runtime event includes sanitized `agent_hints`, including `latency_sensitivity` when present. | `**agent_hint_log_fields(request)` | worker runtime JSON `agent_hints.latency_sensitivity` |
| 9 | Runtime helper extracts agent hints | [`runtime_logging.py:145`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/components/src/dynamo/common/runtime_logging.py:145) | The shared runtime logger extracts and emits the hint keys and values. | `def agent_hint_log_fields(request: dict[str, Any])` | `agent_hints_keys` includes `latency_sensitivity` |
| 10 | Report parses worker-side latency hint | [`run_priority_scheduling_probe.py:1273`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1273) | Postprocess reads `agent_hints.latency_sensitivity` from worker runtime JSON. | `hint_latency_sensitivity = maybe_float(hints.get("latency_sensitivity"))` | `worker_agent_hints_latency_sensitivity` |
| 11 | Report copies latency hint onto rows | [`run_priority_scheduling_probe.py:1402`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1402) | The request rows receive `worker_agent_hints_latency_sensitivity`, which becomes the readable proof column. | `row["worker_agent_hints_latency_sensitivity"] = ...` | `worker_latency_sensitivity` |
| 12 | Report assigns attach order | [`run_priority_scheduling_probe.py:1410`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1410) | Postprocess sorts worker attach timestamps and assigns `attached_rank`. | `attached_rows.sort(...)`<br>`row["attached_rank"] = index` | `attached_rank` |
| 13 | Report computes high-sensitivity jump-ahead count | [`run_priority_scheduling_probe.py:1445`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1445) | For each high-sensitivity request, postprocess counts earlier low-sensitivity requests it attached before. | `if low_attached is not None and low_attached > high_attached:`<br>`attached_leapfrogs += 1` | `beat_low_attach` / `high_jump_ahead_count` |
| 14 | Summary marks worker hint status | [`run_priority_scheduling_probe.py:1596`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py:1596) | For latency-sensitivity runs, the summary checks the high rows for the expected float hint value. | `request_float_status(...)`<br>`field="worker_agent_hints_latency_sensitivity"` | `worker_hint_status=full` / `hint_seen=yes` |
| 15 | Microbenchmark report preserves hint kind | [`build_priority_scheduling_microbenchmark_report.py:240`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py:240) | The compact matrix records that this was a `latency_sensitivity` run. | `hint_kind = str(summary.get("hint_kind") or "priority")` | `hint_kind=latency_sensitivity` |
| 16 | Microbenchmark report computes jump-ahead rate | [`build_priority_scheduling_microbenchmark_report.py:259`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py:259) | The compact matrix converts raw leapfrogs into `high_jump_ahead_count` and `high_jump_ahead_rate`. | `"high_jump_ahead_count": jump_count`<br>`"high_jump_ahead_rate": percent_text(...)` | `high_jump_ahead_count` / `high_jump_ahead_rate` |
| 17 | Matrix reports final verdict | [`build_priority_scheduling_microbenchmark_report.py:247`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py:247) | The public matrix marks the run reordered when at least one high-sensitivity request jumped ahead. | `result = f"{prefix}_reordered" if jump_count > 0 else "no_visible_reorder"` | `result=latency_sensitivity_reordered` |

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

This can use either synthetic two-turn prompts or direct SWE-bench Pro task
prompts. The direct SWE-bench mode is task-level only; it does not execute full
multi-step agents.

### What This Test Really Does

This experiment compares two two-turn conversations:

- control: normal turn A, then normal turn B
- protected: turn A asks Dynamo to warm up turn B speculatively in the
  background

The real question is:

- did speculative prefill make turn B faster than the control arm?

It is **not** asking whether control turn B should be a total cache miss.
Control turn B can still reuse normal conversation state.

### What `sweep` Means Here

One sweep cell means:

- run one control two-turn conversation
- run one protected two-turn conversation
- compare control turn B against protected turn B

Across the sweep:

- one public knob changes between runs
- most commonly that knob is `SPEC_PREFILL_WARMUP_WAIT_MS`
- the turn structure stays the same unless you override it
- the important question is whether protected turn B gets faster once the
  speculative warmup has more time to help

### What Counts As Success

- the speculative-prefill hint is on for the protected arm
- Dynamo really spawned and sent the warmup
- the warmup completed for the intended target
- protected turn B is faster than control turn B

Columns to check first:

- hint identity: `spec_prefill`
- runtime proof: `prefill_spawned`, `prefill_sent`, `prefill_done`, `prefill_target_seen`
- isolation proof: `prompt_isolation_mode`
- performance effect: `turn_b_ms`, `turn_b_gain_ms`, `effect`

### Worked Success Example

Use this when you want a direct-runtime proof example, not just a latency
change:

- [`contracts/examples/exp12_speculative_prefill_success.md`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/examples/exp12_speculative_prefill_success.md)

### Run

=== This works on GH200 ===
```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
SPEC_PREFILL_MODE=all \
EXPERIMENT_RESET_MODE=flush \
RETENTION_PROMPT_ISOLATION_MODE=disjoint \
SPEC_PREFILL_SWEEP_SEED_MODE=per_value \
SPEC_PREFILL_SWEEP_AXIS=SPEC_PREFILL_WARMUP_WAIT_MS \
SPEC_PREFILL_SWEEP_VALUES="0 500 1000 2000" \
SPEC_PREFILL_TURN_A_WORDS=4000 \
SPEC_PREFILL_TURN_B_WORDS=2048 \
SPEC_PREFILL_OUTPUT_TOKENS=128 \
./agentbench/run_speculative_prefill_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

=== This works on GH200 with real SWE-bench Pro tasks? ===
```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
SPEC_PREFILL_MODE=all \
SPEC_PREFILL_REQUEST_SOURCE=swebench_dataset \
SPEC_PREFILL_SWEBENCH_DATASET=ScaleAI/SWE-bench_Pro \
SPEC_PREFILL_SWEBENCH_SPLIT=test \
SPEC_PREFILL_TURN_A_INDEX=0 \
SPEC_PREFILL_TURN_B_INDEX=1 \
SPEC_PREFILL_COMPARISON_MODE=same_task_isolated \
EXPERIMENT_RESET_MODE=restart \
SPEC_PREFILL_SWEEP_SEED_MODE=per_value \
SPEC_PREFILL_SWEEP_AXIS=SPEC_PREFILL_WARMUP_WAIT_MS \
SPEC_PREFILL_SWEEP_VALUES="0 500 1000 2000" \
SPEC_PREFILL_OUTPUT_TOKENS=128 \
./agentbench/run_speculative_prefill_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

In this mode:

- control turn A uses SWE-bench row `SPEC_PREFILL_TURN_A_INDEX`
- control turn B uses SWE-bench row `SPEC_PREFILL_TURN_B_INDEX`
- with `SPEC_PREFILL_COMPARISON_MODE=same_task_isolated`, protected turn A/B use those exact same rows
- the helper restarts Dynamo between the control and protected arms, so the protected arm does not inherit the control arm's cache
- `SPEC_PREFILL_TURN_A_WORDS` and `SPEC_PREFILL_TURN_B_WORDS` are ignored because real task prompts come from the dataset

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
SPEC_PREFILL_SWEEP_SEED_MODE
SPEC_PREFILL_REQUEST_SOURCE
SPEC_PREFILL_SWEBENCH_DATASET
SPEC_PREFILL_SWEBENCH_SPLIT
SPEC_PREFILL_TURN_A_INDEX
SPEC_PREFILL_TURN_B_INDEX
SPEC_PREFILL_SWEBENCH_PROTECTED_OFFSET
SPEC_PREFILL_COMPARISON_MODE
RETENTION_PROMPT_ISOLATION_MODE
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
cat experiments/reports/latest_speculative_prefill_microbenchmark_summary.md
cat experiments/reports/latest_speculative_prefill_microbenchmark_run_contract.json

ls experiments/charts/exp12_specprefill_*
```

Main outputs:

- `latest_speculative_prefill_microbenchmark_matrix.csv`: one row per arm or per sweep-arm point
- `latest_speculative_prefill_microbenchmark_summary.md`: readable summary
- `latest_speculative_prefill_microbenchmark_run_contract.json`: exact resolved settings
- `experiments/charts/exp12_specprefill_latency_vs_warmup_wait.svg`

### Debug

```bash
docker logs -f dynamo-sglang-worker
```

### Decision Proof

Exp12 now emits a generated decision-proof table after `sweep`, `all`, and
`plot` runs. The table is both documentation and run evidence: it names the code
location, shows the relevant snippet, names the runtime/report signal, and then
sets `checked_true` from the latest run artifacts.

Generated proof files:

- `experiments/reports/latest_exp12_decision_proof.csv`
- `experiments/reports/latest_exp12_decision_proof.md`
- `experiments/charts/exp12_decision_proof.csv`
- `experiments/charts/exp12_decision_proof.md`

Inspect the latest proof:

```bash
cat experiments/reports/latest_exp12_decision_proof.md
cat experiments/charts/exp12_decision_proof.md
```

Decision-proof columns:

- `step`: chronological proof step
- `when`: when the logging/check happens
- `where`: exact source file and line
- `what_it_means`: plain-English meaning
- `code_snippet`: source snippet being checked
- `runtime_signal`: log/report signal expected from the run
- `evidence_source`: file/log/report used for the check
- `evidence_value`: actual observed value from the latest run
- `request_role`: `turn_a`, `turn_b`, warmup, or whole-run scope
- `arm`: control or protected arm
- `prefill_metric`: which prefill proof metric the row checks
- `checked_true`: whether the latest run produced the expected evidence
- `failure_meaning`: what to debug if the check is false

| Step | When | Where | What It Means | Code Snippet | Runtime Signal |
|---:|---|---|---|---|---|
| 1 | Harness attaches speculative-prefill hint | [`run_speculative_prefill_probe.py:716`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:716) | The protected arm sends `nvext.agent_hints.speculative_prefill=true`. | `"speculative_prefill": spec_prefill` | `hint_status=on` / `spec_prefill=True` |
| 2 | Harness names the target turn B request | [`run_speculative_prefill_probe.py:718`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:718) | The hint carries the exact turn-B request id that the warmup should target. | `"spec_prefill_target_request_id": target_request_id` | `spec_prefill_target_request_id` / `prefill_target_seen` |
| 3 | Dynamo declares the typed hint field | [`nvext.rs:426`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/protocols/openai/nvext.rs:426) | Dynamo's OpenAI `nvext` schema has a real `speculative_prefill` field. | `pub speculative_prefill: Option<bool>` | source schema + protected hint row |
| 4 | Dynamo calls the speculative-prefill wrapper | [`preprocessor.rs:1819`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor.rs:1819) | The normal response stream passes through the speculative-prefill decision path. | `let final_stream = speculative_prefill::maybe_wrap_stream(` | `worker.spec_prefill.wrap_checked` |
| 5 | Prefill gate reads the hint | [`speculative_prefill.rs:198`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:198) | The decision gate reads `hints.speculative_prefill` and decides whether to continue. | `.and_then(\|hints\| hints.speculative_prefill)` | `worker.spec_prefill.wrap_checked enabled=true` |
| 6 | Prefill task is spawned | [`speculative_prefill.rs:219`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:219) | Dynamo launches the background task that will build the next-turn warmup. | `"worker.spec_prefill.task_spawned"` | `worker.spec_prefill.task_spawned` / `prefill_spawned` |
| 7 | Warmup prompt is rendered | [`speculative_prefill.rs:327`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:327) | Dynamo rendered the predicted next-turn prefix and counted its tokens. | `"worker.spec_prefill.prefill_rendered"` | `worker.spec_prefill.prefill_rendered` / `prefill_tokens` |
| 8 | Warmup request is sent | [`speculative_prefill.rs:356`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:356) | Dynamo sends the synthetic `max_tokens=1` warmup request into the backend path. | `"worker.spec_prefill.prefill_sent"` | `worker.spec_prefill.prefill_sent` / `prefill_sent` |
| 9 | Warmup request completes | [`speculative_prefill.rs:374`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:374) | Dynamo drains the warmup stream so the prefill lifecycle completes. | `"worker.spec_prefill.prefill_completed"` | `worker.spec_prefill.prefill_completed` / `prefill_done` |
| 10 | Probe parses worker speculative-prefill events | [`run_speculative_prefill_probe.py:1000`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:1000) | Postprocess collects `worker.spec_prefill.*` events from the worker runtime log. | `elif event_type.startswith("worker.spec_prefill."):` | `spec_events` |
| 11 | Probe maps events into proof columns | [`run_speculative_prefill_probe.py:1166`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:1166) | The raw runtime events become `prefill_wrap`, `prefill_spawned`, `prefill_sent`, `prefill_done`, and `prefill_target_seen`. | `"prefill_wrap": wrap_status`<br>`"prefill_spawned": "worker.spec_prefill.task_spawned" in event_types` | `prefill_*` columns |
| 12 | Probe classifies the effect | [`run_speculative_prefill_probe.py:1221`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/run_speculative_prefill_probe.py:1221) | The probe marks whether the protected arm had direct/inferred prefill evidence and whether turn B was faster. | `effect_status = "faster_direct"` | `effect_status` / `effect` |
| 13 | Microbenchmark report normalizes matrix rows | [`build_speculative_prefill_microbenchmark_report.py:176`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/build_speculative_prefill_microbenchmark_report.py:176) | The public report carries the probe proof fields into one compact matrix. | `def normalize_matrix_rows(` | `latest_speculative_prefill_microbenchmark_matrix.csv` |
| 14 | Microbenchmark report carries prefill columns | [`build_speculative_prefill_microbenchmark_report.py:205`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/build_speculative_prefill_microbenchmark_report.py:205) | The compact matrix keeps the direct proof columns used by slides and debugging. | `"prefill_wrap": pick(row, "prefill_wrap")` | `prefill_wrap` / `prefill_sent` / `prefill_done` |
| 15 | Microbenchmark report writes public outputs | [`build_speculative_prefill_microbenchmark_report.py:352`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/speculative_prefill/build_speculative_prefill_microbenchmark_report.py:352) | The final public matrix and summary are written from the normalized rows. | `write_csv(out_dir / "microbenchmark_matrix.csv", matrix_rows, MATRIX_COLUMNS)` | `microbenchmark_matrix.csv` / `microbenchmark_summary.csv` |

Simple reading: the first rows prove the harness sent the hint and target, the
middle rows prove Dynamo executed the speculative-prefill path, and the final
rows prove the public matrix preserved the evidence.

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
- `prompt_isolation_mode`
- `turn_a_prompt_family`
- `turn_b_prompt_family`
- `turn_a_prompt_hash`
- `turn_b_prompt_hash`
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

Use this when you want one readable script that runs the known-good experiment
wrappers one after another.

The suite is config-driven. The config contains separate, clearly named blocks
for the synthetic and SWE-bench Pro versions of Experiments 9, 11, 12, and 13.
Select the exact blocks you want with `SUITE_RUNS`.

Public files:

- suite config:
  - [`agentbench/agentic_hint_sweeps_suite.conf.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/agentic_hint_sweeps_suite.conf.sh)
- foreground runner:
  - [`agentbench/run_agentic_hint_sweeps_suite_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_agentic_hint_sweeps_suite_single_host.sh)
- nohup runner:
  - [`agentbench/run_agentic_hint_sweeps_suite_nohup.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_agentic_hint_sweeps_suite_nohup.sh)

### What This Really Does

The suite does not merge all experiments into one runtime command. It runs the
same public wrappers you already use directly, waits for each wrapper to finish,
then starts the next selected case.

Available `SUITE_RUNS` cases:

```text
exp9_synthetic
exp9_swebench
exp9_trajectory
exp11_synthetic
exp11_swebench
exp12_synthetic
exp12_swebench
exp13_synthetic
exp13_swebench
```

Default selection in the config:

```text
SUITE_DEFAULT_RUNS="exp9_synthetic exp9_swebench exp11_synthetic exp11_swebench exp12_synthetic exp12_swebench exp13_synthetic exp13_swebench"
```

Use `SUITE_RUNS` only when you want to override that default. Legacy
`SUITE_EXPERIMENTS="9 11 12"` still works when `SUITE_RUNS` is unset, but it
maps to the synthetic cases only. Prefer `SUITE_RUNS` for new runs.

### Config Layout

Edit the suite config file directly. It is already split into sections:

- shared suite settings
- Experiment 9 synthetic: KV retention
- Experiment 9 SWE-bench: KV retention over real SWE-bench Pro task prompts
- Experiment 9 trajectory: KV retention over Exp6 captured trajectory prompts
- Experiment 11 synthetic: priority scheduling
- Experiment 11 SWE-bench: priority scheduling over real SWE-bench Pro task prompts
- Experiment 12 synthetic: speculative prefill
- Experiment 12 SWE-bench: speculative prefill over real SWE-bench Pro task prompts
- Experiment 13 synthetic: latency sensitivity
- Experiment 13 SWE-bench: latency sensitivity over real SWE-bench Pro task prompts

The config file is:

```bash
agentbench/agentic_hint_sweeps_suite.conf.sh
```

Default prompt-isolation policy:

- `RETENTION_PROMPT_ISOLATION_MODE=disjoint` for retention-style prompts
- `SPEC_PREFILL_PROMPT_ISOLATION_MODE=disjoint` for Experiment 12

### Run

Use this when you want the selected SWE-bench suite to keep running if your
terminal disconnects:

```bash
cd ~/kv_cache_offloading

RUN_ID="agentic_hint_sweeps_gh200_$(date +%Y%m%d_%H%M%S)"
LOG_DIR="experiments/reports/agentic_hint_sweeps_suite_nohup/${RUN_ID}"
mkdir -p "${LOG_DIR}"

nohup env \
  AGENTIC_HINT_SUITE_ID="${RUN_ID}" \
  SUITE_RUNS="exp9_swebench exp11_swebench exp12_swebench exp13_swebench" \
  DYNAMO_MACHINE_PROFILE=gh200 \
  ./agentbench/run_agentic_hint_sweeps_suite_single_host.sh \
    Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
  > "${LOG_DIR}/run.log" 2>&1 < /dev/null &

echo "RUN_ID=${RUN_ID}"
echo "LOG=${LOG_DIR}/run.log"
echo "PID=$!"
```

Nohup version for only the full-trajectory Exp9 case:

```bash
cd ~/kv_cache_offloading

RUN_ID="exp9_trajectory_gh200_$(date +%Y%m%d_%H%M%S)"
LOG_DIR="experiments/reports/agentic_hint_sweeps_suite_nohup/${RUN_ID}"
mkdir -p "${LOG_DIR}"

nohup env \
  AGENTIC_HINT_SUITE_ID="${RUN_ID}" \
  SUITE_RUNS="exp9_trajectory" \
  DYNAMO_MACHINE_PROFILE=gh200 \
  ./agentbench/run_agentic_hint_sweeps_suite_single_host.sh \
    Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
  > "${LOG_DIR}/run.log" 2>&1 < /dev/null &

echo "RUN_ID=${RUN_ID}"
echo "LOG=${LOG_DIR}/run.log"
echo "PID=$!"
```

Watch the run:

```bash
tail -f "${LOG_DIR}/run.log"
```

If you reconnect later:

```bash
cd ~/kv_cache_offloading

tail -f "$(ls -td experiments/reports/agentic_hint_sweeps_suite_nohup/* | head -1)/run.log"
```

### Main Suite Knobs

```text
SUITE_CONFIG_PATH
DYNAMO_MACHINE_PROFILE
SUITE_DEFAULT_RUNS
SUITE_RUNS
SUITE_EXPERIMENTS
SUITE_ISOLATION_MODE
SUITE_CONTINUE_ON_ERROR
SUITE_INTERACTIVE_BUILD_PROGRESS
SUITE_ENSURE_PRECISE_RUNTIME
SUITE_CHART_GROUP
RETENTION_PROMPT_ISOLATION_MODE
SPEC_PREFILL_PROMPT_ISOLATION_MODE
```

### Main Runtime Policy Knob

`SUITE_ISOLATION_MODE` is still the main runtime policy setting:

- `per_case`
  - restart between experiments
  - use each selected case's known-good reset mode
  - current defaults:
    - synthetic cases: `flush`
    - SWE-bench Pro cases: `restart`
- `clean`
  - restart between experiments
  - restart between sweep values
- `flush`
  - restart between experiments
  - flush between sweep values
- `fast`
  - restart between experiments
  - no restart between sweep values
  - no flush between sweep values

Recommended:

- `per_case`: safest default for the mixed synthetic + SWE-bench suite
- `clean`: slowest, most conservative
- `flush`: useful when you intentionally want every selected case to use flush
- `fast`: quickest for iteration

For the default mixed suite, do not force `SUITE_ISOLATION_MODE=flush` unless
you intentionally want the SWE-bench cases to use flush too. The known-good
SWE-bench cases currently use `restart`.

### Outputs

Charts are copied into [`experiments/charts/`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/charts) as soon as each experiment finishes, so you can inspect them before the full suite completes.

The suite also removes chart files for experiments that are not in the current
`SUITE_RUNS` selection, so stale chart files do not linger when you run a subset.

The suite also keeps separated chart copies:

```text
experiments/charts/swebench/
experiments/charts/synthetic/
experiments/charts/mixed/
experiments/charts/archive/<suite_id>/
```

Default grouping:

- all selected `*_swebench` cases -> `experiments/charts/swebench/`
- all selected `*_synthetic` cases -> `experiments/charts/synthetic/`
- mixed selections -> `experiments/charts/mixed/`

Override the group name when you want a custom folder:

```bash
SUITE_CHART_GROUP=gh200_swebench_30values
```

The top-level `experiments/charts/` folder remains the latest convenience view.
The grouped folder keeps the latest charts for that group. The archive folder
keeps the exact charts and matrices for one suite run.
At suite start, the selected grouped folder is cleared of old `exp9_` through
`exp13_` files so it reflects the current grouped run.

Top-level suite outputs:

```bash
cat experiments/reports/latest_agentic_hint_sweeps_suite_summary.md
cat experiments/reports/latest_agentic_hint_sweeps_suite_manifest.json
cat experiments/reports/latest_agentic_hint_sweeps_suite_driver.log
```

For nohup runs:

```bash
tail -n 200 -f experiments/reports/latest_agentic_hint_sweeps_suite_nohup.log
tail -n 200 -f experiments/reports/latest_agentic_hint_sweeps_suite_driver.log
```

Main outputs:

- `latest_agentic_hint_sweeps_suite_summary.md`: one landing-page summary for the full run
- `latest_agentic_hint_sweeps_suite_manifest.json`: exact experiment statuses, chart paths, and report paths
- `latest_agentic_hint_sweeps_suite_driver.log`: suite-level launch log
- `experiments/charts/`: shared folder containing only the latest chart SVGs and the matrix CSVs they were generated from

### Regenerate Dense-Sweep Charts

Use this if the experiment already finished but the SVGs look cluttered because
you used many sweep values. These commands rebuild only the charts from the
latest matrix CSVs; they do not rerun the expensive experiments.

Experiment 9:

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
KV_RETENTION_MODE=plot \
KV_RETENTION_PLOT_MATRIX_CSV=experiments/reports/latest_kv_retention_microbenchmark_matrix.csv \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

Experiment 11:

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRIORITY_SCHEDULING_MODE=plot \
PRIORITY_SCHEDULING_PLOT_MATRIX_CSV=experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv \
./agentbench/run_priority_scheduling_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

Experiment 12:

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
SPEC_PREFILL_MODE=plot \
SPEC_PREFILL_PLOT_MATRIX_CSV=experiments/reports/latest_speculative_prefill_microbenchmark_matrix.csv \
./agentbench/run_speculative_prefill_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

Experiment 13:

```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
LATENCY_SENSITIVITY_MODE=plot \
PRIORITY_SCHEDULING_PLOT_MATRIX_CSV=experiments/reports/latest_latency_sensitivity_microbenchmark_matrix.csv \
./agentbench/run_latency_sensitivity_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

Check the regenerated public chart files:

```bash
ls -lh experiments/charts/exp9_*.svg
ls -lh experiments/charts/exp11_*.svg
ls -lh experiments/charts/exp12_*.svg
ls -lh experiments/charts/exp13_*.svg
```

The suite banners show the actual selected case count, for example `1/8`,
`2/8`, and so on.
When a wrapper uses `MODE=all`, the banner also shows the resolved behavior, for example:

- Experiment 9: `all (resolved to sweep + plot)`
- Experiment 11: `all (resolved to sweep + plot)`
- Experiment 12: `all (resolved to sweep + plot)`
- Experiment 13: `all (resolved to sweep + plot)`

The suite terminal output and nohup log now print very clear start/end banners
for each selected case, so you can easily see when each synthetic or SWE-bench
run begins and ends.

If a precise image rebuild happens, you will also now see
clear build banners such as:

- `PRECISE IMAGE BUILD START`
- `PRECISE IMAGE BUILD DONE`

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
