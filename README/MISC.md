# Misc Debug Notes

## Experiment 6: Deep Agents Recursion Debug

Use this when Experiment 6 hits `GraphRecursionError` and you want to inspect
why the agent is taking many graph steps instead of hiding the issue with a cap.

This run intentionally disables model-only planning:

- `AGENTBENCH_MODEL_ONLY_PHASES=""`
- `AGENTBENCH_TRACE_AGENT_STREAM=1`

That means planning runs through the real Deep Agents graph, and every graph
step is written into `stage_lifecycle_trace_raw.json`.

```bash
cd ~/kv_cache_offloading

export AGENTBENCH_EXECUTION_LOOP=1
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=1
export AGENTBENCH_PRINT_CHECKPOINTS=1
export DYN_TOOL_CALL_PARSER=qwen3_coder
export DYN_REASONING_PARSER=qwen3
export AGENTBENCH_DEEPAGENTS_SOURCE=upstream
export AGENTBENCH_FORCE_TOOL_CHOICE=auto
export AGENTBENCH_DISABLE_GENERAL_PURPOSE_SUBAGENT=1
export AGENTBENCH_BATCH_CONTINUE_ON_ERROR=0
export PROMPT_EVOLUTION_REQUIRE_TOOL_LOOP=1
export PROMPT_EVOLUTION_TOOL_LOOP_CASE=edit-validate

# Important: disable model-only planning so this run exposes the real loop.
export AGENTBENCH_MODEL_ONLY_PHASES=""
export AGENTBENCH_TRACE_AGENT_STREAM=1
export AGENTBENCH_TRACE_AGENT_STREAM_MODE=values
export AGENTBENCH_AGENT_RECURSION_LIMIT=80

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
PROMPT_EVOLUTION_BATCH_START_INDEX=0 \
PROMPT_EVOLUTION_BATCH_END_INDEX=1 \
PROMPT_EVOLUTION_VALUE_CHAR_LIMIT=200000 \
./agentbench/run_prompt_evolution_batch_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

After the run fails or finishes, inspect the stream trace:

```bash
cd ~/kv_cache_offloading

RUN_DIR="$(ls -td experiments/raw/agentbench/results/agentbench-* | head -1)"
export RUN_DIR

python3 - <<'PY'
import json
import os
from pathlib import Path

run_dir = Path(os.environ["RUN_DIR"])
p = run_dir / "others" / "stage_lifecycle_trace_raw.json"
events = json.loads(p.read_text())

for e in events:
    if e.get("event_kind") != "agent_stream_step":
        continue
    s = e.get("chunk_summary", {})
    msgs = s.get("last_messages", [])
    last = msgs[-1] if msgs else {}
    print(
        e["stage"],
        "step=", e.get("chunk_index"),
        "messages=", s.get("message_count"),
        "last_type=", last.get("type"),
        "tools=", last.get("tool_call_names"),
        "preview=", (last.get("content_preview") or "")[:160].replace("\n", " "),
    )

for e in events:
    if e.get("event_kind") == "agent_stream_error":
        print("\nERROR:", e.get("error_type"), e.get("error"))
        print("last:", e.get("last_chunk_summary"))
PY
```

How to read the output:

- If you see the same tool or same message pattern repeating, it is probably a
  real loop.
- If you see many different file reads, edits, and validation commands, the task
  is genuinely long and needs a better phase budget.
- If planning loops before useful tool work, the issue is in the planning graph
  path, not in the execution phase.
- If execution loops after planning succeeds, the issue is in tool use,
  validation, or stop-condition handling.

