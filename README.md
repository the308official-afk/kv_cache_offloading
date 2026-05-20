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
