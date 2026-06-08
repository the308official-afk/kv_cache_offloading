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
