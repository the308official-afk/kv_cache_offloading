# AgentBench

`agentbench/` is the single-GPU agent-harness layer for this repo.

Current focus:

- run **Deep Agents** against the local single-host Dynamo frontend
- use **SWE-bench Pro** tasks as the input source
- let the harness break one hard task into multiple steps before those model calls hit Dynamo

## Scope

This first integration is intentionally narrow:

- single-host only
- one local Dynamo frontend
- one local SGLang worker
- one SWE-bench Pro task at a time

It is meant to prove:

- Deep Agents can sit on top of your current single-host setup
- SWE-bench Pro gives you harder, more realistic agentic inputs than the current synthetic workloads
- the model calls inside that agent loop can go through your local Dynamo frontend

It does **not yet** do full SWE-bench Pro patch evaluation.

## Flow

`SWE-bench Pro task -> deepagents harness -> ChatOpenAI client -> Dynamo frontend -> single local SGLang worker`

## 1. Start the single-host serving stack

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh start
./run_dynamo_single_host.sh status
./run_dynamo_single_host.sh test
```

## 2. Install Python dependencies

If `pip` is not installed:

```bash
sudo dnf install -y python3-pip
```

Then install the agent stack:

```bash
cd ~/kv_cache_offloading
python3 -m pip install -r agentbench/requirements.txt
```

## 3. Run one SWE-bench Pro task through Deep Agents

Example using the Hugging Face dataset:

```bash
cd ~/kv_cache_offloading
python3 agentbench/deepagents_swebench_single_host.py \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions \
  --model Qwen/Qwen2.5-0.5B
```

Example using a local CSV instead:

```bash
cd ~/kv_cache_offloading
python3 agentbench/deepagents_swebench_single_host.py \
  --csv-path /path/to/swe_bench_pro_full.csv \
  --index 0 \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions \
  --model Qwen/Qwen2.5-0.5B
```

## 4. Inspect the output

Each run writes one JSON bundle under:

- `agentbench/results/`

Inspect the latest one:

```bash
cd ~/kv_cache_offloading
LATEST_RUN=$(ls -td agentbench/results/* | head -n 1)
echo "$LATEST_RUN"
cat "$LATEST_RUN/result.json"
```

## What the runner does

The runner:

1. loads one SWE-bench Pro task
2. formats the task into a richer agent prompt
3. creates a Deep Agents harness
4. points that harness at your local Dynamo frontend through `ChatOpenAI`
5. invokes the agent and saves the result

## Current limitations

- this is not yet the official SWE-bench Pro scoring pipeline
- it does not yet clone and patch the target repo automatically
- it uses SWE-bench Pro as a **hard task source**, not yet as a full end-to-end benchmark evaluator
- per-step dynamic hinting inside the Deep Agents loop is not implemented yet; the current model client uses one static `nvext.agent_hints` payload for the run
