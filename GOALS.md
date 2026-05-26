# CORE GOALS

Blue part - Can be restored from CPU memory / storage
Orange part:
- how does it scale as the blue part and the input set that can be reused grows larger and larger w.r.t. FLOPS<compute>, memory use: quadratic?
- for prefil and decode*
- focus on decode
- For the decode stage, NVIDIA put feedforward network unto LPU from Groq and keep GPU with attention calculation
      - what should we do? 
      - should it be SRAM based hardware?
      - can we augment GPU so that its more efficient for the FFN phase

# STATE-OF-THE-ART IMPLEMENTATION

"During decode, NVIDIA’s Rubin/Groq LPX-style heterogeneous design keeps attention/KV-cache work on the GPU, while FFN/MoE execution runs on Groq LPUs, with activations exchanged between GPU and LPU each token."

Mostly yes, with two corrections.

First, it is **Groq**, not Grok. Grok is xAI’s model; **Groq** is the LPU company/architecture.

Second, the idea is not specific only to agentic workflows. It is a **decode-stage inference architecture** that agentic workflows could benefit from.

The correct version is:

> During decode, NVIDIA’s Rubin/Groq LPX-style heterogeneous design keeps **attention/KV-cache work on the GPU**, while **FFN/MoE execution runs on Groq LPUs**, with activations exchanged between GPU and LPU each token.

How to think about it:

```text
Decode token loop:
  GPU: attention over KV cache
  LPU/LPX: FFN or MoE compute
  GPU <-> LPU: exchange intermediate activations
```

For this project, the key point is: this is a **hardware-level attention/FFN disaggregation** idea.

The current Dynamo/SGLang setup is doing a different kind of disaggregation:

```text
Current setup:
  prefill/decode routing
  KV-cache-aware routing
  KV logging/offload/hint propagation

NVIDIA/Groq LPX idea:
  split transformer-layer work itself:
  attention on GPU, FFN/MoE on LPU
```

So the statement is directionally correct, but should be phrased as:

> NVIDIA’s Rubin/Groq LPX design proposes decode-stage heterogeneous execution: GPUs handle attention over KV cache, while Groq LPUs handle FFN/MoE computation. This could be especially useful for agentic workflows because decode loops are long, latency-sensitive, and repeatedly touch KV state.
