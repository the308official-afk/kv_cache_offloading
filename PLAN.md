# Research Plan

This file is the high-level research strategy for turning the current Dynamo + SGLang setup into a platform for hint-guided LLM serving research.

## Goal

Build a reproducible evaluation environment that supports research on:

1. hint-aware prefill/decode routing
2. cache-value functions for eviction and placement
3. hint-guided KV memory hierarchy
4. asynchronous KV prefetching
5. heterogeneous GPU routing
6. a genetic-hint compiler

## Practical Priority Order

This is the recommended implementation order for the project:

1. hint-aware prefill/decode routing
2. cache-value function for eviction/placement
3. hint-guided KV memory hierarchy
4. asynchronous KV prefetching
5. heterogeneous GPU routing
6. genetic-hint compiler

## Why This Order

### 1. Hint-aware prefill/decode routing

Start here because it:

- fits Dynamo’s architecture naturally
- is easy to measure
- can improve TTFT and utilization quickly
- does not require solving the full KV hierarchy first

Core question:

- if a request advertises that it is prefill-heavy or decode-heavy, can routing improve latency or efficiency?

### 2. Cache-value function for eviction/placement

This should become the central abstraction of the project.

The basic idea:

`value(KV block) = f(priority, reuse_probability, recency, size, future_turn_likelihood, SLA)`

Once this exists, it can drive:

- eviction
- placement
- prefetch
- route bias

### 3. Hint-guided KV memory hierarchy

This becomes much more meaningful after the system can estimate KV value.

Main questions:

- which KV stays on GPU?
- which moves to CPU?
- which spills to NVMe?
- which should be dropped?

### 4. Asynchronous KV prefetching

This should come after routing and cache-value work.

It depends on having at least a rough notion of:

- future-turn likelihood
- reuse probability
- which KV is worth warming early

### 5. Heterogeneous GPU routing

This becomes more useful once the project has:

- multiple GPU types
- differentiated routing logic
- stable observability

Main questions:

- which requests belong on which accelerator?
- which workers should handle prefill-heavy vs decode-heavy requests?

### 6. Genetic-hint compiler

Do not start here.

Build this after learning:

- which hints are predictive
- which hints actually improve runtime decisions
- which hint schema the serving stack can consume well

The compiler should be the formalization of what the earlier phases discover.

## Recommended System Layers

To support all six directions, build the system in layers.

### Layer 1: Stable serving substrate

Base platform:

- 1 head node
- 2 worker nodes
- Dynamo frontend
- SGLang workers
- reproducible AWS setup scripts
- both `round-robin` and `kv` routing modes available

This is the infrastructure base.

### Layer 2: Measurement substrate

Before adding new scheduling ideas, add structured measurement.

At minimum, capture:

- request id
- workload type
- hint values
- router mode
- chosen worker
- TTFT
- end-to-end latency
- output tokens
- cached tokens
- error/timeout outcome

Without this layer, it will be hard to compare research ideas rigorously.

### Layer 3: Workload harness

Build a small set of synthetic workloads first.

Recommended initial workloads:

1. shared-prefix multi-turn workload
2. mixed-priority workload
3. prefill/decode imbalance workload

These are enough to begin meaningful comparisons.

### Layer 4: Hint schema

Define a small stable request-hint schema early.

Recommended initial fields:

- `priority`
- `latency_sla_ms`
- `expected_output_tokens`
- `reuse_likelihood`
- `agent_phase`
- `cache_policy`
- `prefill_weight`
- `decode_weight`

Keep the schema small at first.

### Layer 5: First research direction

Implement:

- hint-aware prefill/decode routing

This should be the first experimental focus.

### Layer 6: Core cache abstraction

Implement:

- cache-value function

This becomes the foundation for later work.

### Layer 7: KV hierarchy and beyond

Then expand into:

- KV placement across GPU/CPU/NVMe
- prefetching
- heterogeneous worker routing
- hint compilation

## First Recommended Experiment

### Main question

Can hint-aware routing improve TTFT and cache reuse on shared-prefix agent workloads?

### Experimental setup

- 1 head/frontend node
- 2 workers
- same model on both workers
- shared-prefix multi-turn workload

### Compare

- round-robin routing
- KV-aware routing
- hint-aware routing

### Measure

- TTFT
- end-to-end latency
- p95/p99 latency
- cached token reuse
- worker choice
- recomputation avoided

### Why this should be first

It is:

- measurable
- directly tied to your current infrastructure
- close to the strongest research directions in the literature
- a good platform for later papers or benchmark claims

## What the Current Setup Can Support

The current multi-node Dynamo + SGLang setup is best suited to:

- testing frontend-to-worker routing
- comparing router modes
- measuring cache reuse under shared-prefix workloads
- evaluating prompt-level QoS / semantic scheduling
- building a benchmark harness on top of a real distributed serving stack

## Simple Decision Rule

When choosing what to implement next, prefer work that:

- uses the current infrastructure directly
- produces measurable differences
- improves the ability to compare scheduling decisions
- strengthens the benchmark harness

That is why the next two best steps are:

1. build the benchmark and metrics layer
2. implement hint-aware prefill/decode routing experiments

## Short Version

The practical research sequence is:

1. make the infrastructure measurable
2. test hint-aware routing first
3. build a cache-value function
4. use that to drive placement, eviction, and prefetch
5. expand to heterogeneous routing
6. formalize everything into a genetic-hint compiler
