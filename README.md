# slide creation prompt
Give me a polished version of these slides attached:
- Dont add/remove any data in any of the slides
- Dont truncate or omit any information in any of the slides, every data (e.g., JSON key and value) MUST be displayed in the slides
- I’m presenting to a technical audience 
- JSON information should look nice and presentable
- Use white background except when rendering JSON data
- Give me page numbers for easier debugging

First give me some recommendations on polishing the slides before I ask you to proceed 

# kv_cache_offloading

Reproducible AgentBench + Dynamo + SGLang harness for proving:

```text
AgentBench -> Dynamo native frontend/preprocessor -> SGLang worker
```

Success means an AgentBench SWE-bench result contains worker `[RUNTIME_JSON]`
events with `agent_hints`, `hint_probe_id`, and `request_context` in
`worker.decode.*`.

## EC2 Setup

Use an Ampere-or-newer NVIDIA GPU instance with a 200-300 GB root disk.

```bash
sudo dnf install -y python3.11 python3.11-pip git

cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh rootdisk
newgrp docker
./aws/check_ec2_rootdisk_worker_ready.sh

python3.11 -m pip install -r agentbench/requirements.txt
export HF_TOKEN=your_token_here
```

From a local checkout, upload with:

```bash
./aws/upload.sh
```

## Deep Agents Dependency

`agentbench/requirements.txt` installs Deep Agents in editable mode from:

```text
agentbench/upstream/deepagents/libs/deepagents
```

On a fresh machine, create that checkout before installing requirements:

```bash
cd ~/kv_cache_offloading

mkdir -p agentbench/upstream

if [ ! -f agentbench/upstream/deepagents/libs/deepagents/pyproject.toml ]; then
  git clone https://github.com/langchain-ai/deepagents.git agentbench/upstream/deepagents
  git -C agentbench/upstream/deepagents checkout 2cf7e25dbb40e783d9d4d545c29e595800bf314f
fi

python3.11 -m pip install -r agentbench/requirements.txt
```

Run the install from the repo root, not from inside `agentbench/`, because the
editable path is relative to `~/kv_cache_offloading`.

## Preflight Check

Run this before building or starting Dynamo on a new machine, especially GH200.

```bash
cd ~/kv_cache_offloading

echo "host arch: $(uname -m)"
python3.11 --version
docker version --format 'docker {{.Server.Version}}'
df -h /
docker system df

test -n "${HF_TOKEN:-}" && echo "HF_TOKEN is set" || echo "HF_TOKEN is missing"

docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

ss -ltnp | grep ':8000' || true
```

If moving from `g5.xlarge` to GH200, do not reuse the G5-built Dynamo images
unless the GH200 host is also `x86_64`. G5 builds are `linux/amd64`; many GH200
hosts are `aarch64`/`arm64`, so rebuild Dynamo natively on the GH200.

After building, verify image architecture:

```bash
docker image inspect local/dynamo-frontend:runtime-json-logs --format '{{.Architecture}}'
docker image inspect local/dynamo-sglang:runtime-json-logs --format '{{.Architecture}}'
```

Expected values:

```text
x86_64 host -> amd64 images
aarch64 host -> arm64 images
```

## Smoke Test Without Rebuild

Use the published Dynamo image first when you only want to prove Docker, GPU,
model loading, and the basic OpenAI-compatible request path.

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

This does not prove `agent_hints` reach worker logs. That proof requires the
instrumented build below.

If startup fails because etcd is not healthy, start a clean `dynamo-etcd`
container manually:

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

Then rerun the smoke-test start command.

## Patch And Build Dynamo

```bash
cd ~/kv_cache_offloading
rm -rf runtime_upstream/dynamo
./runtime_instrumentation/prepare_instrumented_dynamo_source.sh

LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```

The prep script applies runtime JSON logging, preserves `nvext.agent_hints` and
`nvext.request_context`, adds worker hint proof fields, and repairs known
upstream drift (`overlap_score_credit`, stale `choice.stop_reason`).

Built images:

```text
local/dynamo-frontend:runtime-json-logs
local/dynamo-sglang:runtime-json-logs
```

## Start Runtime

```bash
cd ~/kv_cache_offloading
chmod +x run_dynamo_head.sh run_dynamo_single_host.sh run_dynamo_worker.sh

./run_dynamo_single_host.sh stop

DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

Check model registration:

```bash
./run_dynamo_single_host.sh status
curl -fsS http://127.0.0.1:8000/v1/models
```

If the model is not listed yet:

```bash
docker logs -f dynamo-sglang-worker
docker logs -f --tail 200 dynamo-sglang-frontend
curl -fsS http://127.0.0.1:8000/v1/models
```

## Run AgentBench

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

## Verify

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
`hint_probe_id: "...::hint_probe"`. Per-stage value snapshots are written under
`prompt_evolution_values/`. New result directories use simple readable names
such as `agentbench-nodebb_20260519_140124`.

## Key Files

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
