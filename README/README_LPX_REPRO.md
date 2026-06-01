# LPX Decode Profiling Reproduction Guide

This file is the shortest reliable path to reproduce the successful LPX decode
profiling experiment on a fresh GPU machine.

The target result is one profiled Dynamo/SGLang decode request with:

- Nsight Systems `.nsys-rep`
- Nsight SQLite export
- kernel bucket split: `ffn_mlp`, `attention_kv`, `other`
- phase split: `prefill`, `decode`, plus any `unassigned` trace work
- LPX what-if speedup table

The exact numbers vary by GPU, driver, and image build. The important success
signal is not bit-for-bit equality; it is nonzero CUDA kernel time with the same
artifact structure and the same dominant FFN/MLP behavior.

## 1. Machine Requirements

Use an NVIDIA GPU machine with:

- Ampere-or-newer NVIDIA GPU
- NVIDIA driver visible to containers
- Docker
- NVIDIA Container Toolkit
- Python 3.11
- Git
- 80-120 GB free disk
- Full Nsight Systems Linux package, including both `nsys` and `QdstrmImporter`
- Hugging Face token recommended

Do not reuse Dynamo Docker images built on another CPU architecture. Rebuild on
the target machine. For example, GH200/Grace systems are usually `aarch64`, while
standard cloud GPU instances are often `x86_64`.

## 2. Machine Preflight

Run these checks before building or profiling:

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

If the Docker GPU test fails, fix NVIDIA Container Toolkit before continuing.
If `QdstrmImporter` is missing, install the full Nsight Systems `.run` package,
not a CLI-only package.

## 3. Install Nsight Systems

Use this on the GPU machine if `nsys` or `QdstrmImporter` is missing:

```bash
cd ~
mkdir -p tools/nsight-systems-install
cd tools/nsight-systems-install

NSYS_VERSION="2026.3.1.157-3804839"

case "$(uname -m)" in
  x86_64)
    NSYS_RUN="NsightSystems-linux-public-${NSYS_VERSION}.run"
    ;;
  aarch64|arm64)
    NSYS_RUN="NsightSystems-linux-sbsa-public-${NSYS_VERSION}.run"
    ;;
  *)
    echo "Unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

wget -O "${NSYS_RUN}" \
  "https://developer.download.nvidia.com/devtools/nsight-systems/${NSYS_RUN}"

chmod +x "${NSYS_RUN}"
rm -rf extracted
mkdir -p extracted
./"${NSYS_RUN}" --target "$PWD/extracted" --noexec

NSYS_BIN="$(find "$PWD/extracted" -type f -name nsys | head -1)"
QDISTRM_BIN="$(find "$PWD/extracted" -type f -name QdstrmImporter | head -1)"

test -n "${NSYS_BIN}" || { echo "ERROR: nsys not found"; exit 1; }
test -n "${QDISTRM_BIN}" || { echo "ERROR: QdstrmImporter not found"; exit 1; }

export PATH="$(dirname "$NSYS_BIN"):$(dirname "$QDISTRM_BIN"):${PATH}"

command -v nsys
command -v QdstrmImporter
nsys --version
```

For future shells, add the final `export PATH=...` line to `~/.bashrc`.

## 4. Clone Repo And Install Python Dependencies

If this is a fresh machine, clone the experiment repo first:

```bash
cd ~
git clone https://github.com/the308official-afk/kv_cache_offloading.git kv_cache_offloading
cd ~/kv_cache_offloading
```

If the repo already exists on the machine, do not clone again. Just enter it and
make sure it is up to date:

```bash
cd ~/kv_cache_offloading
git pull --ff-only
```

Then install Python dependencies from inside the repo:

```bash
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
cd ~/kv_cache_offloading

python3.11 - <<'PY'
import deepagents
import datasets
import pandas
import langchain_openai

print("Python deps OK")
print("deepagents:", deepagents.__file__)
PY
```

Optional but recommended for faster model download:

```bash
export HF_TOKEN=your_token_here
```

## 5. Build Instrumented Dynamo Images

Run from the repo root:

```bash
cd ~/kv_cache_offloading
chmod +x run_dynamo_head.sh run_dynamo_single_host.sh run_dynamo_worker.sh

rm -rf upstream/dynamo
./runtime_instrumentation/prepare_instrumented_dynamo_source.sh

LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

Verify image architecture:

```bash
docker image inspect local/dynamo-frontend:runtime-json-logs --format '{{.Architecture}}'
docker image inspect local/dynamo-sglang:runtime-json-logs --format '{{.Architecture}}'
```

Expected:

```text
x86_64 host -> amd64 images
aarch64 host -> arm64 images
```

## 6. Run The LPX Decode Profile

Make sure the current shell can find the matching Nsight tools:

```bash
cd ~/tools/nsight-systems-install

NSYS_BIN="$(find "$PWD/extracted" -type f -name nsys | head -1)"
QDISTRM_BIN="$(find "$PWD/extracted" -type f -name QdstrmImporter | head -1)"
export PATH="$(dirname "$NSYS_BIN"):$(dirname "$QDISTRM_BIN"):${PATH}"

command -v nsys
command -v QdstrmImporter
```

Run the successful case:

```bash
cd ~/kv_cache_offloading

WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false --cuda-graph-trace=node' \
PROFILE_STOP_TIMEOUT_SECS=240 \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

Expected worker-log ending:

```text
Generated:
  /profiles/profile-decode_<timestamp>_ctx8192_out256.nsys-rep
```

The `--cuda-graph-trace=node` flag is important. Without it, Nsight may only
show graph creation rows instead of useful CUDA kernel rows.

## 7. Verify Artifacts

After the script returns:

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"
LATEST_RESULT_ROOT="$(ls -td experiments/reports/lpx_decode_split/results/* | head -1)"

echo "$LATEST_PROFILE"
echo "$LATEST_RESULT_ROOT"

find "$LATEST_RESULT_ROOT" -name measurements.csv -o -name summary.md
find "$LATEST_PROFILE" -maxdepth 3 -type f | sort

cat "$LATEST_RESULT_ROOT"/*/summary.md
cat "$LATEST_PROFILE/kernel_analysis/summary.md"
cat "$LATEST_PROFILE/kernel_analysis/lpx_what_if/summary.md"
```

Required files:

```text
<profile>/<run>.nsys-rep
<profile>/<run>.sqlite
<profile>/dynamo-sglang-worker.full.log
<profile>/kernel_analysis/kernel_classification.json
<profile>/kernel_analysis/summary.md
<profile>/kernel_analysis/bucket_summary.csv
<profile>/kernel_analysis/phase_summary.csv
<profile>/kernel_analysis/phase_bucket_summary.csv
<profile>/kernel_analysis/top_phase_kernels.csv
<profile>/kernel_analysis/lpx_what_if/summary.md
<result>/measurements.csv
<result>/summary.md
```

Required success signals in `kernel_analysis/summary.md`:

```text
Kernel table: `CUPTI_ACTIVITY_KIND_KERNEL`
Kernel rows: greater than 0
Total kernel duration ms: greater than 0
Phase assignment: `relative_tail_heuristic`
```

`Phase assignment: epoch_wall` is also valid. On these runs,
`relative_tail_heuristic` is expected because the analyzer maps the measured
request to the tail of the Nsight trace after the worker log gives
`request_received`, `request_attached`, and `request_completed`.

The summary should include:

```text
Bucket Summary
Phase Summary
Phase x Bucket Summary
Top Phase Kernels
Top Kernels
```

The LPX what-if summary should include rows for FFN speedups `2.0`, `4.0`, and
`8.0`.

## 8. Reference Successful Result

The successful run on 2026-05-27 produced this decode-sweep summary:

```text
prompt target: 8192
max tokens: 256
successful requests: 1
avg latency ms: 6471.5
avg completion tok/s: 23.80
avg prompt tokens: 5576.0
avg completion tokens: 154.0
```

Overall kernel split:

```text
FFN/MLP:       8793.319 ms  88.959%
Attention/KV:  767.085 ms   7.760%
Other:         324.247 ms   3.280%
```

Assigned prefill phase:

```text
FFN/MLP:       1236.026 ms  94.494% of prefill
Attention/KV:   41.125 ms   3.144% of prefill
Other:          30.893 ms   2.362% of prefill
```

Assigned decode phase:

```text
FFN/MLP:       3591.038 ms  86.124% of decode
Attention/KV:  429.680 ms  10.305% of decode
Other:         148.877 ms   3.571% of decode
```

LPX what-if rows with zero transfer cost:

```text
2x FFN speedup -> 1.8011x projected kernel speedup
4x FFN speedup -> 3.0048x projected kernel speedup
8x FFN speedup -> 4.5125x projected kernel speedup
```

It is normal to see an `unassigned` phase. That trace work is outside the
measured decode-sweep request window, usually warmup, readiness, small probe
requests, graph setup, or shutdown-adjacent work. Use the overall bucket split
for full-trace claims and the `prefill` / `decode` rows for measured-request
phase claims.

## 9. If The Run Partially Succeeds

### `.nsys-rep` exists but analysis is missing

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"
BASENAME="$(basename "$LATEST_PROFILE")"

nsys export --force-overwrite true --type sqlite \
  --output "$LATEST_PROFILE/${BASENAME}.sqlite" \
  "$LATEST_PROFILE/${BASENAME}.nsys-rep"

rm -rf "$LATEST_PROFILE/kernel_analysis"

python3.11 experiments/scripts/lpx_decode_split/analyze_nsys_sqlite.py \
  --sqlite "$LATEST_PROFILE/${BASENAME}.sqlite" \
  --worker-log "$LATEST_PROFILE/dynamo-sglang-worker.full.log" \
  --out-dir "$LATEST_PROFILE/kernel_analysis"

python3.11 experiments/scripts/lpx_decode_split/estimate_lpx_speedup.py \
  --classification-json "$LATEST_PROFILE/kernel_analysis/kernel_classification.json" \
  --completion-tokens 256 \
  --out-dir "$LATEST_PROFILE/kernel_analysis/lpx_what_if"
```

### Phase assignment is `none`

Confirm measured request events exist:

```bash
grep -n 'decode-sweep_.*ctx.*out' "$LATEST_PROFILE/dynamo-sglang-worker.full.log" | tail -20
```

You should see the same `external_request_id` for:

```text
worker.decode.request_received
worker.decode.request_attached
worker.decode.request_completed
```

Then rerun the analysis commands above with the latest
`experiments/scripts/lpx_decode_split/analyze_nsys_sqlite.py`.

### Only `.qdstrm` exists

Try import with the matching `QdstrmImporter`:

```bash
QdstrmImporter \
  -i "$LATEST_PROFILE/${BASENAME}.qdstrm" \
  -o "$LATEST_PROFILE/${BASENAME}.nsys-rep"
```

If the importer says:

```text
Qdstrm file does not have valid time conversion factors.
```

that raw stream is not recoverable. Use the newest profile with an existing
`.nsys-rep`, or rerun the profile after ensuring the worker uses the same host
Nsight package as `QdstrmImporter`.

Find the newest completed profile:

```bash
LATEST_PROFILE="$(find experiments/raw/lpx_decode_split/profiles -name '*.nsys-rep' -exec dirname {} \; | sort -r | head -1)"
echo "$LATEST_PROFILE"
```

## 10. Common Environment Mistakes

- Running recovery commands on your laptop after SSH disconnects. If the prompt
  path starts with `/Users/...`, reconnect to the GPU machine first.
- Using macOS `find -printf`. Use `find ... -exec dirname {} \;` for portable
  completed-profile discovery.
- Installing Nsight without `QdstrmImporter`.
- Reusing x86 Docker images on an Arm GPU machine, or vice versa.
- Omitting `--cuda-graph-trace=node`, which can produce useless graph-creation
  rows.
- Forgetting to pass `--worker-log` when manually rerunning
  `analyze_nsys_sqlite.py`, which prevents phase assignment.
