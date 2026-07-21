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

RUN_ID="exp6_prompt_evolution_gh200_$(date +%Y%m%d_%H%M%S)"
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
  DYNAMO_MACHINE_PROFILE=gh200 \
  PRECISE_START_MODE=clean \
  PROMPT_EVOLUTION_BATCH_START_INDEX=0 \
  PROMPT_EVOLUTION_BATCH_END_INDEX=730 \
  PROMPT_EVOLUTION_VALUE_CHAR_LIMIT=200000 \
  ./agentbench/run_prompt_evolution_batch_single_host.sh \
    Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
  > "${LOG_DIR}/run.log" 2>&1 < /dev/null &

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

The wrapper clears old Experiment 6 report state at the beginning of each run,
including cumulative `all_runs_*`, `latest_runs_*`, `latest_run_*`,
`prompt_evolution_*`, prior `runs/`, prior `prompt_evolution_batch_*`
directories, and old Experiment 6 public files in `experiments/charts`.
Then it copies only the latest readable Experiment 6 outputs into the shared
chart folder:

```bash
ls experiments/charts/exp6_*
cat experiments/charts/exp6_prompt_evolution_run_overview.csv
cat experiments/charts/exp6_prompt_evolution_task_summary.csv
cat experiments/charts/exp6_swebench_trajectory_prompt_catalog.csv
```

`exp6_prompt_evolution_run_overview.csv` is the manager-facing table used for
the run-overview slides. It is the first report to inspect after Experiment 6.
`exp6_swebench_trajectory_prompt_catalog.csv` is the prompt catalog that
Experiment 9 uses when `RETENTION_REQUEST_SOURCE=swebench_trajectory`.

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
KV_RETENTION_RESET_MODE=restart \
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

Use this when direct task-level SWE-bench prompts do not create enough cache pressure.

Step 0: capture real SWE-bench phase prompts with Experiment 6.

If an Experiment 6 task reaches the Deep Agents graph recursion limit with
`AGENTBENCH_SOFT_STOP_RECURSION=1`, the task is marked `recursion_soft_stop`.
Any phase prompts that were already dispatched are still written to
`others/result.json`, then copied into the trajectory catalog for Experiment 9.

For a quick smoke test:

```bash
cd ~/kv_cache_offloading

RUN_ID="exp6_prompt_evolution_gh200_$(date +%Y%m%d_%H%M%S)"
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
  DYNAMO_MACHINE_PROFILE=gh200 \
  PRECISE_START_MODE=clean \
  PROMPT_EVOLUTION_BATCH_START_INDEX=0 \
  PROMPT_EVOLUTION_BATCH_END_INDEX=20 \
  PROMPT_EVOLUTION_VALUE_CHAR_LIMIT=200000 \
  ./agentbench/run_prompt_evolution_batch_single_host.sh \
    Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
  > "${LOG_DIR}/run.log" 2>&1 < /dev/null &

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

For larger retention sweeps, capture enough tasks first. For example,
`DISTRACTOR_COUNTS="600"` needs at least 601 captured tasks:

- 1 protected task
- 600 distractor tasks

Step 1: confirm the trajectory prompt catalog from the captured Experiment 6
outputs.

The Experiment 6 wrapper builds this automatically by default and writes:

```bash
experiments/reports/latest_swebench_trajectory_prompt_catalog.csv
experiments/charts/exp6_swebench_trajectory_prompt_catalog.csv
```

To rebuild the catalog manually from the latest Experiment 6 traces:

```bash
cd ~/kv_cache_offloading

./agentbench/prepare_swebench_trajectory_prompts.sh
```

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

If the count is below 21, either wait for more Experiment 6 tasks to finish or
lower the largest distractor count.

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
KV_RETENTION_RESET_MODE=restart \
DISTRACTOR_COUNTS="5 10 15 20" \
PROTECTED_HINT_PROFILES="high-priority" \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

For the larger run after capturing enough Experiment 6 tasks, change:

```text
DISTRACTOR_COUNTS="100 200 400 600"
```

Mental model:

- Experiment 6 captures real SWE-bench phase prompts first
- the preparer turns those captured prompts into a replay catalog
- one protected task stage becomes A
- many stages from other tasks become distractors
- Experiment 9 only replays prompts; it does not run tools/tests/code edits

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

Strongest proof in this setup:

- `hint_kind=priority`
- `hint_seen=yes`
- `high_jump_ahead_count > 0`
- `high_jump_ahead_rate > 0%`
- `result=priority_reordered`

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

ls experiments/charts/exp13_latencysens_*
```

Main outputs:

- `latest_latency_sensitivity_microbenchmark_matrix.csv`: one compact row per sweep point
- `latest_latency_sensitivity_microbenchmark_summary.md`: readable summary
- `latest_latency_sensitivity_microbenchmark_run_contract.json`: exact resolved settings
- `latest_latency_sensitivity_microbenchmark_jump_ahead.svg`: line chart of jump-ahead rate versus arrival gap
- `experiments/charts/exp13_latencysens_jump_ahead_vs_arrival_gap.svg`: same chart in the shared chart folder

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

- [`contracts/latency_sensitivity_microbenchmark.contract.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/contracts/latency_sensitivity_microbenchmark.contract.sh)
  Contract. Sets `PRIORITY_HINT_KIND=latency_sensitivity`, disables top-level
  priority by default, and redirects outputs to `latest_latency_sensitivity_*`.

- [`agentbench/run_latency_sensitivity_microbenchmark_single_host.sh`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/run_latency_sensitivity_microbenchmark_single_host.sh)
  Public wrapper. Loads the latency-sensitivity contract and delegates to the
  proven priority-scheduling harness.

- [`experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py) `build_hint_payload(...)`
  Script layer. Builds either `agent_hints.priority` or
  `agent_hints.latency_sensitivity` based on `PRIORITY_HINT_KIND`.

- [`experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/run_priority_scheduling_probe.py) `runtime_agent_hints(...)`
  Report layer. Reads worker-side `agent_hints` from runtime JSON logs.

- [`experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/scripts/priority_scheduling/build_priority_scheduling_microbenchmark_report.py)
  Report builder. Emits the compact `hint_kind`, `hint_seen`,
  `hint_path_status`, and jump-ahead columns.

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

To run only the SWE-bench cases:

```bash
cd ~/kv_cache_offloading

SUITE_RUNS="exp9_swebench exp11_swebench exp12_swebench exp13_swebench" \
DYNAMO_MACHINE_PROFILE=gh200 \
./agentbench/run_agentic_hint_sweeps_suite_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

### Nohup

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
