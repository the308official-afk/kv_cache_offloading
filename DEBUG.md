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

## GPU Or Docker Problems

Verify the host and Docker can see the GPU:

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

If `nvidia-smi` works on the host but fails inside Docker, reinstall or
reconfigure NVIDIA Container Toolkit.

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