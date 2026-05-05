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

Use `g5.xlarge` or `g5.2xlarge` for workers.

Single-host GH200 mode is also supported for development.

First-time bootstrap on the GH200 host:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh rootdisk
newgrp docker
./aws/check_ec2_rootdisk_worker_ready.sh
```

Start the single-host stack:

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh start
```

Verify it:

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh status
./run_dynamo_single_host.sh logs
./run_dynamo_single_host.sh test
```

Then run HintBench against `http://127.0.0.1:8000/v1/chat/completions`.

Short run:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin.yaml \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Long run:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin_long.yaml \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Very long run:

```bash
cd ~/kv_cache_offloading
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin_very_long.yaml \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Stop the single-host stack:

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh stop
```

This is useful for local iteration, but it is not a substitute for the real two-worker setup.

## Run One Experiment

```bash
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin.yaml \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Outputs go to:

- `hintbench/results/<experiment_name>_<timestamp>/`

Each run directory contains:

- `metadata.json`
- `workload.jsonl`
- `results.jsonl`
- `summary.json`

Result timestamps default to `America/Chicago`.

Default client backend:

- `async_loadgen`

Optional LangChain backend:

- set `client_backend: langchain` in the experiment config
- install:

```bash
python3 -m pip install -U langchain-openai langchain-core
```

LangChain uses `ChatOpenAI` against the same OpenAI-compatible frontend and sends hints through `extra_body`. LangChain documents both `base_url` and `extra_body` on `ChatOpenAI`: [ChatOpenAI docs](https://api.python.langchain.com/en/latest/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html).

Quick test:

```bash
cd ~/kv_cache_offloading
python3 -m pip install -U langchain-openai langchain-core
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin_langchain.yaml \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Inspect the latest LangChain run:

```bash
cd ~/kv_cache_offloading
LATEST_RUN=$(ls -td hintbench/results/baseline_round_robin_langchain* | head -n 1)
echo "$LATEST_RUN"
cat "$LATEST_RUN/summary.json"
tail -n 20 "$LATEST_RUN/results.jsonl"
cat "$LATEST_RUN/metadata.json"
```

This uses:

- [hintbench/clients/langchain_loadgen.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/hintbench/clients/langchain_loadgen.py)
- [hintbench/experiments/baseline_round_robin_langchain.yaml](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/hintbench/experiments/baseline_round_robin_langchain.yaml)
- [hintbench/constants.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/hintbench/constants.py)

LangChain request instrumentation is controlled in `hintbench/constants.py`:

- `REQUEST_LOG_ENABLED`
- `REQUEST_LOG_EVERY`
- `REQUEST_LOG_MODE`
- `CONVERTED_MESSAGE_LOG_ENABLED`
- `CONVERTED_MESSAGE_LOG_EVERY`
- `CONVERTED_MESSAGE_LOG_MODE`
- `HINT_INJECTION_LOG_ENABLED`
- `HINT_INJECTION_LOG_EVERY`
- `HINT_INJECTION_LOG_MODE`
- `REQUEST_DISPATCH_LOG_ENABLED`
- `REQUEST_DISPATCH_LOG_EVERY`
- `REQUEST_DISPATCH_LOG_MODE`

Supported `REQUEST_LOG_MODE` values:

- `single_line`
- `compact`
- `full`

The converted-message logger uses the same three modes and prints the LangChain
message objects right after `to_langchain_messages(...)`.

The hint-injection logger uses the same three modes and prints the `extra_body`
payload right before LangChain sends `nvext.agent_hints` to the frontend.

The request-dispatch logger uses the same three modes and prints the final
frontend/model/message boundary immediately before `llm.ainvoke(...)`.

Current limitation:

- the LangChain path does not currently capture Dynamo-specific fields like `ttft_ms`, `kv_hit_rate`, `cached_tokens`, or `worker_id`
- use the default `async_loadgen` backend when you want the richest Dynamo-specific metrics

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

## Run the Standard Suite

```bash
python3 hintbench/run_suite.py \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

This runs:

- `baseline_round_robin`
- `kv_router`
- `hint_routing`

`run_suite.py` restarts the head node between runs, checks `/v1/models`, and writes:

- per-run folders under `hintbench/results/`
- one suite folder under `hintbench/results/suite_<timestamp>/`

Suite outputs include:

- `comparison.txt`
- `comparison.json`
- `latency.txt`
- `latency.json`
- `cached_tokens.txt`
- `cached_tokens.json`
- `worker_distribution.txt`
- `worker_distribution.json`

## Run the Longer Suite

```bash
python3 hintbench/run_suite.py \
  --long \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

This uses:

- `baseline_round_robin_long.yaml`
- `kv_router_long.yaml`
- `hint_routing_long.yaml`

Use the short suite for fast checks and the long suite for more stable evaluation.

## Run the Very Long Suite

```bash
python3 hintbench/run_suite.py \
  --very-long \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

This uses:

- `baseline_round_robin_very_long.yaml`
- `kv_router_very_long.yaml`
- `hint_routing_very_long.yaml`

Use this for the heaviest stability checks and the largest comparison runs.

## Compare Existing Runs

```bash
python3 hintbench/analysis/compare_runs.py \
  hintbench/results/baseline_round_robin_20260504_163703 \
  hintbench/results/kv_router_20260504_164046 \
  hintbench/results/hint_routing_20260504_164139
```

## Analysis Scripts

Latency:

```bash
python3 hintbench/analysis/plot_latency.py \
  hintbench/results/baseline_round_robin_20260505_101759 \
  hintbench/results/kv_router_20260505_101810 \
  hintbench/results/hint_routing_20260505_101816
```

Cached tokens:

```bash
python3 hintbench/analysis/plot_cached_tokens.py \
  hintbench/results/baseline_round_robin_20260505_101759 \
  hintbench/results/kv_router_20260505_101810 \
  hintbench/results/hint_routing_20260505_101816
```

Worker distribution:

```bash
python3 hintbench/analysis/plot_worker_distribution.py \
  hintbench/results/baseline_round_robin_20260505_101759 \
  hintbench/results/kv_router_20260505_101810 \
  hintbench/results/hint_routing_20260505_101816
```

## Runtime Patch Layer

Runtime-patch docs live here:

- [hintbench/runtime_patches/README.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/hintbench/runtime_patches/README.md)

Offline simulation:

```bash
python3 hintbench/runtime_patches/simulate_hint_router.py \
  --run-dir hintbench/results/baseline_round_robin_20260505_101759
```

---

# Live Hint Shim

> Advanced / optional path. Use this after the standard HintBench experiment flow is already working.

Start the shim:

```bash
export HINTBENCH_UPSTREAMS_JSON='[
  {"worker_id":"frontend-a","url":"http://127.0.0.1:8000/v1/chat/completions"}
]'

python3 hintbench/runtime_patches/live_hint_router.py \
  --host 127.0.0.1 \
  --port 8100 \
  --log-file hintbench/results/live_hint_router/short_run1.jsonl
```

Short live-shim run:

```bash
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin.yaml \
  --frontend-url http://127.0.0.1:8100/v1/chat/completions
```

Long live-shim run:

```bash
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin_long.yaml \
  --frontend-url http://127.0.0.1:8100/v1/chat/completions
```

Very long live-shim run:

```bash
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin_very_long.yaml \
  --frontend-url http://127.0.0.1:8100/v1/chat/completions
```

Analyze one live log:

```bash
python3 hintbench/runtime_patches/analyze_live_router_log.py --log-file hintbench/results/live_hint_router/short_run1.jsonl
```

Friendly backend names come from:

- [hintbench/runtime_patches/worker_name_map.json](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/hintbench/runtime_patches/worker_name_map.json)

Aggregate repeated live runs:

```bash
python3 hintbench/runtime_patches/aggregate_live_router_logs.py \
  hintbench/results/live_hint_router/run1.jsonl \
  hintbench/results/live_hint_router/run2.jsonl \
  hintbench/results/live_hint_router/run3.jsonl
```

With one upstream, the shim logs live hint-aware decisions but does not override Dynamo’s internal worker choice.

---
