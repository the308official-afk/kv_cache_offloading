# Runtime Patches

This directory is the first bridge from the benchmark harness into real runtime-side routing logic.

## Current status

The live Dynamo frontend you are running still comes from a container image, so its internal router code is not directly editable from this repo yet.

Because of that, the first implementation here is:

- a concrete hint-aware routing policy module
- an offline simulator that applies that policy to a workload
- a lightweight live routing shim that can apply the same policy to real HTTP traffic

This lets you make the routing policy explicit before you build a custom frontend image.

## Files

- `hint_router_policy.py`
  - normalizes incoming hint metadata
  - scores candidate workers
  - chooses the best worker using a transparent scoring function

- `simulate_hint_router.py`
  - replays a `workload.jsonl`
  - simulates worker choice over time
  - writes one routing decision per request

- `live_hint_router.py`
  - exposes an OpenAI-style `/v1/chat/completions` endpoint
  - chooses an upstream target using the hint-aware policy
  - forwards the request to the chosen upstream
  - logs one routing decision per live request

- `analyze_live_router_log.py`
  - reads the live decision log
  - summarizes success rate, latency, policy scores, chosen-upstream counts, and the real downstream worker IDs Dynamo returned
  - applies friendly worker names from `worker_name_map.json` when available

- `aggregate_live_router_logs.py`
  - combines several live decision logs
  - reports per-run and aggregate alignment, latency, and cache-reuse summaries

## Example

```bash
python3 hintbench/runtime_patches/simulate_hint_router.py \
  --run-dir hintbench/results/baseline_round_robin_20260505_101759
```

Live shim example:

```bash
export HINTBENCH_UPSTREAMS_JSON='[
  {"worker_id":"frontend-a","url":"http://127.0.0.1:8000/v1/chat/completions"}
]'

python3 hintbench/runtime_patches/live_hint_router.py \
  --host 127.0.0.1 \
  --port 8100
```

Then point a client at:

```text
http://127.0.0.1:8100/v1/chat/completions
```

This is the recommended first use:

- keep the stock Dynamo frontend on `127.0.0.1:8000`
- run the shim on `127.0.0.1:8100`
- point HintBench at the shim URL
- inspect the shim decision log afterward

Example:

```bash
export HINTBENCH_UPSTREAMS_JSON='[
  {"worker_id":"frontend-a","url":"http://127.0.0.1:8000/v1/chat/completions"}
]'

python3 hintbench/runtime_patches/live_hint_router.py \
  --host 127.0.0.1 \
  --port 8100
```

Then in another shell:

```bash
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin.yaml \
  --frontend-url http://127.0.0.1:8100/v1/chat/completions
```

The shim writes decisions to:

```text
hintbench/results/live_hint_router/decisions.jsonl
```

For repeated live runs, use one log file per run, for example:

```bash
python3 hintbench/runtime_patches/live_hint_router.py \
  --host 127.0.0.1 \
  --port 8100 \
  --log-file hintbench/results/live_hint_router/run1.jsonl
```

Summarize that log with:

```bash
python3 hintbench/runtime_patches/analyze_live_router_log.py
```

The analyzer defaults to:

```text
hintbench/runtime_patches/worker_name_map.json
```

so you can replace opaque Dynamo worker IDs with friendlier labels such as:

- `kv-dynamo-worker-a-g5`
- `kv-dynamo-worker-b-g5`

Aggregate several live runs with:

```bash
python3 hintbench/runtime_patches/aggregate_live_router_logs.py \
  hintbench/results/live_hint_router/run1.jsonl \
  hintbench/results/live_hint_router/run2.jsonl \
  hintbench/results/live_hint_router/run3.jsonl
```

Important:

- with only one upstream, the shim can log hint-aware decisions but cannot change the stock frontend's internal worker choice
- to affect live routing, you need multiple real upstream targets or a deeper custom frontend integration

## Why this matters

This is the first place where hint-aware routing becomes concrete instead of just conceptual.

The next step after this is to port the same policy into a custom frontend/runtime path so the live serving system can use it directly.
