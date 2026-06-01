# Core Pipeline: Upstream vs Custom

This document describes the basic non-instrumentation pipeline:

```text
SWE-bench Pro -> AgentBench runner -> prompt builder -> Deep Agents
-> Dynamo frontend -> SGLang worker
```

## Out Of The Box

The following components are upstream/off-the-shelf:

- **SWE-bench Pro dataset**: loaded from Hugging Face with `datasets`.
- **Deep Agents framework**: cloned from upstream and installed from
  `upstream/deepagents/libs/deepagents`.
- **Deep Agents deploy-coding-agent example content**: reused when running with
  `--app-variant upstream_deploy_coding_agent`.
- **Dynamo frontend/runtime**: OpenAI-compatible frontend and request routing.
- **SGLang worker**: model serving backend that runs the model.
- **LangChain/OpenAI client surface**: `ChatOpenAI` is used as the client
  interface to the local Dynamo `/v1` endpoint.

## Custom In This Repo

The following components are project-specific implementation:

- **AgentBench runner**:
  `agentbench/deepagents_swebench_single_host.py`.
  This is not an external AgentBench package. It is the local harness that loads
  one SWE-bench task, prepares the workspace, starts one run, calls the Deep
  Agents app, and writes result artifacts.
- **Prompt builder**:
  `agentbench/deepagents_app/src/prompts.py`.
  This turns raw SWE-bench task fields into the model-facing coding task prompt.
- **Deep Agents adapter app**:
  `agentbench/deepagents_app/src/agent.py`.
  This wires upstream Deep Agents to the local Dynamo frontend, selects the
  instruction surface, builds the filesystem/shell backend, and attaches
  request metadata.
- **Dynamo/SGLang launch glue**:
  `run_dynamo_single_host.sh`, `run_dynamo_head.sh`, and
  `run_dynamo_worker.sh`.
  These start etcd, NATS, the Dynamo frontend, and the SGLang worker in the
  shape needed by this project.
- **Run artifacts and reports**:
  result directories, measurements, prompt-evolution reports, runtime alignment
  summaries, and helper diagnostics are custom.

## Summary

The model-serving stack is mostly upstream Dynamo + SGLang. The agent framework
is upstream Deep Agents. The dataset is upstream SWE-bench Pro. The custom part
is the glue: loading one task, building the prompt, adapting Deep Agents to the
local Dynamo endpoint, launching the local runtime, and saving the benchmark
artifacts.

## How Much Of `agentbench/` Is Custom?

The `agentbench/` directory is now reserved for the local harness, adapters,
diagnostics, and sample tasks. Generated benchmark outputs live under
`experiments/raw/agentbench/results/`. Upstream source
checkouts live under `upstream/`:

- `upstream/deepagents/`: cloned upstream Deep Agents repo.
- `upstream/dynamo/`: cloned upstream Dynamo repo.
- `upstream/sglang/`: extracted SGLang source overlay.
- `experiments/raw/agentbench/results/`: generated experiment output, not source logic.

The core `agentbench/` pipeline is custom project code.

Core custom pieces include:

- `agentbench/deepagents_swebench_single_host.py`
- `agentbench/deepagents_app/`
- `agentbench/deepagents_app/src/prompts.py`
- `agentbench/deepagents_app/src/agent.py`
- `agentbench/log_utils.py`
- `agentbench/constants.py`
- `agentbench/run_*.sh`
- `agentbench/diagnose_*.py`
- `agentbench/sample_task*.json`

The core `agentbench/` pipeline is custom. It uses upstream SWE-bench Pro,
upstream Deep Agents, Dynamo, SGLang, and LangChain/OpenAI client APIs, but the
benchmark harness, prompt construction, runtime wiring, artifact capture, and
analysis/reporting are project-specific.
