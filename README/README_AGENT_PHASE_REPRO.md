# Agent Phase SWE-bench Worker Profiling Reproduction Guide

This guide reproduces the full-pipeline experiment:

```text
SWE-bench task -> repo-local DeepAgents harness -> Dynamo frontend -> SGLang worker under Nsight
```

Nsight is collected only on the SGLang worker. DeepAgents is used to create a
realistic SWE-bench workload, but it is not profiled with Nsight.

The target report is:

```text
experiments/raw/deepagents_swebench_profile/profiles/<run>/kernel_analysis/summary.md
experiments/raw/deepagents_swebench_profile/profiles/<run>/kernel_analysis/agent_phase_inference_bucket_summary.csv
```

The key table is:

```text
agent_phase x inference_phase(prefill/decode) x bucket(ffn_mlp/attention_kv/other)
```

## 1. Machine Requirements

Use a GPU machine with:

- Ampere-or-newer NVIDIA GPU
- NVIDIA driver visible to Docker
- Docker and NVIDIA Container Toolkit
- Python 3.11
- Git
- 80-120 GB free disk
- Nsight Systems host tools: `nsys` and `QdstrmImporter`
- Hugging Face token recommended

Run these checks:

```bash
echo "host arch: $(uname -m)"
python3.11 --version
git --version
docker version --format 'docker {{.Server.Version}}'
df -h /
docker system df

docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

test -n "${HF_TOKEN:-}" && echo "HF_TOKEN is set" || echo "HF_TOKEN is missing"
command -v nsys || echo "nsys is missing"
command -v QdstrmImporter || echo "QdstrmImporter is missing"
```

Do not reuse Dynamo Docker images across CPU architectures. Rebuild on the
target machine.

## 2. Clone And Install Dependencies

```bash
cd ~
git clone https://github.com/the308official-afk/kv_cache_offloading.git kv_cache_offloading
cd ~/kv_cache_offloading

mkdir -p upstream

if [ ! -f upstream/deepagents/libs/deepagents/pyproject.toml ]; then
  git clone https://github.com/langchain-ai/deepagents.git upstream/deepagents
  git -C upstream/deepagents checkout 2cf7e25dbb40e783d9d4d545c29e595800bf314f
fi

python3.11 -m pip install --upgrade pip
python3.11 -m pip install ./upstream/deepagents/libs/deepagents
python3.11 -m pip install -r agentbench/requirements.txt
```

Verify:

```bash
python3.11 - <<'PY'
import deepagents
import datasets
import pandas
import langchain_openai

print("Python deps OK")
print("deepagents:", deepagents.__file__)
PY
```

## 3. Build Instrumented Dynamo Images

```bash
cd ~/kv_cache_offloading
chmod +x run_dynamo_head.sh run_dynamo_single_host.sh run_dynamo_worker.sh

rm -rf upstream/dynamo
./runtime_instrumentation/prepare_instrumented_dynamo_source.sh

LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

Check image architecture:

```bash
docker image inspect local/dynamo-frontend:runtime-json-logs --format '{{.Architecture}}'
docker image inspect local/dynamo-sglang:runtime-json-logs --format '{{.Architecture}}'
```

## 4. Run One Phased SWE-bench Profile

Make sure the shell can find the matching Nsight tools:

```bash
cd ~/tools/nsight-systems-install

NSYS_BIN="$(find "$PWD/extracted" -type f -name nsys | head -1)"
QDISTRM_BIN="$(find "$PWD/extracted" -type f -name QdstrmImporter | head -1)"
export PATH="$(dirname "$NSYS_BIN"):$(dirname "$QDISTRM_BIN"):${PATH}"

command -v nsys
command -v QdstrmImporter
```

Run the phased workload:

```bash
cd ~/kv_cache_offloading

AGENTBENCH_WORKFLOW_MODE=phased \
WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false --cuda-graph-trace=node' \
PROFILE_STOP_TIMEOUT_SECS=240 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
TASK_INDEX=0 \
experiments/scripts/deepagents_swebench_profile/profile_one_case.sh
```

To target a specific SWE-bench instance instead of an index:

```bash
INSTANCE_ID='your_instance_id_here' \
AGENTBENCH_WORKFLOW_MODE=phased \
WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false --cuda-graph-trace=node' \
PROFILE_STOP_TIMEOUT_SECS=240 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/deepagents_swebench_profile/profile_one_case.sh
```

Check logs:

```bash
docker logs -f dynamo-sglang-worker
```

The wrapper runs four separate model phases:

```text
planning
execution
patch_generation
review
```

Each phase sends its own `nvext.agent_hints.agent_phase` and
`nvext.agent_hints.hint_probe_id`.

## 5. Verify Success

Start with the verifier and the compact timing table. This avoids dumping the
full kernel summary when you only need the phase-level result.

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/raw/deepagents_swebench_profile/profiles/* | head -1)"
AGENTBENCH_RESULT_DIR="$(cat "$LATEST_PROFILE/agentbench-result-dir.txt")"

echo "$LATEST_PROFILE"
echo "$AGENTBENCH_RESULT_DIR"

python3.11 experiments/scripts/deepagents_swebench_profile/verify_profile_run.py \
  --profile-dir "$LATEST_PROFILE" \
  --agentbench-result-dir "$AGENTBENCH_RESULT_DIR" \
  --show-timing-table
```

The timing table is the fastest success view. It shows, for each agent phase,
how much worker kernel time landed in prefill/decode and in FFN/attention/other
buckets.

To see only the most important decode rows:

```bash
python3.11 experiments/scripts/deepagents_swebench_profile/verify_profile_run.py \
  --profile-dir "$LATEST_PROFILE" \
  --agentbench-result-dir "$AGENTBENCH_RESULT_DIR" \
  --show-timing-table \
  --inference-phase decode
```

To see only the most important prefill rows:

```bash
python3.11 experiments/scripts/deepagents_swebench_profile/verify_profile_run.py \
  --profile-dir "$LATEST_PROFILE" \
  --agentbench-result-dir "$AGENTBENCH_RESULT_DIR" \
  --show-timing-table \
  --inference-phase prefill
```

To focus on one agent phase:

```bash
python3.11 experiments/scripts/deepagents_swebench_profile/verify_profile_run.py \
  --profile-dir "$LATEST_PROFILE" \
  --agentbench-result-dir "$AGENTBENCH_RESULT_DIR" \
  --show-timing-table \
  --agent-phase execution
```

You can combine filters:

```bash
python3.11 experiments/scripts/deepagents_swebench_profile/verify_profile_run.py \
  --profile-dir "$LATEST_PROFILE" \
  --agentbench-result-dir "$AGENTBENCH_RESULT_DIR" \
  --show-timing-table \
  --agent-phase planning,execution,patch_generation,review \
  --inference-phase decode
```

Only use the raw files when you want the full dump:

```bash
find "$LATEST_PROFILE" -maxdepth 3 -type f | sort
cat "$LATEST_PROFILE/kernel_analysis/summary.md"
column -s, -t "$LATEST_PROFILE/kernel_analysis/agent_phase_inference_bucket_summary.csv" | less -S
```

Required success files:

```text
<profile>/<run>.nsys-rep
<profile>/<run>.sqlite
<profile>/dynamo-sglang-worker.full.log
<profile>/agentbench-result-dir.txt
<profile>/kernel_analysis/kernel_classification.json
<profile>/kernel_analysis/summary.md
<profile>/kernel_analysis/agent_phase_summary.csv
<profile>/kernel_analysis/agent_phase_bucket_summary.csv
<profile>/kernel_analysis/agent_phase_inference_bucket_summary.csv
<profile>/kernel_analysis/top_agent_phase_kernels.csv
```

The success signal is not exact timing equality across machines. The success
signal is:

- verifier prints `Verified phased SWE-bench worker profile`
- worker runtime JSON includes all four agent phases
- the kernel report has nonzero CUDA kernel rows
- `agent_phase_inference_bucket_summary.csv` has rows for prefill/decode and
  FFN/attention buckets

## 6. Optional HBM Bytes Per Phase/Bucket

After a successful Nsight Systems run, run a targeted Nsight Compute pass over
the top kernels. This reruns the same AgentBench command from the profile
directory and estimates HBM traffic by joining Nsight Compute per-launch memory
bytes with the Nsight Systems phase/bucket kernel counts.

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/raw/deepagents_swebench_profile/profiles/* | head -1)"

experiments/scripts/deepagents_swebench_profile/profile_hbm_top_kernels.sh "$LATEST_PROFILE"
```

Key output:

```bash
cat "$LATEST_PROFILE/kernel_analysis/hbm/hbm_summary.md"
column -s, -t "$LATEST_PROFILE/kernel_analysis/hbm/hbm_phase_bucket_summary.csv" | less -S
```

Useful knobs:

```bash
# Smaller/faster first pass.
HBM_TOP_KERNELS_PER_GROUP=1 \
HBM_INFERENCE_PHASES=decode \
experiments/scripts/deepagents_swebench_profile/profile_hbm_top_kernels.sh "$LATEST_PROFILE"

# Include prefill and decode for FFN and attention buckets.
HBM_TOP_KERNELS_PER_GROUP=2 \
HBM_INFERENCE_PHASES=decode,prefill \
HBM_BUCKETS=ffn_mlp,attention_kv \
experiments/scripts/deepagents_swebench_profile/profile_hbm_top_kernels.sh "$LATEST_PROFILE"
```

The HBM script skips the extra readiness generation request by default so the
Nsight Compute averages are less polluted by a tiny warmup prompt. To force the
readiness request back on:

```bash
HBM_SKIP_GENERATION_READY=0 \
experiments/scripts/deepagents_swebench_profile/profile_hbm_top_kernels.sh "$LATEST_PROFILE"
```

If `ncu` is not inside the worker image, point the wrapper at a host Nsight
Compute install:

```bash
WORKER_PROFILE_NCU_DIR=/opt/nvidia/nsight-compute/2026.3.0 \
experiments/scripts/deepagents_swebench_profile/profile_hbm_top_kernels.sh "$LATEST_PROFILE"
```

If your Nsight Compute version uses different metric names, override them:

```bash
WORKER_PROFILE_NCU_METRICS='dram__bytes_read.sum,dram__bytes_write.sum' \
experiments/scripts/deepagents_swebench_profile/profile_hbm_top_kernels.sh "$LATEST_PROFILE"
```

Interpretation note: this is a selected-kernel estimate. It is strongest for
the dominant kernels in each phase/bucket, and the report includes
`matched_duration_pct` so you can see how much selected kernel time the HBM
estimate covers.

## 7. Useful Debug Checks

If phase rows are missing, inspect worker hints:

```bash
grep -n 'agent_phase' "$LATEST_PROFILE/dynamo-sglang-worker.full.log" | head -40
grep -n 'hint_probe_id' "$LATEST_PROFILE/dynamo-sglang-worker.full.log" | head -40
```

If `.sqlite` is missing but `.nsys-rep` exists:

```bash
BASENAME="$(basename "$LATEST_PROFILE")"

nsys export --force-overwrite true --type sqlite \
  --output "$LATEST_PROFILE/${BASENAME}.sqlite" \
  "$LATEST_PROFILE/${BASENAME}.nsys-rep"

python3.11 experiments/scripts/lpx_decode_split/analyze_nsys_sqlite.py \
  --sqlite "$LATEST_PROFILE/${BASENAME}.sqlite" \
  --worker-log "$LATEST_PROFILE/dynamo-sglang-worker.full.log" \
  --out-dir "$LATEST_PROFILE/kernel_analysis"
```

If `.nsys-rep` is missing and only `.qdstrm` exists, the worker shutdown likely
did not finish Nsight export. Re-run with:

```bash
PROFILE_STOP_TIMEOUT_SECS=240
```

If the model rejects long prompts, keep the wrapper defaults:

```text
SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length 65536'
```
