# AgentBench

`agentbench/` is the single-GPU agent-harness layer for this repo.

Best one-line summary:

`agentbench/` is now a single-GPU explicit multi-step coding-agent harness that can route hard tasks through your Dynamo frontend and leave behind step traces and patch artifacts.

It is for harder agentic workloads than `hintbench/`: take one complicated software-engineering task, break it into explicit steps, send those step-level requests through the local Dynamo frontend, and optionally work inside a real writable repo workspace.

For the upstream-aligned Deep Agents app that now owns the main prompt/model wiring, see:

- [agentbench/deepagents_app/README.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/README.md)
- [agentbench/UPSTREAM_DEEPAGENTS_ADOPTION_MAP.md](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/UPSTREAM_DEEPAGENTS_ADOPTION_MAP.md)

## Prerequisite

### 1. Start the single-host serving stack

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh start
./run_dynamo_single_host.sh status
./run_dynamo_single_host.sh test
```

### 2. Install Python dependencies

If `pip` is not installed:

```bash
sudo dnf install -y python3-pip
```

Check your Python version:

```bash
python3 --version
```

`deepagents` requires Python `3.11+`. If `python3` is older than `3.11`, install and use `python3.11` instead:

```bash
sudo dnf install -y python3.11 python3.11-pip
python3.11 --version
```

Then install the agent stack with the interpreter you will use to run AgentBench:

```bash
cd ~/kv_cache_offloading
python3 -m pip install -r agentbench/requirements.txt
```

or, if you need Python 3.11 explicitly:

```bash
cd ~/kv_cache_offloading
python3.11 -m pip install -r agentbench/requirements.txt
```

## Experiments

### Experiment 1: Sample Task Decomposition Run

Use this first. It proves the single-host agentic path works end to end with no dataset download.

Flow: `sample task -> decomposition plan -> step-level deepagents requests -> final synthesis -> Dynamo frontend -> single local SGLang worker`

Command:

```bash
cd ~/kv_cache_offloading
python3.11 agentbench/deepagents_swebench_single_host.py \
  --json-path agentbench/sample_task.json \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions \
  --model Qwen/Qwen2.5-0.5B
```

Outputs:
- `result.json`
- `plan.json`
- `step_results.json`
- `final_summary.txt`

Notes:
- skips Hugging Face completely
- best for initial validation
- output quality depends heavily on model size

### Experiment 2: SWE-bench Pro Task as Input Source

Use this when you want a real benchmark-style task instead of the local sample.

Flow: `SWE-bench Pro task -> decomposition plan -> step-level deepagents requests -> final synthesis -> Dynamo frontend -> single local SGLang worker`

Command:

```bash
cd ~/kv_cache_offloading
python3.11 agentbench/deepagents_swebench_single_host.py \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions \
  --model Qwen/Qwen2.5-0.5B
```

Outputs:
- `result.json`
- `plan.json`
- `step_results.json`
- `final_summary.txt`

Notes:
- first run may be slow because the dataset split must be downloaded
- uses SWE-bench Pro as a hard task source, not yet as the official evaluator flow

### Experiment 3: Local CSV Task Run

Use this when you want faster repeated runs or your own curated task file.

Flow: `local CSV task -> decomposition plan -> step-level deepagents requests -> final synthesis -> Dynamo frontend -> single local SGLang worker`

Command:

```bash
cd ~/kv_cache_offloading
python3.11 agentbench/deepagents_swebench_single_host.py \
  --csv-path /path/to/swe_bench_pro_full.csv \
  --index 0 \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions \
  --model Qwen/Qwen2.5-0.5B
```

Outputs:
- `result.json`
- `plan.json`
- `step_results.json`
- `final_summary.txt`

Notes:
- CSV must already be prepared in the expected format
- often more convenient than repeated HF downloads

### Experiment 4: Writable Repo Workspace Run

Use this when you want more than prompt-only reasoning and want a `git diff` style artifact after the run.

Flow: `task -> repo workspace clone/copy -> decomposition plan -> step-level deepagents requests -> final synthesis -> Dynamo frontend -> single local SGLang worker -> git diff artifact`

Command:

```bash
cd ~/kv_cache_offloading
python3.11 agentbench/deepagents_swebench_single_host.py \
  --json-path agentbench/sample_task.json \
  --repo-path /path/to/local/repo \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions \
  --model Qwen/Qwen2.5-0.5B
```

Outputs:
- `result.json`
- `plan.json`
- `step_results.json`
- `final_summary.txt`
- `git_status.txt`
- `git_diff_stat.txt`
- `workspace.patch`

Notes:
- the repo is cloned or copied into the run directory as a writable workspace
- closer to SWE-bench-style execution, but still not the full official evaluator flow

## Inspect Results

Inspect the latest run:

```bash
cd ~/kv_cache_offloading
LATEST_RUN=$(ls -td agentbench/results/* | head -n 1)
echo "$LATEST_RUN"
cat "$LATEST_RUN/result.json"
```

Inspect the explicit decomposition flow:

```bash
cat "$LATEST_RUN/plan.json"
cat "$LATEST_RUN/step_results.json"
cat "$LATEST_RUN/final_summary.txt"
```

If the run used a repo workspace, inspect patch artifacts too:

```bash
cat "$LATEST_RUN/git_status.txt"
cat "$LATEST_RUN/git_diff_stat.txt"
cat "$LATEST_RUN/workspace.patch"
```

## Current Limitations

- this is not yet the official SWE-bench Pro scoring pipeline
- it can work against a local or remote repo workspace now, but it does not yet automatically materialize the exact official SWE-bench Pro repo/commit pair from task metadata
- it captures `git diff` style artifacts, but it does not yet gather predictions in the official SWE-bench Pro submission format
- it does not yet run the official SWE-bench Pro evaluator
- the runner now changes hints by phase (`planning`, `step_n_execution`, `synthesis`), but it does not yet do richer adaptive hinting based on runtime observations or tool outcomes
