# AgentBench

`agentbench/` is now a single-GPU coding-agent harness where complex tasks from sources like SWE-bench Pro are broken into several steps by Deep Agents before the resulting requests are sent through your Dynamo frontend, with step traces and patch artifacts saved after the run. Use it for harder agentic workloads than `hintbench/`: load one software-engineering task, decompose it, send the step-level requests through the local Dynamo frontend, and inspect the saved artifacts. The active app prefers the cloned upstream Deep Agents source at runtime when present.

## Prerequisite

Start the single-host serving stack:

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh start
./run_dynamo_single_host.sh status
./run_dynamo_single_host.sh test
```

Install Python dependencies. `deepagents` requires Python `3.11+`:

```bash
sudo dnf install -y python3.11 python3.11-pip
cd ~/kv_cache_offloading
python3.11 -m pip install -r agentbench/requirements.txt
```

## Instrumentation

AgentBench now logs:
- the complex task before it enters the Deep Agents harness
- the planning, step-execution, and synthesis requests right before they leave the harness for Dynamo

Control this in [agentbench/constants.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/constants.py):
- `AGENTBENCH_LOG_MODE = "short" | "full" | "off"`
- `AGENTBENCH_LOG_EVERY_N = 10`
- checkpoints are also saved per run in `checkpoints.json`

Checkpoint map:
- `1` task loaded before Deep Agents harness: the normalized complex task as AgentBench received it, before prompt expansion or planning. [agentbench/deepagents_swebench_single_host.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_swebench_single_host.py)
- `3` planning request leaving Deep Agents harness: the first outbound planning prompt plus hints sent to Dynamo so the task can be decomposed. [agentbench/deepagents_app/src/agent.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/src/agent.py)
- `4` step execution request leaving Deep Agents harness: each per-step execution prompt plus hints sent to Dynamo after the plan is created. [agentbench/deepagents_app/src/agent.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/src/agent.py)
- `5` final synthesis request leaving Deep Agents harness: the final summarization prompt plus hints sent to Dynamo after all step results are collected. [agentbench/deepagents_app/src/agent.py](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/deepagents_app/src/agent.py)

## Experiments

### Experiment 1: Upstream Deploy-Coding-Agent Variant Run

Use this as the main upstream-based testbed. It supports both the local sample task and `SWE-bench Pro` while using the cloned upstream `deploy-coding-agent` instructions and skills.

Flow: `task source (sample task or SWE-bench Pro) -> upstream deploy-coding-agent instructions + skills -> decomposition plan -> step-level deepagents requests -> final synthesis -> Dynamo frontend -> single local SGLang worker`

Sample task:

```bash
cd ~/kv_cache_offloading
bash agentbench/run_upstream_deploy_coding_agent_single_host.sh
```

`SWE-bench Pro`:

```bash
cd ~/kv_cache_offloading
bash agentbench/run_upstream_deploy_coding_agent_single_host.sh \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0
```

Stronger-behavior variant:

Use this when you want a cleaner but richer upstream demo on the small model. It keeps the upstream `deploy-coding-agent` instructions and skills, but uses the easier sample task and a `4`-step budget.

```bash
cd ~/kv_cache_offloading
bash agentbench/run_upstream_deploy_coding_agent_stronger_behavior_single_host.sh
```

Outputs:
- `result.json`
- `plan.json`
- `step_results.json`
- `final_summary.txt`

Notes:
- uses the cloned upstream `deploy-coding-agent` instructions and skills
- still runs through your local single-host Dynamo path
- defaults to `agentbench/sample_task.json` when no task source is passed
- this is the best candidate for your core testbed

## Inspect Results

```bash
cd ~/kv_cache_offloading
LATEST_RUN=$(ls -td agentbench/results/* | head -n 1)
echo "$LATEST_RUN"
cat "$LATEST_RUN/result.json"
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
- it does not yet automatically materialize the exact official SWE-bench Pro repo/commit pair from task metadata
- it does not yet gather predictions in the official SWE-bench Pro submission format
- it does not yet run the official SWE-bench Pro evaluator
- hints already vary by phase (`planning`, `step_n_execution`, `synthesis`), but they are not yet adaptively changed from runtime observations or tool outcomes
