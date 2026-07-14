

```bash
cd ~/kv_cache_offloading

./agentbench/debug_prompt_evolution_tool_calls.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

```bash
cd ~/kv_cache_offloading

export MODEL_NAME='Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8'
export DYN_TOOL_CALL_PARSER=hermes

./run_dynamo_single_host.sh stop || true

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
./run_dynamo_single_host.sh start

./agentbench/debug_prompt_evolution_tool_calls.sh \
  "$MODEL_NAME"

```

