# AgentBench Experiment Runs

This guide runs one SWE-bench Pro task through the local AgentBench/Deep Agents
harness via Dynamo and SGLang. Use it to collect prompt-evolution artifacts,
runtime-hint evidence, cache/token stats, and task-completion evidence.

The core path is:

```text
SWE-bench Pro -> AgentBench runner -> prompt builder -> Deep Agents
-> Dynamo frontend -> SGLang worker -> result artifacts
```

## 1. Choose Model

Use `MODEL_KIND` to switch between the general Instruct model and the
code-specialized Coder model. Keep the same selected model for both Dynamo
startup and the AgentBench run command.

```bash
cd ~/kv_cache_offloading

MODEL_KIND="${MODEL_KIND:-coder}"  # coder or instruct
case "$MODEL_KIND" in
  coder)
    MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct'
    ;;
  instruct)
    MODEL_NAME='Qwen/Qwen2.5-7B-Instruct'
    ;;
  *)
    echo "MODEL_KIND must be coder or instruct" >&2
    exit 1
    ;;
esac

echo "Using model: $MODEL_NAME"
```

## 2. Start Dynamo/SGLang

Experiment artifacts can be collected with either non-instrumented or
instrumented Dynamo/SGLang.

- Use **non-instrumented** Dynamo/SGLang when the goal is only the prompt
  evolution story and AgentBench-side measurements.
- Use **instrumented** Dynamo/SGLang when the run also needs worker-side
  `agent_hints`, `hint_probe_id`, and `worker.decode.*` proof.

### 2.1 Non-Instrumented Run

Use this faster path when the only goal is to collect:

```text
prompt_evolution_report.*
prompt_evolution_values/*.json
others/measurements.*
others/cache_value_analysis.*
others/run_summary_table.csv
```

Start the published default Dynamo/SGLang runtime:

```bash
./run_dynamo_single_host.sh stop

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
./run_dynamo_single_host.sh start
```

Do not set `FRONTEND_IMAGE` or `WORKER_IMAGE` for the non-instrumented path.
Leaving them unset uses the published default image instead of local
instrumented images.

Verify the model is available:

```bash
curl -fsS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/models
```

If this run hits the 32k context limit, restart with the larger SGLang context
override:

```bash
./run_dynamo_single_host.sh stop

SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length 65536' \
./run_dynamo_single_host.sh start
```

### 2.2 Instrumented Run

Use this path when the experiment should also include strong runtime-hint
evidence from worker logs.

If the SWE-bench prompt exceeds the default 32k context window, restart with the
larger SGLang context override:

```bash
./run_dynamo_single_host.sh stop

SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1 \
DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length 65536' \
./run_dynamo_single_host.sh start
```

See logs

```bash
docker logs -f dynamo-sglang-worker
```

Verify the model is available:

```bash
curl -fsS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/models
```

Verify the long-context override reached the worker container:

```bash
docker inspect dynamo-sglang-worker \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | \
  grep SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN
```

Expected:

```text
SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1
```

## 3. Prepare AgentBench Environment

Before running the task on a new machine, complete
[README_AGENTBENCH_ENVIRONMENT.md](README_AGENTBENCH_ENVIRONMENT.md).

That setup verifies:

- the harness writes `workspace.patch` at the report root
- Node is visible from the shell used to launch AgentBench
- NodeBB npm dependencies are installed
- Redis-backed NodeBB test dependencies are available
- `nodebb-test-redis` and `config.json` exist
- selected NodeBB tests get past environment setup errors

Do not rerun AgentBench while the manual preflight still fails with:

```text
node: command not found
Cannot find module '...'
ENOENT ... config.json
```

## 4. Run One AgentBench Task

### 4.1 Baseline Single-Loop Run

Use this first when you want a complete run that actually attempts the task.
This mode gives Deep Agents one continuous tool loop instead of splitting the
work into separate planning/execution/review calls.

```bash
cd ~/kv_cache_offloading

AGENTBENCH_WORKFLOW_MODE=baseline \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --prompt-evolution-value-char-limit 1000
```

Check if the run succeeded in executing the task assigned it

```bash
LATEST_RESULT="$(ls -td agentbench/results/* | head -1)"
echo "$LATEST_RESULT"

wc -c "$LATEST_RESULT/workspace.patch"
cat "$LATEST_RESULT/others/git_status.txt"
cat "$LATEST_RESULT/others/git_diff_stat.txt"
```

### 4.2 Phased Run

Use this when the goal is phase-level stats: planning, execution,
patch-generation, and review. It is better for runtime analysis, but if the
planning response is empty or malformed, later phases may inherit bad context.

```bash
cd ~/kv_cache_offloading

AGENTBENCH_WORKFLOW_MODE=phased \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --prompt-evolution-value-char-limit 1000
```

The `--prompt-evolution-value-char-limit 1000` option keeps each captured
before/after value readable by truncating long strings with an ellipsis.

## 5. Find The Latest Result

```bash
LATEST_RESULT="$(ls -td agentbench/results/* | head -1)"
echo "$LATEST_RESULT"
```

## 6. Check Task Completion

Use this before reading the richer reports. A complete task attempt should
usually leave a non-empty patch or git diff.

```bash
cat "$LATEST_RESULT/others/git_status.txt"
cat "$LATEST_RESULT/others/git_diff_stat.txt"
wc -c "$LATEST_RESULT/workspace.patch"
```

Useful signal:

```text
workspace.patch size > 0
git_status.txt or git_diff_stat.txt is non-empty
model output includes edit/write/execute tool activity, not only ls/read_file
```

If baseline edits files but phased does not, debug the phased orchestration. If
both baseline and phased runs fail to edit files, try the other model by
rerunning from **1. Choose Model** with `MODEL_KIND=instruct` or
`MODEL_KIND=coder`.

If the latest run still writes `others/workspace.patch`, that run used an older
copy of the harness or was created before the report-layout update. New runs
should write:

```text
agentbench/results/<run_id>/workspace.patch
```

## 7. Inspect Prompt Evolution Artifacts

```bash
cat "$LATEST_RESULT/prompt_evolution_values/index.json"
ls "$LATEST_RESULT/prompt_evolution_values"
cat "$LATEST_RESULT/prompt_evolution_report.md"
```

Main prompt-evolution artifacts:

```text
prompt_evolution_report.json
prompt_evolution_report.md
prompt_evolution_report.csv
prompt_evolution_values/index.json
prompt_evolution_values/*.json
```

The per-stage value files under `prompt_evolution_values/` contain:

```json
{
  "stage": "...",
  "diff_summary": {},
  "before": {},
  "after": {}
}
```

## 8. Inspect Measurement And Cache Stats

```bash
cat "$LATEST_RESULT/others/run_summary_table.csv"
cat "$LATEST_RESULT/others/measurement_summary_table.csv"
cat "$LATEST_RESULT/others/cache_value_summary_table.csv"
cat "$LATEST_RESULT/others/kv_hierarchy_summary_table.csv"
```

For phase-level runs, inspect:

```bash
cat "$LATEST_RESULT/step_results.json"
cat "$LATEST_RESULT/stage_lifecycle_table.csv"
```

## 9. Verify Runtime-Hint Evidence

```bash
grep -R "hint_probe_id\|agent_hints\|worker.decode" -n "$LATEST_RESULT" | head -50
cat "$LATEST_RESULT/runtime_hint_alignment_analysis.md"
cat "$LATEST_RESULT/others/runtime_hint_alignment_summary_table.csv"
```

Success signal: `others/worker_runtime.log` contains
`worker.decode.request_received`, `worker.decode.request_attached`, or
`worker.decode.request_completed` events with AgentBench `agent_hints`, including
`hint_probe_id: "...::hint_probe"`.

This worker-side success signal requires the instrumented runtime. A
non-instrumented run can still produce the prompt-evolution files, but it will
not prove that hints reached the SGLang worker logs.

## 10. Expected Prompt Evolution Stages

Typical stages include:

- `task_input`
- `formatted_prompt`
- `final_model_request`
- `system_context`
- `tool_runtime_context`
- `runtime_preprocessing`
- `model_behavior`
