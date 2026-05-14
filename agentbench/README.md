# AgentBench

## Setup

```bash
sudo dnf install -y python3.11 python3.11-pip git
cd ~/kv_cache_offloading
python3.11 -m pip install -r agentbench/requirements.txt
export HF_TOKEN=your_token_here
```

Shared model default:
- [model_config.sh](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/model_config.sh)

## Single-Host Runtime

Stock single-host start:

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

## Python-Only Worker Dev Mode

Use this for worker-side Python changes without rebuilding the worker image:

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh stop

WORKER_DEV_MODE=1 \
WORKER_DEV_SOURCE_ROOT=~/kv_cache_offloading/runtime_upstream/dynamo/components/src/dynamo \
WORKER_DEV_BINDINGS_ROOT=~/kv_cache_offloading/runtime_upstream/dynamo/lib/bindings/python/src/dynamo \
DYN_RUNTIME_JSON_LOGS=1 \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
./run_dynamo_single_host.sh start
```

On EC2 or other remote Linux hosts, use `~/kv_cache_offloading/...` paths, not `/Users/...`.

## Instrumented Runtime

Full instrumented frontend + worker:

```bash
docker system prune -af
docker builder prune -af

cd ~/kv_cache_offloading
rm -rf runtime_upstream/dynamo
./runtime_instrumentation/fetch_dynamo_source.sh
./runtime_instrumentation/apply_runtime_json_logging_patch.sh
./runtime_instrumentation/build_instrumented_dynamo_images.sh

DYN_RUNTIME_JSON_LOGS=1 \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

Worker-first instrumented build:

```bash
cd ~/kv_cache_offloading
rm -rf runtime_upstream/dynamo
./runtime_instrumentation/fetch_dynamo_source.sh
./runtime_instrumentation/apply_runtime_json_logging_patch.sh
SKIP_FRONTEND=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh

DYN_RUNTIME_JSON_LOGS=1 \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start
```

## Experiments

Sample task:

```bash
cd ~/kv_cache_offloading
bash agentbench/run_upstream_deploy_coding_agent_single_host.sh
```

`SWE-bench Pro`:

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh stop
./run_dynamo_single_host.sh status

WORKER_DEV_MODE=1 \
WORKER_DEV_SOURCE_ROOT=~/kv_cache_offloading/runtime_upstream/dynamo/components/src/dynamo \
WORKER_DEV_BINDINGS_ROOT=~/kv_cache_offloading/runtime_upstream/dynamo/lib/bindings/python/src/dynamo \
DYN_RUNTIME_JSON_LOGS=1 \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
./run_dynamo_single_host.sh start

./run_dynamo_single_host.sh logs -f
./run_dynamo_single_host.sh logs-head -f
./run_dynamo_single_host.sh logs-worker -f

PYTHON_BIN=python3.11 \
bash agentbench/run_upstream_deploy_coding_agent_single_host.sh \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0
```

Stronger-behavior sample:

```bash
cd ~/kv_cache_offloading
bash agentbench/run_upstream_deploy_coding_agent_stronger_behavior_single_host.sh
```

## Artifacts

- `task_lifecycle_trace`: full task trace
- `measurement_analysis`: performance summary
- `cache_value_analysis`: cache value summary
- `kv_hierarchy_analysis`: cache placement summary
- `runtime_events`: runtime observations
- `runtime_alignment_analysis`: recommendation vs runtime comparison
- `checkpoints`: pipeline checkpoints
- `result`: full run record
