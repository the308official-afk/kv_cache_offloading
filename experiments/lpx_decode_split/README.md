# LPX Decode Split Experiments

This experiment family studies the hardware question behind NVIDIA/Groq
LPX-style decode disaggregation:

```text
During decode, how much of the workload behaves like KV/attention pressure,
and how much behaves like FFN/MoE compute?
```

The current setup cannot run FFN on a Groq LPU. Instead, it runs trace-driven
experiments on Dynamo/SGLang and produces measurements for a "what if FFN moved
to LPU?" model later.

## First Experiment: Decode Sweep

Run controlled requests through the Dynamo frontend while varying:

- prompt size
- output size
- repeats

This helps separate two broad effects:

- larger prompt/context tends to stress attention and KV-cache reads
- larger output tends to stress the per-token decode loop

Run:

```bash
cd ~/kv_cache_offloading

python3.11 experiments/lpx_decode_split/run_decode_sweep.py \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model Qwen/Qwen2.5-7B-Instruct \
  --prompt-token-targets 1024,4096,8192,16384 \
  --max-tokens-list 64,256 \
  --repeats 2
```

Outputs are written under:

```text
experiments/lpx_decode_split/results/
```

Main files:

- `measurements.jsonl`
- `measurements.csv`
- `summary.md`

## Interpretation

If latency grows sharply as prompt/context size grows, the decode path is likely
more attention/KV sensitive.

If latency grows mainly with output tokens and is less sensitive to prompt size,
FFN/MoE compute may be a larger target for heterogeneous acceleration.

The next step after this sweep is to pair the same runs with `nsys`/`ncu` kernel
profiles and classify kernels into attention/KV versus FFN/GEMM groups.

## Profile One Decode Case

Use this when you want the first hard split between:

```text
attention/KV kernels
FFN/MLP/GEMM kernels
other runtime kernels
```

Start from one controlled case:

```bash
cd ~/kv_cache_offloading

PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/lpx_decode_split/profile_one_decode_case.sh
```

The wrapper:

1. starts the instrumented Dynamo runtime
2. launches the SGLang worker under `nsys profile`
3. sends one controlled decode-sweep request
4. stops the worker so Nsight flushes the report
5. exports SQLite when `nsys` is available on the host
6. classifies kernel time with `analyze_nsys_sqlite.py`
7. writes the LPX what-if estimate under `kernel_analysis/lpx_what_if/`
8. splits classified kernels into approximate `prefill` and `decode` phases
   using worker `worker.decode.*` runtime log events

The default profile uses:

```text
--cuda-graph-trace=node
```

This matters because SGLang can serve through CUDA graph replay. Nsight's graph
mode records graph-level activity but not node activities, which can leave the
analysis with only `Graph Creation` / `GraphExec Creation` rows.

Profile outputs are written under:

```text
experiments/lpx_decode_split/profiles/
```

If SQLite export is not automatic, export manually:

```bash
nsys export --force-overwrite true --type sqlite \
  --output experiments/lpx_decode_split/profiles/<run>/<run>.sqlite \
  experiments/lpx_decode_split/profiles/<run>/<run>.nsys-rep
```

Then classify:

```bash
python3.11 experiments/lpx_decode_split/analyze_nsys_sqlite.py \
  --sqlite experiments/lpx_decode_split/profiles/<run>/<run>.sqlite \
  --worker-log experiments/lpx_decode_split/profiles/<run>/dynamo-sglang-worker.full.log \
  --out-dir experiments/lpx_decode_split/profiles/<run>/kernel_analysis
```

The important output is:

```text
kernel_analysis/summary.md
```

That file is the first measured estimate for the GPU/LPU split model:

```text
observed decode kernel time
  = attention/KV time
  + FFN/MLP time
  + other runtime time
```

The same summary also includes `Phase Summary`, `Phase x Bucket Summary`, and
`Top Phase Kernels` when `dynamo-sglang-worker.full.log` is available. CSV
versions are written to:

```text
kernel_analysis/phase_summary.csv
kernel_analysis/phase_bucket_summary.csv
kernel_analysis/top_phase_kernels.csv
```

## LPX What-If Estimate

After classification, estimate GPU+LPU payoff:

```bash
python3.11 experiments/lpx_decode_split/estimate_lpx_speedup.py \
  --classification-json experiments/lpx_decode_split/profiles/<run>/kernel_analysis/kernel_classification.json \
  --completion-tokens 256 \
  --lpu-speedups 2,4,8 \
  --transfer-ms-per-token 0,0.05,0.1,0.25
```

Output:

```text
kernel_analysis/lpx_what_if/summary.md
```

This estimates:

```text
projected_kernel_ms =
  attention_kv_ms
  + ffn_mlp_ms / lpu_ffn_speedup
  + other_ms
  + activation_transfer_ms
```
