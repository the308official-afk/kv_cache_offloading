# MISC

Small things worth trying next.

## 1. Check whether this machine accepts top-level priority

This is the fastest way to tell whether the frontend/runtime supports:

- `priority` at the top level
- or only `nvext.agent_hints.priority`

```bash
cd ~/kv_cache_offloading

python3 - <<'PY'
import json
import urllib.request

url = "http://127.0.0.1:8000/v1/chat/completions"
payload = {
    "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
    "messages": [{"role": "user", "content": "Say hello in one word."}],
    "max_tokens": 4,
    "temperature": 0,
    "priority": 10,
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")
        print("STATUS:", resp.status)
        print(body[:1000])
except Exception as e:
    print("REQUEST_FAILED:", e)
    if hasattr(e, "read"):
        try:
            print(e.read().decode("utf-8"))
        except Exception:
            pass
PY
```

If this fails with `Unsupported parameter(s): priority`, use:

```bash
export RETENTION_TOP_LEVEL_PRIORITY_MODE=auto
```

for retention experiments....

### B. Canonical hint-path test

This checks the canonical path we care about most:

- `nvext.agent_hints.priority`

```bash
cd ~/kv_cache_offloading

python3 - <<'PY'
import json
import urllib.request

url = "http://127.0.0.1:8000/v1/chat/completions"
payload = {
    "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
    "messages": [{"role": "user", "content": "Say hello in one word."}],
    "max_tokens": 4,
    "temperature": 0,
    "nvext": {
        "agent_hints": {
            "priority": 10
        }
    }
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")
        print("STATUS:", resp.status)
        print(body[:1000])
except Exception as e:
    print("REQUEST_FAILED:", e)
    if hasattr(e, "read"):
        try:
            print(e.read().decode("utf-8"))
        except Exception:
            pass
PY
```

How to interpret it:

- If the top-level priority test fails but this one succeeds, the machine does
  not support top-level `priority`, but it does support
  `nvext.agent_hints.priority`.
- If both succeed, both paths are supported.
- If this one fails too, the canonical hint path itself is broken on that
  machine.

## 2. Start a clean instrumented Dynamo

Good default startup when you want retention, hint, and runtime evidence.

```bash
./run_dynamo_single_host.sh stop

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

Then watch the worker:

```bash
docker logs -f dynamo-sglang-worker
```

## 3. Run the simplest retention sweep first

This is the quickest sanity check that the pipeline works end to end.

```bash
cd ~/kv_cache_offloading

RETENTION_SWEEP_ID="retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
DISTRACTOR_COUNTS="2 10 20" \
KV_TIER_MODES="gpu_only" \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES="high-priority" \
PROTECTED_INPUT_LEN=200 \
DISTRACTOR_INPUT_LEN=200 \
GPU_ONLY_MEM_FRACTION_STATIC=0.7 \
RANDOM_OUTPUT_LEN=1 \
MAX_CONTEXT_TOKENS=17146 \
RETENTION_TOP_LEVEL_PRIORITY_MODE=auto \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_kv_retention_threshold_sweep_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

## 4. Compare `light` vs `precise`

Use the same sweep twice:

- once with `RETENTION_ATTRIBUTION_MODE=light`
- once with `RETENTION_ATTRIBUTION_MODE=precise`

Goal:

- see whether the conclusion changes
- see whether the runtime overhead is worth it

## 5. Compare `high-priority` vs `high-reuse`

Try the same sweep with:

```bash
PROTECTED_HINT_PROFILES="high-priority"
```

and then:

```bash
PROTECTED_HINT_PROFILES="high-reuse"
```

Goal:

- check whether priority hints and reuse hints behave differently
- see which one shows stronger retention separation

## 6. Push the eviction threshold harder

If `2 10 20` is too gentle, try:

```bash
DISTRACTOR_COUNTS="2 10 20 40 60 80 100 200"
```

Goal:

- find the exact point where control loses reuse
- see whether protected survives deeper into the sweep

## 7. Try a more cache-sensitive prompt size

If the run is too easy, increase:

```bash
PROTECTED_INPUT_LEN=8000
DISTRACTOR_INPUT_LEN=2000
```

If the run is too harsh, reduce:

```bash
PROTECTED_INPUT_LEN=200
DISTRACTOR_INPUT_LEN=200
```

Goal:

- find the “middle pressure” regime where hints have room to matter

## 8. Check whether SGLang actually acted on priority

After a retention sweep, look for these columns in:

```text
experiments/reports/retention_threshold_matrix.csv
```

Most useful columns:

- `frontend_top_level_priority_compatibility`
- `worker_hint_status`
- `worker_priority_mechanism_ready`
- `worker_priority_path_status`
- `hint_runtime_effect_status`

What you want to see:

- frontend compatibility is not `unsupported`
- worker hint status is `full`
- mechanism ready is `true`
- priority path status becomes `applied`

## 9. Run the sweep in the background

Useful for long runs.

```bash
cd ~/kv_cache_offloading

RETENTION_SWEEP_ID="retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=precise \
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

Then monitor:

```bash
LATEST_THRESHOLD_SWEEP="$(ls -td experiments/reports/retention_threshold_sweeps/* | head -1)"
echo "$LATEST_THRESHOLD_SWEEP"

tail -f "$LATEST_THRESHOLD_SWEEP/nohup.log"
cat "$LATEST_THRESHOLD_SWEEP/retention_threshold_matrix.csv"
```

## 10. Try the same sweep on another machine

Best cross-machine comparison knobs:

- same model
- same `DISTRACTOR_COUNTS`
- same `PROTECTED_INPUT_LEN`
- same `DISTRACTOR_INPUT_LEN`
- same `GPU_ONLY_MEM_FRACTION_STATIC`
- same `WORKER_BASE_ARGS`

Then compare:

- `worker_kv_capacity_tokens`
- `a_replay_latency_ms`
- `a_replay_cached_tokens`
- `hint_runtime_effect_status`

## 11. Good questions to keep asking

- Does the frontend accept top-level `priority` on this machine?
- Did the worker actually receive the hint?
- Did the worker’s priority path apply it?
- Did replay stay faster than first A?
- Did cached tokens increase on replay?
- Did protected survive deeper than control?

## 12. GH200 priority regression checklist

Use this when `priority` worked yesterday on GH200, but fails today.

Most likely meaning:

- you are not running the same frontend image today
- or you restarted Dynamo without the instrumented local images
- or the local Dynamo source / rebuild path drifted

### A. Check which images are actually running

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

What you want:

- `dynamo-frontend` should point to `local/dynamo-frontend:runtime-json-logs`
- `dynamo-sglang-worker` should point to `local/dynamo-sglang:runtime-json-logs`

If you see stock images instead, that is probably the problem.

### B. Check that the local images exist

```bash
docker images | grep -E 'dynamo-frontend|dynamo-sglang'
```

You want to see:

- `local/dynamo-frontend:runtime-json-logs`
- `local/dynamo-sglang:runtime-json-logs`

### C. Re-prepare instrumented Dynamo source

```bash
cd ~/kv_cache_offloading

./runtime_instrumentation/prepare_instrumented_dynamo_source.sh
```

This makes sure:

- upstream Dynamo source exists
- the source is checked out to a known-compatible pinned Dynamo revision
- the hint-preservation patch is applied
- runtime JSON logging support is present

If it says `Patch could not be applied cleanly`, that does not automatically
mean failure. The prepare script now repairs known upstream Dynamo drift after
the patch step. The real pass condition is the final line:

- `Instrumented Dynamo source is ready.`

The new summary is easier to read:

- `applied_or_already_present` = nothing to worry about
- `drift_repaired` = upstream changed, repair succeeded
- `Safe to continue: yes` = go ahead and build images

### D. Rebuild instrumented images for GH200

```bash
cd ~/kv_cache_offloading

DOCKER_BUILD_PLATFORM=linux/arm64 \
DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

This is the safest rebuild path for GH200 / ARM.

### E. Restart Dynamo with the local images explicitly

```bash
./run_dynamo_single_host.sh stop

DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

Then immediately watch the worker:

```bash
docker logs -f dynamo-sglang-worker
```

### F. Re-run the direct top-level priority smoke test

```bash
cd ~/kv_cache_offloading

python3 - <<'PY'
import json
import urllib.request

url = "http://127.0.0.1:8000/v1/chat/completions"
payload = {
    "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
    "messages": [{"role": "user", "content": "Say hello in one word."}],
    "max_tokens": 4,
    "temperature": 0,
    "priority": 10,
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")
        print("STATUS:", resp.status)
        print(body[:1000])
except Exception as e:
    print("REQUEST_FAILED:", e)
    if hasattr(e, "read"):
        try:
            print(e.read().decode("utf-8"))
        except Exception:
            pass
PY
```

Interpretation:

- if this succeeds, the frontend currently accepts top-level `priority`
- if this fails with `Unsupported parameter(s): priority`, the frontend path is still wrong

### G. If the smoke test passes, force the retention run to use priority

```bash
export RETENTION_TOP_LEVEL_PRIORITY_MODE=force
```

Why:

- `force` makes the experiment fail loudly if priority breaks again
- that is better than silently falling back when you are explicitly testing priority behavior

### H. If the smoke test still fails

Then the problem is not “GH200 cannot do it”.
It more likely means:

- the frontend build on this machine is not the same as the one that worked yesterday
- or the runtime patch path changed
- or you are not actually launching the rebuilt local frontend image

At that point, compare:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}'
docker inspect dynamo-frontend --format '{{.Config.Image}}'
docker inspect dynamo-sglang-worker --format '{{.Config.Image}}'
```

and keep the output with the run notes.

Goal:

- confirm which images are actually running
- confirm whether you started with the instrumented frontend
- confirm whether the frontend still accepts top-level `priority`

### A. Check the running Dynamo images

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}'
```

What you want to see:

- `dynamo-frontend` using `local/dynamo-frontend:runtime-json-logs`
- `dynamo-sglang-worker` using `local/dynamo-sglang:runtime-json-logs`

### B. Check image creation times

```bash
docker image inspect local/dynamo-frontend:runtime-json-logs \
  --format 'frontend created={{.Created}} id={{.Id}}'

docker image inspect local/dynamo-sglang:runtime-json-logs \
  --format 'worker created={{.Created}} id={{.Id}}'
```

This helps you see whether today you are actually running the same build you expected.

### C. Check that the local Dynamo source exists

```bash
cd ~/kv_cache_offloading

ls -ld upstream/dynamo
git -C upstream/dynamo rev-parse --short HEAD
```

### D. Prepare the instrumented Dynamo source again

```bash
cd ~/kv_cache_offloading

./runtime_instrumentation/prepare_instrumented_dynamo_source.sh
```

### E. Rebuild the instrumented images for GH200

```bash
cd ~/kv_cache_offloading

DOCKER_BUILD_PLATFORM=linux/arm64 \
DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

### F. Restart Dynamo with the explicit local images

```bash
./run_dynamo_single_host.sh stop

DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

Then watch the worker:

```bash
docker logs -f dynamo-sglang-worker
```

### G. Re-run the direct top-level priority smoke test

```bash
cd ~/kv_cache_offloading

python3 - <<'PY'
import json
import urllib.request

url = "http://127.0.0.1:8000/v1/chat/completions"
payload = {
    "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
    "messages": [{"role": "user", "content": "Say hello in one word."}],
    "max_tokens": 4,
    "temperature": 0,
    "priority": 10,
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")
        print("STATUS:", resp.status)
        print(body[:1000])
except Exception as e:
    print("REQUEST_FAILED:", e)
    if hasattr(e, "read"):
        try:
            print(e.read().decode("utf-8"))
        except Exception:
            pass
PY
```

Interpretation:

- if this succeeds, the frontend accepts top-level `priority`
- if this fails with `Unsupported parameter(s): priority`, then the frontend path you are running today still does not support it

### H. Once the smoke test passes, force the retention experiment to use priority

```bash
export RETENTION_TOP_LEVEL_PRIORITY_MODE=force
```

Why `force`?

- `auto` is a compatibility fallback
- `force` is better once the frontend is fixed, because it fails loudly if priority breaks again

### I. Compare the worker runtime across machines

If `--radix-eviction-policy priority` worked on one machine but fails on
another, capture the actual worker runtime on both machines and compare them:

```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE=ec2   # or gh200
source runtime_instrumentation/dynamo_machine_profile.sh

./runtime_instrumentation/probe_worker_runtime.sh
```

This writes a report under:

```bash
experiments/reports/runtime_probe/
```

Compare these fields between the two machines:

- `worker_image`
- `architecture`
- package versions for `dynamo` / `sglang`
- whether `probe_value=priority` is accepted or rejected
- the `Help Snippet` section around `radix-eviction-policy`


```bash
cd ~/kv_cache_offloading

export RETENTION_TOP_LEVEL_PRIORITY_MODE=disable

RETENTION_SWEEP_ID="retention_threshold_sweep_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=precise \
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
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority" \
./agentbench/run_kv_retention_threshold_sweep_nohup.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
```

```bash
LATEST=$(ls -td experiments/raw/agentbench/results/* | head -1)

python3 experiments/scripts/agentbench_report/build_run_report.py \
  --agentbench-result-dir "$LATEST" \
  --transfer-log experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl
```






Here’s a concise version you can use.
What We Have Achieved
Built a realistic agentic benchmark stack: SWE-bench Pro -> AgentBench -> Deep Agents -> Dynamo -> SGLang
Automated 12 experiment types for:prompt evolution
KV reuse / retention
KV host-device transfer attribution
priority scheduling
speculative prefill
multi-task / multi-model sweeps
GPU-only, GPU+CPU, GPU+CPU+storage studies

Added precise runtime instrumentation so we can separate:hint sent
worker saw hint
runtime behavior changed

What We Can Measure
TTFT / latency
cached tokens / reuse ratio
KV transfer activity
retention / eviction boundary
scheduling order under priority
logging overhead
cross-model and cross-hardware comparisons
What Is Working
priority works as a real control
speculative_prefill works as a real control
osl / expected_output_tokens work as routing/resource signals
full design-space sweeps are working
What Is Still Open
prove whether cache_control is a true retention control in this stack
strengthen direct proof inside SGLang decision paths
expand support for more hint types beyond current live controls
Why This Matters
We are characterizing resource usage for a high-profile agentic workload
We are recreating realistic agentic use cases on Nvidia systems
We are using the results to guide roadmap decisions with:Storage
AIG-SHARKS
DESG
GPU Architecture

Core Research Value
connects realistic agent behavior to memory/storage usage
exposes where latency, KV movement, and retention bottlenecks come from
gives concrete data to drive architectural enhancements
If you want, I can compress this further into:
one intro slide
one achievements slide
one open-questions slide.





# salloc --nodelist=radha1 -t 3:59:00
docker container rm pytorch-vllm -f	
docker run -it \
	--network=host --ipc=host --device=/dev/kfd --device=/dev/dri --group-add video  --cap-add=SYS_PTRACE --security-opt seccomp=unconfined -v $HOME/dockerx:/dockerx --shm-size=64G \
	-v /data/ojaiyeob:/workspace/data \
	-w /var/lib/jenkins/dlrm/FAMBench/benchmarks/dlrm/ootb/bench \
	--name pytorch-vllm \
	--rm rocm/pytorch:latest \
	-lc '
			pwd
			cd /workspace/dlrm/FAMBench/benchmarks/dlrm/ootb/bench
			ls -l
			./dlrm_s_benchmark.sh
		'
