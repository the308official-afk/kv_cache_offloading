

```bash
cd ~/kv_cache_offloading

./agentbench/debug_prompt_evolution_tool_calls.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE=gh200
source runtime_instrumentation/dynamo_machine_profile.sh

export MODEL_NAME='Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8'
export DYN_TOOL_CALL_PARSER=hermes

./run_dynamo_single_host.sh stop || true

FRONTEND_IMAGE="$FRONTEND_IMAGE" \
WORKER_IMAGE="$WORKER_IMAGE" \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru" \
./run_dynamo_single_host.sh start
```

