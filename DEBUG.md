# Debug Guide

## Frontend Did Not Become Healthy

If startup fails with:

```text
Frontend did not become healthy on port 8000.
```

collect the container state and logs:

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh status

docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Command}}'

docker logs --tail 200 dynamo-frontend
docker logs --tail 100 dynamo-etcd
docker logs --tail 100 dynamo-nats
```

The most important output is:

```bash
docker logs --tail 200 dynamo-frontend
```

If it contains:

```text
unknown shorthand flag: 'l' in -lc
```

then the frontend image entrypoint is still `/epp` instead of `/bin/bash`.
Make sure the machine has the latest `run_dynamo_head.sh`, which starts the
frontend container with:

```bash
--entrypoint /bin/bash
```

Check the local script:

```bash
grep -n -- '--entrypoint /bin/bash' run_dynamo_head.sh
```

If there is no match, upload the latest repo files and retry.

## Port 8000 Already In Use

Check whether another process already owns port 8000:

```bash
ss -ltnp | grep ':8000' || true
```

If something is listening on port 8000, either stop that process/container or
start Dynamo on another port:

```bash
./run_dynamo_single_host.sh stop

DYNAMO_FRONTEND_PORT=8001 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
./run_dynamo_single_host.sh start
```

Then verify:

```bash
curl -fsS http://127.0.0.1:8001/v1/models
```

## etcd Is Not Running

Dynamo uses etcd like a small registry. The worker registers itself there, and
the frontend uses it to discover workers. If etcd is down, the frontend may not
become healthy.

Check etcd:

```bash
docker ps -a --filter name=dynamo-etcd \
  --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Command}}'

docker logs --tail 200 dynamo-etcd
```

Restart only etcd:

```bash
docker restart dynamo-etcd
```

Try a clean stack restart:

```bash
./run_dynamo_single_host.sh stop
./run_dynamo_single_host.sh start
```

If etcd still exits, clear its saved state and start fresh:

```bash
./run_dynamo_single_host.sh stop

rm -rf ~/kv_cache_offloading/dynamo_head_state/etcd-data

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
./run_dynamo_single_host.sh start
```

Also check whether etcd's port is already in use:

```bash
ss -ltnp | grep ':2379' || true
```

If something is listening on `2379`, stop that process/container before
retrying.

Temporary manual etcd start, if you only need to bring the registry up for a
single-host smoke test:

```bash
curl -s http://127.0.0.1:2379/health || true

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

Prefer the container name `dynamo-etcd`. The repo scripts look for that name in
`status`, `logs`, and `stop`. A manually started container named only `etcd` can
work on port `2379`, but the scripts will not manage it cleanly and it can later
cause port conflicts.

## Worker Or Model Not Ready

If the frontend becomes healthy but the model never appears in `/v1/models`,
watch the worker logs:

```bash
docker logs -f --tail 200 dynamo-sglang-worker
```

Then check model registration again:

```bash
curl -fsS http://127.0.0.1:8000/v1/models
```

If using a non-default frontend port, replace `8000` with that port.

## First Simple Request

Once etcd, nats, frontend, and worker are up, first confirm the model is
registered:

```bash
curl -fsS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/models
```

Then send a tiny chat completion:

```bash
curl -sS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
      {"role": "user", "content": "Reply with exactly: ok"}
    ],
    "max_tokens": 8
  }'
echo
```

Expected response: JSON with a `choices[0].message.content` value similar to
`ok`.

You can also use the built-in script test:

```bash
DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT:-8000}" ./run_dynamo_single_host.sh test
```

If this run uses port `8001`, either export it once:

```bash
export DYNAMO_FRONTEND_PORT=8001
```

or replace the URLs with `http://127.0.0.1:8001/...`.

## Model Context Length Exceeded

If AgentBench fails with an error like:

```text
current token count exceeds the model maximum context length of 32768 tokens
```

the Dynamo/SGLang path is working, but the request plus agent/tool context is
too large for the worker's configured context window.

Ways to fix it without changing Dynamo/SGLang context length:

```bash
# Try a different, smaller SWE-bench task.
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model Qwen/Qwen2.5-7B-Instruct \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 1
```

Other non-restart options:

- use a smaller task index or specific smaller `--instance-id`
- use the direct smoke-test curl instead of AgentBench when you only need to
  prove the runtime works
- reduce prompt/tool-history size in AgentBench code if you need this exact
  task to fit a 32k context window

Lowering generation output tokens only helps when the request is barely over the
limit. It will not fix a prompt/tool transcript that already exceeds 32k before
generation.

For a basic runtime smoke test, use the tiny direct request instead of
AgentBench:

```bash
curl -sS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
      {"role": "user", "content": "Reply with exactly: ok"}
    ],
    "max_tokens": 8
  }'
echo
```

For AgentBench, restart the worker with a larger SGLang context length if the
GPU has enough memory:

```bash
./run_dynamo_single_host.sh stop

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length 65536' \
./run_dynamo_single_host.sh start
```

If you are using a non-default frontend port, include it in the restart and in
the AgentBench URL:

```bash
export DYNAMO_FRONTEND_PORT=8001
```

Then rerun AgentBench with:

```bash
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model Qwen/Qwen2.5-7B-Instruct \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0
```

If the larger context causes GPU OOM, pick a smaller SWE-bench task index or use
a larger-memory machine. Lowering `max_tokens` only helps when the prompt is
near the limit; it does not help if the prompt/tool transcript alone already
exceeds the context window.

If SGLang rejects the larger context with:

```text
User-specified context_length (65536) is greater than the derived context_length (32768)
```

then the model/runtime derived a 32k safe limit. Preferred fixes:

- keep the default 32k context and use a smaller AgentBench task
- use a model/runtime configuration that naturally supports the needed context

Override only if you accept the risk of incorrect outputs or CUDA errors:

```bash
./run_dynamo_single_host.sh stop

SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length 65536' \
./run_dynamo_single_host.sh start
```

If using instrumented local images, include `DYN_RUNTIME_JSON_LOGS=1`,
`FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs`, and
`WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs` in the restart command.

## GPU Or Docker Problems

Verify the host and Docker can see the GPU:

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

If `nvidia-smi` works on the host but fails inside Docker, reinstall or
reconfigure NVIDIA Container Toolkit.

## Deep Agents Editable Install Missing

If dependency installation fails with an error like:

```text
... is not a valid editable requirement
```

then either `agentbench/upstream/deepagents` is missing, or the install command
was run from the wrong directory.

The repo expects Deep Agents to exist here:

```text
agentbench/upstream/deepagents/libs/deepagents
```

That nested `libs/deepagents` directory is the Python package. Do not install
editable mode from `agentbench/upstream/deepagents` itself.

From the repo root, run:

```bash
cd ~/kv_cache_offloading

mkdir -p agentbench/upstream

if [ ! -f agentbench/upstream/deepagents/libs/deepagents/pyproject.toml ]; then
  git clone https://github.com/langchain-ai/deepagents.git agentbench/upstream/deepagents
  git -C agentbench/upstream/deepagents checkout 2cf7e25dbb40e783d9d4d545c29e595800bf314f
fi

python3.11 -m pip install -r agentbench/requirements.txt
```

Direct install equivalent:

```bash
cd ~/kv_cache_offloading
python3.11 -m pip install -e ./agentbench/upstream/deepagents/libs/deepagents
```

Quick verification:

```bash
python3.11 - <<'PY'
import deepagents
print(deepagents.__file__)
PY
```

## Deep Agents Installed But Import Fails

If AgentBench fails with:

```text
ModuleNotFoundError: No module named 'deepagents'
```

and this command prints `WARNING: Package(s) not found: deepagents`:

```bash
python3.11 -m pip show deepagents
```

then Deep Agents is not installed in the `python3.11` environment currently
running AgentBench. Install it with `python3.11 -m pip`, not plain `pip`.

first make sure you are using the same Python interpreter for install and run:

```bash
cd ~/kv_cache_offloading

which python3.11
python3.11 -m pip --version
python3.11 -m pip show deepagents || true
```

Check that the local Deep Agents checkout exists:

```bash
test -f agentbench/upstream/deepagents/libs/deepagents/pyproject.toml && echo "Deep Agents checkout exists" || echo "Deep Agents checkout missing"
```

If the checkout is missing:

```bash
mkdir -p agentbench/upstream
git clone https://github.com/langchain-ai/deepagents.git agentbench/upstream/deepagents
git -C agentbench/upstream/deepagents checkout 2cf7e25dbb40e783d9d4d545c29e595800bf314f
```

If the checkout exists but `python3.11 -m pip show deepagents` says
`WARNING: Package(s) not found: deepagents`, the source is present but not
installed into the `python3.11` environment yet.

Reinstall with the exact interpreter used to run AgentBench:

```bash
python3.11 -m pip install --upgrade pip
python3.11 -m pip install -e ./agentbench/upstream/deepagents/libs/deepagents
python3.11 -m pip install -r agentbench/requirements.txt
```

Verify the import:

```bash
python3.11 - <<'PY'
import sys
import deepagents
print(sys.executable)
print(deepagents.__file__)
PY
```

If you are using a virtual environment, activate it before both install and run,
or call the venv Python directly:

```bash
source .venv/bin/activate
python -m pip install -r agentbench/requirements.txt
python agentbench/deepagents_swebench_single_host.py --help
```

Temporary fallback if editable install is still not visible:

```bash
cd ~/kv_cache_offloading
export PYTHONPATH="$PWD/agentbench/upstream/deepagents/libs/deepagents:${PYTHONPATH:-}"
python3.11 - <<'PY'
import deepagents
print(deepagents.__file__)
PY
```

## Disk Pressure

Check disk usage:

```bash
df -h /
docker system df
```

For a smoke test, keep at least 30-50 GB free. For a Dynamo rebuild, keep at
least 80-120 GB free.

## Image Architecture

On GH200, verify host architecture:

```bash
uname -m
```

If it prints `aarch64`, rebuild Dynamo images on that machine. Images built on
`g5.xlarge` are usually `linux/amd64` and should not be reused on ARM64 GH200.

After building local images:

```bash
docker image inspect local/dynamo-frontend:runtime-json-logs --format '{{.Architecture}}'
docker image inspect local/dynamo-sglang:runtime-json-logs --format '{{.Architecture}}'
```

Expected:

```text
x86_64 host -> amd64 images
aarch64 host -> arm64 images
```

## Clean Restart

Use this to retry a non-instrumented smoke test:

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh stop

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
./run_dynamo_single_host.sh start
```

Verify:

```bash
curl -fsS http://127.0.0.1:8000/v1/models
./run_dynamo_single_host.sh test
```

=====
docker run -d
--name etcd
--network host
quay.io/coreos/etcd:v3.5.14
etcd
--listen-client-urls http://0.0.0.0:2379
--advertise-client-urls http://127.0.0.1:2379 Then verify:

curl -s http://127.0.0.1:2379/health
docker run -d \
  --name etcd \
  --network host \
  quay.io/coreos/etcd:v3.5.14 \
  etcd \
  --listen-client-urls http://0.0.0.0:2379 \
  --advertise-client-urls http://127.0.0.1:2379
Then verify:

curl -s http://127.0.0.1:2379/health
# Expected: {"health":"true","reason":""}
