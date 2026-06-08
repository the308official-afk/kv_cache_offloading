# Agentic Hardware Publications

Short notes on papers and technical writeups related to efficient hardware and
systems for agentic harness workloads.

## ThunderAgent: A Simple, Fast and Program-Aware Agentic Inference System

Core idea: Treat an AI agent run as one long-running program, not as many
separate model requests. The system tracks whether the agent is thinking,
waiting on a tool, or finished, so it can protect useful KV cache, avoid
recomputing long histories, balance GPU memory, and clean up tool environments.

## NVIDIA Dynamo: Full-Stack Optimizations for Agentic Inference

Core idea: Agent workloads reuse the same growing conversation history again
and again. Dynamo tries to keep that history's KV cache warm and route later
agent calls back to places where the cache can be reused, instead of making the
model reread the same prefix every time.

## Tetris: Efficient and Predictive KV Cache Offloading for Agentic and Reasoning Workloads

Core idea: Long agent and reasoning runs can fill GPU memory with KV cache.
When memory gets tight, Tetris predicts which runs will need a lot more cache
and decides whether to move KV cache to CPU memory or recompute it later. For
long runs, saving and reloading the cache is often better than throwing it away.
The prediction is updated during generation using a small model that reads LLM
hidden states, so the scheduler can start moving KV cache before memory is
fully exhausted.

## Efficient Multi-round LLM Inference over Disaggregated Serving

Core idea: Agent and retrieval workloads do not have just one prefill followed
by one decode. After each tool or retrieval result, the system gets a new small
prefill step before decoding continues. AMPD decides in real time whether each
of these prefill steps should run on a prefill worker or on the decode worker,
so the system avoids both slow first-token latency and decode slowdowns.

## Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving

Core idea: Make KV cache the center of the serving system. Mooncake separates
prefill and decode workers, but also uses CPU memory and SSD as extra places to
store KV cache. Its scheduler tries to keep useful KV cache available while
meeting latency goals, instead of treating KV cache as a temporary byproduct of
model execution.

## DistServe: Disaggregating Prefill and Decoding for Goodput-optimized LLM Serving

Core idea: Reading the prompt and generating tokens stress the system in
different ways. DistServe puts prefill and decode on different GPU groups so a
long prompt does not slow down token generation for other requests, and busy
decoding does not delay the first token for new requests.

## P/D-Serve: Serving Disaggregated Large Language Model at Scale

Core idea: Split prompt reading and token generation at cluster scale, then keep
adjusting how much hardware is assigned to each side. P/D-Serve models the
whole prefill/decode pipeline, routes work to avoid idle or overloaded workers,
and optimizes KV-cache transfer between the two sides.

## Revisiting Disaggregated Large Language Model Serving for Performance and Energy Implications

Core idea: Splitting prefill and decode is not automatically better. The gain
depends on request load, how fast KV cache can move between workers, and the
energy cost of using separate hardware. The paper is a warning to measure the
full system before assuming disaggregation saves time or power.

## SGLang: Efficient Execution of Structured Language Model Programs

Core idea: Many LLM applications are programs with repeated prompts, branches,
tool calls, and structured outputs. SGLang gives those programs a runtime that
can reuse shared KV cache with RadixAttention and speed up constrained outputs,
instead of treating every model call as a separate plain chat request.

## Hydragen: High-Throughput LLM Inference with Shared Prefixes

Core idea: When many requests start with the same long prompt, do not make each
request read the shared KV cache separately. Hydragen splits attention into the
shared prefix part and the per-request suffix part, so the shared work can be
batched into faster hardware-friendly operations.

## FlashInfer: Efficient and Customizable Attention Engine for LLM Inference Serving

Core idea: Real serving workloads have many attention shapes, KV-cache layouts,
and batching patterns. FlashInfer provides fast, customizable GPU kernels for
these cases, so serving systems like SGLang and vLLM can run attention and
related inference steps efficiently instead of relying on one generic kernel.

## FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-precision

Core idea: Modern Hopper GPUs can move data and do matrix math at the same
time, but older attention kernels do not fully use that ability. FlashAttention-3
overlaps data movement with computation, interleaves attention math more
carefully, and uses FP8 support to make attention faster while keeping accuracy
under control.

## RetroInfer: A Vector-Storage Approach for Scalable Long-Context LLM Inference

Core idea: Very long contexts create huge KV caches, but each new token often
needs only a small important part of that old context. RetroInfer stores KV
cache like a vector index, keeps much of it in CPU memory, and retrieves the
most useful KV entries for the current token instead of scanning everything.

## TurboQuant: Redefining AI Efficiency with Extreme Compression

Core idea: KV cache vectors can be stored with far fewer bits if they are
rotated and quantized carefully. TurboQuant compresses KV cache online with
methods like PolarQuant and QJL, reducing memory and bandwidth needs while
trying to preserve the attention scores that decide which old tokens matter.
