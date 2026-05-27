# kv_cache_offloading

Reproducible AgentBench + Dynamo + SGLang harness for two research workflows:

```text
1. LPX decode profiling:
   Dynamo native frontend -> SGLang worker under Nsight Systems

2. AgentBench runtime-hint tracing and phased SWE-bench profiling:
   AgentBench/DeepAgents -> Dynamo frontend/preprocessor -> SGLang worker
```

The most important current result is the LPX decode split experiment. A
successful run produces:

```text
experiments/lpx_decode_split/profiles/<run>/kernel_analysis/summary.md
experiments/lpx_decode_split/profiles/<run>/kernel_analysis/lpx_what_if/summary.md
```

For the self-contained reproduction playbook, use
[`README_LPX_REPRO.md`](README_LPX_REPRO.md).

For the full phased SWE-bench workload, where only the SGLang worker is profiled
and the report is split by `planning`, `execution`, `patch_generation`, and
`review`, use [`README_AGENT_PHASE_REPRO.md`](README_AGENT_PHASE_REPRO.md).

Reference success signal from the first complete run:

```text
Kernel table: CUPTI_ACTIVITY_KIND_KERNEL
Kernel rows: 29809
Total kernel duration ms: 9884.823

FFN/MLP:      8794.067 ms  88.965%
Attention/KV:  766.629 ms   7.756%
Other:         324.127 ms   3.279%
```

Exact numbers will vary by GPU, driver, image build, and model cache state, but
the report should have nonzero kernel time, bucketed `ffn_mlp`, `attention_kv`,
and `other` rows, plus a generated LPX what-if speedup table.

--------------------------------------------------------------------------------

## 0. Core Pipeline: Upstream vs Custom

This section describes the basic non-instrumentation pipeline:

```text
SWE-bench Pro -> AgentBench runner -> prompt builder -> Deep Agents
-> Dynamo frontend -> SGLang worker
```

### Out Of The Box

These pieces are upstream/off-the-shelf:

- **SWE-bench Pro dataset**: loaded from Hugging Face with `datasets`.
- **Deep Agents framework**: cloned from upstream and installed from
  `agentbench/upstream/deepagents/libs/deepagents`.
- **Deep Agents deploy-coding-agent example content**: reused when running with
  `--app-variant upstream_deploy_coding_agent`.
- **Dynamo frontend/runtime**: OpenAI-compatible frontend and request routing.
- **SGLang worker**: model serving backend that runs the model.
- **LangChain/OpenAI client surface**: `ChatOpenAI` is used as the client
  interface to the local Dynamo `/v1` endpoint.

### Custom In This Repo

These pieces are custom implementation:

- **AgentBench runner**:
  `agentbench/deepagents_swebench_single_host.py`.
  This is not an external AgentBench package. It is the local harness that loads
  one SWE-bench task, prepares the workspace, starts one run, calls the Deep
  Agents app, and writes result artifacts.
- **Prompt builder**:
  `agentbench/deepagents_app/src/prompts.py`.
  This turns raw SWE-bench task fields into the model-facing coding task prompt.
- **Deep Agents adapter app**:
  `agentbench/deepagents_app/src/agent.py`.
  This wires upstream Deep Agents to the local Dynamo frontend, selects the
  instruction surface, builds the filesystem/shell backend, and attaches
  request metadata.
- **Dynamo/SGLang launch glue**:
  `run_dynamo_single_host.sh`, `run_dynamo_head.sh`, and
  `run_dynamo_worker.sh`.
  These start etcd, NATS, the Dynamo frontend, and the SGLang worker in the
  shape needed by this project.
- **Run artifacts and reports**:
  result directories, measurements, prompt-evolution reports, runtime alignment
  summaries, and helper diagnostics are custom.

### Short Version

The model-serving stack is mostly upstream Dynamo + SGLang. The agent framework
is upstream Deep Agents. The dataset is upstream SWE-bench Pro. The custom part
is the glue: loading one task, building the prompt, adapting Deep Agents to the
local Dynamo endpoint, launching the local runtime, and saving the benchmark
artifacts.

--------------------------------------------------------------------------------

## 1. Golden Path: Reproduce LPX Decode Profiling

Use this section on a new machine when the goal is to reproduce the final
successful GPU/LPU split experiment.

### 1.1 Machine Requirements

Use an NVIDIA GPU machine with:

- Ampere-or-newer GPU
- NVIDIA driver
- Docker
- NVIDIA Container Toolkit
- Python 3.11 with `pip`
- Git
- 80-120 GB free disk for model cache, Docker images, and build artifacts
- Nsight Systems host tools: `nsys` and `QdstrmImporter`
- Hugging Face token recommended for reliable model downloads

Verify Docker GPU access:

```bash
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

Do not reuse Docker images between machines unless CPU architecture matches.
Many GH200 hosts are `aarch64`/`arm64`; x86 hosts build `linux/amd64` images.
Rebuild Dynamo natively on the target machine when architectures differ.

--------------------------------------------------------------------------------

### 1.2 Install Nsight Systems Host Tools

Nsight is required for kernel classification. Smoke tests and AgentBench
correctness runs do not require it, but LPX profiling does.

Install NVIDIA's full Linux `.run` package. Use `linux-public` on `x86_64` and
`linux-sbsa-public` on `aarch64`/Arm server systems:

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
    echo "Unsupported architecture for this command: $(uname -m)" >&2
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

export PATH="$(dirname "${NSYS_BIN}"):$(dirname "${QDISTRM_BIN}"):${PATH}"

command -v nsys
command -v QdstrmImporter
nsys --version
```

To make this persistent, append the final `export PATH=...` line to `~/.bashrc`
after confirming both commands resolve.

If `QdstrmImporter` is missing, you probably installed a CLI-only package. Use
the full Nsight Systems installer instead.

--------------------------------------------------------------------------------

### 1.3 Clone And Install Python Dependencies

```bash
cd ~
git clone https://github.com/the308official-afk/kv_cache_offloading.git kv_cache_offloading
cd ~/kv_cache_offloading

mkdir -p agentbench/upstream

if [ ! -f agentbench/upstream/deepagents/libs/deepagents/pyproject.toml ]; then
  git clone https://github.com/langchain-ai/deepagents.git agentbench/upstream/deepagents
  git -C agentbench/upstream/deepagents checkout 2cf7e25dbb40e783d9d4d545c29e595800bf314f
fi

python3.11 -m pip install --upgrade pip
python3.11 -m pip install -r agentbench/requirements.txt

export HF_TOKEN=your_token_here
```

Run installs from the repo root. Deep Agents must be installed into the same
interpreter used later:

```bash
cd ~/kv_cache_offloading

python3.11 -m pip show deepagents

python3.11 - <<'PY'
import deepagents
import datasets
import pandas
import langchain_openai

print("Python deps OK")
print("deepagents:", deepagents.__file__)
PY
```

If the checkout exists but `python3.11 -m pip show deepagents` says the package
is missing, force reinstall:

```bash
cd ~/kv_cache_offloading

python3.11 -m pip install ./agentbench/upstream/deepagents/libs/deepagents
python3.11 -m pip install -r agentbench/requirements.txt
```

--------------------------------------------------------------------------------

### 1.4 Preflight Check

Run this before building or profiling:

```bash
cd ~/kv_cache_offloading

echo "host arch: $(uname -m)"
python3.11 --version
docker version --format 'docker {{.Server.Version}}'
df -h /
docker system df

test -n "${HF_TOKEN:-}" && echo "HF_TOKEN is set" || echo "HF_TOKEN is missing"

docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

command -v nsys || echo "nsys is missing"
command -v QdstrmImporter || echo "QdstrmImporter is missing"

ss -ltnp | grep ':8000' || true
```

--------------------------------------------------------------------------------

### 1.5 Build Instrumented Dynamo Images

The LPX profile wrapper expects local instrumented images by default.

```bash
cd ~/kv_cache_offloading
chmod +x run_dynamo_head.sh run_dynamo_single_host.sh run_dynamo_worker.sh

rm -rf runtime_upstream/dynamo
./runtime_instrumentation/prepare_instrumented_dynamo_source.sh

LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

Built images:

```text
local/dynamo-frontend:runtime-json-logs
local/dynamo-sglang:runtime-json-logs
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

--------------------------------------------------------------------------------

### 1.6 Run The Successful LPX Profile Case

This command starts Dynamo/SGLang, runs the SGLang worker under Nsight Systems,
sends one synthetic decode request, stops the worker gracefully so Nsight flushes
the report, exports SQLite, classifies kernels, and writes the LPX what-if table.

```bash
cd ~/kv_cache_offloading

WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false --cuda-graph-trace=node' \
PROFILE_STOP_TIMEOUT_SECS=240 \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/lpx_decode_split/profile_one_decode_case.sh
```

The `--cuda-graph-trace=node` flag is important. Without it, Nsight may only
show `Graph Creation` / `GraphExec Creation` rows and report zero useful kernel
duration.

--------------------------------------------------------------------------------

### 1.7 Verify LPX Outputs

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/lpx_decode_split/profiles/* | head -1)"
LATEST_RESULT_ROOT="$(ls -td experiments/lpx_decode_split/results/* | head -1)"

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
<profile>/kernel_analysis/kernel_classification.json
<profile>/kernel_analysis/summary.md
<profile>/kernel_analysis/phase_summary.csv
<profile>/kernel_analysis/phase_bucket_summary.csv
<profile>/kernel_analysis/top_phase_kernels.csv
<profile>/kernel_analysis/lpx_what_if/summary.md
<result>/measurements.csv
<result>/summary.md
```

Good success signals:

```text
Kernel table: CUPTI_ACTIVITY_KIND_KERNEL
Kernel rows: greater than 0
Total kernel duration ms: greater than 0
Bucket Summary includes ffn_mlp, attention_kv, and other
Phase x Bucket Summary includes prefill and decode rows
LPX What-If Speedup table is present
```

The phase split is assigned from `worker.decode` runtime log timestamps. When
Nsight and log timestamps share an epoch clock, the analyzer reports
`Phase assignment: epoch_wall`. Otherwise it reports
`Phase assignment: relative_tail_heuristic`, which is valid for this wrapper
because the measured request runs at the end and the worker is stopped
immediately after the request.

Reference first complete result:

```text
FFN/MLP:      8794.067 ms  88.965%
Attention/KV:  766.629 ms   7.756%
Other:         324.127 ms   3.279%

2x FFN speedup -> about 1.80x projected kernel speedup
4x FFN speedup -> about 3.01x projected kernel speedup
8x FFN speedup -> about 4.51x projected kernel speedup
```

--------------------------------------------------------------------------------

## 2. Golden Path Failure Recovery

Use this section only when the LPX profile path above does not produce the
expected files.

### 2.1 etcd Is Unhealthy

Dynamo uses etcd as a local service registry. If startup fails with
`Frontend did not become healthy`, start a clean `dynamo-etcd` container:

```bash
docker rm -f dynamo-etcd etcd >/dev/null 2>&1 || true

mkdir -p ~/kv_cache_offloading/dynamo_head_state/etcd-data

docker run -d \
  --name dynamo-etcd \
  --network host \
  -v ~/kv_cache_offloading/dynamo_head_state/etcd-data:/etcd-data \
  quay.io/coreos/etcd:v3.5.14 \
  /usr/local/bin/etcd \
  --name dynamo-etcd \
  --data-dir /etcd-data \
  --listen-client-urls http://0.0.0.0:2379 \
  --advertise-client-urls http://127.0.0.1:2379

curl -s http://127.0.0.1:2379/health
```

Expected:

```json
{"health":"true","reason":""}
```

Then rerun the LPX profile command.

--------------------------------------------------------------------------------

### 2.2 `.nsys-rep` Exists But `lpx_what_if` Is Missing

Run only the estimator:

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/lpx_decode_split/profiles/* | head -1)"

python3.11 experiments/lpx_decode_split/estimate_lpx_speedup.py \
  --classification-json "$LATEST_PROFILE/kernel_analysis/kernel_classification.json" \
  --completion-tokens 256 \
  --out-dir "$LATEST_PROFILE/kernel_analysis/lpx_what_if"

cat "$LATEST_PROFILE/kernel_analysis/lpx_what_if/summary.md"
```

--------------------------------------------------------------------------------

### 2.3 `.nsys-rep` Exists But SQLite Or Kernel Analysis Is Missing

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/lpx_decode_split/profiles/* | head -1)"
BASENAME="$(basename "$LATEST_PROFILE")"

test -f "$LATEST_PROFILE/${BASENAME}.nsys-rep" || {
  echo "ERROR: missing $LATEST_PROFILE/${BASENAME}.nsys-rep"
  echo "If only .qdstrm exists, use section 2.5 first."
  exit 1
}

nsys export --force-overwrite true --type sqlite \
  --output "$LATEST_PROFILE/${BASENAME}.sqlite" \
  "$LATEST_PROFILE/${BASENAME}.nsys-rep"

python3.11 experiments/lpx_decode_split/analyze_nsys_sqlite.py \
  --sqlite "$LATEST_PROFILE/${BASENAME}.sqlite" \
  --worker-log "$LATEST_PROFILE/dynamo-sglang-worker.full.log" \
  --out-dir "$LATEST_PROFILE/kernel_analysis"

python3.11 experiments/lpx_decode_split/estimate_lpx_speedup.py \
  --classification-json "$LATEST_PROFILE/kernel_analysis/kernel_classification.json" \
  --completion-tokens 256 \
  --out-dir "$LATEST_PROFILE/kernel_analysis/lpx_what_if"
```

--------------------------------------------------------------------------------

### 2.4 Kernel Analysis Exists But Phase Assignment Is `none`

If `kernel_analysis/summary.md` reports `Phase assignment: none`, first confirm
that the measured decode-sweep request events are present:

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/lpx_decode_split/profiles/* | head -1)"
BASENAME="$(basename "$LATEST_PROFILE")"

grep -n 'decode-sweep_.*ctx.*out' "$LATEST_PROFILE/dynamo-sglang-worker.full.log" | tail -20
```

Expected log events for the same request:

```text
worker.decode.request_received
worker.decode.request_attached
worker.decode.request_completed
```

Then rerun only the analysis step. You do not need to rerun Nsight:

```bash
rm -rf "$LATEST_PROFILE/kernel_analysis"

python3.11 experiments/lpx_decode_split/analyze_nsys_sqlite.py \
  --sqlite "$LATEST_PROFILE/${BASENAME}.sqlite" \
  --worker-log "$LATEST_PROFILE/dynamo-sglang-worker.full.log" \
  --out-dir "$LATEST_PROFILE/kernel_analysis"

python3.11 experiments/lpx_decode_split/estimate_lpx_speedup.py \
  --classification-json "$LATEST_PROFILE/kernel_analysis/kernel_classification.json" \
  --completion-tokens 256 \
  --out-dir "$LATEST_PROFILE/kernel_analysis/lpx_what_if"

cat "$LATEST_PROFILE/kernel_analysis/summary.md"
cat "$LATEST_PROFILE/kernel_analysis/lpx_what_if/summary.md"
```

Expected: `Phase assignment` should be `epoch_wall` or
`relative_tail_heuristic`, and the phase tables should include `prefill` and
`decode`.

--------------------------------------------------------------------------------

### 2.5 Only `.qdstrm` Exists

Use matching host `QdstrmImporter`:

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/lpx_decode_split/profiles/* | head -1)"
BASENAME="$(basename "$LATEST_PROFILE")"

QdstrmImporter \
  -i "$LATEST_PROFILE/${BASENAME}.qdstrm" \
  -o "$LATEST_PROFILE/${BASENAME}.nsys-rep"
```

Then run the SQLite and analysis commands from **2.3**.

If import fails with:

```text
Qdstrm file does not have valid time conversion factors.
```

that raw stream is not recoverable. Use the newest profile that already contains
`.nsys-rep`, or regenerate the profile after ensuring the same Nsight package is
available on `PATH`. The profile wrapper auto-detects host `nsys`, mounts it
into the worker, and avoids the mismatched-importer failure.

Find the newest completed profile:

```bash
LATEST_PROFILE="$(find experiments/lpx_decode_split/profiles -name '*.nsys-rep' -exec dirname {} \; | sort -r | head -1)"
echo "$LATEST_PROFILE"
```

--------------------------------------------------------------------------------

### 2.6 Kernel Summary Shows Only Graph Creation Rows

If `kernel_analysis/summary.md` shows only:

```text
Graph Creation
GraphExec Creation
Total kernel duration ms: 0.0
```

rerun with CUDA graph node tracing:

```bash
WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false --cuda-graph-trace=node' \
PROFILE_STOP_TIMEOUT_SECS=240 \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/lpx_decode_split/profile_one_decode_case.sh
```

If that still fails, collect a slower profile with SGLang CUDA graphs disabled:

```bash
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --disable-cuda-graph' \
WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false' \
PROFILE_STOP_TIMEOUT_SECS=240 \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/lpx_decode_split/profile_one_decode_case.sh
```

```bash
docker logs -f dynamo-sglang-worker
```

--------------------------------------------------------------------------------

## 3. Optional Smoke Test Without Rebuild

Use this only to prove Docker, GPU, model loading, and the basic OpenAI-compatible
request path. This does not prove runtime JSON hints or LPX profiling.

```bash
cd ~/kv_cache_offloading
chmod +x run_dynamo_head.sh run_dynamo_single_host.sh run_dynamo_worker.sh

./run_dynamo_single_host.sh stop

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
./run_dynamo_single_host.sh start
```

Do not set `FRONTEND_IMAGE` or `WORKER_IMAGE` for this smoke test; leaving them
unset uses the published default image instead of local instrumented images.

Verify:

```bash
curl -fsS http://127.0.0.1:8000/v1/models
./run_dynamo_single_host.sh test
```

--------------------------------------------------------------------------------

## 4. Optional Direct Hint Probe

Use this after building instrumented images when you want to prove `agent_hints`
reach the worker without running AgentBench.

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh stop

DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

Then send a direct hint probe:

```bash
PROBE_ID="manual-instrumented-dynamo-probe-$(date +%s)"

curl -sS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d "{
    \"model\": \"Qwen/Qwen2.5-7B-Instruct\",
    \"messages\": [
      {\"role\": \"user\", \"content\": \"Reply with exactly: ok\"}
    ],
    \"max_tokens\": 8,
    \"nvext\": {
      \"agent_hints\": {
        \"hint_probe_id\": \"${PROBE_ID}\",
        \"program_id\": \"manual_probe\",
        \"agent_phase\": \"hint_path_test\",
        \"expected_output_tokens\": 8
      },
      \"request_context\": {
        \"probe\": \"manual_instrumented_dynamo\"
      }
    }
  }"

echo
echo "PROBE_ID=${PROBE_ID}"
```

Check worker logs:

```bash
docker logs dynamo-sglang-worker 2>&1 | \
  grep -E "${PROBE_ID}|agent_hints|hint_probe_id|worker.decode" | \
  tail -50
```

Success signal: a worker `[RUNTIME_JSON]` event contains the same
`hint_probe_id` and `agent_hints`.

--------------------------------------------------------------------------------

## 5. Optional AgentBench Run

AgentBench requests are larger than the LPX synthetic decode request because
they include SWE-bench task text, Deep Agents instructions, tools, and tool
history.

If you see:

```text
current token count exceeds the model maximum context length of 32768 tokens
```

restart the worker with a larger context window:

```bash
./run_dynamo_single_host.sh stop

SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1 \
DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length 65536' \
./run_dynamo_single_host.sh start
```

Run one AgentBench task:

```bash
cd ~/kv_cache_offloading

python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions \
  --model Qwen/Qwen2.5-7B-Instruct \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --prompt-evolution-value-char-limit 1000
```

Verify AgentBench runtime-hint results:

```bash
LATEST_RESULT="$(ls -td agentbench/results/* | head -1)"
echo "$LATEST_RESULT"

grep -R "hint_probe_id\|agent_hints\|worker.decode" -n "$LATEST_RESULT" | head -50
cat "$LATEST_RESULT/runtime_hint_alignment_analysis.md"
cat "$LATEST_RESULT/others/runtime_hint_alignment_summary_table.csv"
cat "$LATEST_RESULT/prompt_evolution_values/index.json"
ls "$LATEST_RESULT/prompt_evolution_values"
```

Success signal: `others/worker_runtime.log` contains
`worker.decode.request_received`, `worker.decode.request_attached`, or
`worker.decode.request_completed` events with AgentBench `agent_hints`, including
`hint_probe_id: "...::hint_probe"`.

--------------------------------------------------------------------------------

## 6. Key Files

- `experiments/lpx_decode_split/profile_one_decode_case.sh`
- `experiments/lpx_decode_split/run_decode_sweep.py`
- `experiments/lpx_decode_split/analyze_nsys_sqlite.py`
- `experiments/lpx_decode_split/estimate_lpx_speedup.py`
- `runtime_instrumentation/prepare_instrumented_dynamo_source.sh`
- `runtime_instrumentation/build_instrumented_dynamo_images.sh`
- `runtime_instrumentation/patches/dynamo_preserve_agent_hints_to_worker.patch`
- `runtime_instrumentation/patches/dynamo_runtime_json_logging.patch`
- `runtime_instrumentation/repair_dynamo_hint_logging_source.py`
- `runtime_instrumentation/repair_dynamo_router_field_rename.py`
- `runtime_instrumentation/repair_dynamo_stream_choice_stop_reason.py`
- `run_dynamo_single_host.sh`
- `run_dynamo_head.sh`
- `run_dynamo_worker.sh`
- `agentbench/deepagents_swebench_single_host.py`
- `agentbench/deepagents_app/src/agent.py`
- `DEBUG.md`
