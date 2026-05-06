# HintBench

`hintbench/` is the benchmark harness for hint-guided Dynamo + SGLang experiments.

## Pipeline

![HintBench pipeline](../flow-chart.png)

## Prerequisite

Start the serving cluster first.

Head node:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_docker.sh
DYNAMO_MODEL_PATH=Qwen/Qwen2.5-0.5B ./run_dynamo_head.sh start
./run_dynamo_head.sh status
./run_dynamo_head.sh logs
hostname -I
```

Worker node:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh rootdisk
newgrp docker
./aws/check_ec2_rootdisk_worker_ready.sh
DYNAMO_MODEL_PATH=Qwen/Qwen2.5-0.5B \
DYNAMO_SERVED_MODEL_NAME=Qwen/Qwen2.5-0.5B \
ETCD_ENDPOINTS=http://<head-private-ip>:2379 \
./run_dynamo_worker.sh start
./run_dynamo_worker.sh status
./run_dynamo_worker.sh logs -f
```

Default worker flags in this setup:

```text
--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru
```

Use `g5.xlarge` or `g5.2xlarge` for workers.

Single-host GH200 mode is also supported for development.

Bootstrap once:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh rootdisk
newgrp docker
./aws/check_ec2_rootdisk_worker_ready.sh
```

Start / verify / stop:

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh start
./run_dynamo_single_host.sh status
./run_dynamo_single_host.sh logs
./run_dynamo_single_host.sh logs -f
./run_dynamo_single_host.sh test
./run_dynamo_single_host.sh stop
```

This mode is useful for local iteration, but it is not a substitute for the real two-worker setup.

## Experiment Catalog

### NVIDIA Hint Coverage

This is the hint-level view of the same guide.

| Hint from NVIDIA guide | What it means | Current support in this setup | Notes |
|---|---|---|---|
| `priority` | Marks how urgent or important a request is. Higher values are meant to get better queueing and scheduling treatment. | Supported | This is the main NVIDIA-documented hint your current setup uses end to end. |
| `osl` | Short for output sequence length. It tells the router how long the response is expected to be, so routing can account for output-block pressure. | Not yet supported end to end | The frontend does not enable `--router-track-output-blocks`, so this NVIDIA path is not active. |
| `speculative_prefill` | Tells the system to warm the KV cache for a likely next turn after the current response completes. | Not yet supported | Current request defaults do not send this hint, and the workflow does not trigger the NVIDIA speculative-prefill path. |
| `session_control` | Opens and closes isolated session slots for short-lived subagents so their KV does not pollute the main shared cache. | Not yet supported | Current requests do not send `nvext.session_control`, and the runtime does not enable the related streaming-session path. |

Your setup also uses several **custom experimental hints** that are not the main NVIDIA-documented hint set:

- `reuse_likelihood`
  - how likely the request is to benefit from staying near existing KV cache or repeated prefixes
- `agent_phase`
  - what phase of the workflow the request belongs to, such as planning or execution
- `latency_sensitivity`
  - how much the request should prefer lower wait time over other goals like cache locality
- `program_id`
  - which application, workflow, or experiment generated the request
- `context_type`
  - what kind of context the request is using, for example shared-prefix multi-turn conversation
- `expected_output_tokens`
  - your estimate of how long the response will be

These are part of your HintBench research layer, not the NVIDIA page’s core hint API.

Related worker/runtime defaults in this repo now include:

- `--enable-priority-scheduling`
- `--radix-eviction-policy lru`

So priority is currently used in both:

- request scheduling
- request hints

Priority-based KV eviction is **not currently available in this runtime image**. The worker accepts:

- `lru`
- `lfu`

and rejects:

- `priority`

### Experiment 1: Direct Baseline Run

**Goal**  
Run one benchmark directly against the frontend with the default async client.

**What it tests**  
End-to-end request flow, latency, cached tokens, and per-run summary generation.

**When to use it**  
Use this for the simplest benchmark run and for smoke-testing the cluster.

**Flow**

`Experiment YAML -> run_experiment.py -> shared_prefix.py -> async_loadgen.py -> Dynamo frontend -> SGLang workers -> results.jsonl + summary.json`

**Command**

Short:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin.yaml \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Long:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin_long.yaml \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Very long:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin_very_long.yaml \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

**Outputs**

- `hintbench/results/<experiment_name>_<timestamp>/`
- `metadata.json`
- `workload.jsonl`
- `results.jsonl`
- `summary.json`

**Notes / limitations**

- Uses the default `async_loadgen` client backend.
- Result timestamps default to `America/Chicago`.

---

### Experiment 2: Three-Mode Routing Suite

**Goal**  
Compare `baseline_round_robin`, `kv_router`, and `hint_routing` automatically.

**What it tests**  
Routing-mode differences across latency, cached tokens, and worker distribution.

**When to use it**  
Use this when you want a standard comparison run instead of a single benchmark.

**Flow**

`run_suite.py -> restart head per mode -> run_experiment.py x 3 -> round-robin / kv / hint runs -> comparison + analysis files`

**Command**

Short:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_suite.py \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Long:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_suite.py \
  --long \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Very long:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_suite.py \
  --very-long \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

**Outputs**

- per-run folders under `hintbench/results/`
- one suite folder under `hintbench/results/suite_<timestamp>/`
- `comparison.txt`
- `comparison.json`
- `latency.txt`
- `latency.json`
- `cached_tokens.txt`
- `cached_tokens.json`
- `worker_distribution.txt`
- `worker_distribution.json`

**Notes / limitations**

- `run_suite.py` restarts the head node between runs.
- It checks `/v1/models` before each run so invalid worker-registration states fail early.

---

### Experiment 3: Single-Host LangChain Client-Path Run

**Goal**  
Run the full single-host stack with LangChain present and no shim.

**What it tests**  
The 4-stage LangChain client path on one machine:
- request generation
- LangChain message conversion
- hint injection
- frontend-to-worker inference

**When to use it**  
Use this when you want the simplest same-host setup for:
- LangChain checkpoint logging
- hint-injection debugging
- 4-stage validation without the live shim

**Pipeline type**  
This is the **4-stage pipeline**:

`request generator -> LangChain -> Dynamo frontend -> SGLang worker`

**Flow**

`request generator -> LangChain -> Dynamo frontend on localhost -> single local SGLang worker`

**Command**

Start the single-host stack:

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh start
./run_dynamo_single_host.sh status
./run_dynamo_single_host.sh test
./run_dynamo_single_host.sh logs -f
```

Install LangChain if needed:

```bash
cd ~/kv_cache_offloading
sudo dnf install -y python3-pip
python3 -m pip install -U langchain-openai langchain-core
```

Run the LangChain experiment directly to the frontend on `8000`:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin_langchain.yaml \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Inspect the latest run:

```bash
cd ~/kv_cache_offloading
LATEST_RUN=$(ls -td hintbench/results/baseline_round_robin_langchain* | head -n 1)
echo "$LATEST_RUN"
cat "$LATEST_RUN/summary.json"
tail -n 20 "$LATEST_RUN/results.jsonl"
cat "$LATEST_RUN/metadata.json"
```

**Outputs**

- normal HintBench run directory
- LangChain checkpoint logs in the terminal running `run_experiment.py`
- single-host service logs via `./run_dynamo_single_host.sh logs`

**Notes / limitations**

- Do **not** start `live_hint_router.py` for this experiment.
- Use frontend URL `http://127.0.0.1:8000/v1/chat/completions`, not `8100`.
- This is the clearest single-host path when you want **LangChain present but no shim**.

---

### Experiment 4: LangChain Client-Path Run

**Goal**  
Run the benchmark through LangChain instead of the default async client.

**What it tests**  
How LangChain converts messages, injects `nvext.agent_hints`, and dispatches to the frontend.

**When to use it**  
Use this when you want to inspect the client-side request path and LangChain-specific instrumentation.

**Pipeline type**  
This is the **4-stage pipeline**:

`request generator -> LangChain -> Dynamo frontend -> SGLang workers`

**Flow**

`Experiment YAML -> run_experiment.py -> shared_prefix.py -> langchain_loadgen.py -> ChatOpenAI -> Dynamo frontend -> SGLang workers`

**Command**

Install LangChain:

```bash
cd ~/kv_cache_offloading
python3 -m pip install -U langchain-openai langchain-core
```

Run:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin_langchain.yaml \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Inspect the latest run:

```bash
cd ~/kv_cache_offloading
LATEST_RUN=$(ls -td hintbench/results/baseline_round_robin_langchain* | head -n 1)
echo "$LATEST_RUN"
cat "$LATEST_RUN/summary.json"
tail -n 20 "$LATEST_RUN/results.jsonl"
cat "$LATEST_RUN/metadata.json"
```

**Outputs**

- normal HintBench run directory
- stdout checkpoint logs from `langchain_loadgen.py`

**Notes / limitations**

- Uses [hintbench/clients/langchain_loadgen.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/hintbench/clients/langchain_loadgen.py).
- Current LangChain instrumentation knobs live in [hintbench/constants.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/hintbench/constants.py):
  - `REQUEST_LOG_*`
  - `CONVERTED_MESSAGE_LOG_*`
  - `HINT_INJECTION_LOG_*`
  - `REQUEST_DISPATCH_LOG_*`
- Supported log modes:
  - `single_line`
  - `compact`
  - `full`
- The LangChain path does not currently capture Dynamo-specific fields like `ttft_ms`, `kv_hit_rate`, `cached_tokens`, or `worker_id`.
- This is the clearest experiment to use when you want **LangChain present but no shim**.

Outgoing requests are OpenAI-style requests with hints attached under `nvext.agent_hints`:

```json
{
  "model": "Qwen/Qwen2.5-0.5B",
  "messages": ["..."],
  "max_tokens": 128,
  "temperature": 0.0,
  "nvext": {
    "agent_hints": {
      "priority": 5,
      "reuse_likelihood": 0.9,
      "agent_phase": "execution",
      "latency_sensitivity": 0.7,
      "program_id": "hintbench.shared_prefix",
      "context_type": "multi_turn_shared_prefix",
      "expected_output_tokens": 128
    }
  }
}
```

---

### Experiment 5: Live Hint Shim Logging Run

**Goal**  
Send traffic through the live shim and record live routing decisions.

**What it tests**  
Hint parsing, shadow policy scoring, upstream choice, actual backend worker choice, and alignment.

**When to use it**  
Use this when you want online routing observability rather than just end-to-end benchmark outputs.

**Pipeline type**  
This is the **5-stage pipeline**:

`request generator / client -> shim -> Dynamo frontend -> SGLang workers`

If you combine this with Experiment 3, the full path becomes:

`request generator -> LangChain -> shim -> Dynamo frontend -> SGLang workers`

**Flow**

`HintBench client -> live_hint_router.py -> Dynamo frontend -> SGLang workers`

Shim side output:

`live_hint_router.py -> decisions.jsonl`

Main run output:

`SGLang workers -> normal HintBench results`

**Command**

Start the shim:

```bash
cd ~/kv_cache_offloading
export HINTBENCH_UPSTREAMS_JSON='[
  {"worker_id":"frontend-a","url":"http://127.0.0.1:8000/v1/chat/completions"}
]'

python3 hintbench/runtime_patches/live_hint_router.py \
  --host 127.0.0.1 \
  --port 8100 \
  --log-file hintbench/results/live_hint_router/short_run1.jsonl
```

Run through the shim:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin.yaml \
  --frontend-url http://127.0.0.1:8100/v1/chat/completions
```

Analyze:

```bash
cd ~/kv_cache_offloading
python3 hintbench/runtime_patches/analyze_live_router_log.py \
  --log-file hintbench/results/live_hint_router/short_run1.jsonl
```

**Outputs**

- normal HintBench run directory
- `hintbench/results/live_hint_router/*.jsonl`
- live shim analysis summary

**Notes / limitations**

- With one upstream, the shim logs and scores live requests but does not override Dynamo’s internal worker choice directly.

---
