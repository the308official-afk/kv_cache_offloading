# Implementation Roadmap

This file turns the high-level research strategy into concrete next steps for this repository.

Status markers:

- `Done`
- `In Progress`
- `Next`

## Phase 1: Build the benchmark harness (`Done`)

The first goal is not to patch Dynamo immediately. The first goal is to make experiments repeatable.

Add these top-level directories:

- `hintbench/workloads/`
- `hintbench/hints/`
- `hintbench/clients/`
- `hintbench/experiments/`
- `hintbench/metrics/`
- `hintbench/analysis/`
- `hintbench/results/`

Recommended purpose of each:

### `hintbench/workloads/`

Put workload generators here.

Recommended first files:

- `shared_prefix.py`
- `mixed_priority.py`
- `prefill_decode_mix.py`

These should generate request streams, not run experiments directly.

### `hintbench/hints/`

Put the request hint schema and simple hint policies here.

Recommended first files:

- `schema.json`
- `static_priority.py`
- `phase_policy.py`

The first version should stay small and deterministic.

### `hintbench/clients/`

Put the request-sending client here.

Recommended first files:

- `openai_client.py`
- `async_loadgen.py`

The client should:

- hit the head/frontend node
- attach hints in `nvext`
- emit structured results

### `hintbench/experiments/`

Put named experiment configurations here.

Recommended first files:

- `baseline_round_robin.yaml`
- `kv_router.yaml`
- `hint_routing.yaml`

Each config should define:

- router mode
- model
- workload
- concurrency
- duration or request count
- hint policy

### `hintbench/metrics/`

Put metrics collection and structured result formatting here.

Recommended first files:

- `collector.py`
- `schema.py`

This layer should normalize all experiment outputs into one format.

### `hintbench/analysis/`

Put plotting and comparison scripts here.

Recommended first files:

- `plot_latency.py`
- `plot_cached_tokens.py`
- `plot_worker_distribution.py`

### `hintbench/results/`

Store experiment outputs here.

Recommended structure:

- one subdirectory per experiment run
- include:
  - raw JSONL request records
  - summary JSON
  - plots

## Phase 2: Define the first request/result schema (`Done`)

The first version of the client harness should record one structured result per request.

Minimum request fields:

- `request_id`
- `experiment_name`
- `workload_name`
- `router_mode`
- `model`
- `prompt_id`
- `shared_prefix_group`
- `hint_payload`

Minimum response/result fields:

- `success`
- `status_code`
- `error`
- `latency_ms`
- `ttft_ms` if available
- `completion_tokens`
- `prompt_tokens`
- `cached_tokens`
- `worker_id` if observable
- `timestamp`

This is the minimum data needed for useful comparisons.

## Phase 3: Implement the first workload (`Done`)

Implement `hintbench/workloads/shared_prefix.py` first.

It should generate:

- one shared system prompt
- multiple user prompts that branch from that prefix
- multi-turn sequences

This is the best workload for:

- cache reuse
- worker locality
- routing experiments

The first version can be synthetic and small.

## Phase 4: Implement the first client harness (`Done`)

Implement `hintbench/clients/async_loadgen.py` next.

It should:

- send async requests to the head node
- support configurable concurrency
- attach `nvext` hints
- store one JSONL result record per request

The client should not depend on Dynamo internals.

It should treat the frontend as a normal OpenAI-style API.

## Phase 5: First experiment configs (`Done`)

Add these first:

### `baseline_round_robin.yaml`

Purpose:

- establish end-to-end behavior with no KV-routing intelligence

Use:

- `round-robin`
- shared-prefix workload
- no advanced hints

### `kv_router.yaml`

Purpose:

- compare against KV-aware routing

Use:

- `kv`
- shared-prefix workload
- same load shape as baseline

### `hint_routing.yaml`

Purpose:

- compare hint-driven request metadata against plain KV mode

Use:

- same workload
- controlled hints such as:
  - priority
  - reuse likelihood
  - agent phase

## Phase 6: First analysis outputs (`Done`)

The first plots should answer:

- does routing reduce latency?
- does routing improve cache reuse?
- do requests concentrate on workers with locality?

First three plots:

1. latency distribution by router mode
2. cached tokens by router mode
3. request count by worker

These are enough for the first serious comparison.

## Phase 7: First runtime patch target (`In Progress`)

Do not patch everything at once.

The first runtime-side patch target should be:

- hint-aware routing logic

That means:

- inspect incoming `nvext`
- attach normalized request metadata
- influence worker selection

This should come only after the harness can compare:

- round-robin
- KV-aware
- hint-aware

Current Phase 7 status:

- offline hint-aware routing policy scaffold exists
- offline simulator exists
- live hint-routing shim exists
- live decision logging exists
- policy-vs-actual backend comparison exists

Still remaining for Phase 7:

- move from live observation to stronger live routing influence
- reduce `unknown` shadow choices at the start of runs
- decide whether to add a multi-run live-log aggregator before deeper routing control
- decide whether the next control step should be:
  - a stronger shim-based live experiment
  - or a deeper custom frontend/runtime integration

## Phase 8: Second runtime patch target (`Next`)

After routing is measurable, implement:

- cache-value scoring

This should initially be simple and transparent.

Example inputs:

- priority
- shared-prefix reuse score
- expected output length
- recency

The first version should be heuristic, not learned.

## Phase 9: Learned or genetic hint layer

Only after the heuristic layer is measurable should the project attempt:

- learned hint generation
- genetic-hint compilation

At that point the main question becomes:

- can an upstream hint policy emit better routing and cache signals than static heuristics?

## First concrete coding tasks

These are the recommended first implementation tasks for this repo:

1. create the `hintbench/` directory tree
2. implement `hintbench/workloads/shared_prefix.py`
3. implement `hintbench/clients/async_loadgen.py`
4. implement `hintbench/metrics/collector.py`
5. add `baseline_round_robin.yaml`
6. add `kv_router.yaml`
7. add `hint_routing.yaml`
8. add `plot_latency.py`
9. add `plot_cached_tokens.py`
10. add `plot_worker_distribution.py`

## First concrete research milestone

The first milestone for the repo should be:

**Show whether routing mode changes TTFT and cache reuse under a shared-prefix workload.**

This is a strong first milestone because it is:

- realistic
- measurable
- close to your current infrastructure
- a necessary foundation for the more ambitious ideas

## What not to do first

Avoid these too early:

- learned routing models
- full compiler work
- heterogeneous GPU experiments
- complex multi-tier KV placement logic

Those all become much easier once the benchmark harness exists.

## Recommended near-term execution order

The practical order for the next implementation sprint is:

1. build the `hintbench/` skeleton
2. build the first workload generator
3. build the async request client
4. build the metrics collector
5. compare `round-robin` vs `kv`
6. only then patch hint-aware routing

## Phase 1.5

After the Phase 1 scaffold exists, add a single runner that ties together:

- workload generation
- request execution
- metrics collection

The first runner should:

- read one experiment config
- write a workload JSONL file
- run the async client harness
- produce a summary JSON

That runner now lives at:

- `hintbench/run_experiment.py`
