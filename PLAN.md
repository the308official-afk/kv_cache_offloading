# Research Plan

This file is the current research strategy for turning the Dynamo + SGLang + AgentBench setup into a platform for hardware-aware LLM serving research.

The guiding goal is no longer just "make the serving stack work." The goal is to learn enough about request behavior, KV behavior, and scheduling behavior to make smarter future hardware decisions around:

- GPU size and count
- CPU and host-memory capacity
- local storage / NVMe usage
- worker specialization
- mixed-hardware deployments

## Main Goal

Build a reproducible evaluation environment that helps answer:

- what part of the serving path is actually the bottleneck?
- which requests deserve the fastest hardware?
- which KV should stay on GPU versus move elsewhere?
- when does more GPU help more than more CPU, RAM, or storage?
- how should different hardware classes be used once the cluster grows?

## Research Directions

The current recommended research directions are:

1. measurement substrate
2. cache-value function for eviction and placement
3. hint-guided KV memory hierarchy
4. hint-aware prefill/decode routing
5. heterogeneous GPU routing
6. asynchronous KV prefetching
7. genetic-hint compiler

## Why This Order

### 1. Measurement substrate

Start here first.

Before changing hardware or routing policies, the system needs to reveal what is actually happening during serving.

This layer should help answer:

- where is time being spent?
- where does memory pressure come from?
- which workloads are prefill-heavy?
- which workloads are decode-heavy?
- which requests show reuse and which do not?

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
- error / timeout outcome

Without this layer, later hardware or routing decisions will be guesswork.

### 2. Cache-value function for eviction and placement

This should become the central abstraction of the project.

The key idea is to assign a value to each KV block or reusable request state:

`value(KV block) = f(priority, reuse_probability, recency, size, future_turn_likelihood, SLA)`

This layer should help answer:

- what is worth keeping on expensive memory?
- what can be evicted first?
- what should bias routing decisions?
- what should be retained for likely follow-up turns?

This research direction matters for future hardware decisions because it tells you what the system actually wants fast memory for.

### 3. Hint-guided KV memory hierarchy

This is the most directly hardware-relevant research direction.

Once the system can estimate KV value, the next question is where that KV should live:

- GPU memory
- CPU memory
- local SSD / NVMe
- nowhere, if it should be dropped

This layer should help answer:

- which KV must stay on GPU?
- which KV can be spilled safely?
- which requests justify expensive residency?
- what memory tier is actually limiting performance?

This direction is especially important if the long-term goal includes hardware upgrades, because it informs whether you need more GPU memory, more host memory, faster storage, or better movement policies.

### 4. Hint-aware prefill/decode routing

This is the first major scheduling direction.

The core question is:

- if a request advertises that it is prefill-heavy or decode-heavy, can routing improve latency or efficiency?

This layer should help answer:

- should certain requests go to specific workers?
- should planning / prefill-heavy / decode-heavy phases be treated differently?
- can hints improve TTFT, throughput, or utilization?

This matters for future hardware planning because it can reveal whether different workers should specialize by request shape rather than all workers being treated the same.

### 5. Heterogeneous GPU routing

This becomes important once the cluster contains different hardware classes.

The main question is:

- which requests belong on which accelerator?

This layer should help answer:

- which requests deserve premium GPUs?
- which requests can run on cheaper hardware?
- when is a larger GPU actually worth the cost?
- how should prefill-heavy and decode-heavy workloads be assigned in a mixed cluster?

This is the direction that most directly turns hint-aware scheduling into hardware-aware scheduling.

### 6. Asynchronous KV prefetching

This should come after routing and cache-value work.

It depends on already having some estimate of:

- reuse probability
- future-turn likelihood
- which KV is worth warming early

This layer should help answer:

- can the system move useful KV before it is urgently needed?
- can certain latency spikes be avoided by warming likely future state?
- when is prefetch worth the movement cost?

This is a useful optimization layer, but it should follow the more foundational measurement, value, and hierarchy work.

### 7. Genetic-hint compiler

Do not start here.

This should come after the earlier stages teach you:

- which hints are predictive
- which hints improve runtime decisions
- which hint schema the serving stack can actually consume well

The compiler should become the formalization layer that turns observed request structure into a compact, useful hint program for the runtime.

This is valuable eventually, but only after the system already knows what hint-guided behavior is worth expressing.

## Recommended System Layers

To support these directions, build the system in layers.

### Layer 1: Stable serving substrate

Base platform:

- Dynamo frontend
- SGLang workers
- reproducible AWS setup scripts
- both `round-robin` and `kv` routing modes available

This is the infrastructure base.

### Layer 2: Measurement substrate

Before adding new hardware-aware scheduling ideas, add structured measurement and logging.

This is the foundation for every later comparison.

This layer should now explicitly include two views of the world:

1. the **policy-side view**
   - what AgentBench recommends
   - what cache-value scoring recommends
   - what KV hierarchy scoring recommends

2. the **runtime-side view**
   - what Dynamo / SGLang actually did
   - whether KV was reused
   - whether KV stayed hot
   - whether KV was evicted, spilled, fetched, or recomputed

### Layer 3: Workload harness

Use AgentBench plus a small set of synthetic workloads.

Recommended initial workloads:

1. shared-prefix multi-turn workload
2. mixed-priority workload
3. prefill/decode imbalance workload

These are enough to begin meaningful scheduling and memory experiments.

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

### Layer 5: Hardware-relevant scheduling

Implement:

- hint-aware prefill/decode routing
- cache-value scoring

This is where the system starts learning what kind of hardware different requests really need.

### Layer 6: Memory hierarchy

Implement:

- KV placement across GPU / CPU / NVMe
- prefetch policies

This is where memory-tier decisions become explicit.

This layer should not stop at recommending placements.

It should also compare:

- `recommended_tier`
vs
- `actual_runtime_behavior`

so the system can tell whether the current runtime is behaving like the policy expects.

### Layer 7: Hardware specialization

Then expand into:

- heterogeneous GPU routing
- later hint compilation

This is where the system starts turning serving knowledge into hardware-aware cluster policy.

## First Recommended Experimental Focus

### Main question

Can the current setup measure enough about request shape, token behavior, and reuse to support future hardware decisions?

### First practical goals

1. make the infrastructure measurable
2. shape workloads into useful categories
3. score request / KV value
4. test hint-aware routing policies

### Why this should be first

It is:

- directly useful now
- compatible with single-GPU and multi-worker setups
- necessary before making hardware changes
- the foundation for deciding whether future gains should come from more GPU, more CPU/RAM, faster storage, or smarter scheduling

## What the Current Setup Can Support

### With the current single-GPU setup

You can already do solid work on:

- measurement substrate
- workload harness
- hint schema refinement
- early cache-value-function design

You can also start partial work on:

- hint-aware prefill/decode analysis
- local KV hierarchy policy
- trace-driven prefetch design

### With a 1 frontend + 2 workers setup

You can start stronger work on:

- measurement substrate
- workload harness
- hint-aware prefill/decode routing
- hint schema refinement
- cache-value scoring

You can also begin partial but meaningful work on:

- hint-guided KV hierarchy
- asynchronous KV prefetching

And if the workers differ in hardware class, you can begin:

- heterogeneous GPU routing

## Runtime Alignment Requirement

As the project moves beyond measurement and into cache-value and KV-hierarchy work, the system must be able to compare:

- what the policy recommends
- what the runtime actually chose

Without this comparison, the research stack can only produce hypotheses, not validated placement conclusions.

### Recommended alignment fields

The runtime-side logging should eventually expose, per request or per phase:

- request id
- phase / workload type
- chosen worker
- cache hit / miss outcome
- cached token count
- whether KV was kept on GPU
- whether KV was moved to CPU
- whether KV was moved to NVMe or other cold tier
- whether KV was recomputed instead of fetched
- whether an eviction happened
- whether a fetch-from-cold-storage happened
- latency impact of the runtime decision, if measurable

### Comparison target

Each run should eventually support a direct comparison between:

- `recommended_tier`
- `actual_tier`
- `recommended_keep_or_evict`
- `actual_keep_or_evict`

This will make it possible to answer questions like:

- when does the runtime agree with the policy?
- when does the runtime choose something else?
- when the runtime disagrees, is it faster or slower?
- what hardware tier is under-serving high-value KV?
- which policy assumptions are wrong?

### Why this matters

This alignment layer is especially important for hardware research.

It is the bridge between:

- software-side placement recommendations
and
- real runtime memory behavior

Without it, the system can say:

- "this phase should stay on GPU"

but cannot say:

- "the worker actually kept it on GPU"
- "the worker moved it to CPU"
- "the worker recomputed it instead"

### Practical next logging target

The next observability milestone should be:

1. keep the current AgentBench-side files:
   - `measurements.json`
   - `cache_value_analysis.json`
   - `kv_hierarchy_analysis.json`

2. add runtime-side worker/frontend logs or metrics that record:
   - actual cache reuse
   - actual eviction / retention decisions
   - actual memory-tier behavior

3. build a comparison layer that joins:
   - policy recommendation
   - runtime action
   - latency outcome

This should become part of the normal benchmark artifact set.

## Proposed Runtime Log Schema

To make the runtime-alignment layer concrete, the next observability target should be a per-request or per-phase runtime log record with a stable JSON shape.

### Suggested artifact

Recommended filename pattern:

- `runtime_events.jsonl`

Recommended style:

- one JSON object per request or request-phase
- emitted by the Dynamo frontend and/or worker side
- joinable with AgentBench artifacts using request id and phase

### Proposed JSON shape

```json
{
  "timestamp": "2026-05-11T16:30:00.000Z",
  "request_id": "req_123",
  "parent_run_id": "instance_NodeBB__NodeBB-...",
  "task_instance_id": "instance_NodeBB__NodeBB-...",
  "phase": "step_4_execution",
  "worker_id": "worker-0",
  "worker_host": "ip-172-31-xx-xx",
  "model_name": "Qwen/Qwen2.5-7B-Instruct",
  "router_mode": "kv",
  "request_hints": {
    "priority": 5,
    "reuse_likelihood": 0.9,
    "agent_phase": "step_4_execution",
    "latency_sensitivity": 0.7,
    "expected_output_tokens": 768
  },
  "cache": {
    "cache_hit": true,
    "cached_token_count": 8064,
    "reused_prefix_tokens": 8064,
    "recomputed_prefix_tokens": 996
  },
  "placement": {
    "actual_tier": "gpu",
    "stayed_on_gpu": true,
    "moved_to_cpu": false,
    "moved_to_nvme": false,
    "fetched_from_cpu": false,
    "fetched_from_nvme": false,
    "recomputed_instead_of_fetch": false
  },
  "eviction": {
    "eviction_happened": false,
    "evicted_block_count": 0,
    "evicted_token_estimate": 0,
    "eviction_reason": null
  },
  "latency": {
    "ttft_ms": 1200.0,
    "end_to_end_ms": 22068.8,
    "prefill_ms": 18000.0,
    "decode_ms": 4068.8,
    "fetch_ms": 0.0,
    "recompute_ms": 0.0
  }
}
```

### Field groups and intended sources

#### 1. Identity fields

Fields:

- `timestamp`
- `request_id`
- `parent_run_id`
- `task_instance_id`
- `phase`

Likely source:

- AgentBench can provide:
  - `parent_run_id`
  - `task_instance_id`
  - `phase`
- Dynamo or worker runtime should provide:
  - `timestamp`
  - `request_id`

Purpose:

- lets the runtime record be joined back to:
  - `measurements.json`
  - `cache_value_analysis.json`
  - `kv_hierarchy_analysis.json`

#### 2. Worker identity fields

Fields:

- `worker_id`
- `worker_host`
- `model_name`
- `router_mode`

Likely source:

- Dynamo frontend:
  - `router_mode`
  - chosen worker identity
- Worker runtime:
  - actual worker id / host
  - actual model name

Purpose:

- tells you where the request really ran

#### 3. Request hint fields

Fields:

- `request_hints`

Likely source:

- Dynamo frontend request body, especially:
  - `nvext.agent_hints`

Purpose:

- lets you compare:
  - requested policy intent
  - actual runtime behavior

#### 4. Cache behavior fields

Fields:

- `cache_hit`
- `cached_token_count`
- `reused_prefix_tokens`
- `recomputed_prefix_tokens`

Likely source:

- worker-side model runtime
- Dynamo worker integration if cache accounting is surfaced there

Purpose:

- tells you how much of the request actually benefited from reuse

#### 5. Placement fields

Fields:

- `actual_tier`
- `stayed_on_gpu`
- `moved_to_cpu`
- `moved_to_nvme`
- `fetched_from_cpu`
- `fetched_from_nvme`
- `recomputed_instead_of_fetch`

Likely source:

- worker-side KV manager
- offload / fetch path instrumentation

Purpose:

- this is the key group for comparing:
  - `recommended_tier`
  - `actual_tier`

#### 6. Eviction fields

Fields:

- `eviction_happened`
- `evicted_block_count`
- `evicted_token_estimate`
- `eviction_reason`

Likely source:

- worker-side KV cache manager

Purpose:

- makes eviction behavior visible instead of inferred

#### 7. Latency fields

Fields:

- `ttft_ms`
- `end_to_end_ms`
- `prefill_ms`
- `decode_ms`
- `fetch_ms`
- `recompute_ms`

Likely source:

- Dynamo frontend:
  - request start/end
  - TTFT if exposed
- worker runtime:
  - prefill/decode timing
  - fetch/recompute timing

Purpose:

- shows the runtime cost of the actual placement/cache decision

### Comparison join target

Once the runtime schema exists, each request-phase can be compared across:

- AgentBench policy side:
  - `cache_value_score`
  - `recommended_tier`
  - `keep_recommendation`

- runtime side:
  - `actual_tier`
  - `cache_hit`
  - `recomputed_instead_of_fetch`
  - `eviction_happened`
  - latency outcome

### First practical implementation target

The first version does not need every field.

The minimum useful runtime log schema should include:

- `timestamp`
- `request_id`
- `phase`
- `worker_id`
- `model_name`
- `request_hints`
- `cache_hit`
- `cached_token_count`
- `actual_tier`
- `recomputed_instead_of_fetch`
- `eviction_happened`
- `ttft_ms`
- `end_to_end_ms`

That minimum version would already be enough to begin policy-vs-runtime comparisons.

### Source-Controlled Runtime Instrumentation Path

For the long-term version of this work, do not rely only on parsing stock container logs.

Use a source-controlled runtime path:

1. obtain upstream runtime source
2. apply a tracked instrumentation patch
3. build custom frontend and worker images
4. run existing Dynamo scripts against those images with runtime JSON logging enabled

That path should become the standard workflow for runtime-side alignment because it makes:

- `request_id` propagation explicit
- frontend dispatch events explicit
- router worker-selection events explicit
- worker-side attach / completion events explicit

In this repo, that workflow now lives under:

- [runtime_instrumentation/README.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/README.md)
- [runtime_instrumentation/fetch_dynamo_source.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/fetch_dynamo_source.sh)
- [runtime_instrumentation/apply_runtime_json_logging_patch.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/apply_runtime_json_logging_patch.sh)
- [runtime_instrumentation/build_instrumented_dynamo_images.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/build_instrumented_dynamo_images.sh)
- [runtime_instrumentation/patches/dynamo_runtime_json_logging.patch](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/runtime_instrumentation/patches/dynamo_runtime_json_logging.patch)

The expected runtime toggle is:

- `DYN_RUNTIME_JSON_LOGS=1`

and the expected image override path is:

- `FRONTEND_IMAGE=<custom frontend image>`
- `WORKER_IMAGE=<custom sglang image>`

## Simple Decision Rule

When choosing what to implement next, prefer work that:

- helps explain current bottlenecks
- produces measurable differences
- clarifies what hardware matters most
- strengthens the benchmark and metrics layer
- improves future placement or routing decisions

## Short Version

The practical research sequence is:

1. make the system measurable
2. learn how to score request / KV value
3. study KV placement across memory tiers
4. test hint-aware routing
5. specialize routing for mixed hardware later
6. add prefetch and hint compilation after the earlier layers mature

## Related Research Threads

The following papers and systems are especially relevant to the current plan.

### Measurement substrate

Best fit:

- Prompt Cache
- KVFlow
- LMCache

Why they matter:

- they suggest what to measure around prefix reuse, cache hits, re-prefill behavior, prompt growth, and fetch-versus-recompute tradeoffs

Useful links:

- [Prompt Cache: Modular Attention Reuse for Low-Latency Inference](https://www.sciencestack.ai/paper/2311.04934v2)
- [KVFlow: Efficient Prefix Caching for Agentic Workflows](https://openreview.net/pdf/2c47adb29432f99879fceb1371b72f6e97e1f3ac.pdf)
- [LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference](https://huggingface.co/papers/2510.09665)

### Cache-value function for eviction and placement

Best fit:

- LMCache
- Learned Prefix Caching
- KVFlow

Why they matter:

- they motivate value signals such as reuse likelihood, future-turn likelihood, cache fetch cost, and whether prefix state is worth retaining

Useful links:

- [LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference](https://huggingface.co/papers/2510.09665)
- [Learned Prefix Caching for Efficient LLM Inference](https://openreview.net/pdf/a340edd38ffafcfd1843a7f71d85464d9fb3e3df.pdf)
- [KVFlow: Efficient Prefix Caching for Agentic Workflows](https://openreview.net/pdf/2c47adb29432f99879fceb1371b72f6e97e1f3ac.pdf)

### Hint-guided KV memory hierarchy

Best fit:

- LMCache
- ContiguousKV
- ShadowServe

Why they matter:

- they focus on where KV should live, how it should move, and how to reduce the cost of fetches and offloading across memory/storage tiers

Useful links:

- [LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference](https://huggingface.co/papers/2510.09665)
- [ContiguousKV: Accelerating LLM Prefill with Granularity-Aligned KV Cache Management](https://arxiv.org/abs/2601.13631)
- [ShadowServe: Interference-Free KV Cache Fetching for Distributed Prefix Caching](https://xyxiang7.github.io/files/shadowserve_preprint.pdf)

### Hint-aware prefill/decode routing

Best fit:

- KVFlow
- Prompt Cache
- CacheBlend

Why they matter:

- they frame routing decisions around prefix reuse, prompt structure, and whether a request should prefer a worker that already holds useful state

Useful links:

- [KVFlow: Efficient Prefix Caching for Agentic Workflows](https://openreview.net/pdf/2c47adb29432f99879fceb1371b72f6e97e1f3ac.pdf)
- [Prompt Cache: Modular Attention Reuse for Low-Latency Inference](https://www.sciencestack.ai/paper/2311.04934v2)
- [CacheBlend](https://www.microsoft.com/en-us/research/wp-content/uploads/2024/09/eurosys25-final999.pdf)

### Heterogeneous GPU routing

Best fit:

- LMCache
- ShadowServe
- ContiguousKV

Why they matter:

- they do not directly solve heterogeneous routing, but they help explain which requests benefit most from premium memory paths or stronger devices

Useful links:

- [LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference](https://huggingface.co/papers/2510.09665)
- [ShadowServe: Interference-Free KV Cache Fetching for Distributed Prefix Caching](https://xyxiang7.github.io/files/shadowserve_preprint.pdf)
- [ContiguousKV: Accelerating LLM Prefill with Granularity-Aligned KV Cache Management](https://arxiv.org/abs/2601.13631)

### Asynchronous KV prefetching

Best fit:

- LMCache
- ShadowServe
- ContiguousKV

Why they matter:

- they connect reuse prediction and memory movement, which is exactly the foundation needed for prefetching useful KV before a request urgently needs it

Useful links:

- [LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference](https://huggingface.co/papers/2510.09665)
- [ShadowServe: Interference-Free KV Cache Fetching for Distributed Prefix Caching](https://xyxiang7.github.io/files/shadowserve_preprint.pdf)
- [ContiguousKV: Accelerating LLM Prefill with Granularity-Aligned KV Cache Management](https://arxiv.org/abs/2601.13631)

### Genetic-hint compiler

Best fit:

- Learned Prefix Caching
- KVShare
- KVFlow

Why they matter:

- they suggest learned or semantic policies that could eventually inform a compiler for producing better runtime hints from workload structure

Useful links:

- [Learned Prefix Caching for Efficient LLM Inference](https://openreview.net/pdf/a340edd38ffafcfd1843a7f71d85464d9fb3e3df.pdf)
- [KVShare: Semantic-Aware Key-Value Cache Sharing for Efficient Large Language Model Inference](https://arxiv.org/abs/2503.16525)
- [KVFlow: Efficient Prefix Caching for Agentic Workflows](https://openreview.net/pdf/2c47adb29432f99879fceb1371b72f6e97e1f3ac.pdf)

### Prompt compression as a cross-cutting thread

Best fit:

- LongLLMLingua
- Characterizing Prompt Compression Methods for Long Context Inference
- CompLLM

Why they matter:

- these are not exactly routing or cache-value papers, but they are directly relevant to reducing how much repeated context each request carries through the system

Useful links:

- [LongLLMLingua](https://huggingface.co/papers/2310.06839)
- [Characterizing Prompt Compression Methods for Long Context Inference](https://huggingface.co/papers/2407.08892)
- [CompLLM](https://huggingface.co/papers/2509.19228)

## Active Experiment: LPX Decode Split

The first concrete experiment for the NVIDIA/Groq LPX-style hardware question is:

```text
experiments/lpx_decode_split/run_decode_sweep.py
```

This experiment does not require Groq LPU hardware. It uses the current
Dynamo/SGLang setup to generate trace evidence for a later "what if FFN moved
to LPU?" model.

Initial question:

```text
As agentic prompt/context length and output length change, does latency behave
more like attention/KV pressure or more like per-token decode/FFN pressure?
```

The experiment varies:

- prompt token target
- requested output tokens
- repeat count

It records:

- latency
- prompt tokens
- completion tokens
- cached tokens when reported by the runtime
- `nvext.agent_hints` probe ids for worker-log joins

This is the first step toward a bolder hardware model:

```text
observed_decode_latency
  = attention/KV component
  + FFN/MoE component
  + scheduling/runtime overhead
```

Once this sweep is stable, pair the same runs with `nsys`/`ncu` and classify
kernels into:

- attention / KV-cache movement
- FFN / GEMM / activation
- runtime overhead

The first profiling wrapper is:

```text
experiments/lpx_decode_split/profile_one_decode_case.sh
```

The first kernel classifier is:

```text
experiments/lpx_decode_split/analyze_nsys_sqlite.py
```

The first GPU+LPU what-if estimator is:

```text
experiments/lpx_decode_split/estimate_lpx_speedup.py
```

This makes the immediate research posture:

```text
Assume GPU+LPU split is compelling.
Measure the attention/KV and FFN/MLP shares directly.
Then estimate the payoff of moving FFN/MLP to LPU under transfer-cost assumptions.
```
