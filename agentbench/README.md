# AgentBench

## Setup

```bash
sudo dnf install -y python3.11 python3.11-pip git
cd ~/kv_cache_offloading
python3.11 -m pip install -r agentbench/requirements.txt
export HF_TOKEN=your_token_here
```

Shared defaults:
- model: [model_config.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/model_config.sh)

## Runtime

Start:

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh start
./run_dynamo_single_host.sh status
./run_dynamo_single_host.sh test
```

Logs:

```bash
./run_dynamo_single_host.sh logs -f
./run_dynamo_single_host.sh logs-head -f
./run_dynamo_single_host.sh logs-worker -f
```

## Worker Dev Mode

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh stop

WORKER_DEV_MODE=1 \
WORKER_DEV_SOURCE_ROOT=~/kv_cache_offloading/runtime_upstream/dynamo/components/src/dynamo \
WORKER_DEV_BINDINGS_ROOT=~/kv_cache_offloading/runtime_upstream/dynamo/lib/bindings/python/src/dynamo \
DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
./run_dynamo_single_host.sh start
```

## Experiments

```bash
python3.11 agentbench/diagnose_dynamo_tool_calls.py \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions \
  --model Qwen/Qwen2.5-7B-Instruct
```

```bash
cd ~/kv_cache_offloading
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions \
  --model Qwen/Qwen2.5-7B-Instruct \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0
```

```bash
python3.11 agentbench/diagnose_dynamo_response.py \
  --result-json agentbench/results/instance_NodeBB__NodeBB-04998908ba6721d64eba79ae3b65a351dcfbc5b5-vnan_20260514_122127/result.json \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions \
  --model Qwen/Qwen2.5-7B-Instruct
```

## Instrumented Runtime Build

Full build:

```bash
docker system prune -af
docker builder prune -af

cd ~/kv_cache_offloading
rm -rf runtime_upstream/dynamo
./runtime_instrumentation/fetch_dynamo_source.sh
./runtime_instrumentation/apply_runtime_json_logging_patch.sh
./runtime_instrumentation/build_instrumented_dynamo_images.sh

DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

Worker-first build:

```bash
cd ~/kv_cache_offloading
rm -rf runtime_upstream/dynamo
./runtime_instrumentation/fetch_dynamo_source.sh
./runtime_instrumentation/apply_runtime_json_logging_patch.sh
SKIP_FRONTEND=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh

DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

## Artifacts

- `task_lifecycle_trace`
- `measurement_analysis`
- `cache_value_analysis`
- `kv_hierarchy_analysis`
- `runtime_events`
- `runtime_alignment_analysis`
- `checkpoints`
- `result`
